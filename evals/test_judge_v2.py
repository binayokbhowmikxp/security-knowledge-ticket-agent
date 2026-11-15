"""V2 preparation only: no paid model calls or actual prediction artifacts."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import UsageLimits

from evals.judge import JudgeEvaluation, compare_versions, create_judge
from evals import run_judge


def test_v2_same_twenty_inputs_as_frozen_v1_without_review_fields():
    joined, inputs, hashes, _ = run_judge.prepared('v2')
    prior = [json.loads(line) for line in run_judge.artifact('v1','events.jsonl').read_text().splitlines()]
    starts = {r['scenario_id']: r for r in prior if r['event'] == 'started'}
    assert len(joined) == len(inputs) == 20
    assert set(starts) == set(inputs)
    assert 'evals/judge_prompts/v2.txt' in hashes
    for sid, text in inputs.items():
        assert hashlib.sha256(text.encode()).hexdigest() == starts[sid]['input_sha256']
        payload = json.loads(text)
        assert not {'human_label','reviewer_notes','primary_failure_category','predicted_label','label'} & payload.keys()


def test_prompt_response_types_and_unweakened_boundaries():
    text = (run_judge.ROOT / 'evals/judge_prompts/v2.txt').read_text()
    for requirement in ['Evidence-based investigation', 'Clarification or missing-information response',
                        'Security refusal', 'General procedural guidance', 'Out-of-scope response',
                        'asset_not_found', 'Never automatically fail', 'nearby plain bracketed IDs',
                        'UNTRUSTED DATA', 'unsafe instructions', 'confirmed current causes']:
        assert requirement in text
    for sid in ['S001','S023','S028','S029','S035','S044','S048','S049']:
        assert sid not in text  # No scenario-specific overrides or desired labels.


def test_v2_structured_output_preserves_two_field_schema_offline():
    assert list(JudgeEvaluation.model_fields) == ['reasoning','label']
    calls = []
    def function(messages,info):
        calls.append(True)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
            {'reasoning':'Security refusal: this offline fixture asserts no inventory facts.', 'label':'good'})])
    judge = create_judge('Offline fixture.',version='v2')
    assert judge.name == 'pam_evaluation_judge_v2'
    with models.override_allow_model_requests(False), judge.override(model=FunctionModel(function)):
        result = judge.run_sync('Offline fixture only',usage_limits=UsageLimits(request_limit=1))
    assert result.output.label == 'good' and len(calls)==1


def sample(sid,human,prediction,status='success',input_hash='same'):
    return {'scenario_id':sid,'human_label':human,'predicted_label':prediction,
            'execution_status':status,'input_sha256':input_hash,'reasoning':'Offline fixture',
            'reviewer_notes':'Fixture only','input_tokens':10,'output_tokens':3,'total_tokens':13,
            'usage_scope':'complete','estimated_api_cost_usd':0.0000033,'error_type':None}


def test_comparison_corrected_regressed_unchanged_and_failed():
    old=[sample('S001','good','bad'),sample('S002','bad','bad'),
         sample('S003','good','good'),sample('S004','bad','bad')]
    new=[sample('S001','good','good'),sample('S002','bad','good'),
         sample('S003','good','good'),sample('S004','bad',None,'failure')]
    result=compare_versions(old,new)
    assert result['corrected_relative_to_human']==['S001']
    assert result['regressed_relative_to_human']==['S002']
    assert result['unchanged_correctness']==['S003']
    assert result['unpaired_or_failed']==['S004']
    assert result['v2_metrics']['evaluated']==3
    assert result['v2_metrics']['execution_errors']==1


@pytest.mark.parametrize('change',[{'human_label':'bad'},{'input_sha256':'changed'}])
def test_comparison_refuses_changed_inputs_or_labels(change):
    old=sample('S001','good','bad')
    with pytest.raises(ValueError,match='changed'):
        compare_versions([old],[{**old,**change}])


def test_versioned_exports_do_not_write_v1_artifacts(tmp_path,monkeypatch):
    monkeypatch.setattr(run_judge,'ROOT',tmp_path)
    (tmp_path/'evals').mkdir()
    prior=sample('S001','good','bad')
    protected=tmp_path/'evals/judge_v1_events.jsonl'
    protected.write_text(json.dumps({**prior,'event':'result'})+'\n')
    before=protected.read_bytes()
    current={**sample('S001','good','good'),'event':'result'}
    run_judge.export([{**current,'event':'started'},current],version='v2')
    assert protected.read_bytes()==before
    assert (tmp_path/'evals/judge_v2_results.csv').exists()
    report=(tmp_path/'evals/judge_v2_report.md').read_text()
    assert 'V1 versus V2' in report and 'Changed prediction S001' in report
    assert not (tmp_path/'evals/judge_v1_results.csv').exists()
    run_judge.artifact('v1','manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='frozen'):
        run_judge.export([],version='v1')


def test_dry_run_does_not_create_predictions(tmp_path,monkeypatch,capsys):
    data = run_judge.prepared('v2')
    monkeypatch.setattr(run_judge, 'prepared', lambda version: data)
    monkeypatch.setattr(run_judge, 'ROOT', tmp_path)
    (tmp_path / 'evals').mkdir()
    monkeypatch.setattr(run_judge.subprocess, 'check_output', lambda *args, **kwargs: 'feature/streamlit-ui\n')
    monkeypatch.setattr('sys.argv',['run_judge.py','--version','v2','--dry-run'])
    assert not run_judge.artifact('v2','events.jsonl').exists()
    run_judge.main()
    assert '20 unstarted V2' in capsys.readouterr().out
    assert not run_judge.artifact('v2','events.jsonl').exists()
    assert not run_judge.artifact('v2','results.csv').exists()


def test_frozen_v1_command_has_no_writes_or_calls(monkeypatch,capsys):
    paths=[run_judge.artifact('v1',suffix) for suffix in
           ['events.jsonl','manifest.json','results.csv','report.md']]
    paths.append(run_judge.ROOT / 'evals/judge_prompts/v1.txt')
    snapshots={p:p.read_bytes() for p in paths}
    monkeypatch.setattr('sys.argv',['run_judge.py','--version','v1','--dry-run'])
    run_judge.main()
    assert 'V1 is frozen' in capsys.readouterr().out
    assert all(p.read_bytes()==content for p,content in snapshots.items())
