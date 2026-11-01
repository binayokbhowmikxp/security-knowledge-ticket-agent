"""Offline tests: predetermined model calls, real PydanticAI tool execution."""
import json
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from pam_agent_pydantic import agent, get_asset_details, investigate_asset


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
        # Public model-facing schema proves that only our one tool is registered.
        assert [tool.name for tool in info.function_tools] == ['get_asset_details']
        schema = info.function_tools[0].parameters_json_schema
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
        with pytest.raises(UsageLimitExceeded):
            investigate_asset('Keep looking up LNX-001.')
