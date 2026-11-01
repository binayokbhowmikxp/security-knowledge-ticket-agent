"""Redacted diagnostics derived from in-memory framework messages and errors.

Never serialize raw messages, retry content, exception text, or tracebacks.
"""
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, RetryFeedbackPart, ToolReturnPart
from openai import APIConnectionError, APIStatusError

from pam_evidence import VALIDATION_REASON_CODES, collect_evidence


TOOL_CAUSES = {'validation_error', 'model_retry', 'unknown_tool', 'unavailable_tool'}
OUTPUT_CAUSES = {'validation_error', 'model_retry', 'no_output'}


def _exceptions(exc):
    pending, seen = [exc], set()
    while pending and len(seen) < 16:
        current = pending.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        underlying = current.__cause__ or current.__context__
        if underlying is not None:
            pending.append(underlying)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)


def _retry_event(part):
    if isinstance(part, RetryFeedbackPart):
        scope, allowed = 'output', OUTPUT_CAUSES
    elif isinstance(part, ToolReturnPart) and part.outcome == 'retried':
        scope, allowed = 'tool', TOOL_CAUSES
    else:
        return None
    retry = part.retry
    if retry is None:
        return None
    event = {'scope': scope, 'cause': retry.cause if retry.cause in allowed else 'other'}
    for name in ['attempt', 'max_retries']:
        value = getattr(retry, name, None)
        if type(value) is int:
            event[name] = value
    return event


def retry_activity(messages):
    """Typed feedback is evidence of retry activity; request counts are not."""
    events = []
    for message in messages:
        for part in message.parts:
            event = _retry_event(part)
            if event is not None:
                events.append(event)
    return {
        'output_retry_observed': any(e['scope'] == 'output' for e in events),
        'output_validation_retry_observed': any(e['scope'] == 'output'
            and e['cause'] in {'model_retry', 'validation_error'} for e in events),
        'tool_retry_observed': any(e['scope'] == 'tool' for e in events),
        'retry_events': events,
    }


def safe_error_metadata(exc, stage):
    """Expose only type names, integer status, fixed categories and stage."""
    chain = list(_exceptions(exc))
    status = next((e.status_code for e in chain if type(getattr(e, 'status_code', None)) is int), None)
    category = 'local_execution_error'
    if any(isinstance(e, (APIStatusError, ModelHTTPError)) for e in chain):
        category = 'provider_http_error'
    elif any(isinstance(e, APIConnectionError) for e in chain):
        category = 'provider_connection_error'
    elif any(isinstance(e, UsageLimitExceeded) for e in chain):
        category = 'usage_limit'
    elif any(isinstance(e, TypeError) for e in chain):
        category = 'local_type_error'
    for error in chain:
        tb = error.__traceback__
        while tb is not None:
            if tb.tb_frame.f_globals.get('__name__') == 'pam_evidence':
                stage = 'result_validation'
            tb = tb.tb_next
    return {'error_type': type(exc).__name__, 'exception_chain': [type(e).__name__ for e in chain],
            'http_status': status, 'category': category, 'stage': stage}


def failed_run_diagnostics(exc, messages, stage='agent_execution'):
    """Summarize a failed run captured by capture_run_messages, never its drafts."""
    result = safe_error_metadata(exc, stage)
    # Read only our validator's structured attributes; never parse retry text.
    rejections = getattr(exc, 'pam_validation_rejections', ())
    if isinstance(rejections, (tuple, list)):
        result['validation_rejections'] = [
            {'rejection': number, 'reason_codes': sorted({code for code in codes
                if isinstance(code, str) and code in VALIDATION_REASON_CODES})}
            for number, codes in enumerate(rejections, 1) if isinstance(codes, (tuple, list))
        ]
    for error in _exceptions(exc):
        codes = getattr(error, 'pam_validation_reason_codes', None)
        if isinstance(codes, (tuple, list)):
            result['terminal_validation_reason_codes'] = sorted({code for code in codes
                if isinstance(code, str) and code in VALIDATION_REASON_CODES})
            break
    evidence, trace = collect_evidence(messages)
    result.update({'evidence_ids': evidence, 'trace': trace,
                   'executed_tools': [e['tool'] for e in trace
                       if e['error'] in {None, 'asset_not_found', 'tool_error'}],
                   **retry_activity(messages)})
    # The terminal rejected retry may not have been appended to message history.
    terminal = []
    for error in _exceptions(exc):
        event = _retry_event(getattr(error, 'tool_retry', None))
        if event is not None:
            terminal.append(event)
    result['terminal_retry_events'] = terminal
    if result['category'] == 'local_execution_error' and terminal:
        event = terminal[0]
        if event['scope'] == 'output':
            result['category'] = ('output_validation_failure' if event['cause'] != 'no_output'
                                  else 'missing_output_failure')
        else:
            result['category'] = ('tool_availability_failure' if event['cause'] in
                                 {'unknown_tool', 'unavailable_tool'} else 'tool_retry_failure')
    elif (result['category'] == 'local_execution_error'
          and isinstance(exc, UnexpectedModelBehavior) and result['tool_retry_observed']):
        # Report observed context, not an inferred reason for retry exhaustion.
        result['category'] = 'framework_failure_after_tool_retry'
    # Captured responses provide partial reported usage, not a provider invoice
    # or the count of attempts that never returned a response.
    responses = [m for m in messages if isinstance(m, ModelResponse)]
    if responses:
        result['partial_usage'] = {
            'partial': True, 'recorded_model_responses': len(responses),
            'input_tokens': sum(m.usage.input_tokens for m in responses),
            'output_tokens': sum(m.usage.output_tokens for m in responses),
            'total_tokens': sum(m.usage.total_tokens for m in responses),
        }
    return result
