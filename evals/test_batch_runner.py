"""Offline checks for CSV validation and fail-closed resume bookkeeping."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('batch_runner', Path(__file__).with_name('run_batch.py'))
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def test_approved_csv_order_and_ids():
    rows = batch.load_scenarios(batch.ROOT / 'evals/scenarios.csv')
    assert len(rows) == 50
    assert [r['scenario_id'] for r in rows] == [f'S{i:03d}' for i in range(1, 51)]


@pytest.mark.parametrize('problem', ['header', 'empty', 'duplicate', 'type', 'count'])
def test_invalid_scenarios_rejected(tmp_path, problem):
    with (batch.ROOT / 'evals/scenarios.csv').open(newline='') as f:
        rows = list(csv.reader(f))
    if problem == 'header':
        rows[0].append('answer')
    elif problem == 'empty':
        rows[1][0] = ' '
    elif problem == 'duplicate':
        rows[2][0] = rows[1][0].upper()
    elif problem == 'type':
        rows[1][2] = 'unsupported'
    else:
        rows.pop()
    path = tmp_path / 'scenarios.csv'
    with path.open('w', newline='') as f:
        csv.writer(f).writerows(rows)
    with pytest.raises(ValueError):
        batch.load_scenarios(path)


def test_resume_reserves_interrupted_and_failed_rows(tmp_path):
    rows = batch.load_scenarios(batch.ROOT / 'evals/scenarios.csv')
    hashes = {'data': 'test-hash'}
    path = tmp_path / 'results.jsonl'
    events = [{**rows[0], 'fingerprints': hashes, 'event': 'started'},
              {**rows[0], 'fingerprints': hashes, 'event': 'result', 'status': 'failure'},
              {**rows[1], 'fingerprints': hashes, 'event': 'started'}]
    for event in events:
        batch.append_event(path, event)
    saved = batch.read_events(path, rows, hashes)
    assert {e['scenario_id'] for e in saved} == {'S001', 'S002'}
    assert len([r for r in rows if r['scenario_id'] not in {e['scenario_id'] for e in saved}]) == 48
    with pytest.raises(ValueError):
        batch.read_events(path, rows, {'data': 'changed'})
    batch.append_event(path, events[0])
    with pytest.raises(ValueError, match='Duplicate start'):
        batch.read_events(path, rows, hashes)


def test_partial_journal_refuses_replay(tmp_path):
    path = tmp_path / 'results.jsonl'
    path.write_text('{"event":')
    with pytest.raises(json.JSONDecodeError):
        batch.read_events(path, [], {})
