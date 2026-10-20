"""Offline regression tests load notebook definitions, never the live API cell.

Scripted model responses test protocol handling only; they are not live LLM evidence.
"""
import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_notebook():
    namespace = {}
    notebook = json.loads((ROOT / 'notebooks/03-agent.ipynb').read_text())
    with contextlib.redirect_stdout(io.StringIO()):
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code' and set(cell['metadata'].get('tags', [])) & {'setup', 'implementation'}:
                exec(compile(''.join(cell['source']), '03-agent.ipynb', 'exec'), namespace)
    return namespace


def call(name, arguments, call_id='call_1'):
    return SimpleNamespace(type='function_call', name=name,
                           arguments=arguments, call_id=call_id)


def response(*items, text=''):
    return SimpleNamespace(output=list(items), output_text=text)


class ScriptedClient:
    def __init__(self, responses):
        self.script = iter(responses)
        self.requests = []
        self.responses = self

    def create(self, **kwargs):
        # Snapshot input because the loop extends its local list after this call.
        self.requests.append({**kwargs, 'input': list(kwargs['input'])})
        return next(self.script)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_notebook()

    def run_script(self, client, **kwargs):
        return self.ns['run_agent']('Investigate PAM rotation', client, trace=False, **kwargs)

    def test_tools_retrieve_real_records(self):
        docs = self.ns['search_documentation']('Linux onboarding')
        self.assertTrue(docs)
        self.assertTrue({d['id'] for d in docs} <= {d['id'] for d in self.ns['documents']})
        tickets = self.ns['search_past_tickets']('Linux password rotation onboarding')
        self.assertIn('TKT-001', {t['ticket_id'] for t in tickets})
        asset = self.ns['get_asset_details']('lnx-001')
        self.assertEqual(asset['asset_id'], 'LNX-001')
        asset['platform'] = 'changed'
        self.assertEqual(self.ns['get_asset_details']('LNX-001')['platform'], 'Linux')

    def test_empty_evidence_and_missing_asset(self):
        self.assertEqual(self.ns['search_documentation']('zzzxxyyqq'), [])
        self.assertEqual(self.ns['search_past_tickets']('zzzxxyyqq'), [])
        missing = self.ns['get_asset_details']('UNKNOWN-999')
        self.assertEqual(missing['error'], 'asset_not_found')
        self.assertEqual(self.ns['returned_ids'](missing), [])

    def test_invalid_or_unknown_tools(self):
        execute = self.ns['execute_tool']
        self.assertEqual(execute('delete_asset', '{}')[0]['error'], 'unknown_tool')
        for args in ['bad json', '[]', '{}', '{"query": 1}', '{"query": ""}',
                     '{"query": "Linux", "extra": true}', json.dumps({'query': 'x' * 2001})]:
            with self.subTest(args=args[:40]):
                self.assertEqual(execute('search_documentation', args)[0]['error'], 'invalid_arguments')
        self.assertEqual(execute('get_asset_details', '{"asset_id":"../file"}')[0]['error'], 'invalid_arguments')

    def test_multiple_calls_and_conversation_linkage(self):
        reasoning = SimpleNamespace(type='reasoning')
        first = call('get_asset_details', '{"asset_id":"LNX-001"}', 'asset_call')
        second = call('search_documentation', '{"query":"Linux rotation"}', 'docs_call')
        final = 'Synthetic guidance [LNX-001] [ROT-001]'
        client = ScriptedClient([response(reasoning, first, second), response(text=final)])
        result = self.run_script(client)
        self.assertEqual(result['answer'], final)
        self.assertEqual([e['tool'] for e in result['trace']], ['get_asset_details', 'search_documentation'])
        history = client.requests[1]['input']
        self.assertIs(history[1], reasoning)
        outputs = [item for item in history if isinstance(item, dict) and item.get('type') == 'function_call_output']
        self.assertEqual([item['call_id'] for item in outputs], ['asset_call', 'docs_call'])
        self.assertEqual(json.loads(outputs[0]['output'])['asset_id'], 'LNX-001')
        self.assertFalse(client.requests[0]['store'])
        self.assertEqual(len(client.requests[0]['tools']), 3)

    def test_unknown_asset_sent_back_without_evidence_id(self):
        client = ScriptedClient([
            response(call('get_asset_details', '{"asset_id":"UNKNOWN-999"}')),
            response(text='No synthetic asset record exists; insufficient evidence.'),
        ])
        result = self.run_script(client)
        self.assertEqual(result['evidence_ids'], [])
        self.assertEqual(result['trace'][0]['error'], 'asset_not_found')
        self.assertIn('asset_not_found', client.requests[1]['input'][-1]['output'])

    def test_validation_error_can_be_corrected(self):
        client = ScriptedClient([
            response(call('search_documentation', '{"query":3}', 'invalid')),
            response(call('search_documentation', '{"query":"Linux"}', 'valid')),
            response(text='Synthetic guidance [ONB-001]'),
        ])
        result = self.run_script(client)
        self.assertEqual(result['trace'][0]['error'], 'invalid_arguments')
        self.assertTrue(result['trace'][1]['returned_ids'])

    def test_loop_and_call_limits_and_empty_response(self):
        client = ScriptedClient([response(call('get_asset_details', '{"asset_id":"LNX-001"}'))])
        with self.assertRaisesRegex(RuntimeError, 'without a final answer'):
            self.run_script(client, max_iterations=1)
        with self.assertRaisesRegex(RuntimeError, 'Too many tool calls'):
            self.run_script(ScriptedClient([response(*[call('x', '{}') for _ in range(9)])]))
        with self.assertRaisesRegex(RuntimeError, 'neither a tool call'):
            self.run_script(ScriptedClient([response()]))

    def test_api_error_is_not_replaced_with_answer(self):
        class FailingClient:
            @property
            def responses(self):
                raise ConnectionError('Test transport failure')
        with self.assertRaises(ConnectionError):
            self.run_script(FailingClient())

    def test_citation_membership_rejects_unretrieved_and_unknown_ids(self):
        check = self.ns['check_citations']
        result = {'answer': 'Synthetic guidance [ROT-001]', 'evidence_ids': ['ROT-001']}
        self.assertEqual(check(result), {'ROT-001'})
        for answer in ['Synthetic guidance [ROT-999]',
                       'Synthetic guidance [UNKNOWN-999]', 'Synthetic guidance without citations']:
            with self.subTest(answer=answer), self.assertRaises(AssertionError):
                check({**result, 'answer': answer})

    def test_trace_does_not_print_raw_query(self):
        client = ScriptedClient([
            response(call('search_documentation', '{"query":"PRIVATE_MARKER Linux"}')),
            response(text='Synthetic guidance [ONB-001]'),
        ])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.ns['run_agent']('question', client)
        self.assertNotIn('PRIVATE_MARKER', output.getvalue())
        self.assertNotIn('PRIVATE_MARKER', json.dumps(result['trace']))

    def test_optional_citations_still_validate_membership(self):
        check = self.ns['check_citations']
        result = {'answer': 'Synthetic training: no record exists.', 'evidence_ids': []}
        self.assertEqual(check(result, require_citations=False), set())
        with self.assertRaises(AssertionError):
            check({**result, 'answer': 'Synthetic training [UNKNOWN-999]'}, require_citations=False)

    def test_uncited_draft_gets_one_revision_without_tools(self):
        client = ScriptedClient([
            response(call('get_asset_details', '{"asset_id":"LNX-001"}')),
            response(text='A dependency must be causing this failure.'),
            response(text='Synthetic guidance: rotation failed; cause unknown [LNX-001].'),
        ])
        result = self.run_script(client)
        self.assertEqual(result['revision_count'], 1)
        self.assertEqual(result['citation_issues'], [])
        self.assertEqual(len(client.requests), 3)
        self.assertNotIn('tools', client.requests[-1])
        prompt = client.requests[-1]['input'][-1]['content']
        self.assertIn('Remove unsupported speculation', prompt)
        self.assertIn('If documentation was not retrieved', prompt)
        self.assertIn('ONLY the tool results already in this conversation', prompt)

    def test_bad_revision_is_reported_without_another_retry(self):
        client = ScriptedClient([
            response(call('get_asset_details', '{"asset_id":"LNX-001"}')),
            response(text='Synthetic guidance [LNX-999]'),
            response(text='Synthetic guidance still without citations'),
        ])
        result = self.run_script(client)
        self.assertEqual(result['revision_count'], 1)
        self.assertTrue(result['citation_issues'])
        self.assertEqual(len(client.requests), 3)
        with self.assertRaises(AssertionError):
            self.ns['check_citations'](result)

    def test_missing_asset_does_not_trigger_citation_revision(self):
        client = ScriptedClient([
            response(call('get_asset_details', '{"asset_id":"UNKNOWN-999"}')),
            response(text='Synthetic training: no record exists for UNKNOWN-999; insufficient evidence.'),
        ])
        result = self.run_script(client)
        self.assertEqual(result['revision_count'], 0)
        self.assertEqual(result['citation_issues'], [])
        self.ns['check_scenario']('C', result)

    def test_missing_evidence_kind_citation_is_detected(self):
        issues = self.ns['citation_issues']('Synthetic guidance [TKT-001]', ['LNX-001', 'TKT-001'])
        self.assertTrue(any('asset' in issue for issue in issues))

    def test_empty_revision_is_an_error(self):
        client = ScriptedClient([
            response(call('get_asset_details', '{"asset_id":"LNX-001"}')),
            response(text='Uncited draft'), response(),
        ])
        with self.assertRaisesRegex(RuntimeError, 'revision returned no final answer'):
            self.run_script(client)

    def test_scenario_c_accepts_honest_uncited_missing_evidence(self):
        result = {
            'answer': 'Synthetic training: no record exists for UNKNOWN-999; insufficient evidence to determine the cause.',
            'evidence_ids': [],
            'trace': [{'tool': 'get_asset_details', 'error': 'asset_not_found'}],
        }
        self.ns['check_scenario']('C', result)
        self.ns['check_scenario']('C', {**result, 'answer':
            'Synthetic training: UNKNOWN-999 does not correspond to any existing synthetic asset record; no evidence is available.'})
        with self.assertRaises(AssertionError):
            self.ns['check_scenario']('C', {**result, 'trace': []})
        with self.assertRaises(AssertionError):
            self.ns['check_scenario']('C', {**result, 'answer':
                'Synthetic training: UNKNOWN-999 has a confirmed policy mismatch.'})

    def test_scenario_a_requires_documentation_but_allows_extra_tools(self):
        result = {
            'answer': 'Synthetic training guidance [ONB-004]',
            'evidence_ids': ['ONB-004'],
            'trace': [{'tool': 'search_past_tickets'}, {'tool': 'search_documentation'}],
        }
        self.ns['check_scenario']('A', result)
        for answer in ['Synthetic training ONB-004', 'Synthetic training [TKT-001]']:
            with self.subTest(answer=answer), self.assertRaises(AssertionError):
                self.ns['check_scenario']('A', {**result, 'answer': answer, 'evidence_ids': ['ONB-004', 'TKT-001']})

    def test_scenario_b_requires_asset_and_tickets_without_documentation(self):
        result = {
            'answer': 'Synthetic training [LNX-001] [TKT-001]. Missing evidence: sanitized errors; cause unknown.',
            'evidence_ids': ['LNX-001', 'TKT-001'],
            'trace': [{'tool': name} for name in
                      ['search_past_tickets', 'get_asset_details']],
        }
        self.ns['check_scenario']('B', result)
        for citation in ['[LNX-001]', '[TKT-001]']:
            with self.subTest(citation=citation), self.assertRaises(AssertionError):
                self.ns['check_scenario']('B', {**result, 'answer': result['answer'].replace(citation, '')})
        for tool in ['get_asset_details', 'search_past_tickets']:
            with self.subTest(tool=tool), self.assertRaises(AssertionError):
                self.ns['check_scenario']('B', {**result, 'trace': [e for e in result['trace'] if e['tool'] != tool]})
        for answer in ['Synthetic training LNX-001 TKT-001. Missing evidence.',
                       result['answer'] + ' [ROT-999]',
                       'Synthetic training [LNX-001] [TKT-001].']:
            with self.subTest(answer=answer), self.assertRaises(AssertionError):
                self.ns['check_scenario']('B', {**result, 'answer': answer})

    def test_smoke_runner_continues_after_assertion_and_api_failure(self):
        valid = {
            'answer': 'Synthetic training: no record exists for UNKNOWN-999.',
            'evidence_ids': [],
            'trace': [{'tool': 'get_asset_details', 'error': 'asset_not_found'}],
        }
        invalid = {'answer': 'Synthetic training without citations', 'evidence_ids': [], 'trace': []}
        with patch.dict(self.ns, {'run_agent': unittest.mock.Mock(
                side_effect=[invalid, ConnectionError('test transport failure'), valid])}):
            with contextlib.redirect_stdout(io.StringIO()):
                results, reports = self.ns['run_smoke_tests'](object())
        self.assertEqual([reports[label]['status'] for label in 'ABC'], ['FAIL', 'ERROR', 'PASS'])
        self.assertEqual(results['A'], invalid)
        self.assertEqual(results['C'], valid)


if __name__ == '__main__':
    unittest.main()
