"""Offline comparison only: production TF-IDF versus unique keyword overlap.

Run from the repository root: uv run python evals/retrieval_benchmark.py
Draft relevance judgments live in retrieval_questions.csv; this script never edits them.
"""
from collections import Counter
import csv
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pam_tools

COLLECTIONS = {
    'documentation': {
        'filename': 'pam_knowledge.json', 'id_field': 'id', 'k': 5,
        'text_fields': ['title', 'content', 'category', 'platform'],
    },
    'tickets': {
        'filename': 'pam_tickets.json', 'id_field': 'ticket_id', 'k': 4,
        'text_fields': ['issue_summary', 'category', 'related_asset',
                        'investigation_findings', 'documented_outcome'],
    },
}
QUESTION_FIELDS = ['query', 'collection', 'relevant_ids', 'relevance_reason']
METRICS = ['hit_at_1', 'hit_at_k', 'recall_at_k', 'mrr_at_k']
# Same default word-token rule and lowercase normalization as current minsearch.
TOKEN = re.compile(r'(?u)\b\w\w+\b')


def load_collections():
    return {name: json.loads((ROOT / 'data' / spec['filename']).read_text(encoding='utf-8'))
            for name, spec in COLLECTIONS.items()}


def load_questions(path, collections):
    with path.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != QUESTION_FIELDS:
            raise ValueError('Expected query,collection,relevant_ids,relevance_reason columns')
        rows = list(reader)
    seen = set()
    for number, row in enumerate(rows, 1):
        if set(row) != set(QUESTION_FIELDS) or not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError(f'Invalid fields at row {number}')
        name = row['collection']
        if name not in COLLECTIONS:
            raise ValueError(f'Unknown collection at row {number}')
        pam_tools.validate_text(row['query'], 'query')
        if re.search(r'\b[A-Za-z]+-\d{3}\b', row['query']):
            raise ValueError(f'Source ID in query at row {number}')
        signature = (name, ' '.join(row['query'].lower().split()))
        if signature in seen:
            raise ValueError('Duplicate collection/query pair')
        seen.add(signature)
        ids = [sid.strip() for sid in row['relevant_ids'].split(';')]
        known = {r[COLLECTIONS[name]['id_field']] for r in collections[name]}
        if len(ids) != len(set(ids)) or not set(ids) <= known:
            raise ValueError(f'Invalid or duplicate relevant IDs at row {number}')
        row['relevant_ids'] = ids
        row['benchmark_id'] = f'R{number:02d}'
    if Counter(r['collection'] for r in rows) != {'documentation': 10, 'tickets': 10}:
        raise ValueError('Expected exactly 10 queries per collection')
    return rows


def tokens(text):
    return set(TOKEN.findall(text.lower()))


def keyword_search(query, records, collection):
    """Unique token intersection count; ties preserve original corpus order.

    Use all and only production text fields, no stop-word removal, stemming,
    query expansion, term weighting, platform filtering or relevance labels.
    Zero-overlap records are omitted, as production omits zero-score records.
    """
    spec = COLLECTIONS[collection]
    query_terms = tokens(pam_tools.validate_text(query, 'query'))
    scored = []
    for position, record in enumerate(records):
        record_terms = set().union(*(tokens(record.get(field, '') or '') for field in spec['text_fields']))
        score = len(query_terms & record_terms)
        if score:
            scored.append((score, position, record[spec['id_field']]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [sid for _, _, sid in scored[:spec['k']]]


def score_ranking(ranked_ids, relevant_ids, k):
    if k < 1 or not relevant_ids or len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError('Need positive K, nonempty relevance and unique ranked IDs')
    relevant = set(relevant_ids)
    top = ranked_ids[:k]
    ranks = [rank for rank, sid in enumerate(top, 1) if sid in relevant]
    return {'hit_at_1': int(bool(ranks) and ranks[0] == 1),
            'hit_at_k': int(bool(ranks)),
            'recall_at_k': len(ranks) / len(relevant),
            'mrr_at_k': 1 / ranks[0] if ranks else 0.0}


def summarize(rows):
    summary = {}
    for group in [*COLLECTIONS, 'overall']:
        selected = [r for r in rows if group == 'overall' or r['collection'] == group]
        summary[group] = {'query_count': len(selected)}
        for method in ['tfidf', 'keyword']:
            summary[group][method] = {
                metric: sum(r[method]['scores'][metric] for r in selected) / len(selected)
                for metric in METRICS
            }
    return summary


def run_benchmark():
    collections = load_collections()
    questions_path = ROOT / 'evals/retrieval_questions.csv'
    questions = load_questions(questions_path, collections)
    # Fixed inputs are used by both methods. Production functions are unchanged.
    functions = {'documentation': pam_tools.search_documentation, 'tickets': pam_tools.search_past_tickets}
    rows = []
    for question in questions:
        name = question['collection']
        spec = COLLECTIONS[name]
        tfidf = [r[spec['id_field']] for r in functions[name](question['query'])]
        keyword = keyword_search(question['query'], collections[name], name)
        row = {**question, 'k': spec['k']}
        for method, ranking in [('tfidf', tfidf), ('keyword', keyword)]:
            row[method] = {'ranked_ids': ranking,
                           'scores': score_ranking(ranking, question['relevant_ids'], spec['k'])}
        rows.append(row)
    paths = ['evals/retrieval_questions.csv', 'evals/retrieval_benchmark.py', 'pam_tools.py',
             'data/pam_knowledge.json', 'data/pam_tickets.json', 'uv.lock']
    return {
        'metadata': {
            'relevance_status': 'Handcrafted draft judgments, not independently verified ground truth',
            'aggregation': 'Unweighted macro-average across queries; overall mixes collection-specific K',
            'keyword_rule': 'Unique lowercase word-token intersection, >=2 Unicode word characters; no stop words; original corpus order breaks ties; positive scores only',
            'collection_specs': COLLECTIONS,
            'fingerprints': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            'python_version': platform.python_version(),
            'versions': {p: version(p) for p in ['minsearch', 'numpy', 'scikit-learn']},
        },
        'summary': summarize(rows), 'queries': rows,
    }


def save_results(result):
    (ROOT / 'evals/retrieval_benchmark_results.json').write_text(json.dumps(result, indent=2) + '\n')
    fields = ['benchmark_id', *QUESTION_FIELDS, 'k', 'tfidf_top_k', 'keyword_top_k']
    fields += [f'{method}_{metric}' for method in ['tfidf', 'keyword'] for metric in METRICS]
    with (ROOT / 'evals/retrieval_benchmark_results.csv').open('w', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in result['queries']:
            exported = {key: row[key] for key in ['benchmark_id', 'query', 'collection', 'relevance_reason', 'k']}
            exported['relevant_ids'] = ';'.join(row['relevant_ids'])
            for method in ['tfidf', 'keyword']:
                exported[f'{method}_top_k'] = ';'.join(row[method]['ranked_ids'])
                exported.update({f'{method}_{metric}': row[method]['scores'][metric] for metric in METRICS})
            writer.writerow(exported)


if __name__ == '__main__':
    result = run_benchmark()
    save_results(result)
    print(json.dumps(result['summary'], indent=2))
