"""Offline tests: predetermined model calls, real PydanticAI tool execution."""
import json
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

import pam_tools
from pam_agent_pydantic import (
    agent, get_asset_details, investigate_asset, search_documentation, search_past_tickets,
)


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
