"""Offline validation by default; --live executes only previously unstarted rows.

Run: .venv/bin/python evals/run_batch.py [--live]
A durable started event reserves each scenario before its API call. If interrupted,
that scenario is deliberately not retried: its remote completion is unknowable.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TYPES = {'happy_path': 15, 'varied_phrasing': 12, 'edge_case': 10,
         'out_of_scope': 6, 'breaking': 7}
CATEGORIES = {'onboarding', 'password_rotation', 'web_connector', 'out_of_scope'}


def load_scenarios(path):
    with path.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ['question', 'category', 'type']:
            raise ValueError('CSV requires exactly question,category,type columns')
        rows = list(reader)
    seen = set()
    for number, row in enumerate(rows, 1):
        if (set(row) != {'question', 'category', 'type'}
                or not all(isinstance(v, str) and v.strip() for v in row.values())):
            raise ValueError(f'Invalid fields at scenario {number}')
        if row['type'] not in TYPES or row['category'] not in CATEGORIES:
            raise ValueError(f'Invalid classification at scenario {number}')
        normalized = ' '.join(row['question'].casefold().split())
        if normalized in seen:
            raise ValueError(f'Duplicate question at scenario {number}')
        seen.add(normalized)
        row['scenario_id'] = f'S{number:03d}'
    if Counter(r['type'] for r in rows) != TYPES:
        raise ValueError('Approved 50-scenario distribution required')
    return rows


def fingerprint():
    paths = ['evals/scenarios.csv', 'evals/run_batch.py', 'pam_agent_pydantic.py',
             'pam_tools.py', 'pam_evidence.py', 'pam_diagnostics.py',
             'pam_monitoring.py', 'uv.lock']
    paths += [f'data/pam_{kind}.json' for kind in ('knowledge', 'assets', 'tickets')]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def append_event(path, event):
    with path.open('a', encoding='utf-8') as target:
        target.write(json.dumps(event, ensure_ascii=False) + '\n')
        target.flush()
        os.fsync(target.fileno())


def read_events(path, rows, hashes):
    events = []
    if not path.exists():
        return events
    started, finished = set(), set()
    valid = {r['scenario_id']: r for r in rows}
    for line in path.read_text().splitlines():
        event = json.loads(line)  # Refuse truncated journals; never guess/replay.
        sid = event['scenario_id']
        if sid not in valid or event['fingerprints'] != hashes:
            raise ValueError('Results do not match current scenarios/code/data')
        if any(event[k] != valid[sid][k] for k in ('question', 'category', 'type')):
            raise ValueError('Result scenario fields mismatch')
        if event['event'] == 'started':
            if sid in started:
                raise ValueError('Duplicate start event')
            started.add(sid)
        elif event['event'] == 'result':
            if sid not in started or sid in finished:
                raise ValueError('Unlinked or duplicate result')
            finished.add(sid)
        else:
            raise ValueError('Unknown journal event')
        events.append(event)
    return events


def write_report(events):
    results = [e for e in events if e['event'] == 'result']
    started = {e['scenario_id'] for e in events if e['event'] == 'started'}
    completed = {e['scenario_id'] for e in results}
    success = [e for e in results if e['status'] == 'success']
    failed = [e for e in results if e['status'] == 'failure']
    lines = ['# Capstone Question 1 — batch execution report', '',
             f'Scenarios attempted: {len(started)}; completed successfully: {len(success)}; failed: {len(failed)}; interrupted/unknown: {len(started - completed)}.', '',
             'Execution success is not an answer-quality score. No gold labels or LLM judge were used.', '',
             '## Breakdown', '', '| Group | Attempted | Success | Failure |', '|---|---:|---:|---:|']
    starts = [e for e in events if e['event'] == 'started']
    for key, values in [('type', TYPES), ('category', sorted(CATEGORIES))]:
        for value in values:
            count = lambda records: sum(e[key] == value for e in records)
            lines.append(f'| {value} | {count(starts)} | {count(success)} | {count(failed)} |')
    tools = Counter(tool for e in results for tool in e['executed_tools'])
    lines += ['', '## Tools and informational checks', '',
              'Executed tool calls (including repeats within a single investigation): ' + json.dumps(dict(tools)),
              f"Citation membership passed: {sum(e['citation_validation_passed'] is True for e in results)}; failed: {sum(e['citation_validation_passed'] is False for e in results)}; unavailable: {sum(e['citation_validation_passed'] is None for e in results)}.", '',
              '| Scenario | Informational findings |', '|---|---|']
    for e in results:
        findings = list(dict.fromkeys(e['citation_issues'] + [c[1] for c in e['informational_findings']]))
        if findings:
            lines.append(f"| {e['scenario_id']} | " + ' '.join(findings).replace('|', '/') + ' |')
    totals = {key: sum(e['usage'].get(key, 0) for e in results) for key in ('input_tokens', 'output_tokens', 'total_tokens')}
    cost = sum(e['estimated_api_cost_usd'] or 0 for e in results)
    lines += ['', '## Usage and estimated cost', '', json.dumps(totals),
              f'Reported-token cost estimate: ${cost:.8f} USD. Existing monitoring rates: $0.15 input / $0.60 output per million tokens; excludes cache discounts and billing adjustments.',
              f"Partial or unavailable usage on {sum(e['usage_scope'] != 'complete' for e in results)} results; such runs make these totals incomplete, not zero-cost failures.", '',
              '## Failures', '']
    lines += [f"- {e['scenario_id']}: {e['error_type']}" for e in failed] or ['None.']
    if started - completed:
        lines.append('Interrupted/unknown, never automatically repeated: ' + ', '.join(sorted(started - completed)))
    lines += ['', '## Reproducibility and limitations', '',
              'results.jsonl is an append-only event journal: one started reservation and one terminal result per scenario. Count result events for answer review, not all lines. Each event stores SHA-256 scenario/data/code fingerprints, UTC timestamps, model, validation mode and package versions. Failed scenarios retain null answers and sanitized diagnostics, never fabricated outputs.',
              'CSV row order defines S001–S050 (header excluded). Resume skips every started scenario, including failures and interrupted reservations; concurrent runs are locked out. A partial journal line fails closed and requires manual review.',
              'The existing agent runs with validate_output=False, six model requests/eight tool executions and its existing tool-validation retry budget. No investigation or SDK transport retries are added. Informational checks do not establish claim-level grounding, correct tool selection, safe recommendations or current root causes. Review all answers manually, especially historical comparisons, conflicting inventory reports, unknown assets and breaking scenarios.',
              'Logfire uses the existing content-disabled instrumentation; trace IDs do not alone prove ingestion or dashboard visibility. No raw provider history, tool arguments, credentials or exception messages are saved. Generated answers are unredacted model output over synthetic inputs and require review.',
              'No additional experiments, judge calls, gold labels or quality scores.']
    (ROOT / 'evals/batch_report.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Authorize paid missing-scenario investigations')
    mode.add_argument('--dry-run', action='store_true', help='Validate only (default)')
    args = parser.parse_args()
    if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != 'feature/streamlit-ui':
        raise ValueError('Run only on feature/streamlit-ui')
    rows = load_scenarios(ROOT / 'evals/scenarios.csv')
    hashes = fingerprint()
    path = ROOT / 'evals/results.jsonl'
    # This lock contains no credentials and is harmless after the process exits.
    with (ROOT / 'evals/.batch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        events = read_events(path, rows, hashes)
        started = {e['scenario_id'] for e in events}
        pending = [r for r in rows if r['scenario_id'] not in started]
        print(f'Validated {len(rows)} scenarios; {len(pending)} unstarted.', flush=True)
        if not args.live:
            return
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        if not os.environ.get('OPENAI_API_KEY', '').strip():
            raise ValueError('OPENAI_API_KEY is required')
        import logfire
        from openai import AsyncOpenAI
        from pydantic_ai import capture_run_messages
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from pam_agent_pydantic import agent, investigate_with_evidence
        from pam_evidence import answer_validation_checks
        from pam_diagnostics import failed_run_diagnostics, retry_activity
        from pam_monitoring import initialize_monitoring, investigation_span, record_outcome, estimated_cost, EXPORT_STATUS_CODES
        monitoring = initialize_monitoring()
        model = OpenAIChatModel('gpt-4o-mini', provider=OpenAIProvider(
            openai_client=AsyncOpenAI(max_retries=0, timeout=60)))
        session = str(uuid.uuid4())
        metadata = {'fingerprints': hashes, 'model': 'gpt-4o-mini', 'validate_output': False,
                    'sdk_transport_retries': 0, 'monitoring_enabled': monitoring,
                    'versions': {p: version(p) for p in ('pydantic-ai-slim', 'openai', 'minsearch', 'logfire')}}
        for row in pending:
            base = {**row, **metadata}
            event = {**base, 'event': 'started', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}
            append_event(path, event)
            events.append(event)
            messages = []
            result = {**base, 'event': 'result', 'answer': None, 'citation_validation_passed': None,
                      'citation_issues': [], 'informational_findings': [], 'error_type': None}
            with investigation_span(session, monitoring) as span:
                try:
                    with capture_run_messages() as messages, agent.override(model=model):
                        summary = investigate_with_evidence(row['question'], validate_output=False)
                    result.update(status='success', answer=summary['answer'],
                                  citation_validation_passed=summary['citation_validation_passed'],
                                  citation_issues=summary['citation_issues'], trace=summary['trace'],
                                  evidence_ids=summary['evidence_ids'], usage=summary['usage'], usage_scope='complete',
                                  informational_findings=answer_validation_checks(summary['answer'], messages))
                    diagnostics = None
                except Exception as exc:
                    diagnostics = failed_run_diagnostics(exc, messages)
                    result.update(status='failure', error_type=diagnostics['error_type'],
                                  diagnostics=diagnostics, trace=diagnostics['trace'],
                                  evidence_ids=diagnostics['evidence_ids'], usage=diagnostics.get('partial_usage', {}),
                                  usage_scope='partial' if 'partial_usage' in diagnostics else 'unavailable')
                activity = retry_activity(messages)
                result['retry_activity'] = activity
                result['trace_id'] = record_outcome(span, result['usage'], activity, diagnostics=diagnostics)
            result['executed_tools'] = [e['tool'] for e in result['trace'] if e['error'] in {None, 'asset_not_found', 'tool_error'}]
            result['estimated_api_cost_usd'] = estimated_cost(result['usage'])
            result['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
            append_event(path, result)
            events.append(result)
            write_report(events)
            print(f"{row['scenario_id']}: {result['status']}", flush=True)
        logfire.force_flush(timeout_millis=10000)
        (ROOT / 'evals/monitoring_export.json').write_text(json.dumps({
            'monitoring_enabled': monitoring, 'recent_trace_export_http_statuses': list(EXPORT_STATUS_CODES)}, indent=2) + '\n')
        write_report(events)


if __name__ == '__main__':
    main()
