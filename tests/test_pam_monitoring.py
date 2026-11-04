"""Monitoring checks are offline; no telemetry or model API requests."""
import json
import subprocess
import sys
from unittest.mock import Mock

import pytest
import pam_monitoring as monitoring


def test_cost_and_partial_accumulation():
    usage = dict(input_tokens=1000, output_tokens=500, total_tokens=1500)
    assert monitoring.estimated_cost(usage) == pytest.approx(0.00045)
    first = monitoring.add_usage({}, usage)
    second = monitoring.add_usage(first, usage, partial=True)
    assert first['total_tokens'] == 1500
    assert second['total_tokens'] == 3000
    assert second['estimated_usd'] == pytest.approx(0.0009)
    assert second['incomplete_runs'] == 1
    assert monitoring.estimated_cost({}) is None
    assert monitoring.add_usage({}, {}, partial=True)['incomplete_runs'] == 1


def test_initialization_once_and_privacy(monkeypatch):
    configure, instrument = Mock(), Mock()
    monkeypatch.setenv('LOGFIRE_TOKEN', 'OFFLINE_ONLY')
    monkeypatch.setattr(monitoring.logfire, 'configure', configure)
    monkeypatch.setattr(monitoring.logfire, 'instrument_pydantic_ai', instrument)
    monitoring.initialize_monitoring.cache_clear()
    try:
        assert monitoring.initialize_monitoring()
        assert monitoring.initialize_monitoring()
        configure.assert_called_once()
        options = configure.call_args.kwargs
        assert options['console'] is False and options['inspect_arguments'] is False
        assert 'scrubbing' not in options  # Default scrubbing remains enabled.
        assert options['advanced'].exception_callback is monitoring.suppress_exception_content
        assert instrument.call_args.kwargs == dict(include_content=False,
            include_binary_content=False, include_model_request_parameters=False)
    finally:
        monitoring.initialize_monitoring.cache_clear()


def test_missing_write_token(monkeypatch):
    monkeypatch.delenv('LOGFIRE_TOKEN', raising=False)
    configure = Mock()
    monkeypatch.setattr(monitoring.logfire, 'configure', configure)
    monitoring.initialize_monitoring.cache_clear()
    try:
        assert monitoring.initialize_monitoring() is False
        configure.assert_not_called()
    finally:
        monitoring.initialize_monitoring.cache_clear()


def test_actual_exported_spans_exclude_content_and_exception_payloads():
    # Isolate global instrumentation from the rest of pytest. Export only in memory.
    script = '''
import json
import logfire
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pam_monitoring import suppress_exception_content
exporter = InMemorySpanExporter()
logfire.configure(send_to_logfire=False, console=False, inspect_arguments=False,
    additional_span_processors=[SimpleSpanProcessor(exporter)],
    advanced=logfire.AdvancedOptions(exception_callback=suppress_exception_content,
        emit_configuration_span=False, pending_spans=False))
agent = Agent('openai:gpt-4o-mini', defer_model_check=True)
@agent.tool_plain
def lookup(query: str):
    return 'PRIVATE_TOOL_RESULT'
def model(messages, info):
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart('lookup', {'query': 'PRIVATE_ARGUMENT'})])
    return ModelResponse(parts=[TextPart('PRIVATE_ANSWER')])
logfire.instrument_pydantic_ai(agent, include_content=False,
    include_binary_content=False, include_model_request_parameters=False)
with agent.override(model=FunctionModel(model)):
    with logfire.span('PAM investigation'):
        agent.run_sync('PRIVATE_PROMPT')
def fail(messages, info):
    raise RuntimeError('PRIVATE_EXCEPTION')
try:
    with agent.override(model=FunctionModel(fail)):
        agent.run_sync('PRIVATE_FAILED_PROMPT')
except RuntimeError:
    pass
spans = exporter.get_finished_spans()
serialized = json.dumps([dict(name=s.name, attributes=dict(s.attributes or {}),
    status=s.status.description, events=[dict(name=e.name, attributes=dict(e.attributes or {}))
    for e in s.events]) for s in spans], default=str)
assert 'PRIVATE_' not in serialized, 'Content leaked into telemetry'
assert any('lookup' in s.name for s in spans)
assert any(s.status.status_code.name == 'ERROR' for s in spans)
assert any(s.parent is not None for s in spans)
print('privacy verified')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    # Do not print subprocess output: a regression could contain sensitive content.
    assert result.returncode == 0, 'Offline telemetry privacy subprocess failed'
    assert result.stdout.strip() == 'privacy verified'
