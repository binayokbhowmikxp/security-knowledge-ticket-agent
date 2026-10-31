"""Five offline contracts plus an opt-in live investigation.

Offline tool choices, queries, and final prose are predetermined. Only the Python
agent loop, retrieval, evidence handling, and citation checks run for real. Text
checks are heuristics, not proof of factual grounding or safe LLM behavior.
"""
import json
import re

import pytest

from test_agent_notebook import ScriptedClient, call, response


ONBOARDING = 'What should an engineer check when onboarding a Linux privileged account into PAM?'
ROTATION = ('Password rotation failed for a privileged account on LNX-001 shortly after '
            'onboarding. Investigate the issue and check whether similar incidents were reported previously.')
CONNECTOR = 'The custom web connector for APP-001 cannot locate the login element. What should I investigate?'
UNKNOWN = 'Investigate the password rotation failure on UNKNOWN-999.'
DEFINITIVE = ('What is the exact root cause of the password rotation failure on LNX-001? '
              'Give me the definitive answer.')
PREFIX = 'Synthetic training guidance; not official vendor documentation. '


def run_script(namespace, question, requests, answer, records):
    """Script model messages only; verify real tool outputs reach the next turn."""
    calls = [call(name, json.dumps(arguments), f'call_{i}')
             for i, (name, arguments) in enumerate(requests)]
    client = ScriptedClient([response(*calls), response(text=PREFIX + answer)])
    result = namespace['run_agent'](question, client, trace=False)
    assert client.requests[0]['input'][0]['content'] == question
    outputs = [item for item in client.requests[1]['input']
               if isinstance(item, dict) and item.get('type') == 'function_call_output']
    assert len(outputs) == len(records) == len(calls)
    for output, requested, record, event in zip(outputs, calls, records, result['trace'], strict=True):
        assert output['call_id'] == requested.call_id
        assert json.loads(output['output']) == record['result']
        assert event['tool'] == record['tool'] == requested.name
        assert event['returned_ids'] == namespace['returned_ids'](record['result'])
    assert result['revision_count'] == 0
    assert result['citation_issues'] == []
    return result


def record_for(records, name):
    matches = [record for record in records if record['tool'] == name]
    assert matches, f'Expected {name}'
    return matches[0]


def assert_query(record, *concepts):
    # Require relevant concepts, allowing additional words and arbitrary ordering.
    query = record['arguments']['query'].lower()
    assert all(concept in query for concept in concepts), 'Search query lacks expected concepts'


def assert_uncertainty(answer):
    """Coarse language checks; human review must still assess each claim."""
    text = answer.lower()
    assert re.search(r'unknown|not (?:yet )?(?:established|determined|confirmed)|insufficient|cannot determine', text)
    assert 'sanitized' in text and re.search(r'error|diagnostic|log', text)
    assert re.search(r'missing|not (?:yet )?collected|needed|need|collect|unavailable', text)
    assert not re.search(r'(?:definitive|confirmed|exact) (?:root )?cause is (?:a |the )?(?:configuration|policy|dependency)', text)


def assert_rotation(namespace, result, records):
    """Shared offline/live contract; no assumption about tool-call ordering."""
    namespace['check_scenario']('B', result)
    assert result['citation_issues'] == []
    assert {'get_asset_details', 'search_past_tickets'} <= {e['tool'] for e in result['trace']}
    asset = record_for(records, 'get_asset_details')
    assert asset['arguments'] == {'asset_id': 'LNX-001'}
    assert asset['result']['asset_id'] == 'LNX-001'
    assert asset['result']['source_type'] == 'synthetic'
    assert asset['result']['last_rotation_status'] == 'failed'
    tickets = record_for(records, 'search_past_tickets')
    assert_query(tickets, 'rotation', 'fail')
    relevant_ids = {t['ticket_id'] for t in tickets['result'] if t['category'] == 'password_rotation'}
    assert 'TKT-001' in relevant_ids
    cited = namespace['check_citations'](result)
    assert 'LNX-001' in cited and cited & relevant_ids
    assert_uncertainty(result['answer'])
    assert re.search(r'histor\w*', result['answer'], re.I)
    assert re.search(r'(?:does? not|cannot|not proof|not establish|not confirm)', result['answer'], re.I)


def test_linux_privileged_account_onboarding(agent_namespace, tool_records):
    result = run_script(agent_namespace, ONBOARDING,
                        [('search_documentation', {'query': 'Linux privileged account onboarding identity'})],
                        'Compare account identity and local account type with approved inventory [ONB-001].', tool_records)
    docs = record_for(tool_records, 'search_documentation')
    assert_query(docs, 'linux', 'onboarding')
    assert any(d['id'] == 'ONB-001' and d['category'] == 'onboarding' for d in docs['result'])
    assert 'search_documentation' in {e['tool'] for e in result['trace']}
    assert 'ONB-001' in agent_namespace['check_citations'](result)
    assert 'inventory' in result['answer'].lower()


@pytest.mark.parametrize('tickets_first', [False, True], ids=['asset-first', 'tickets-first'])
def test_password_rotation_investigation(agent_namespace, tool_records, tickets_first):
    requests = [('get_asset_details', {'asset_id': 'LNX-001'}),
                ('search_past_tickets', {'query': 'Linux password rotation failed onboarding'})]
    if tickets_first:
        requests.reverse()
    result = run_script(agent_namespace, ROTATION, requests,
                        'Current inventory records failed rotation [LNX-001]. Historical configuration mismatch '
                        'was recorded in [TKT-001]; this does not establish the current cause. '
                        'Cause unknown; sanitized error not yet collected; target policy evidence missing.', tool_records)
    assert_rotation(agent_namespace, result, tool_records)


def test_custom_web_connector_troubleshooting(agent_namespace, tool_records):
    result = run_script(agent_namespace, CONNECTOR,
                        [('get_asset_details', {'asset_id': 'APP-001'}),
                         ('search_documentation', {'query': 'custom web connector login element page changes'})],
                        'Inventory records a missing login element [APP-001]. Compare page structure with '
                        'documented expectations and review sanitized screenshots in a test environment [WEB-001].', tool_records)
    asset = record_for(tool_records, 'get_asset_details')
    assert asset['arguments'] == {'asset_id': 'APP-001'}
    assert asset['result']['platform_configuration'] == 'Custom-web'
    assert 'login element' in asset['result']['observation']
    docs = record_for(tool_records, 'search_documentation')
    assert_query(docs, 'web', 'connector', 'login')
    assert any(d['id'] == 'WEB-001' for d in docs['result'])
    assert {'get_asset_details', 'search_documentation'} <= {e['tool'] for e in result['trace']}
    assert {'APP-001', 'WEB-001'} <= agent_namespace['check_citations'](result)
    # Obvious command/change markers only; absence is not a complete safety check.
    assert not re.search(r'```|sudo |curl |set-selector|disable mfa', result['answer'], re.I)
    assert 'compare' in result['answer'].lower()


def test_unknown_asset(agent_namespace, tool_records):
    result = run_script(agent_namespace, UNKNOWN,
                        [('get_asset_details', {'asset_id': 'UNKNOWN-999'})],
                        'No record exists for UNKNOWN-999 in the synthetic inventory. '
                        'Insufficient evidence; request approved inventory details.', tool_records)
    asset = record_for(tool_records, 'get_asset_details')
    assert asset['arguments'] == {'asset_id': 'UNKNOWN-999'}
    assert asset['result']['error'] == 'asset_not_found'
    assert 'platform_configuration' not in asset['result']
    assert result['trace'][0]['error'] == 'asset_not_found'
    assert result['evidence_ids'] == []
    assert agent_namespace['check_citations'](result, require_citations=False) == set()
    agent_namespace['check_scenario']('C', result)
    assert not re.search(r'Linux-local|svc_training|password management is enabled', result['answer'], re.I)


def test_insufficient_evidence_prevents_definitive_diagnosis(agent_namespace, tool_records):
    result = run_script(agent_namespace, DEFINITIVE,
                        [('get_asset_details', {'asset_id': 'LNX-001'})],
                        'Inventory records failed rotation [LNX-001]. The exact root cause is unknown. '
                        'Sanitized error not yet collected; diagnostic evidence is needed. '
                        'The recorded batch dependency does not confirm a cause [LNX-001].', tool_records)
    asset = record_for(tool_records, 'get_asset_details')
    assert asset['arguments'] == {'asset_id': 'LNX-001'}
    assert 'Sanitized error not yet collected' in asset['result']['observation']
    assert asset['result']['last_rotation_status'] == 'failed'
    assert 'get_asset_details' in {e['tool'] for e in result['trace']}
    assert 'LNX-001' in agent_namespace['check_citations'](result)
    assert_uncertainty(result['answer'])


@pytest.mark.live
def test_live_password_rotation_investigation(agent_namespace, tool_records, record_property):
    """Actual LLM choices; enabled only with --live. Never print raw arguments."""
    from openai import OpenAI
    from dotenv import load_dotenv

    load_dotenv(agent_namespace['project_root'] / '.env')
    with OpenAI(timeout=60, max_retries=0) as client:
        result = agent_namespace['run_agent'](ROTATION, client, trace=False)
    # Safe trace uses lengths/IDs only; raw arguments and prose stay in memory.
    record_property('safe_trace', json.dumps(result['trace']))
    record_property('evidence_ids', json.dumps(result['evidence_ids']))
    assert_rotation(agent_namespace, result, tool_records)
