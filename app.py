"""Small Streamlit frontend; each submitted question runs the existing PAM agent."""
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
import streamlit as st
from pydantic_ai import capture_run_messages

from pam_agent_pydantic import investigate_with_evidence
from pam_diagnostics import failed_run_diagnostics, retry_activity
from pam_monitoring import (initialize_monitoring, investigation_span, record_outcome,
                            estimated_cost, add_usage)


SAFE_ERROR = ('The investigation failed and no answer was accepted. '
              'Check API access or evidence validation before submitting again.')


def render_message(message):
    """Render only answer content and the agent's existing redacted summary."""
    with st.chat_message(message['role']):
        if message.get('error'):
            st.error(message['error'])
            if 'diagnostics' in message:
                with st.expander('Failure details'):
                    st.json(message['diagnostics'])
            return
        if message['role'] == 'user':
            st.markdown(message['content'])
            return
        result = message['result']
        st.markdown(result['answer'])
        if not result['citation_validation_passed']:
            st.warning('Informational citation checks reported issues; output validation is not enforced.')
        with st.expander('Agent activity'):
            if not result['trace']:
                st.caption('No tool activity was reported.')
            for event in result['trace']:
                status = event['error'] or 'completed'
                st.write(f"{event['tool']} — {status}")
                if event['returned_ids']:
                    st.caption('Evidence: ' + ', '.join(event['returned_ids']))
        with st.expander('Evidence and usage'):
            st.write('Retrieved evidence:', result['evidence_ids'])
            st.write('Informational citation checks (not enforced):',
                     'No issues detected' if result['citation_validation_passed'] else 'Issues found')
            if result['citation_issues']:
                st.write(result['citation_issues'])
            usage = result['usage']
            for key, label in [('model_requests', 'Model requests'),
                               ('tool_calls', 'Tool calls'), ('total_tokens', 'Total tokens')]:
                if key in usage:
                    st.write(f'{label}: {usage[key]}')
            cost = estimated_cost(usage)
            if cost is not None:
                st.write(f"Input tokens: {usage['input_tokens']}; output tokens: {usage['output_tokens']}")
                st.write(f'Estimated cost: ${cost:.8f} USD')
            if message.get('trace_id'):
                st.caption('Logfire trace ID: ' + message['trace_id'])
            st.caption('Citation checks do not prove that every claim is supported.')


def main():
    st.set_page_config(page_title='PAM Knowledge & Ticket Agent', page_icon='🔎')
    load_dotenv(Path(__file__).resolve().with_name('.env'))
    monitoring_enabled = initialize_monitoring()
    if 'monitoring_session_id' not in st.session_state:
        st.session_state.monitoring_session_id = str(uuid4())
        st.session_state.usage_totals = {}
    configured = bool(os.environ.get('OPENAI_API_KEY', '').strip())
    st.title('PAM Knowledge & Ticket Agent')
    st.caption('Read-only PAM guidance from synthetic training data.')
    st.info('Experimental mode: output validation disabled. Answers are not verified.')
    st.caption('Each question runs independently. Chat history is for display only.')
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    with st.sidebar:
        st.write('Model: gpt-4o-mini')
        st.caption('Submitted questions use the real OpenAI API and incur usage charges.')
        usage_panel = st.empty()
        if not monitoring_enabled:
            st.caption('Logfire export disabled: LOGFIRE_TOKEN is missing.')
        if not configured:
            st.warning('Set OPENAI_API_KEY in the local .env file to ask a question.')
        if st.button('Clear conversation'):
            st.session_state.messages = []
            st.rerun()
    for message in st.session_state.messages:
        render_message(message)
    question = st.chat_input('Ask a PAM question or describe a synthetic incident',
                             max_chars=8000, disabled=not configured)
    if question and question.strip():
        user_message = {'role': 'user', 'content': question}
        st.session_state.messages.append(user_message)
        render_message(user_message)
        with investigation_span(st.session_state.monitoring_session_id, monitoring_enabled) as span:
            messages = []
            try:
                with capture_run_messages() as messages, st.spinner('Investigating…'):
                    result = investigate_with_evidence(question, validate_output=False)
                activity = retry_activity(messages)
                assistant_message = {'role': 'assistant', 'result': result,
                                     'retry_activity': activity}
                usage = result['usage']
                diagnostics = None
            except Exception as exc:
                # Never display/log exception payloads, arguments, or raw messages.
                diagnostics = failed_run_diagnostics(exc, messages)
                assistant_message = {'role': 'assistant', 'error': SAFE_ERROR,
                                     'diagnostics': diagnostics}
                usage = diagnostics.get('partial_usage', {})
                activity = retry_activity(messages)
            assistant_message['trace_id'] = record_outcome(span, usage, activity, diagnostics=diagnostics)
            st.session_state.usage_totals = add_usage(
                st.session_state.usage_totals, usage, partial=diagnostics is not None)
        st.session_state.messages.append(assistant_message)
        render_message(assistant_message)

    with usage_panel.container():
        totals = st.session_state.usage_totals
        st.write(f"Session reported tokens: {totals.get('total_tokens', 0)}")
        st.write(f"Session estimated cost: ${totals.get('estimated_usd', 0):.8f} USD")
        st.caption('List-price estimate, not an invoice; includes cleared conversations.')
        if totals.get('incomplete_runs', 0):
            st.warning('Usage is incomplete: failed runs or missing counts may add unreported charges.')


if __name__ == '__main__':
    main()
