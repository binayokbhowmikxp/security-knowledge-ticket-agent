"""Native output correction with scripted models, real tools, no provider calls."""
import json

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from pam_agent_pydantic import agent, investigate_asset, investigate_with_evidence
from pam_evidence import DISCLAIMER, summarize_result


@pytest.fixture(autouse=True)
def block_provider_requests():
    with models.override_allow_model_requests(False):
        yield


@pytest.fixture
def script():
    """Record actual framework requests while supplying deterministic responses."""
    def make(*outputs):
        pending = iter(outputs)
        seen = []
        def model_function(messages, info):
            seen.append({'messages': list(messages), 'tools': {t.name for t in info.function_tools}})
            return ModelResponse(parts=next(pending), usage=RequestUsage(input_tokens=11, output_tokens=7))
        return FunctionModel(model_function), seen
    return make


def asset_call(asset_id='LNX-001', call_id='asset'):
    return ToolCallPart('get_asset_details', {'asset_id': asset_id}, tool_call_id=call_id)


def final(text):
    return [TextPart(text)]


def test_valid_answer_needs_no_output_retry(script):
    model, seen = script([asset_call()], final(DISCLAIMER + ' Failed rotation [LNX-001]; cause unknown.'))
    with agent.override(model=model):
        raw = investigate_asset('Investigate LNX-001.')
    assert len(seen) == raw.usage.requests == 2
    assert summarize_result(raw)['citation_validation_passed'] is True


def test_missing_citations_corrected_using_actual_multiple_sources(script):
    calls = [asset_call(), ToolCallPart('search_past_tickets',
             {'query': 'PRIVATE_CORRECTION_MARKER Linux rotation failed onboarding'}, tool_call_id='tickets')]
    answer = DISCLAIMER + ' Failed rotation [LNX-001]. Historical mismatch [TKT-001] does not confirm the cause.'
    model, seen = script(calls, final(DISCLAIMER + ' Draft without citations.'), final(answer))
    with agent.override(model=model):
        raw = investigate_asset('Investigate LNX-001 and similar incidents.')
    summary = summarize_result(raw)
    assert summary['answer'] == answer
    assert summary['citation_validation_passed'] is True and summary['citation_issues'] == []
    assert {'LNX-001', 'TKT-001'} <= set(summary['evidence_ids'])
    assert [event['tool'] for event in summary['trace']] == ['get_asset_details', 'search_past_tickets']
    assert all(event['error'] is None for event in summary['trace'])
    assert 'PRIVATE_CORRECTION_MARKER' not in json.dumps(summary['trace'])
    assert raw.usage.requests == len(seen) == 3
    assert raw.usage.tool_calls == 2
    assert summary['usage']['input_tokens'] == raw.usage.input_tokens == 33
    assert summary['usage']['output_tokens'] == raw.usage.output_tokens == 21
    # Existing asset/ticket tools are hidden; only missing documentation is offered.
    assert seen[-1]['tools'] == {'search_documentation'}


@pytest.mark.parametrize('draft', [
    DISCLAIMER + ' Invented [ROT-999].',
    DISCLAIMER + ' Inventory [LNX-001](LNX-001).',
    'Failed rotation [LNX-001].',
], ids=['fabricated', 'markdown-link', 'missing-disclaimer'])
def test_invalid_citation_or_disclaimer_corrected_once(script, draft):
    model, seen = script([asset_call()], final(draft), final(DISCLAIMER + ' Failed rotation [LNX-001].'))
    with agent.override(model=model):
        summary = summarize_result(investigate_asset('Investigate LNX-001.'))
    assert summary['citation_validation_passed'] is True
    assert summary['answer'].startswith(DISCLAIMER)
    assert 'ROT-999' not in summary['answer'] and '](' not in summary['answer']
    assert len(seen) == 3


def test_unknown_asset_correction_removes_unrelated_source(script):
    model, seen = script([asset_call('UNKNOWN-999')],
                         final(DISCLAIMER + ' No record exists [LNX-001].'),
                         final(DISCLAIMER + ' No synthetic inventory record exists for UNKNOWN-999; cause unknown.'))
    with agent.override(model=model):
        summary = summarize_result(investigate_asset('Investigate UNKNOWN-999.'))
    assert summary['citation_validation_passed'] is True
    assert summary['evidence_ids'] == []
    assert summary['trace'][0]['error'] == 'asset_not_found'
    assert summary['trace'][0]['returned_ids'] == []
    assert '[LNX-001]' not in summary['answer']
    assert len(seen) == 3


@pytest.mark.parametrize('runner', [investigate_asset, investigate_with_evidence])
def test_second_invalid_answer_fails_explicitly(script, runner):
    model, seen = script([asset_call()], final(DISCLAIMER + ' No citations.'),
                         final(DISCLAIMER + ' Still no citations.'))
    with agent.override(model=model):
        with pytest.raises(UnexpectedModelBehavior, match='maximum output retries'):
            runner('Investigate LNX-001.')
    assert len(seen) == 3  # Two proposed answers; no third attempt.


def test_citation_only_correction_hides_all_tools_when_docs_already_searched(script):
    calls = [ToolCallPart('search_documentation', {'query': 'Linux onboarding'}, tool_call_id='docs')]
    model, seen = script(calls, final(DISCLAIMER + ' Missing citations.'),
                         final(DISCLAIMER + ' Compare identity records [ONB-001].'))
    with agent.override(model=model):
        raw = investigate_asset('Linux onboarding checks?')
    assert seen[-1]['tools'] == set()
    assert raw.usage.tool_calls == 1
    assert summarize_result(raw)['citation_validation_passed'] is True


def test_correction_can_retrieve_missing_documentation_within_same_budget(script):
    model, seen = script([asset_call()], final(DISCLAIMER + ' Uncited draft.'),
                         [ToolCallPart('search_documentation', {'query': 'Linux rotation failed onboarding'},
                                       tool_call_id='docs')],
                         final(DISCLAIMER + ' Failed rotation [LNX-001]. Collect sanitized errors [ROT-001].'))
    with agent.override(model=model):
        raw = investigate_asset('Investigate LNX-001.')
    summary = summarize_result(raw)
    assert seen[2]['tools'] == {'search_documentation'}
    assert seen[3]['tools'] == set()
    assert summary['citation_validation_passed'] is True
    assert {'LNX-001', 'ROT-001'} <= set(summary['evidence_ids'])
    assert [e['tool'] for e in summary['trace']] == ['get_asset_details', 'search_documentation']
    assert raw.usage.requests == 4 and raw.usage.tool_calls == 2


def test_correction_cannot_execute_hidden_inventory_tool(script, monkeypatch):
    import pam_tools
    original = pam_tools.get_asset_details
    executions = []
    def observed(asset_id):
        executions.append(asset_id)
        return original(asset_id)
    monkeypatch.setattr(pam_tools, 'get_asset_details', observed)
    model, seen = script([asset_call()], final(DISCLAIMER + ' Missing citation.'),
                         [asset_call(call_id='unnecessary_repeat')],
                         final(DISCLAIMER + ' Failed rotation [LNX-001].'))
    with agent.override(model=model):
        raw = investigate_asset('Investigate LNX-001.')
    assert 'get_asset_details' not in seen[2]['tools']
    assert executions == ['LNX-001']
    assert raw.usage.tool_calls == 1


def test_request_budget_includes_correction(script):
    outputs = [[asset_call(call_id=f'asset_{i}')] for i in range(5)]
    model, seen = script(*outputs, final(DISCLAIMER + ' Missing citations.'))
    with agent.override(model=model):
        with pytest.raises(UsageLimitExceeded, match='request_limit of 6'):
            investigate_asset('Investigate LNX-001.')
    assert len(seen) == 6  # No seventh request, even for correction.


def test_tool_budget_still_applies_during_correction(script):
    calls = [asset_call(call_id=f'asset_{i}') for i in range(8)]
    model, seen = script(calls, final(DISCLAIMER + ' Missing citations.'),
                         [ToolCallPart('search_documentation', {'query': 'Linux rotation'}, tool_call_id='docs')])
    with agent.override(model=model):
        with pytest.raises(UsageLimitExceeded, match='tool_calls_limit of 8'):
            investigate_asset('Investigate LNX-001.')
    assert len(seen) == 3


def test_high_level_summary_accepts_corrected_output(script):
    model, seen = script([asset_call()], final(DISCLAIMER + ' Uncited draft.'),
                         final(DISCLAIMER + ' Failed rotation [LNX-001]; diagnosis not established.'))
    with agent.override(model=model):
        summary = investigate_with_evidence('Investigate LNX-001.')
    assert summary['citation_validation_passed'] is True
    assert summary['citation_issues'] == []
    assert summary['usage']['model_requests'] == len(seen) == 3
    assert summary['usage']['tool_calls'] == 1
    assert summary['trace'][0]['returned_ids'] == ['LNX-001']
