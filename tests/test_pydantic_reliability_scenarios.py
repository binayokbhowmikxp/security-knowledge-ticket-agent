"""Offline B/D/E contracts: scripted model messages, real framework and retrieval."""
import json
import re

import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

import pam_tools
from pam_agent_pydantic import agent, investigate_with_evidence
from pam_diagnostics import failed_run_diagnostics, retry_activity
from pam_evidence import DISCLAIMER, answer_validation_checks, citation_issues, documentation_issues


@pytest.fixture(autouse=True)
def block_provider_requests():
    with models.override_allow_model_requests(False):
        yield


@pytest.fixture
def scripted_model():
    def make(*turns):
        script, requests = iter(turns), []
        def respond(messages, info):
            requests.append(list(messages))
            # Check actual results and call linkage without relying on return order.
            calls = {part.tool_call_id: part for message in messages for part in message.parts
                     if isinstance(part, ToolCallPart)}
            for message in messages:
                for part in message.parts:
                    if isinstance(part, ToolReturnPart) and part.outcome == 'success':
                        requested = calls[part.tool_call_id]
                        assert part.tool_name == requested.tool_name
                        assert part.content == getattr(pam_tools, part.tool_name)(**requested.args_as_dict())
            return ModelResponse(parts=next(script), usage=RequestUsage(input_tokens=10, output_tokens=5))
        return FunctionModel(respond), requests
    return make


def output(text):
    return [TextPart(text)]


def rotation_calls():
    return [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='asset'),
            ToolCallPart('search_past_tickets', {'query': 'Linux rotation failed onboarding'}, tool_call_id='tickets')]


ROTATION_QUERY = ('Password rotation failed for a privileged account on LNX-001 shortly after onboarding. '
                  'Investigate the issue and check whether similar incidents were reported previously.')
ROTATION_FACTS = (DISCLAIMER + ' Inventory records failed rotation [LNX-001]. Historical configuration '
                  'difference and successful validation [TKT-001] do not diagnose this incident. '
                  'The current failure has not been diagnosed. ')


@pytest.mark.parametrize('mode', ['valid-citations', 'basic-evidence', 'remove-procedure', 'retrieve-docs'])
def test_scenario_b_accepts_evidence_or_bounded_documentation_correction(scripted_model, mode):
    accepted = ROTATION_FACTS
    turns = [rotation_calls()]
    if mode in {'remove-procedure', 'retrieve-docs'}:
        turns.append(output(ROTATION_FACTS + ' Review batch job dependencies.'))
    if mode == 'retrieve-docs':
        turns.append([ToolCallPart('search_documentation', {'query': 'password rotation dependencies'}, tool_call_id='docs')])
        accepted += 'Review documented dependencies [ROT-005].'
    elif mode in {'basic-evidence', 'remove-procedure'}:
        accepted += ('Documentation evidence is unavailable. Please provide missing sanitized errors, '
                     'timestamps and approved diagnostic evidence.')
    turns.append(output(accepted))
    model, requests = scripted_model(*turns)
    with capture_run_messages() as captured, agent.override(model=model):
        summary = investigate_with_evidence(ROTATION_QUERY)
    assert summary['answer'] == accepted
    assert summary['citation_validation_passed'] is True and summary['citation_issues'] == []
    assert {'LNX-001', 'TKT-001'} <= set(summary['evidence_ids'])
    assert '[LNX-001]' in accepted and '[TKT-001]' in accepted
    assert documentation_issues(accepted, captured) == []
    assert retry_activity(captured)['output_validation_retry_observed'] is (mode in {'remove-procedure', 'retrieve-docs'})
    expected_requests = {'valid-citations': 2, 'basic-evidence': 2, 'remove-procedure': 3, 'retrieve-docs': 4}[mode]
    assert summary['usage']['model_requests'] == len(requests) == expected_requests
    assert summary['usage']['tool_calls'] == (3 if mode == 'retrieve-docs' else 2)


@pytest.mark.parametrize('draft,code', [
    (DISCLAIMER + ' PRIVATE_REASON_MARKER no citations.', 'missing_citation'),
    (ROTATION_FACTS + ' Unsupported [ROT-999].', 'unretrieved_citation'),
    (ROTATION_FACTS + ' Bad link [TKT-001](TKT-001).', 'invalid_citation_format'),
    (ROTATION_FACTS.removeprefix(DISCLAIMER), 'missing_disclaimer'),
    (ROTATION_FACTS + ' Review batch job dependencies.', 'unsupported_documentation_guidance'),
])
def test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes(scripted_model, draft, code):
    terminal = ROTATION_FACTS + ' Review batch job dependencies.'
    model, requests = scripted_model(rotation_calls(), output(draft), output(terminal))
    with capture_run_messages() as captured, agent.override(model=model):
        with pytest.raises(UnexpectedModelBehavior) as caught:
            investigate_with_evidence(ROTATION_QUERY)
    diagnostic = failed_run_diagnostics(caught.value, captured)
    assert code in diagnostic['validation_rejections'][0]['reason_codes']
    assert diagnostic['validation_rejections'][1]['reason_codes'] == ['unsupported_documentation_guidance']
    assert diagnostic['terminal_validation_reason_codes'] == ['unsupported_documentation_guidance']
    assert len(requests) == 3
    assert 'PRIVATE_REASON_MARKER' not in json.dumps(diagnostic)
    assert 'Review batch job dependencies' not in json.dumps(diagnostic)
    assert {'LNX-001', 'TKT-001'} <= set(diagnostic['evidence_ids'])
    # Human-readable messages retain the same public reporting interfaces.
    pairs = answer_validation_checks(draft, captured)
    assert [message for _, message in pairs] == (citation_issues(draft, diagnostic['evidence_ids'])
                                               + documentation_issues(draft, captured))


def test_reason_history_is_per_run_and_terminal_codes_are_not_invented(scripted_model):
    invalid = ROTATION_FACTS + ' Review batch job dependencies.'
    # Fail after one output rejection by repeatedly requesting a hidden tool.
    model, _ = scripted_model(rotation_calls(), output(invalid),
                              [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='hidden1')],
                              [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='hidden2')])
    with capture_run_messages() as captured, agent.override(model=model):
        with pytest.raises(UnexpectedModelBehavior) as caught:
            investigate_with_evidence(ROTATION_QUERY)
    diagnostic = failed_run_diagnostics(caught.value, captured)
    assert diagnostic['validation_rejections'] == [
        {'rejection': 1, 'reason_codes': ['unsupported_documentation_guidance']}]
    assert 'terminal_validation_reason_codes' not in diagnostic
    # A later unrelated failure must not inherit the earlier run's reasons.
    later = failed_run_diagnostics(RuntimeError('PRIVATE_REASON_MARKER'), [])
    assert later['validation_rejections'] == []
    assert 'terminal_validation_reason_codes' not in later
    assert 'PRIVATE_REASON_MARKER' not in json.dumps(later)


@pytest.mark.parametrize('reverse', [False, True], ids=['asset-first', 'docs-first'])
def test_scenario_d_custom_web_connector(scripted_model, reverse):
    question = 'The custom web connector for APP-001 cannot locate the login element. What should I investigate?'
    calls = [ToolCallPart('get_asset_details', {'asset_id': 'APP-001'}, tool_call_id='asset'),
             ToolCallPart('search_documentation', {'query': 'PRIVATE_WEB_MARKER custom web connector login element page changes'}, tool_call_id='docs')]
    if reverse:
        calls.reverse()
    answer = (DISCLAIMER + ' Inventory reports the missing login element [APP-001]. '
              'Compare the application page structure with documented connector expectations [WEB-001]. '
              'Use sanitized screenshots in a test environment [WEB-001]. '
              'Do not modify the production connector or bypass authentication controls.')
    model, requests = scripted_model(calls, output(answer))
    with capture_run_messages() as captured, agent.override(model=model):
        summary = investigate_with_evidence(question)
    assert summary['answer'] == answer
    assert {'APP-001', 'WEB-001'} <= set(summary['evidence_ids'])
    assert '[APP-001]' in answer and '[WEB-001]' in answer
    assert summary['citation_validation_passed'] is True
    assert documentation_issues(answer, captured) == []
    results = {part.tool_name: part.content for message in captured for part in message.parts
               if isinstance(part, ToolReturnPart)}
    assert results['get_asset_details'] == pam_tools.get_asset_details('APP-001')
    assert results['get_asset_details']['platform_configuration'] == 'Custom-web'
    assert 'login element' in results['get_asset_details']['observation']
    assert any(record['id'] == 'WEB-001' and record['category'] == 'web_connector'
               for record in results['search_documentation'])
    assert not re.search(r'```|sudo |curl |set-selector|disable mfa', answer, re.I)
    assert 'Do not modify' in answer and 'bypass authentication controls' in answer
    assert {event['tool'] for event in summary['trace']} == {'get_asset_details', 'search_documentation'}
    assert all(event['error'] is None for event in summary['trace'])
    assert 'PRIVATE_WEB_MARKER' not in json.dumps(summary['trace'])
    assert summary['usage'] == {'model_requests': 2, 'tool_calls': 2,
                                'input_tokens': 20, 'output_tokens': 10, 'total_tokens': 30}
    assert len(requests) == 2


def test_scenario_e_definitive_diagnosis_request(scripted_model):
    question = ('What is the exact root cause of the password rotation failure on LNX-001? '
                'Give me the definitive answer.')
    answer = (DISCLAIMER + ' Inventory records failed rotation and a batch-job dependency [LNX-001]. '
              'The current root cause is unknown. The sanitized error has not yet been collected [LNX-001]. '
              'A recorded dependency does not establish causation. Please provide sanitized errors, '
              'timestamps and approved diagnostic evidence.')
    model, requests = scripted_model(
        [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='asset')], output(answer))
    with agent.override(model=model):
        summary = investigate_with_evidence(question)
    returned = next(part.content for message in requests[1] for part in message.parts
                    if isinstance(part, ToolReturnPart))
    assert returned == pam_tools.get_asset_details('LNX-001')
    assert returned['last_rotation_status'] == 'failed'
    assert 'Sanitized error not yet collected' in returned['observation']
    assert 'Batch job dependency recorded' in returned['dependencies']
    assert summary['answer'].startswith(DISCLAIMER)
    assert summary['evidence_ids'] == ['LNX-001']
    assert '[LNX-001]' in summary['answer']
    assert 'current root cause is unknown' in summary['answer']
    assert 'sanitized error has not yet been collected' in summary['answer']
    assert 'dependency does not establish causation' in summary['answer']
    assert not re.search(r'(?:definitive|confirmed) (?:root )?cause is', summary['answer'])
    assert summary['citation_validation_passed'] is True
    assert summary['trace'][0]['returned_ids'] == ['LNX-001']
    assert summary['usage']['model_requests'] == 2 and summary['usage']['tool_calls'] == 1
