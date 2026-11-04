"""Offline UI behavior only. Stubs never ship in the real application."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import pam_agent_pydantic


APP = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture
def ui(monkeypatch):
    # Keep tests independent of the developer's actual .env and API key.
    monkeypatch.setattr('dotenv.load_dotenv', lambda *args, **kwargs: False)
    monkeypatch.setattr('pam_monitoring.initialize_monitoring', lambda: False)
    monkeypatch.setenv('OPENAI_API_KEY', 'OFFLINE_TEST_ONLY_NOT_A_KEY')
    run = Mock(return_value={
        'answer': 'Synthetic training guidance; test answer [LNX-001].',
        'evidence_ids': ['LNX-001'],
        'trace': [{'sequence': 1, 'tool': 'get_asset_details', 'tool_call_id': 'call_1',
                   'returned_ids': ['LNX-001'], 'error': None}],
        'citation_issues': [], 'citation_validation_passed': True,
        'usage': {'model_requests': 2, 'tool_calls': 1, 'input_tokens': 80, 'output_tokens': 43, 'total_tokens': 123},
    })
    monkeypatch.setattr(pam_agent_pydantic, 'investigate_with_evidence', run)
    return AppTest.from_file(str(APP)).run(), run


def test_chat_persists_and_clear_does_not_rerun_agent(ui):
    app, run = ui
    assert not app.exception
    run.assert_not_called()
    assert app.info[0].value == 'Experimental mode: output validation disabled. Answers are not verified.'
    app.chat_input[0].set_value('Investigate LNX-001.').run()
    run.assert_called_once_with('Investigate LNX-001.', validate_output=False)
    assert len(app.chat_message) == 2
    assert any(item.value == 'get_asset_details — completed' for item in app.markdown)
    assert [item.label for item in app.expander] == ['Agent activity', 'Evidence and usage']
    app.run()
    assert app.session_state['usage_totals']['total_tokens'] == 123
    assert run.call_count == 1
    assert len(app.chat_message) == 2
    app.chat_input[0].set_value('What evidence is missing?').run()
    assert run.call_count == 2
    assert run.call_args.args == ('What evidence is missing?',)
    assert run.call_args.kwargs == {'validate_output': False}
    assert len(app.chat_message) == 4
    app.sidebar.button[0].click().run()
    assert app.session_state['messages'] == []
    assert len(app.chat_message) == 0
    assert run.call_count == 2
    assert app.session_state['usage_totals']['total_tokens'] == 246
    assert not app.exception


def test_failure_shows_safe_error_and_never_retries(ui):
    app, run = ui
    run.side_effect = RuntimeError('PRIVATE_EXCEPTION_MARKER credentials/provider payload')
    app.chat_input[0].set_value('Investigate a synthetic incident.').run()
    assert len(app.error) == 1
    assert 'no answer was accepted' in app.error[0].value
    assert 'PRIVATE_EXCEPTION_MARKER' not in app.error[0].value
    assert 'PRIVATE_EXCEPTION_MARKER' not in str(app.session_state['messages'])
    assert [item.label for item in app.expander] == ['Failure details']
    assert 'PRIVATE_EXCEPTION_MARKER' not in app.json[0].value
    assert 'local_execution_error' in app.json[0].value
    assert app.session_state['usage_totals']['incomplete_runs'] == 1
    app.run()
    assert run.call_count == 1
    assert not app.exception


def test_failure_details_preserve_only_safe_validation_codes(ui):
    from pydantic_ai import ModelRetry
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    app, run = ui
    retry = ModelRetry('PRIVATE_REJECTED_DRAFT_MARKER')
    retry.pam_validation_reason_codes = ('unsupported_documentation_guidance',)
    failure = UnexpectedModelBehavior('PRIVATE_PROVIDER_MARKER')
    failure.__cause__ = retry
    failure.pam_validation_rejections = (('missing_citation',), ('unsupported_documentation_guidance',))
    run.side_effect = failure
    app.chat_input[0].set_value('Investigate a synthetic incident.').run()
    details = app.json[0].value
    assert 'missing_citation' in details and 'unsupported_documentation_guidance' in details
    assert 'terminal_validation_reason_codes' in details
    assert 'PRIVATE_REJECTED_DRAFT_MARKER' not in details
    assert 'PRIVATE_PROVIDER_MARKER' not in details
    assert not app.exception
    assert run.call_count == 1


def test_older_error_history_remains_renderable(ui):
    app, run = ui
    app.session_state['messages'] = [{'role': 'assistant', 'error': 'Previous investigation failed.'}]
    app.run()
    assert app.error[0].value == 'Previous investigation failed.'
    assert not app.exception
    run.assert_not_called()


def test_missing_key_disables_input_without_agent_request(ui, monkeypatch):
    app, run = ui
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    app.run()
    assert app.chat_input[0].disabled
    run.assert_not_called()
    assert len(app.sidebar.warning) == 1


def test_citation_issues_are_not_presented_as_a_pass(ui):
    app, run = ui
    run.return_value = {**run.return_value, 'citation_validation_passed': False,
                        'citation_issues': ['Missing valid current asset citation.']}
    app.chat_input[0].set_value('Investigate LNX-001.').run()
    assert len(app.warning) == 1
    assert 'Informational citation checks reported issues' in app.warning[0].value
    assert not app.exception
