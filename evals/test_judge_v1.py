"""Offline V1 preparation, one-shot structured output and measurement tests."""
import json

import pytest
from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import UsageLimits

from evals.judge import (JudgeEvaluation, create_judge, join_labeled, metrics,
                         prepare_input, verify_approved_labels)
from evals.label_evals import load_results, load_sources
from evals.run_judge import prepared, load_events


def test_join_uses_ids_and_normalizes_case():
    results = [{'scenario_id': 'S002'}, {'scenario_id': 'S001'}]
    joined = join_labeled(results, [{'scenario_id': 'S001', 'label': 'GOOD'},
                                    {'scenario_id': 'S002', 'label': 'Bad'}])
    assert [(r['scenario_id'], h['label']) for r,h in joined] == [('S001','good'),('S002','bad')]
    with pytest.raises(ValueError):
        join_labeled(results, [{'scenario_id': 'S999', 'label': 'Good'}])
    with pytest.raises(ValueError):
        join_labeled(results, [{'scenario_id': 'S001', 'label': 'Good'}] * 2)


def test_exact_authorized_subset_and_label_count_guard():
    joined, inputs, _, _ = prepared()
    assert len(joined) == len(inputs) == 20
    with pytest.raises(ValueError, match='authorized'):
        verify_approved_labels(joined[:-1])


def test_inputs_exclude_human_fields_and_preserve_response():
    results = load_results()
    sources = load_sources(results)
    result = {**results[8], 'label': 'PRIVATE_HUMAN_LABEL',
              'reviewer_notes': 'PRIVATE_NOTES', 'primary_failure_category': 'PRIVATE_CATEGORY'}
    text = prepare_input(result, sources)
    assert not any(marker in text for marker in ['PRIVATE_HUMAN_LABEL','PRIVATE_NOTES','PRIVATE_CATEGORY'])
    payload = json.loads(text)
    assert payload['full_saved_agent_response'] == result['answer']
    assert 'LNX-001' not in payload['retrieved_records']
    assert payload['reference_inventory_not_retrieved']['LNX-001']['source']['record']['asset_id'] == 'LNX-001'
    assert 'NOT RETRIEVED' in payload['reference_inventory_not_retrieved']['LNX-001']['origin']
    assert set(payload['retrieved_records']) == set(result['evidence_ids'])


def test_unretrieved_ids_cannot_be_promoted():
    results = load_results()
    bad = {**results[0], 'evidence_ids': results[0]['evidence_ids'] + ['LNX-001']}
    with pytest.raises(ValueError, match='confirmed'):
        prepare_input(bad, load_sources(results))


def test_reasoning_precedes_label_and_invalid_output_rejected():
    assert list(JudgeEvaluation.model_fields) == ['reasoning','label']
    with pytest.raises(ValidationError):
        JudgeEvaluation(reasoning='Valid explanation', label='unknown')
    with pytest.raises(ValidationError):
        JudgeEvaluation(reasoning='', label='bad')


def test_real_framework_offline_structured_output_one_request():
    calls = []
    def function(messages, info):
        calls.append(1)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
            {'reasoning': 'Specific missing evidence in this test fixture.', 'label': 'bad'})])
    judge = create_judge('Evaluate only this offline fixture.')
    with models.override_allow_model_requests(False), judge.override(model=FunctionModel(function)):
        result = judge.run_sync('Offline input', usage_limits=UsageLimits(request_limit=1))
    assert result.output.label == 'bad' and len(calls) == 1


def test_metrics_bad_positive_errors_not_predictions():
    def row(h,p,status='success'):
        return {'human_label':h,'predicted_label':p,'execution_status':status}
    m = metrics([row('bad','bad'),row('good','bad'),row('bad','good'),row('good','good'),
                 row('bad',None,'failure')])
    assert (m['TP'],m['FP'],m['FN'],m['TN']) == (1,1,1,1)
    assert m['accuracy'] == m['precision_bad'] == m['recall_bad'] == .5
    assert m['execution_errors'] == 1 and m['disagreements'] == 2
    assert metrics([])['accuracy'] is None
    assert metrics([row('good','good')])['precision_bad'] is None


def test_resume_skips_started_and_rejects_mixed_fingerprints(tmp_path):
    path=tmp_path/'events.jsonl'
    event={'scenario_id':'S001','event':'started','run_fingerprint':'frozen'}
    path.write_text(json.dumps(event)+'\n')
    assert len(load_events(path,'frozen',{'S001'})) == 1
    with pytest.raises(ValueError):
        load_events(path,'changed',{'S001'})
    path.write_text((json.dumps(event)+'\n')*2)
    with pytest.raises(ValueError):
        load_events(path,'frozen',{'S001'})
