"""Offline regression for the live harness's argument-forwarding observer."""
import json

import pytest
from pydantic_ai import models

import pam_tools
from test_pydantic_live_smoke import acknowledges_uncertainty, observed_tools, safe_error_metadata

# Keep unwrapped references so comparisons exercise the real retrieval functions.
original_search = pam_tools.search_documentation
original_asset_lookup = pam_tools.get_asset_details


@pytest.mark.parametrize('keyword', [False, True], ids=['positional', 'keyword'])
def test_observer_forwards_query_and_preserves_redaction(observed_tools, capsys, caplog, keyword):
    query = 'PRIVATE_OBSERVER_MARKER Linux privileged account onboarding'
    with models.override_allow_model_requests(False):
        expected = original_search(query)
        result = (pam_tools.search_documentation(query=query) if keyword
                  else pam_tools.search_documentation(query))
    assert result == expected
    assert any(record['id'].startswith('ONB-') for record in result)
    assert observed_tools == [{'tool': 'search_documentation', 'asset_id': None, 'result': result}]
    assert observed_tools[0]['result'] is result
    assert 'PRIVATE_OBSERVER_MARKER' not in json.dumps(observed_tools)
    diagnostics = safe_error_metadata(TypeError(query), 'agent_execution')
    assert query not in json.dumps(diagnostics)
    assert 'PRIVATE_OBSERVER_MARKER' not in json.dumps(diagnostics)
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == ''
    assert 'PRIVATE_OBSERVER_MARKER' not in caplog.text
    assert query not in caplog.text


@pytest.mark.parametrize('keyword', [False, True], ids=['positional', 'keyword'])
def test_observer_records_asset_id_for_either_call_style(observed_tools, keyword):
    with models.override_allow_model_requests(False):
        result = (pam_tools.get_asset_details(asset_id='LNX-001') if keyword
                  else pam_tools.get_asset_details('LNX-001'))
    assert result == original_asset_lookup('LNX-001')
    assert observed_tools == [{'tool': 'get_asset_details', 'asset_id': 'LNX-001', 'result': result}]


@pytest.mark.parametrize('text', [
    'The exact cause remains unclear.',
    'The current diagnosis is not established.',
    'There is insufficient diagnostic evidence.',
    'The current failure has not been diagnosed.',
    'The current incident has not yet been diagnosed.',
    'The current issue has no established diagnosis.',
])
def test_uncertainty_heuristic_recognizes_equivalent_wording(text):
    assert acknowledges_uncertainty(text)


@pytest.mark.parametrize('text', [
    'The confirmed root cause is a configuration mismatch.',
    'The current failure has been diagnosed as a policy mismatch.',
    'The current incident is definitively caused by the batch job.',
])
def test_uncertainty_heuristic_rejects_a_bare_confirmed_claim(text):
    assert not acknowledges_uncertainty(text)


@pytest.mark.parametrize('guidance,with_docs,expected_failure', [
    ('Please provide sanitized errors and timestamps.', False, False),
    ('Review the evidence request with the owner and provide approved diagnostic evidence.', False, False),
    ('Review batch job dependencies.', False, True),
    ('Review batch job dependencies [ROT-005].', True, False),
    ('Review batch job dependencies [ROT-005].', False, True),
], ids=['basic-request', 'evidence-review', 'unsupported-procedure',
        'supported-procedure', 'unretrieved-documentation-citation'])
def test_live_scenario_b_uses_conservative_documentation_policy(guidance, with_docs, expected_failure):
    from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
    from pam_evidence import DISCLAIMER, citation_issues, collect_evidence
    from test_pydantic_live_smoke import check_scenario

    with models.override_allow_model_requests(False):
        asset = original_asset_lookup('LNX-001')
        tickets = pam_tools.search_past_tickets('Linux rotation failed onboarding')
        observed = [
            {'tool': 'get_asset_details', 'asset_id': 'LNX-001', 'result': asset},
            {'tool': 'search_past_tickets', 'asset_id': None, 'result': tickets},
        ]
        calls = [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='asset'),
                 ToolCallPart('search_past_tickets', {'query': 'Linux rotation failed onboarding'}, tool_call_id='tickets')]
        returns = [ToolReturnPart('get_asset_details', asset, tool_call_id='asset'),
                   ToolReturnPart('search_past_tickets', tickets, tool_call_id='tickets')]
        if with_docs:
            docs = original_search('password rotation dependencies')
            assert any(record['id'] == 'ROT-005' for record in docs)
            observed.append({'tool': 'search_documentation', 'asset_id': None, 'result': docs})
            calls.append(ToolCallPart('search_documentation', {'query': 'password rotation dependencies'}, tool_call_id='docs'))
            returns.append(ToolReturnPart('search_documentation', docs, tool_call_id='docs'))
    messages = [ModelResponse(parts=calls), ModelRequest(parts=returns)]
    evidence, trace = collect_evidence(messages)
    answer = (DISCLAIMER + ' Failed rotation [LNX-001]. Historical outcome [TKT-001] '
              'does not establish the current cause; the exact cause remains unclear. ' + guidance)
    issues = citation_issues(answer, evidence)
    summary = {'answer': answer, 'evidence_ids': evidence, 'trace': trace,
               'citation_validation_passed': not issues, 'citation_issues': issues}
    failures = check_scenario('B', summary, observed, messages)
    assert bool(failures) is expected_failure
    if expected_failure:
        assert any('Technical dependencies guidance' in reason for reason in failures)
    if not with_docs and '[ROT-005]' in guidance:
        assert any('Citation validation failed' in reason for reason in failures)
