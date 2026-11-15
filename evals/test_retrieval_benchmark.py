"""Offline retrieval benchmark contracts; never execute the model or edit qrels."""
import csv
import json
from pathlib import Path

import pytest

import pam_tools
from evals import retrieval_benchmark as benchmark


def test_benchmark_schema_counts_and_valid_ids():
    collections = benchmark.load_collections()
    rows = benchmark.load_questions(benchmark.ROOT / 'evals/retrieval_questions.csv', collections)
    assert len(rows) == 20
    assert [r['benchmark_id'] for r in rows] == [f'R{i:02d}' for i in range(1,21)]
    assert sum(r['collection']=='documentation' for r in rows) == 10
    assert sum(r['collection']=='tickets' for r in rows) == 10
    # Every curated historical case is represented by at least one relevance judgment.
    relevant = {sid for r in rows if r['collection']=='tickets' for sid in r['relevant_ids']}
    assert relevant == {r['ticket_id'] for r in collections['tickets']}


@pytest.mark.parametrize('problem', ['header','reference','source_in_query','duplicate','count','empty'])
def test_invalid_benchmark_rejected(tmp_path,problem):
    with (benchmark.ROOT / 'evals/retrieval_questions.csv').open(newline='') as source:
        rows = list(csv.reader(source))
    if problem=='header':rows[0].append('gold_label')
    elif problem=='reference':rows[1][2]='TKT-999'
    elif problem=='source_in_query':rows[1][0]='Find ONB-001'
    elif problem=='duplicate':rows[2][0]=rows[1][0]
    elif problem=='count':rows.pop()
    else:rows[1][3]=' '
    path=tmp_path/'questions.csv'
    with path.open('w',newline='') as target:csv.writer(target).writerows(rows)
    with pytest.raises(ValueError):
        benchmark.load_questions(path,benchmark.load_collections())


def test_keyword_overlap_unique_tokens_and_stable_corpus_order():
    # A repeated term earns no extra score; non-searchable IDs/source_type earn none.
    records=[{'id':'Z','title':'alpha alpha alpha','content':'','source_type':'beta'},
             {'id':'A','title':'ALPHA','content':'BETA'},
             {'id':'B','title':'alpha','content':''},
             {'id':'beta','title':'no match','content':''}]
    assert benchmark.keyword_search('ALPHA beta',records,'documentation')==['A','Z','B']
    assert benchmark.keyword_search('alpha',records,'documentation')==['Z','A','B']
    assert benchmark.keyword_search('zzzznonexistent',records,'documentation')==[]
    assert benchmark.keyword_search('ALPHA beta',records,'documentation')==['A','Z','B']
    assert benchmark.tokens('a A x Alpha-beta PASSWORD_ROTATION')=={'alpha','beta','password_rotation'}


def test_same_searchable_fields_and_tokenization_as_production():
    collections=benchmark.load_collections()
    for name,spec in benchmark.COLLECTIONS.items():
        index=pam_tools._search_index(spec['filename'])
        assert index.text_fields==spec['text_fields']
        analyzer=index.vectorizers[spec['text_fields'][0]].build_analyzer()
        text='A Linux password-change timeout, HTTPS and account_type 123'
        assert benchmark.tokens(text)==set(analyzer(text))
        for record in collections[name]:
            assert set().union(*(benchmark.tokens(record[field]) for field in spec['text_fields']))


@pytest.mark.parametrize('collection,query,k',[
    ('documentation','Linux onboarding password rotation web connector',5),
    ('tickets','Linux onboarding password rotation web connector',4),
])
def test_retrieval_limits_and_same_number_of_positive_matches(collection,query,k):
    data=benchmark.load_collections()[collection]
    keyword=benchmark.keyword_search(query,data,collection)
    function=pam_tools.search_documentation if collection=='documentation' else pam_tools.search_past_tickets
    assert len(keyword)==len(function(query))==k
    assert len(set(keyword))==k


@pytest.mark.parametrize('ranking,relevant,k,expected',[
    (['b','x'],['b','c'],2,{'hit_at_1':1,'hit_at_k':1,'recall_at_k':.5,'mrr_at_k':1}),
    (['x','b','a'],['a','b','c'],2,{'hit_at_1':0,'hit_at_k':1,'recall_at_k':1/3,'mrr_at_k':.5}),
    (['x','y','a'],['a'],2,{'hit_at_1':0,'hit_at_k':0,'recall_at_k':0,'mrr_at_k':0}),
    ([],['a'],5,{'hit_at_1':0,'hit_at_k':0,'recall_at_k':0,'mrr_at_k':0}),
])
def test_metric_formulas_and_cutoff(ranking,relevant,k,expected):
    assert benchmark.score_ranking(ranking,relevant,k)==expected


def test_invalid_metrics_and_macro_aggregation():
    with pytest.raises(ValueError):benchmark.score_ranking(['a','a'],['a'],5)
    with pytest.raises(ValueError):benchmark.score_ranking([],[],5)
    with pytest.raises(ValueError):benchmark.score_ranking([],['a'],0)
    hit=benchmark.score_ranking(['a'],['a'],5)
    miss=benchmark.score_ranking([],['a'],4)
    rows=[{'collection':'documentation','tfidf':{'scores':hit},'keyword':{'scores':miss}},
          {'collection':'tickets','tfidf':{'scores':miss},'keyword':{'scores':hit}}]
    summary=benchmark.summarize(rows)
    assert summary['overall']['tfidf']['hit_at_k']==.5
    assert summary['overall']['keyword']['mrr_at_k']==.5
    assert summary['documentation']['tfidf']['recall_at_k']==1


def test_reproducible_results_saved_rankings_and_unchanged_qrels(tmp_path,monkeypatch):
    path=benchmark.ROOT/'evals/retrieval_questions.csv'
    before=path.read_bytes()
    first=benchmark.run_benchmark()
    pam_tools._load_records.cache_clear()
    pam_tools._search_index.cache_clear()
    assert benchmark.run_benchmark()==first
    assert first==json.loads((benchmark.ROOT/'evals/retrieval_benchmark_results.json').read_text())
    assert path.read_bytes()==before
    for row in first['queries']:
        assert len(row['tfidf']['ranked_ids'])==len(row['keyword']['ranked_ids'])<=row['k']
    (tmp_path/'evals').mkdir()
    monkeypatch.setattr(benchmark,'ROOT',tmp_path)
    benchmark.save_results(first)
    json_before=(tmp_path/'evals/retrieval_benchmark_results.json').read_bytes()
    csv_before=(tmp_path/'evals/retrieval_benchmark_results.csv').read_bytes()
    benchmark.save_results(first)
    assert (tmp_path/'evals/retrieval_benchmark_results.json').read_bytes()==json_before
    assert (tmp_path/'evals/retrieval_benchmark_results.csv').read_bytes()==csv_before
    with (tmp_path/'evals/retrieval_benchmark_results.csv').open(newline='') as source:
        exported=list(csv.DictReader(source))
    assert len(exported)==20
    assert exported[0]['tfidf_top_k']==';'.join(first['queries'][0]['tfidf']['ranked_ids'])
