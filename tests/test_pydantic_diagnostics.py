"""Offline failure reproductions using actual framework capture and retry metadata."""
import json

import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from pam_agent_pydantic import agent, investigate_with_evidence
from pam_diagnostics import failed_run_diagnostics, retry_activity
from pam_evidence import DISCLAIMER


@pytest.fixture(autouse=True)
def block_provider_requests():
    with models.override_allow_model_requests(False):
        yield


@pytest.fixture
def run_failure():
    def run(outputs):
        script = iter(outputs)
        def model_function(messages, info):
            return ModelResponse(parts=next(script), usage=RequestUsage(input_tokens=7, output_tokens=5))
        with capture_run_messages() as captured:
            with agent.override(model=FunctionModel(model_function)):
                try:
                    investigate_with_evidence('PRIVATE_FAILURE_MARKER synthetic investigation')
                except Exception as exc:
                    diagnostic = failed_run_diagnostics(exc, captured)
                else:
                    pytest.fail('Expected a failed run with no accepted result')
        # Raw captured data stays in memory and is never emitted.
        assert len(captured) > 0
        assert any(isinstance(message, ModelResponse) for message in captured)
        assert 'PRIVATE_FAILURE_MARKER' not in json.dumps(diagnostic)
        return diagnostic
    return run


def asset(asset_id='LNX-001', call_id='PRIVATE_FAILURE_MARKER'):
    return ToolCallPart('get_asset_details', {'asset_id': asset_id}, tool_call_id=call_id)


def text(answer):
    return [TextPart(answer)]


def test_failed_output_validation_has_typed_output_feedback(run_failure):
    diagnostic = run_failure([[asset()], text(DISCLAIMER + ' PRIVATE_FAILURE_MARKER uncited.'),
                              text(DISCLAIMER + ' PRIVATE_FAILURE_MARKER still uncited.')])
    assert diagnostic['error_type'] == 'UnexpectedModelBehavior'
    assert diagnostic['category'] == 'output_validation_failure'
    assert diagnostic['http_status'] is None
    assert diagnostic['output_validation_retry_observed'] is True
    assert diagnostic['tool_retry_observed'] is False
    assert diagnostic['executed_tools'] == ['get_asset_details']
    assert diagnostic['evidence_ids'] == ['LNX-001']
    assert diagnostic['terminal_retry_events'][0]['scope'] == 'output'
    assert diagnostic['partial_usage'] == {'partial': True, 'recorded_model_responses': 3,
                                          'input_tokens': 21, 'output_tokens': 15, 'total_tokens': 36}


def test_hidden_tool_attempt_distinct_from_output_retry(run_failure):
    diagnostic = run_failure([[asset()], text(DISCLAIMER + ' Missing citation.'),
                              [asset(call_id='second')], text(DISCLAIMER + ' Still missing citation.')])
    assert diagnostic['output_validation_retry_observed'] is True
    assert diagnostic['tool_retry_observed'] is True
    assert any(e['scope'] == 'tool' and e['cause'] in {'unknown_tool', 'unavailable_tool'}
               for e in diagnostic['retry_events'])
    assert diagnostic['executed_tools'] == ['get_asset_details']
    assert diagnostic['evidence_ids'] == ['LNX-001']


def test_invalid_tool_arguments_have_tool_retry_evidence(run_failure):
    invalid = ToolCallPart('search_documentation', {'query': {'private': 'PRIVATE_FAILURE_MARKER'}},
                          tool_call_id='invalid')
    diagnostic = run_failure([[invalid], [invalid]])
    assert diagnostic['error_type'] == 'UnexpectedModelBehavior'
    assert diagnostic['output_validation_retry_observed'] is False
    assert diagnostic['tool_retry_observed'] is True
    assert any(e['scope'] == 'tool' and e['cause'] == 'validation_error'
               for e in diagnostic['retry_events'])
    assert diagnostic['executed_tools'] == []
    assert diagnostic['evidence_ids'] == []


def test_unknown_asset_failure_preserves_missing_lookup_without_invented_source(run_failure):
    diagnostic = run_failure([[asset('UNKNOWN-999')],
                              text(DISCLAIMER + ' No record [LNX-001].'),
                              text(DISCLAIMER + ' No record [LNX-001].')])
    assert diagnostic['evidence_ids'] == []
    assert diagnostic['executed_tools'] == ['get_asset_details']
    assert diagnostic['trace'][0]['error'] == 'asset_not_found'
    assert diagnostic['output_validation_retry_observed'] is True


def test_uncaptured_failure_does_not_invent_usage_or_retries():
    diagnostic = failed_run_diagnostics(RuntimeError('PRIVATE_FAILURE_MARKER'), [])
    assert 'PRIVATE_FAILURE_MARKER' not in json.dumps(diagnostic)
    assert 'partial_usage' not in diagnostic
    assert diagnostic['executed_tools'] == []
    assert diagnostic['retry_events'] == []
    assert diagnostic['terminal_retry_events'] == []


def test_successful_unknown_asset_has_no_validation_retry():
    outputs = iter([[asset('UNKNOWN-999')], text(DISCLAIMER +
                    ' No synthetic inventory record exists for UNKNOWN-999; provide sanitized errors.')])
    def model_function(messages, info):
        return ModelResponse(parts=next(outputs))
    with capture_run_messages() as captured, agent.override(model=FunctionModel(model_function)):
        summary = investigate_with_evidence('Investigate UNKNOWN-999.')
    assert summary['evidence_ids'] == []
    assert summary['trace'][0]['error'] == 'asset_not_found'
    assert summary['citation_validation_passed'] is True
    assert retry_activity(captured)['output_validation_retry_observed'] is False


def test_repeated_hidden_tool_attempts_are_not_misclassified_as_output_retry_exhaustion(run_failure):
    diagnostic = run_failure([[asset()], text(DISCLAIMER + ' Missing citation.'),
                              *[[asset(call_id=f'hidden_{i}')] for i in range(4)]])
    assert diagnostic['error_type'] == 'UnexpectedModelBehavior'
    assert diagnostic['category'] == 'framework_failure_after_tool_retry'
    assert diagnostic['output_validation_retry_observed'] is True
    assert diagnostic['tool_retry_observed'] is True
    assert diagnostic['executed_tools'] == ['get_asset_details']
    assert diagnostic['partial_usage']['recorded_model_responses'] == 4
