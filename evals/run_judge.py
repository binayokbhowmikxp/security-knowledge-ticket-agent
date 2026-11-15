"""Versioned judge runner. Dry-run by default; use --version v2 for the pending iteration."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.judge import create_judge, join_labeled, metrics, prepare_input, verify_approved_labels, compare_versions
from evals.label_evals import load_results, load_sources
from evals.run_batch import append_event

def artifact(version, suffix):
    if version not in {'v1', 'v2'}:
        raise ValueError('Unsupported judge version')
    return ROOT / f'evals/judge_{version}_{suffix}'

FIELDS = ['scenario_id', 'human_label', 'predicted_label', 'reasoning', 'execution_status',
          'error_type', 'input_tokens', 'output_tokens', 'total_tokens', 'usage_scope',
          'estimated_api_cost_usd', 'reviewer_notes', 'timestamp_utc', 'input_sha256', 'run_fingerprint']


def prepared(version='v1'):
    if version not in {'v1', 'v2'}:
        raise ValueError('Unsupported judge version')
    results = load_results()
    sources = load_sources(results)
    with (ROOT / 'evals/labels.csv').open(newline='', encoding='utf-8') as f:
        labels = list(csv.DictReader(f))
    joined = join_labeled(results, labels)
    verify_approved_labels(joined)
    inputs = {r['scenario_id']: prepare_input(r, sources) for r, _ in joined}
    paths = ['evals/judge.py', 'evals/run_judge.py', f'evals/judge_prompts/{version}.txt',
             'evals/label_evals.py', 'evals/results.jsonl', 'evals/labels.csv', 'uv.lock']
    paths += [f'data/pam_{name}.json' for name in ['knowledge', 'assets', 'tickets']]
    if version == 'v2':
        # Eligibility/comparison only; V1 predictions never enter model input.
        prior = [json.loads(line) for line in artifact('v1', 'events.jsonl').read_text().splitlines()]
        prior_results = {row['scenario_id']: row for row in prior if row['event'] == 'result'}
        if set(prior_results) != set(inputs):
            raise ValueError('V2 must use exactly the same 20 V1 scenario IDs')
        for result, human in joined:
            sid = result['scenario_id']
            if (prior_results[sid]['human_label'] != human['label'] or
                prior_results[sid]['input_sha256'] != hashlib.sha256(inputs[sid].encode()).hexdigest()):
                raise ValueError('V2 human labels or prepared inputs differ from V1')
        paths += ['evals/judge_v1_events.jsonl', 'evals/judge_v1_manifest.json', 'evals/judge_prompts/v1.txt']
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return joined, inputs, hashes, digest


def load_events(path, digest, ids):
    if not path.exists():
        return []
    events, started, finished = [], set(), set()
    for line in path.read_text().splitlines():
        row = json.loads(line)
        sid = row['scenario_id']
        if row['run_fingerprint'] != digest or sid not in ids:
            raise ValueError('Judge inputs or prompt changed; refusing repeat or mixed runs')
        if row['event'] == 'started' and sid not in started:
            started.add(sid)
        elif row['event'] == 'result' and sid in started and sid not in finished:
            finished.add(sid)
        else:
            raise ValueError('Duplicate/unlinked journal event')
        events.append(row)
    return events


def export(events, version='v1'):
    if version == 'v1' and artifact(version, 'manifest.json').exists():
        raise ValueError('Completed V1 artifacts are frozen; export is disabled')
    records = [r for r in events if r['event'] == 'result']
    destination = artifact(version, 'results.csv')
    temporary = destination.with_suffix('.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, destination)
    m = metrics(records)
    started = {r['scenario_id'] for r in events if r['event'] == 'started'}
    finished = {r['scenario_id'] for r in records}
    lines = [f'# Judge {version.upper()} report', '', 'Bad is the positive class. Errors are not predictions.', '',
             f'Attempted: {len(started)} / 20; completed predictions: {m["evaluated"]}; execution errors: {m["execution_errors"]}; interrupted/unknown: {len(started - finished)}.', '',
             '## Metrics', '', '```json', json.dumps(m, indent=2), '```', '',
             '| Human / Judge | Good | Bad |', '|---|---:|---:|',
             f'| Good | {m["TN"]} (TN) | {m["FP"]} (FP) |',
             f'| Bad | {m["FN"]} (FN) | {m["TP"]} (TP) |', '',
             'Undefined denominators are reported as null, not fabricated zero scores. Metrics use only successfully judged examples.', '',
             '## Every disagreement', '']
    disagreements = [r for r in records if r['execution_status'] == 'success' and r['human_label'] != r['predicted_label']]
    for r in disagreements:
        lines += [f'### {r["scenario_id"]}', '',
                  f'Human: **{r["human_label"]}**; Judge {version.upper()}: **{r["predicted_label"]}**.', '',
                  'Judge reasoning:', '', '> ' + r['reasoning'].replace('\n', '\n> '), '',
                  'Human reviewer notes:', '', '> ' + (r['reviewer_notes'] or '(none)').replace('\n', '\n> '), '',
                  'Initial observation: the quoted assessments apply different judgments to this answer. Compare the specific evidence/citation or completeness requirement in the judge reasoning with the reviewer notes; this disagreement alone does not establish which assessment is correct.', '']
    if not disagreements:
        lines += ['None among completed predictions.', '']
    lines += ['## Execution errors', '']
    errors = [r for r in records if r['execution_status'] == 'failure']
    lines += [f'- {r["scenario_id"]}: {r["error_type"]} (no predicted label)' for r in errors] or ['None.']
    totals = {key: sum(r[key] or 0 for r in records) for key in ['input_tokens', 'output_tokens', 'total_tokens']}
    cost = sum(r['estimated_api_cost_usd'] or 0 for r in records)
    lines += ['', '## Usage and reproducibility', '', json.dumps(totals),
              f'Estimated API cost: **${cost:.8f} USD**, using existing $0.15 input/$0.60 output per million token constants; not an invoice and excludes cache discounts.',
              f'Partial/unavailable usage: {sum(r["usage_scope"] != "complete" for r in records)} evaluations; missing usage is not zero actual cost.', '',
              'Model: real OpenAI gpt-4o-mini; PydanticAI structured JudgeEvaluation with reasoning before label. One model request maximum; transport, tool and output retries disabled. The original PAM agent was not executed.',
              'Input preparation joins by scenario_id and never supplies human labels, notes or categories to the judge. Retrieved record reconstructions require successful saved traces. Reference inventory is separately marked NOT RETRIEVED; diagnostics are nonauthoritative. Frozen dataset hashes are checked against Question 1 fingerprints.',
              f'judge_{version}_manifest.json records prompt/data/code/label fingerprints and package versions. Per-input SHA-256 is stored in results. The append-only judge_{version}_events.jsonl reserves each ID before calling and saves results immediately; resumption skips all started IDs, including errors/interrupted calls. A changed fingerprint or corrupt journal fails closed.',
              f'{version.upper()} criteria were written before execution. Metrics compare a small human-reviewed subset; they are not proof of judge correctness or generalization. No human-label changes or original-agent reruns. Stop for ChatGPT disagreement review.']
    if version == 'v2':
        prior = [json.loads(line) for line in artifact('v1', 'events.jsonl').read_text().splitlines()]
        comparison = compare_versions([r for r in prior if r['event'] == 'result'], records)
        lines += ['', '## V1 versus V2 (Bad positive)', '',
                  'Metrics include only successful predictions per version; compare coverage before interpreting changes.',
                  '```json', json.dumps(comparison, indent=2), '```', '',
                  'Corrected/regressed means agreement with the unchanged human label, not independent factual adjudication.',
                  'Review each changed prediction and its saved reasoning to determine whether the change reflects a genuine rubric improvement.']
        by_id = {r['scenario_id']: r for r in prior if r['event'] == 'result'}
        for record in records:
            sid = record['scenario_id']
            if record['execution_status'] != 'success' or sid not in by_id:
                continue
            if record['predicted_label'] != by_id[sid]['predicted_label']:
                lines += ['', f'### Changed prediction {sid}', '',
                          f'Human: {record["human_label"]}; V1: {by_id[sid]["predicted_label"]}; V2: {record["predicted_label"]}.',
                          '', 'V1 reasoning:', '', '> ' + by_id[sid]['reasoning'].replace('\n', '\n> '),
                          '', 'V2 reasoning:', '', '> ' + record['reasoning'].replace('\n', '\n> ')]
    artifact(version, 'report.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.live and args.dry_run:
        raise ValueError('Choose dry-run or live')
    if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != 'feature/streamlit-ui':
        raise ValueError('Only feature/streamlit-ui is authorized')
    version = args.version
    joined, inputs, hashes, digest = prepared(version)
    journal = artifact(version, 'events.jsonl')
    # V1 is immutable history, not a new run under the versioned runner's code.
    if version == 'v1' and journal.exists():
        manifest = json.loads(artifact(version, 'manifest.json').read_text())
        for path, old_hash in manifest['fingerprints'].items():
            if path not in {'evals/judge.py', 'evals/run_judge.py'} and hashes.get(path) != old_hash:
                raise ValueError('Frozen V1 source data, labels or prompt changed')
        events = load_events(journal, manifest['run_fingerprint'], set(inputs))
        for row in events:
            if row['input_sha256'] != hashlib.sha256(inputs[row['scenario_id']].encode()).hexdigest():
                raise ValueError('Frozen V1 input preparation changed')
        print('V1 is frozen; inputs verified. No calls or artifact writes permitted. Use --version v2.')
        return
    if version == 'v1':
        raise ValueError('Only preparation/execution of V2 is supported; V1 is frozen')
    with (ROOT / f'evals/.judge_{version}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        events = load_events(journal, digest, set(inputs))
        started = {r['scenario_id'] for r in events}
        pending = [(r, human) for r, human in joined if r['scenario_id'] not in started]
        print(f'Verified 20 labels (10 good/10 bad); {len(pending)} unstarted {version.upper()} evaluations.', flush=True)
        if not args.live:
            return
        if not pending:
            export(events, version)
            return
        from dotenv import load_dotenv
        from importlib.metadata import version as package_version
        from openai import AsyncOpenAI
        from pydantic_ai import capture_run_messages
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.usage import UsageLimits
        from pam_diagnostics import failed_run_diagnostics
        from pam_monitoring import estimated_cost
        load_dotenv(ROOT / '.env')
        if not os.environ.get('OPENAI_API_KEY', '').strip():
            raise ValueError('OPENAI_API_KEY required')
        manifest = {'version': version, 'model': 'gpt-4o-mini', 'fingerprints': hashes,
                    'run_fingerprint': digest, 'sdk_retries': 0, 'request_limit': 1,
                    'versions': {p: package_version(p) for p in ['pydantic-ai-slim', 'openai', 'pydantic']}}
        artifact(version, 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        instructions = (ROOT / f'evals/judge_prompts/{version}.txt').read_text()
        judge = create_judge(instructions, version=version)
        model = OpenAIChatModel('gpt-4o-mini', provider=OpenAIProvider(
            openai_client=AsyncOpenAI(max_retries=0, timeout=60)))
        for result, human in pending:
            sid = result['scenario_id']
            base = {'scenario_id': sid, 'human_label': human['label'],
                    'reviewer_notes': human.get('reviewer_notes', ''), 'run_fingerprint': digest,
                    'input_sha256': hashlib.sha256(inputs[sid].encode()).hexdigest()}
            event = {**base, 'event': 'started', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}
            append_event(journal, event)
            events.append(event)
            messages = []
            row = {**base, 'event': 'result', 'predicted_label': None, 'reasoning': None, 'error_type': None}
            try:
                with capture_run_messages() as messages, judge.override(model=model):
                    response = judge.run_sync(inputs[sid], usage_limits=UsageLimits(request_limit=1))
                usage = {key: getattr(response.usage, key) for key in ['input_tokens', 'output_tokens', 'total_tokens']}
                row.update(execution_status='success', predicted_label=response.output.label,
                           reasoning=response.output.reasoning, usage_scope='complete')
            except Exception as exc:
                diagnostics = failed_run_diagnostics(exc, messages, 'judge_execution')
                usage = diagnostics.get('partial_usage', {})
                row.update(execution_status='failure', error_type=diagnostics['error_type'],
                           usage_scope='partial' if usage else 'unavailable', diagnostics=diagnostics)
            row.update({key: usage.get(key) for key in ['input_tokens', 'output_tokens', 'total_tokens']})
            row['estimated_api_cost_usd'] = estimated_cost(usage)
            row['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
            append_event(journal, row)
            events.append(row)
            export(events, version)
            print(f'{sid}: {row["execution_status"]}', flush=True)


if __name__ == '__main__':
    main()
