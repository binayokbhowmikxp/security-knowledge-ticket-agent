"""Offline human-label storage and evidence provenance contracts."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from evals import label_evals as review


def test_only_terminal_results_in_original_order():
    results = review.load_results()
    assert len(results) == 50
    assert [r['scenario_id'] for r in results] == list(review.SCENARIO_IDS)
    assert all(r['event'] == 'result' for r in results)
    journal = [json.loads(line) for line in review.RESULTS_PATH.read_text().splitlines()]
    assert sum(r['event'] == 'started' for r in journal) == 50
    assert results[0]['answer'] == next(r['answer'] for r in journal if r['event'] == 'result')


def test_duplicate_result_rejected(tmp_path):
    rows = review.load_results()
    path = tmp_path / 'results.jsonl'
    path.write_text('\n'.join(json.dumps(r) for r in rows + [rows[0]]))
    with pytest.raises(ValueError, match='Duplicate result'):
        review.load_results(path)


def test_resolve_all_retrieved_kinds_and_separate_unretrieved_mentions():
    results = review.load_results()
    sources = review.load_sources(results)
    assert len(sources) == 52  # 25 articles + 12 assets + 15 tickets
    assert sources['ONB-001']['dataset'] == 'data/pam_knowledge.json'
    assert sources['LNX-001']['record']['asset_id'] == 'LNX-001'
    assert sources['TKT-001']['record']['ticket_id'] == 'TKT-001'
    for result in results:
        retrieved, _ = review.evidence_view(result, sources)
        assert set(retrieved) == set(result['evidence_ids'])
        assert all(value is not None for value in retrieved.values())
    retrieved, mentioned = review.evidence_view(results[8], sources)
    assert 'LNX-001' in mentioned and 'LNX-001' not in retrieved
    retrieved, mentioned = review.evidence_view(results[46], sources)
    assert 'ROT-999' in mentioned and 'ROT-999' not in retrieved


def test_frozen_dataset_mismatch_rejected(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/pam_knowledge.json').write_text('[]')
    with pytest.raises(ValueError, match='frozen batch dataset'):
        review.load_sources(review.load_results(), tmp_path)


def test_save_reload_update_preserves_other_labels_and_multiline_notes(tmp_path):
    path = tmp_path / 'labels.csv'
    assert review.load_labels(path) == {}
    first = review.save_label(path, 'S001', 'Bad', 'incomplete', 'Missing detail, evidence\nand context')
    review.save_label(path, 'S002', 'Good', '', 'Supported')
    review.save_label(path, 'S001', 'Good', '', 'Reconsidered', expected=first)
    labels = review.load_labels(path)
    assert len(labels) == 2
    assert labels['S001']['label'] == 'Good' and labels['S001']['primary_failure_category'] == ''
    assert labels['S002']['reviewer_notes'] == 'Supported'
    with pytest.raises(ValueError, match='another session'):
        review.save_label(path, 'S001', 'Bad', 'other', 'Stale edit', expected=first)
    assert review.load_labels(path) == labels


@pytest.mark.parametrize('decision,category', [(None, ''), ('Bad', ''), ('Bad', 'unknown')])
def test_unconfirmed_or_invalid_labels_never_saved(tmp_path, decision, category):
    path = tmp_path / 'labels.csv'
    with pytest.raises(ValueError):
        review.save_label(path, 'S001', decision, category, '')
    assert not path.exists()


def test_concurrent_different_scenarios_merge_without_lost_rows(tmp_path):
    path = tmp_path / 'labels.csv'
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda sid: review.save_label(path, sid, 'Good', '', 'Human test fixture'),
                      review.SCENARIO_IDS[:8]))
    assert len(review.load_labels(path)) == 8


def test_failed_atomic_replace_keeps_existing_labels(tmp_path, monkeypatch):
    path = tmp_path / 'labels.csv'
    review.save_label(path, 'S001', 'Good', '', 'Existing')
    previous = path.read_bytes()
    def fail(*args):
        raise OSError('simulated disk failure')
    monkeypatch.setattr(review.os, 'replace', fail)
    with pytest.raises(OSError):
        review.save_label(path, 'S002', 'Bad', 'other', 'Not persisted')
    assert path.read_bytes() == previous
    assert not list(tmp_path.glob('.labels-*.tmp'))


def test_duplicate_or_corrupt_labels_refuse_writes(tmp_path):
    path = tmp_path / 'labels.csv'
    review.save_label(path, 'S001', 'Good', '', 'Existing')
    lines = path.read_text().splitlines()
    path.write_text('\n'.join(lines + [lines[1]]) + '\n')
    before = path.read_bytes()
    with pytest.raises(ValueError, match='Duplicate labels'):
        review.save_label(path, 'S002', 'Good', '', 'New')
    assert path.read_bytes() == before


def test_category_counts_and_next_unlabeled(tmp_path):
    path = tmp_path / 'labels.csv'
    review.save_label(path, 'S001', 'Bad', 'incomplete', '')
    review.save_label(path, 'S002', 'Bad', 'incomplete', '')
    review.save_label(path, 'S003', 'Bad', 'wrong_scope', '')
    review.save_label(path, 'S004', 'Good', '', '')
    labels = review.load_labels(path)
    assert review.label_counts(labels) == {'labeled': 4, 'Good': 1, 'Bad': 3,
                                          'failures': {'incomplete': 2, 'wrong_scope': 1}}
    assert review.next_unlabeled(review.load_results(), labels, 'S001') == 'S005'
    assert review.next_unlabeled(review.load_results(), labels, 'S050') == 'S005'
    assert review.next_unlabeled(review.load_results(), dict.fromkeys(review.SCENARIO_IDS), 'S001') is None


def test_ui_requires_human_confirmation_and_persists_after_restart(tmp_path, monkeypatch):
    path = tmp_path / 'labels.csv'
    monkeypatch.setattr(review, 'LABELS_PATH', path)
    ui = AppTest.from_string('from evals.label_evals import main\nmain()').run()
    assert not ui.exception
    assert not path.exists()
    assert ui.radio[0].value is None
    ui.radio[0].set_value('Bad').run()
    next(b for b in ui.button if b.label == 'Confirm label').click().run()
    assert not path.exists()  # Bad with no primary category cannot persist.
    next(s for s in ui.selectbox if s.label.startswith('Primary')).set_value('incomplete').run()
    ui.text_area[0].set_value('Human test fixture').run()
    next(b for b in ui.button if b.label == 'Confirm label').click().run()
    assert not ui.exception
    assert review.load_labels(path)['S001']['label'] == 'Bad'
    next(b for b in ui.button if b.label == 'Next').click().run()
    assert ui.session_state['selected_scenario'] == 'S002'
    next(b for b in ui.button if b.label == 'Previous').click().run()
    assert ui.radio[0].value == 'Bad'
    restarted = AppTest.from_string('from evals.label_evals import main\nmain()').run()
    assert not restarted.exception
    assert restarted.session_state['selected_scenario'] == 'S002'
    assert any('Labeled: 1 / 50' in t.value for t in restarted.sidebar.markdown)
