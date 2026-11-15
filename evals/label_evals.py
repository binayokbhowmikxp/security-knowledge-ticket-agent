"""Human-only review of frozen Question 1 outputs. No agent or API imports.

Launch: .venv/bin/python -m streamlit run evals/label_evals.py
Course pattern: documentation-agent/evals/manual/app.py in
https://github.com/alexeygrigorev/ai-engineering-buildcamp-code
"""
from collections import Counter
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / 'evals/results.jsonl'
LABELS_PATH = ROOT / 'evals/labels.csv'
FAILURE_CATEGORIES = (
    'hallucination', 'wrong_evidence_or_citation', 'wrong_scope', 'incomplete',
    'incorrect_tool_use', 'unsafe_recommendation', 'other',
)
LABEL_FIELDS = ['scenario_id', 'label', 'primary_failure_category', 'reviewer_notes', 'updated_at']
SCENARIO_IDS = tuple(f'S{i:03d}' for i in range(1, 51))
SOURCE_ID = re.compile(r'\b[A-Z]+-\d{3}\b')


def load_results(path=RESULTS_PATH):
    """Read only terminal records, ordered by their original row-derived IDs."""
    records = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        if event.get('event') != 'result':
            continue
        sid = event['scenario_id']
        if sid in records:
            raise ValueError(f'Duplicate result for {sid}; review the journal.')
        returned = {source for call in event['trace'] if call['error'] is None
                    for source in call['returned_ids']}
        if not set(event['evidence_ids']) <= returned:
            raise ValueError(f'Evidence IDs conflict with saved tool trace for {sid}.')
        records[sid] = event
    if set(records) != set(SCENARIO_IDS):
        raise ValueError('Expected exactly 50 terminal results, S001–S050.')
    return [records[sid] for sid in SCENARIO_IDS]


def load_sources(results, root=ROOT):
    """Refuse reconstruction if local datasets differ from collected fingerprints."""
    sources = {}
    for filename, key in [('pam_knowledge.json', 'id'), ('pam_assets.json', 'asset_id'),
                          ('pam_tickets.json', 'ticket_id')]:
        relative = f'data/{filename}'
        content = (root / relative).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if any(result['fingerprints'].get(relative) != digest for result in results):
            raise ValueError(f'{relative} differs from the frozen batch dataset.')
        for record in json.loads(content):
            sid = record[key]
            if sid in sources:
                raise ValueError(f'Duplicate source ID {sid}.')
            sources[sid] = {'dataset': relative, 'record': record}
    return sources


def evidence_view(result, sources):
    """Mentions are never promoted to evidence, even if present in a dataset."""
    retrieved = {sid: sources.get(sid) for sid in result['evidence_ids']}
    mentions = set(SOURCE_ID.findall(result['question'] + '\n' + (result['answer'] or '')))
    return retrieved, sorted(mentions - set(retrieved))


def validate_label(row):
    if set(row) != set(LABEL_FIELDS) or not all(isinstance(v, str) for v in row.values()):
        raise ValueError('Invalid label CSV fields; existing file was preserved.')
    if row['scenario_id'] not in SCENARIO_IDS or row['label'] not in {'Good', 'Bad'}:
        raise ValueError('A known scenario and explicit Good or Bad decision are required.')
    category = row['primary_failure_category']
    if row['label'] == 'Bad' and category not in FAILURE_CATEGORIES:
        raise ValueError('Bad requires a primary failure category.')
    if row['label'] == 'Good' and category:
        raise ValueError('Good must not have a failure category.')
    if not row['updated_at']:
        raise ValueError('Saved labels require a confirmation timestamp.')


def load_labels(path=LABELS_PATH):
    if not path.exists():
        return {}
    with path.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != LABEL_FIELDS:
            raise ValueError('Invalid labels.csv header; existing file was preserved.')
        labels = {}
        for row in reader:
            validate_label(row)
            if row['scenario_id'] in labels:
                raise ValueError('Duplicate labels in CSV; resolve manually before saving.')
            labels[row['scenario_id']] = row
    return labels


def save_label(path, scenario_id, decision, category, notes, expected=None):
    """Merge under a lock; replace atomically; reject stale same-scenario edits.

    expected is the saved row shown when this reviewer opened the scenario, or
    None for an unlabeled scenario. Other scenarios' labels are always reloaded.
    """
    row = dict(zip(LABEL_FIELDS, [scenario_id, decision, (category or '') if decision == 'Bad' else '',
                                notes, datetime.now(timezone.utc).isoformat()]))
    validate_label(row)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        labels = load_labels(path)
        if labels.get(scenario_id) != expected:
            raise ValueError('This label changed in another session. Reload the saved label before editing.')
        labels[scenario_id] = row
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8',
                                             dir=path.parent, prefix='.labels-', suffix='.tmp',
                                             delete=False) as target:
                temporary = Path(target.name)
                writer = csv.DictWriter(target, fieldnames=LABEL_FIELDS, lineterminator='\n')
                writer.writeheader()
                writer.writerows(labels[sid] for sid in sorted(labels))
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return row


def label_counts(labels):
    return {'labeled': len(labels), 'Good': sum(r['label'] == 'Good' for r in labels.values()),
            'Bad': sum(r['label'] == 'Bad' for r in labels.values()),
            'failures': dict(Counter(r['primary_failure_category'] for r in labels.values()
                                     if r['label'] == 'Bad'))}


def next_unlabeled(results, labels, current):
    ids = [r['scenario_id'] for r in results]
    start = ids.index(current)
    return next((ids[(start + offset) % len(ids)] for offset in range(1, len(ids) + 1)
                 if ids[(start + offset) % len(ids)] not in labels), None)


def main():
    import streamlit as st

    st.set_page_config(page_title='PAM Agent Evaluation Console', layout='wide')
    st.title('PAM Agent Evaluation Console')
    st.caption('Review AI-generated investigations, inspect supporting evidence, and assess response quality.')
    st.caption('Informational checks never assign labels. '
               'Changes are saved only after Confirm label; navigation does not save drafts.')
    try:
        results = load_results()
        sources = load_sources(results)
        labels = load_labels(LABELS_PATH)
    except (ValueError, KeyError, OSError) as exc:
        st.error(str(exc))
        st.stop()
    counts = label_counts(labels)
    st.sidebar.write(f"Labeled: {counts['labeled']} / 50 · Good: {counts['Good']} · Bad: {counts['Bad']}")
    st.sidebar.progress(counts['labeled'] / 50)
    st.sidebar.subheader('Bad labels by primary failure')
    st.sidebar.json({category: counts['failures'].get(category, 0) for category in FAILURE_CATEGORIES})
    if 'selected_scenario' not in st.session_state:
        st.session_state.selected_scenario = next((sid for sid in SCENARIO_IDS if sid not in labels), 'S001')

    def move(offset):
        index = SCENARIO_IDS.index(st.session_state.selected_scenario)
        st.session_state.selected_scenario = SCENARIO_IDS[(index + offset) % 50]

    def move_unlabeled():
        target = next_unlabeled(results, labels, st.session_state.selected_scenario)
        if target:
            st.session_state.selected_scenario = target

    st.sidebar.selectbox('Scenario', SCENARIO_IDS, key='selected_scenario')
    left, right = st.sidebar.columns(2)
    left.button('Previous', on_click=move, args=(-1,))
    right.button('Next', on_click=move, args=(1,))
    st.sidebar.button('Next Unlabeled', on_click=move_unlabeled, disabled=len(labels) == 50)
    sid = st.session_state.selected_scenario
    result = results[SCENARIO_IDS.index(sid)]
    saved = labels.get(sid)
    st.subheader(f"{sid} · {result['type']} · {result['category']}")
    st.caption(f"Execution status: {result['status']} · Saved label: {saved['label'] if saved else 'Unlabeled'}")
    st.subheader('Question')
    st.text(result['question'])
    st.subheader('Full original agent answer')
    if result['answer'] is not None:
        st.text(result['answer'])
    else:
        st.info('No generated answer was saved for this failed execution.')
    with st.expander('Executed tools and informational findings', expanded=True):
        st.json({'executed_tools': result['executed_tools'], 'safe_trace': result['trace'],
                 'retrieved_evidence_ids': result['evidence_ids'],
                 'citation_validation_passed': result['citation_validation_passed'],
                 'citation_issues': result['citation_issues'],
                 'informational_findings': result['informational_findings']})
    retrieved, mentioned_only = evidence_view(result, sources)
    st.subheader('Retrieved evidence')
    st.caption('Reconstructed from saved evidence IDs and fingerprint-matched synthetic datasets. '
               'These are corresponding dataset records, not captured historical tool-response bodies.')
    if not retrieved:
        st.info('No successful evidence IDs were recorded.')
    for source_id, source in retrieved.items():
        with st.expander(f'{source_id} — reconstructed retrieved evidence'):
            if source is None:
                st.warning('No corresponding dataset record found; reconstruction unavailable.')
            else:
                st.caption(source['dataset'])
                st.json(source['record'])
    st.subheader('Mentioned in question/answer, not retrieved')
    st.text(', '.join(mentioned_only) if mentioned_only else 'None')
    st.caption('Mentioned IDs are not evidence; their dataset content is not displayed as retrieved.')

    keys = {name: f'{sid}_{name}' for name in ('decision', 'category', 'notes', 'baseline')}
    if any(key not in st.session_state for key in keys.values()):
        st.session_state[keys['baseline']] = saved
        st.session_state[keys['decision']] = saved['label'] if saved else None
        st.session_state[keys['category']] = (saved['primary_failure_category'] or None) if saved else None
        st.session_state[keys['notes']] = saved['reviewer_notes'] if saved else ''
    st.subheader('Human labeling decision')
    decision = st.radio('Decision', ['Good', 'Bad'], index=None, key=keys['decision'])
    category = st.selectbox('Primary failure category (required for Bad)', FAILURE_CATEGORIES,
                            index=None, key=keys['category'])
    notes = st.text_area('Reviewer notes — explain your decision', key=keys['notes'])
    if st.button('Confirm label', type='primary'):
        try:
            row = save_label(LABELS_PATH, sid, decision, category, notes,
                             expected=st.session_state[keys['baseline']])
        except (ValueError, OSError) as exc:
            st.error(str(exc))
        else:
            st.session_state[keys['baseline']] = row
            st.rerun()
    if st.button('Reload saved label (discard unsaved draft)'):
        for key in keys.values():
            st.session_state.pop(key, None)
        st.rerun()


if __name__ == '__main__':
    main()
