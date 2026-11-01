"""A conservative lexical procedure policy; these tests do not prove entailment."""
import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from pam_agent_pydantic import agent, investigate_with_evidence
from pam_diagnostics import retry_activity
from pam_evidence import DISCLAIMER


@pytest.fixture(autouse=True)
def block_provider_requests():
    with models.override_allow_model_requests(False):
        yield


@pytest.mark.parametrize('correction', ['remove-procedure', 'retrieve-docs'])
def test_uncited_technical_guidance_triggers_bounded_correction(correction):
    outputs = [
        [ToolCallPart('get_asset_details', {'asset_id': 'LNX-001'}, tool_call_id='asset')],
        [TextPart(DISCLAIMER + ' Failed rotation [LNX-001]. Review the batch job dependencies.')],
    ]
    if correction == 'retrieve-docs':
        outputs.extend([
            [ToolCallPart('search_documentation', {'query': 'password rotation dependencies'}, tool_call_id='docs')],
            [TextPart(DISCLAIMER + ' Failed rotation [LNX-001]. Review documented dependencies [ROT-005].')],
        ])
    else:
        outputs.append([TextPart(DISCLAIMER + ' Failed rotation [LNX-001]. Documentation evidence is '
                                 'unavailable. Please provide sanitized errors and timestamps.')])
    pending, seen = iter(outputs), []
    def model_function(messages, info):
        seen.append({t.name for t in info.function_tools})
        return ModelResponse(parts=next(pending))
    with capture_run_messages() as captured, agent.override(model=FunctionModel(model_function)):
        summary = investigate_with_evidence('Investigate LNX-001.')
    assert summary['citation_validation_passed'] is True
    assert retry_activity(captured)['output_validation_retry_observed'] is True
    assert seen[2] == {'search_documentation'}
    assert summary['usage']['model_requests'] == (4 if correction == 'retrieve-docs' else 3)
    assert summary['usage']['tool_calls'] == (2 if correction == 'retrieve-docs' else 1)


@pytest.mark.parametrize('evidence_request', [
    'Please provide sanitized errors and timestamps.',
    'Request approved diagnostic evidence from the owner.',
    'Review the evidence request with the owner.',
    'I cannot review configuration because documentation evidence is unavailable.',
])
def test_basic_evidence_requests_need_no_documentation(evidence_request):
    seen = []
    def model_function(messages, info):
        seen.append(True)
        return ModelResponse(parts=[TextPart(DISCLAIMER + ' ' + evidence_request)])
    with agent.override(model=FunctionModel(model_function)):
        summary = investigate_with_evidence('What evidence is missing?')
    assert summary['citation_validation_passed'] is True
    assert len(seen) == 1


def test_unrelated_documentation_is_not_enough_for_dependency_steps():
    from pydantic_ai.exceptions import UnexpectedModelBehavior
    pending = iter([
        [ToolCallPart('search_documentation', {'query': 'custom web connector login element'}, tool_call_id='docs')],
        [TextPart(DISCLAIMER + ' Compare page structure [WEB-001]. Review batch job dependencies [WEB-001].')],
        [TextPart(DISCLAIMER + ' Compare page structure [WEB-001]. Review batch job dependencies [WEB-001].')],
    ])
    def model_function(messages, info):
        return ModelResponse(parts=next(pending))
    with agent.override(model=FunctionModel(model_function)):
        with pytest.raises(UnexpectedModelBehavior):
            investigate_with_evidence('Investigate the synthetic connector.')
