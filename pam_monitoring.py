"""Metadata-only monitoring and list-price estimates; never store agent content here."""
from collections import deque
from contextlib import contextmanager
from functools import lru_cache
import os
from urllib.parse import urlsplit

import logfire
from opentelemetry.trace import Status, StatusCode, get_current_span

# USD per million tokens; estimates exclude cache discounts and billing adjustments.
INPUT_USD_PER_MILLION = 0.15
OUTPUT_USD_PER_MILLION = 0.60
EXPORT_STATUS_CODES = deque(maxlen=32)  # Status codes only, never HTTP headers or bodies.


def estimated_cost(usage):
    if usage.get('input_tokens') is None or usage.get('output_tokens') is None:
        return None
    return (usage['input_tokens'] * INPUT_USD_PER_MILLION
            + usage['output_tokens'] * OUTPUT_USD_PER_MILLION) / 1_000_000


def add_usage(totals, usage, *, partial=False):
    """Call once on submission completion, never while rendering history."""
    updated = dict(totals)
    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
        updated[key] = updated.get(key, 0) + (usage.get(key) or 0)
    updated['estimated_usd'] = updated.get('estimated_usd', 0) + (estimated_cost(usage) or 0)
    updated['incomplete_runs'] = updated.get('incomplete_runs', 0) + int(partial or estimated_cost(usage) is None)
    return updated


def suppress_exception_content(helper):
    helper.no_record_exception()
    # Suppressing the event alone leaves a raw exception in the status description.
    helper.level = 'warning'
    helper.span.set_status(Status(StatusCode.ERROR))


def record_export_status(helper):
    # Observe ingestion acknowledgement only; do not inspect response content.
    if urlsplit(helper.response.request.url).path.endswith('/v1/traces'):
        EXPORT_STATUS_CODES.append(helper.response.status_code)


@lru_cache(maxsize=1)
def initialize_monitoring():
    """Called after dotenv; optional write token, no read token or replay."""
    if not os.environ.get('LOGFIRE_TOKEN', '').strip():
        return False
    from pam_agent_pydantic import agent

    logfire.configure(
        send_to_logfire=True, console=False, inspect_arguments=False,
        service_name='pam-agent',
        advanced=logfire.AdvancedOptions(
            exception_callback=suppress_exception_content,
            server_response_hook=record_export_status,
            emit_configuration_span=False, pending_spans=False),
    )
    logfire.instrument_pydantic_ai(
        agent, include_content=False, include_binary_content=False,
        include_model_request_parameters=False,
    )
    return True


@contextmanager
def investigation_span(session_id, enabled):
    if not enabled:
        yield None
        return
    with logfire.span('PAM investigation', session_id=session_id,
                      agent_name='pam_agent', model='gpt-4o-mini') as span:
        yield span


def record_outcome(span, usage, activity, *, diagnostics=None):
    if span is None:
        return None
    span.set_attribute('execution_status', 'failed' if diagnostics else 'completed')
    for key in ('input_tokens', 'output_tokens', 'total_tokens', 'model_requests', 'tool_calls'):
        if usage.get(key) is not None:
            span.set_attribute(key, usage[key])
    cost = estimated_cost(usage)
    if cost is not None:
        span.set_attribute('estimated_usd', cost)
    # Existing helper returns only typed retry metadata, not drafts or arguments.
    span.set_attribute('retry_activity', activity)
    if diagnostics:
        span.set_attribute('error_category', diagnostics['category'])
        span.set_attribute('usage_partial', True)
        get_current_span().set_status(Status(StatusCode.ERROR))
    return format(get_current_span().get_span_context().trace_id, '032x')
