"""Offline tests: predetermined model calls, real PydanticAI tool execution."""
import json
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

import pam_tools
from pam_agent_pydantic import (
    agent, get_asset_details, investigate_asset, investigate_with_evidence,
    search_documentation, search_past_tickets,
)
from pam_evidence import DISCLAIMER, collect_evidence, summarize_result


@pytest.fixture(autouse=True)
def block_provider_requests():
    """FunctionModel is allowed; accidental real provider requests are forbidden."""
    with models.override_allow_model_requests(False):
        yield


def test_get_existing_asset():
    expected = next(asset for asset in json.loads(
        (Path(__file__).resolve().parents[1] / 'data/pam_assets.json').read_text()
    ) if asset['asset_id'] == 'LNX-001')
    actual = get_asset_details(' lnx-001 ')
    assert actual == expected
    assert actual['source_type'] == 'synthetic'
    actual['platform'] = 'changed by caller'
    assert get_asset_details('LNX-001')['platform'] == 'Linux'


def test_get_unknown_asset():
    assert get_asset_details('unknown-999') == {
        'error': 'asset_not_found',
        'asset_id': 'UNKNOWN-999',
        'message': 'No synthetic asset record exists. Request approved inventory details.',
    }


@pytest.mark.parametrize('asset_id', ['', '   ', '../file', 'LNX-001' + ' ' * 40, 123])
def test_reject_invalid_asset_id(asset_id):
    with pytest.raises(ValueError):
        get_asset_details(asset_id)


@pytest.mark.parametrize('asset_id', ['LNX-001', 'UNKNOWN-999'])
def test_framework_registers_and_executes_asset_tool(asset_id):
    def model_function(messages, info):
        # Keep the original asset assertions while requiring all three tools.
        tools = {tool.name: tool for tool in info.function_tools}
        assert set(tools) == {'get_asset_details', 'search_documentation', 'search_past_tickets'}
        schema = tools['get_asset_details'].parameters_json_schema
        assert schema['properties']['asset_id']['type'] == 'string'
        assert schema['required'] == ['asset_id']
        returns = [part for message in messages for part in message.parts
                   if isinstance(part, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=[ToolCallPart(
                'get_asset_details', {'asset_id': asset_id}, tool_call_id='asset_call',
            )])
        returned = returns[-1]
        assert returned.tool_name == 'get_asset_details'
        assert returned.tool_call_id == 'asset_call'
        assert returned.content == get_asset_details(asset_id)
        # Final prose is scripted, so it does not test an LLM's grounding behavior.
        return ModelResponse(parts=[TextPart('Offline tool execution complete.')])

    with agent.override(model=FunctionModel(model_function)):
        result = investigate_asset(f'Look up {asset_id}.')
    parts = [part for message in result.all_messages() for part in message.parts]
    assert len([part for part in parts if isinstance(part, ToolCallPart)]) == 1
    returned = next(part for part in parts if isinstance(part, ToolReturnPart))
    assert returned.content['asset_id'] == asset_id
    if asset_id == 'UNKNOWN-999':
        assert returned.content['error'] == 'asset_not_found'
        assert 'platform' not in returned.content
    else:
        assert returned.content['last_rotation_status'] == 'failed'
    assert result.usage.requests == 2
    assert result.usage.tool_calls == 1


def test_usage_limits_stop_repeated_tool_calls():
    def repeating_model(messages, info):
        return ModelResponse(parts=[ToolCallPart(
            'get_asset_details', {'asset_id': 'LNX-001'},
            tool_call_id=f'call_{len(messages)}',
        )])

    with agent.override(model=FunctionModel(repeating_model)):
        with pytest.raises(UsageLimitExceeded, match='request_limit of 6'):
            investigate_asset('Keep looking up LNX-001.')


# Phase 2: scripted model messages, actual framework orchestration and retrieval.
@pytest.mark.parametrize('requests,expected_ids', [
    ([('search_documentation', {'query': 'Linux privileged account onboarding'})], {'ONB-001'}),
    ([('get_asset_details', {'asset_id': 'APP-001'}),
      ('search_documentation', {'query': 'custom web connector login element page changes'})],
     {'APP-001', 'WEB-001'}),
    ([('get_asset_details', {'asset_id': 'LNX-001'}),
      ('search_past_tickets', {'query': 'Linux password rotation failed onboarding'}),
      ('search_documentation', {'query': 'Linux rotation failed onboarding'})],
     {'LNX-001', 'TKT-001', 'ROT-001'}),
    ([('search_past_tickets', {'query': 'Linux password rotation failed onboarding'}),
      ('get_asset_details', {'asset_id': 'LNX-001'})], {'LNX-001', 'TKT-001'}),
], ids=['onboarding', 'web-connector', 'rotation-all-tools', 'rotation-tickets-first'])
def test_framework_executes_real_retrieval(requests, expected_ids):
    calls = [ToolCallPart(name, arguments, tool_call_id=f'evidence_{i}')
             for i, (name, arguments) in enumerate(requests)]

    def model_function(messages, info):
        tools = {tool.name: tool for tool in info.function_tools}
        assert set(tools) == {'get_asset_details', 'search_documentation', 'search_past_tickets'}
        for name in ['search_documentation', 'search_past_tickets']:
            schema = tools[name].parameters_json_schema
            assert schema['properties']['query']['type'] == 'string'
            assert schema['required'] == ['query']
        returned = {part.tool_call_id: part for message in messages for part in message.parts
                    if isinstance(part, ToolReturnPart)}
        if not returned:
            return ModelResponse(parts=calls)
        # Map by call ID, never by completion order of independent tools.
        assert set(returned) == {part.tool_call_id for part in calls}
        ids = set()
        for requested in calls:
            actual = returned[requested.tool_call_id]
            assert actual.tool_name == requested.tool_name
            expected = getattr(pam_tools, requested.tool_name)(**requested.args_as_dict())
            assert actual.content == expected
            records = actual.content if isinstance(actual.content, list) else [actual.content]
            assert all(record['source_type'] == 'synthetic' for record in records)
            ids.update(record.get('id') or record.get('asset_id') or record.get('ticket_id')
                       for record in records)
        assert expected_ids <= ids
        return ModelResponse(parts=[TextPart('Scripted completion; no grounding claim.')])

    with agent.override(model=FunctionModel(model_function)):
        result = investigate_asset('Investigate this synthetic PAM scenario.')
    assert result.usage.requests == 2
    assert result.usage.tool_calls == len(calls)


@pytest.mark.parametrize('name,queries', [
    ('search_documentation', ['Linux privileged account onboarding',
                            'Linux password rotation failed onboarding',
                            'custom web connector login element page changes',
                            'zzzxxyyqq', ' Linux onboarding ']),
    ('search_past_tickets', ['Linux password rotation failed onboarding',
                           'custom web connector login element', 'zzzxxyyqq']),
    ('get_asset_details', ['lnx-001', ' LNX-001 ', 'APP-001', 'UNKNOWN-999']),
])
def test_retrieval_matches_original_notebook(agent_namespace, name, queries):
    shared = getattr(pam_tools, name)
    original = agent_namespace[name]
    # Exact records and ranking, including metadata and empty-search behavior.
    for query in queries:
        assert shared(query) == original(query)
    # Compare every source record through an identifying lookup/search too.
    records_key, query_key = {
        'search_documentation': ('documents', 'title'),
        'search_past_tickets': ('past_tickets', 'issue_summary'),
        'get_asset_details': ('assets', 'asset_id'),
    }[name]
    for record in agent_namespace[records_key]:
        assert shared(record[query_key]) == original(record[query_key])


@pytest.mark.parametrize('function,query,limit', [
    (search_documentation, 'Linux onboarding password rotation web connector', 5),
    (search_past_tickets, 'Linux onboarding password rotation web connector', 4),
])
def test_search_results_are_independent_and_bounded(function, query, limit):
    first = function(query)
    assert 0 < len(first) <= limit
    original = function(query)
    first[0]['source_type'] = 'mutated by caller'
    first.clear()
    assert function(query) == original
    assert function('zzzxxyyqq') == []


@pytest.mark.parametrize('function', [search_documentation, search_past_tickets])
@pytest.mark.parametrize('query', ['', '   ', 123, None, 'x' * 2001])
def test_search_query_validation(function, query, agent_namespace):
    # The shared implementation and preserved notebook reject the same inputs.
    for implementation in [function, agent_namespace[function.__name__]]:
        with pytest.raises(ValueError):
            implementation(query)


@pytest.mark.parametrize('question', ['', '   ', 123, None, 'x' * 8001])
def test_question_validation_precedes_model_execution(question):
    def unexpected_model(messages, info):
        pytest.fail('Invalid question must be rejected before model execution')
    with agent.override(model=FunctionModel(unexpected_model)):
        with pytest.raises(ValueError, match='question must be'):
            investigate_asset(question)


def test_question_boundary_and_trimming():
    question = ' ' + 'x' * 7998 + ' '
    def model_function(messages, info):
        assert messages[0].parts[0].content == question.strip()
        return ModelResponse(parts=[TextPart('Scripted boundary check.')])
    with agent.override(model=FunctionModel(model_function)):
        investigate_asset(question)


@pytest.mark.parametrize('name,arguments', [
    ('search_documentation', {'query': ' '}),
    ('search_past_tickets', {'query': 'x' * 2001}),
    ('get_asset_details', {'asset_id': '../file'}),
])
def test_framework_rejects_invalid_tool_values(name, arguments):
    def invalid_model(messages, info):
        return ModelResponse(parts=[ToolCallPart(name, arguments, tool_call_id='invalid')])
    with agent.override(model=FunctionModel(invalid_model)):
        # Python value validation fails fast; this prototype does not convert
        # ValueError to model retry messages. PydanticAI handles schema errors.
        with pytest.raises(ValueError):
            investigate_asset('Validate a synthetic tool request.')


def test_tool_execution_budget_blocks_oversized_batch():
    def oversized_batch(messages, info):
        return ModelResponse(parts=[ToolCallPart(
            'get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id=f'asset_{i}',
        ) for i in range(9)])
    with agent.override(model=FunctionModel(oversized_batch)):
        with pytest.raises(UsageLimitExceeded, match='tool_calls_limit of 8'):
            investigate_asset('Look up LNX-001 repeatedly.')


# Phase 3: use actual framework histories; final prose is still predetermined.
@pytest.fixture
def evidence_run():
    def run(requests, answer):
        def model_function(messages, info):
            returned = [part for message in messages for part in message.parts
                        if isinstance(part, ToolReturnPart)]
            if not returned:
                parts = [ToolCallPart(name, arguments, tool_call_id=f'actual_call_{i}')
                         for i, (name, arguments) in enumerate(requests)]
                return ModelResponse(parts=parts, usage=RequestUsage(input_tokens=17, output_tokens=9))
            return ModelResponse(parts=[TextPart(answer)],
                                 usage=RequestUsage(input_tokens=31, output_tokens=13))
        with agent.override(model=FunctionModel(model_function)):
            raw = investigate_asset('PRIVATE_TEST_MARKER: investigate this synthetic case.')
        return raw, summarize_result(raw)
    return run


def test_evidence_valid_documentation_citation(evidence_run):
    raw, summary = evidence_run(
        [('search_documentation', {'query': 'Linux privileged account onboarding'})],
        DISCLAIMER + ' Compare approved identity records [ONB-001].',
    )
    assert 'ONB-001' in summary['evidence_ids']
    assert summary['citation_issues'] == []
    assert summary['citation_validation_passed'] is True
    assert summary['trace'][0]['tool'] == 'search_documentation'
    assert summary['trace'][0]['returned_ids'] == summary['evidence_ids']


@pytest.mark.parametrize('reverse', [False, True], ids=['asset-first', 'tickets-first'])
def test_evidence_multiple_sources_and_repeated_calls(evidence_run, reverse):
    requests = [
        ('get_asset_details', {'asset_id': 'LNX-001'}),
        ('search_past_tickets', {'query': 'Linux rotation failed onboarding'}),
        ('search_documentation', {'query': 'Linux rotation failed onboarding'}),
        ('get_asset_details', {'asset_id': 'LNX-001'}),
    ]
    if reverse:
        requests.reverse()
    _, summary = evidence_run(requests, DISCLAIMER +
        ' Failed rotation is recorded [LNX-001]. Historical mismatch is a comparison '
        '[TKT-001], not proof of the current cause. Collect sanitized errors [ROT-001].')
    assert {'LNX-001', 'TKT-001', 'ROT-001'} <= set(summary['evidence_ids'])
    assert len(summary['evidence_ids']) == len(set(summary['evidence_ids']))
    assert summary['citation_validation_passed'] is True
    assert len(summary['trace']) == 4
    assert sum(event['returned_ids'] == ['LNX-001'] for event in summary['trace']) == 2
    assert [event['sequence'] for event in summary['trace']] == [1, 2, 3, 4]


@pytest.mark.parametrize('answer,expected_issue', [
    (DISCLAIMER + ' Invented guidance [ROT-999].', 'Unretrieved citations'),
    (DISCLAIMER + ' Guidance without citations.', 'no bracketed citations'),
    ('Inventory records failed rotation [LNX-001].', 'disclaimer'),
    (DISCLAIMER + ' Invented source [SECRET-123].', 'format/category'),
    (DISCLAIMER + ' Wrong-case source [lnx-001].', 'format/category'),
    (DISCLAIMER + ' Wrong-length source [LNX-0001].', 'format/category'),
])
def test_evidence_reports_invalid_answers(evidence_run, answer, expected_issue):
    raw, summary = evidence_run([('get_asset_details', {'asset_id': 'LNX-001'})], answer)
    assert summary['citation_validation_passed'] is False
    assert any(expected_issue in issue for issue in summary['citation_issues'])
    assert raw.usage.requests == 2  # Detection never makes a revision request.
    assert 'ROT-999' not in summary['evidence_ids']
    assert 'SECRET-123' not in summary['evidence_ids']


@pytest.mark.parametrize('omitted,label', [
    ('[LNX-001]', 'current asset'), ('[TKT-001]', 'historical ticket'),
    ('[ROT-001]', 'documentation'),
])
def test_each_retrieved_kind_requires_valid_citation(evidence_run, omitted, label):
    requests = [('get_asset_details', {'asset_id': 'LNX-001'}),
                ('search_past_tickets', {'query': 'Linux rotation failed onboarding'}),
                ('search_documentation', {'query': 'Linux rotation failed onboarding'})]
    answer = DISCLAIMER + ' Findings [LNX-001]. Comparison [TKT-001]. Check [ROT-001].'
    _, summary = evidence_run(requests, answer.replace(omitted, ''))
    assert summary['citation_validation_passed'] is False
    assert any(label in issue for issue in summary['citation_issues'])


@pytest.mark.parametrize('cite_missing', [False, True])
def test_evidence_unknown_asset_is_not_a_source(evidence_run, cite_missing):
    answer = DISCLAIMER + ' No synthetic inventory record exists for UNKNOWN-999.'
    if cite_missing:
        answer += ' [UNKNOWN-999]'
    _, summary = evidence_run([('get_asset_details', {'asset_id': 'UNKNOWN-999'})], answer)
    assert summary['evidence_ids'] == []
    assert summary['trace'][0]['returned_ids'] == []
    assert summary['trace'][0]['error'] == 'asset_not_found'
    assert summary['citation_validation_passed'] is (not cite_missing)


def test_evidence_empty_search_allows_uncited_missing_evidence(evidence_run):
    _, summary = evidence_run([('search_documentation', {'query': 'zzzxxyyqq'})],
                             DISCLAIMER + ' No supporting records; insufficient evidence.')
    assert summary['evidence_ids'] == []
    assert summary['trace'][0]['error'] is None
    assert summary['citation_validation_passed'] is True


def test_trace_excludes_private_content(evidence_run):
    raw, summary = evidence_run(
        [('search_documentation', {'query': 'PRIVATE_TEST_MARKER Linux onboarding'})],
        DISCLAIMER + ' PRIVATE_TEST_MARKER: compare identity [ONB-001].',
    )
    # The private marker really exists in raw messages and the preserved answer.
    assert 'PRIVATE_TEST_MARKER' in str(raw.all_messages())
    assert 'PRIVATE_TEST_MARKER' in summary['answer']
    trace_text = json.dumps(summary['trace'])
    assert 'PRIVATE_TEST_MARKER' not in trace_text
    assert 'Linux onboarding' not in trace_text
    assert 'content' not in trace_text and 'arguments' not in trace_text
    assert all(set(event) == {'sequence', 'tool', 'tool_call_id', 'returned_ids', 'error'}
               for event in summary['trace'])
    assert 'search_documentation' in trace_text and 'ONB-001' in trace_text


def test_usage_is_derived_from_actual_framework_result(evidence_run):
    raw, summary = evidence_run([('get_asset_details', {'asset_id': 'LNX-001'})],
                             DISCLAIMER + ' Failed rotation [LNX-001]; cause unknown.')
    assert summary['usage'] == {
        'model_requests': raw.usage.requests,
        'tool_calls': raw.usage.tool_calls,
        'input_tokens': raw.usage.input_tokens,
        'output_tokens': raw.usage.output_tokens,
        'total_tokens': raw.usage.total_tokens,
    }
    assert summary['usage']['input_tokens'] == 48
    assert summary['usage']['output_tokens'] == 22


def test_high_level_entry_point_runs_once_without_revision():
    def model_function(messages, info):
        # An invalid answer must be preserved and reported, without a retry.
        assert len(messages) == 1
        return ModelResponse(parts=[TextPart(DISCLAIMER + ' Unsupported [ROT-999].')])
    with agent.override(model=FunctionModel(model_function)):
        summary = investigate_with_evidence('Investigate a synthetic case.')
    assert summary['usage']['model_requests'] == 1
    assert summary['citation_validation_passed'] is False
    assert summary['evidence_ids'] == []
    assert summary['trace'] == []


def test_history_links_returns_by_id_not_position():
    # Construct real framework message classes with deliberately reordered results.
    messages = [ModelResponse(parts=[
        ToolCallPart('get_asset_details', {}, tool_call_id='PRIVATE_TEST_MARKER'),
        ToolCallPart('search_documentation', {}, tool_call_id='docs'),
    ]), ModelRequest(parts=[
        ToolReturnPart('search_documentation', [{'id': 'ROT-001'}], tool_call_id='docs'),
        ToolReturnPart('get_asset_details', {'asset_id': 'LNX-001'},
                       tool_call_id='PRIVATE_TEST_MARKER'),
    ])]
    ids, trace = collect_evidence(messages)
    assert ids == ['LNX-001', 'ROT-001']
    assert trace[0]['tool_call_id'] == 'call_2'
    assert trace[1]['tool_call_id'] == 'call_1'
    assert 'PRIVATE_TEST_MARKER' not in json.dumps(trace)


@pytest.mark.parametrize('mode,expected_error', [
    ('unmatched', 'unmatched_tool_return'), ('mismatch', 'tool_name_mismatch'),
    ('failed', 'tool_failed'), ('retry', 'tool_retry'), ('error', 'tool_error'),
])
def test_failed_or_unlinked_returns_never_supply_evidence(mode, expected_error):
    parts = [] if mode == 'unmatched' else [ToolCallPart(
        'get_asset_details', {}, tool_call_id='call')]
    returned = ToolReturnPart(
        'search_documentation' if mode == 'mismatch' else 'get_asset_details',
        {'asset_id': 'LNX-001', **({'error': 'PRIVATE_TEST_MARKER'} if mode == 'error' else {})},
        tool_call_id='call',
        outcome={'failed': 'failed', 'retry': 'retried'}.get(mode, 'success'),
    )
    ids, trace = collect_evidence([ModelResponse(parts=parts), ModelRequest(parts=[returned])])
    assert ids == []
    assert trace[0]['error'] == expected_error
    assert 'PRIVATE_TEST_MARKER' not in json.dumps(trace)


def test_high_level_summary_tracks_multiple_model_turns():
    def model_function(messages, info):
        returned = [part for message in messages for part in message.parts
                    if isinstance(part, ToolReturnPart)]
        if len(returned) < 2:
            return ModelResponse(parts=[ToolCallPart(
                'get_asset_details', {'asset_id': 'LNX-001'},
                tool_call_id=f'asset_{len(returned)}',
            )])
        return ModelResponse(parts=[TextPart(DISCLAIMER +
            ' Inventory records failed rotation [LNX-001]; cause unknown.')])
    with agent.override(model=FunctionModel(model_function)):
        summary = investigate_with_evidence('Look up LNX-001 for this synthetic case.')
    assert summary['evidence_ids'] == ['LNX-001']
    assert len(summary['trace']) == 2
    assert all(event['returned_ids'] == ['LNX-001'] for event in summary['trace'])
    assert summary['usage']['model_requests'] == 3
    assert summary['usage']['tool_calls'] == 2
    assert summary['citation_validation_passed'] is True


def test_ambiguous_call_ids_do_not_supply_evidence():
    messages = [ModelResponse(parts=[
        ToolCallPart('get_asset_details', {}, tool_call_id='same'),
        ToolCallPart('get_asset_details', {}, tool_call_id='same'),
    ]), ModelRequest(parts=[
        ToolReturnPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='same'),
    ])]
    ids, trace = collect_evidence(messages)
    assert ids == []
    assert trace[0]['error'] == 'duplicate_call_id'
    assert all(event['error'] is not None for event in trace)
