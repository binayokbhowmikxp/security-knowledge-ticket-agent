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
])
def test_uncertainty_heuristic_recognizes_equivalent_wording(text):
    assert acknowledges_uncertainty(text)


def test_uncertainty_heuristic_rejects_a_bare_confirmed_claim():
    assert not acknowledges_uncertainty('The confirmed root cause is a configuration mismatch.')
