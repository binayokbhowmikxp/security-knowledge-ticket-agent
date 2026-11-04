"""Experimental opt-out tests execute real tools with offline scripted models."""
import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from pam_agent_pydantic import agent, investigate_asset, investigate_with_evidence
from pam_diagnostics import retry_activity
from pam_evidence import summarize_result


@pytest.mark.parametrize('runner', [investigate_asset, investigate_with_evidence])
@pytest.mark.parametrize('enabled', [False, True])
def test_validation_option_preserves_default_and_disables_rejection(runner, enabled):
    requests = []
    answer = 'Unverified answer without citations. Review batch job dependencies.'
    def model_function(messages, info):
        requests.append(True)
        if len(requests) == 1:
            return ModelResponse(parts=[ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'},
                                                    tool_call_id='asset')])
        return ModelResponse(parts=[TextPart(answer)])
    with models.override_allow_model_requests(False), capture_run_messages() as captured, agent.override(model=FunctionModel(model_function)):
        if enabled:
            # Omit the option: the default must still reject and exhaust one retry.
            with pytest.raises(UnexpectedModelBehavior):
                runner('Investigate LNX-001.')
            assert len(requests) == 3
            assert retry_activity(captured)['output_validation_retry_observed'] is True
        else:
            result = runner('Investigate LNX-001.', validate_output=False)
            summary = result if isinstance(result, dict) else summarize_result(result)
            assert summary['answer'] == answer
            assert summary['citation_validation_passed'] is False
            assert summary['citation_issues']
            assert summary['evidence_ids'] == ['LNX-001']
            assert summary['trace'][0]['tool'] == 'get_asset_details'
            assert summary['trace'][0]['error'] is None
            assert summary['usage']['model_requests'] == len(requests) == 2
            assert summary['usage']['tool_calls'] == 1
            assert retry_activity(captured)['output_validation_retry_observed'] is False
