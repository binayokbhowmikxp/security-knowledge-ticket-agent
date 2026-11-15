"""Versioned structured evaluation of saved outputs; never execute the PAM agent."""
import json
import re
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, AgentRetries


class JudgeEvaluation(BaseModel):
    reasoning: str = Field(min_length=1, description='Concise evidence-based assessment of this saved answer.')
    label: Literal['good', 'bad']


def create_judge(instructions, version='v1'):
    if version not in {'v1', 'v2'}:
        raise ValueError('Unsupported judge version')
    return Agent('openai:gpt-4o-mini', name=f'pam_evaluation_judge_{version}',
                 instructions=instructions, output_type=JudgeEvaluation,
                 retries=AgentRetries(tools=0, output=0), defer_model_check=True)


def join_labeled(results, labels):
    """Normalize case and join by ID, never by CSV row position."""
    by_id = {r['scenario_id']: r for r in results}
    if len(by_id) != len(results):
        raise ValueError('Duplicate result IDs')
    joined, seen = [], set()
    for row in labels:
        sid = row['scenario_id']
        label = row['label'].strip().lower()
        if sid in seen or sid not in by_id or label not in {'good', 'bad'}:
            raise ValueError('Invalid, duplicate or unmatched human label')
        seen.add(sid)
        joined.append((by_id[sid], {**row, 'label': label}))
    return sorted(joined, key=lambda pair: pair[0]['scenario_id'])


def verify_approved_labels(joined):
    from collections import Counter
    human = [label for _, label in joined]
    if (len(human) != 20 or Counter(r['label'] for r in human) != {'good': 10, 'bad': 10}
        or Counter(r['primary_failure_category'] for r in human if r['label'] == 'bad') != {
            'wrong_evidence_or_citation': 5, 'hallucination': 3,
            'incorrect_tool_use': 1, 'incomplete': 1}):
        raise ValueError('Human labels do not match the authorized 20/10/10/category counts')


def prepare_input(result, sources):
    """Explicit allowlist excludes all human labels, notes and failure categories."""
    kinds = {'search_documentation': 'data/pam_knowledge.json',
             'get_asset_details': 'data/pam_assets.json',
             'search_past_tickets': 'data/pam_tickets.json'}
    retrieved = {}
    for call in result['trace']:
        if call['error'] is not None:
            continue
        for sid in call['returned_ids']:
            if sid not in result['evidence_ids']:
                continue
            source = sources.get(sid)
            if source and source['dataset'] != kinds.get(call['tool']):
                raise ValueError('Source kind conflicts with actual tool')
            retrieved[sid] = {'origin': 'reconstructed from saved successful tool trace',
                              'source': source}
    if set(result['evidence_ids']) != set(retrieved):
        raise ValueError('Saved evidence IDs not confirmed by successful trace')
    mentioned_assets = set(re.findall(r'\b(?:LNX|WIN|APP)-\d{3}\b',
                                     result['question'] + '\n' + (result['answer'] or ''), re.I))
    reference = {}
    for asset_id in sorted({sid.upper() for sid in mentioned_assets} - set(retrieved)):
        source = sources.get(asset_id)
        reference[asset_id] = {'origin': 'REFERENCE INVENTORY ONLY — NOT RETRIEVED BY AGENT',
                                'source': source, 'exists_in_frozen_inventory': source is not None}
    payload = {
        'question': result['question'], 'full_saved_agent_response': result['answer'],
        'executed_tools': result['executed_tools'], 'safe_tool_trace': result['trace'],
        'retrieved_evidence_ids': sorted(retrieved), 'retrieved_records': retrieved,
        'reference_inventory_not_retrieved': reference,
        'nonauthoritative_informational_diagnostics': {
            'citation_validation_passed': result['citation_validation_passed'],
            'citation_issues': result['citation_issues'],
            'informational_findings': result['informational_findings']},
    }
    return json.dumps(payload, ensure_ascii=False)


def metrics(records):
    """Bad is positive; errors are excluded and reported separately."""
    valid = [r for r in records if r['execution_status'] == 'success']
    tp = sum(r['human_label'] == 'bad' and r['predicted_label'] == 'bad' for r in valid)
    fp = sum(r['human_label'] == 'good' and r['predicted_label'] == 'bad' for r in valid)
    fn = sum(r['human_label'] == 'bad' and r['predicted_label'] == 'good' for r in valid)
    tn = sum(r['human_label'] == 'good' and r['predicted_label'] == 'good' for r in valid)
    return {'evaluated': len(valid), 'execution_errors': len(records) - len(valid),
            'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn,
            'accuracy': (tp + tn) / len(valid) if valid else None,
            'precision_bad': tp / (tp + fp) if tp + fp else None,
            'recall_bad': tp / (tp + fn) if tp + fn else None,
            'disagreements': fp + fn}


def compare_versions(v1, v2):
    """Reporting only: compare paired predictions against unchanged human labels.

    Predictions/labels are never passed into prepare_input or the judge agent.
    Unpaired or failed evaluations are reported separately, never as corrections.
    """
    def indexed(rows):
        by_id = {r['scenario_id']: r for r in rows}
        if len(by_id) != len(rows):
            raise ValueError('Duplicate comparison IDs')
        return by_id
    old, new = indexed(v1), indexed(v2)
    corrected, regressed, unchanged, unpaired = [], [], [], []
    for sid in sorted(set(old) | set(new)):
        if sid not in old or sid not in new:
            unpaired.append(sid)
            continue
        a, b = old[sid], new[sid]
        if a['human_label'] != b['human_label'] or a['input_sha256'] != b['input_sha256']:
            raise ValueError('Cannot compare changed human labels or judge inputs')
        if a['execution_status'] != 'success' or b['execution_status'] != 'success':
            unpaired.append(sid)
            continue
        was_correct = a['predicted_label'] == a['human_label']
        now_correct = b['predicted_label'] == b['human_label']
        if not was_correct and now_correct:
            corrected.append(sid)
        elif was_correct and not now_correct:
            regressed.append(sid)
        else:
            unchanged.append(sid)
    return {'v1_metrics': metrics(v1), 'v2_metrics': metrics(v2),
            'corrected_relative_to_human': corrected, 'regressed_relative_to_human': regressed,
            'unchanged_correctness': unchanged, 'unpaired_or_failed': unpaired}
