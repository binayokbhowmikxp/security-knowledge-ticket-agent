"""Reusable read-only retrieval over the existing synthetic PAM datasets."""
import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from minsearch import Index


DATA_DIR = Path(__file__).resolve().parent / 'data'


def validate_text(value, label, max_length=2000):
    """Match notebook validation, checking length before trimming whitespace."""
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f'{label} must be a non-empty string of at most {max_length} characters.')
    return value.strip()


@lru_cache(maxsize=3)
def _load_records(filename):
    with (DATA_DIR / filename).open(encoding='utf-8') as source:
        records = json.load(source)
    assert all(record['source_type'] == 'synthetic' for record in records)
    return records


@lru_cache(maxsize=2)
def _search_index(filename):
    if filename == 'pam_knowledge.json':
        text_fields = ['title', 'content', 'category', 'platform']
        keyword_fields = ['id', 'source_type']
    else:
        text_fields = ['issue_summary', 'category', 'related_asset',
                       'investigation_findings', 'documented_outcome']
        keyword_fields = ['ticket_id', 'source_type']
    index = Index(text_fields=text_fields, keyword_fields=keyword_fields)
    index.fit(_load_records(filename))
    return index


def search_documentation(query: str) -> list[dict]:
    """Return up to five independent synthetic article records using TF-IDF."""
    query = validate_text(query, 'query')
    return deepcopy(_search_index('pam_knowledge.json').search(query, num_results=5))


def get_asset_details(asset_id: str) -> dict:
    """Return an independent inventory record or the existing missing-asset error."""
    asset_id = validate_text(asset_id, 'asset_id', 40).upper()
    if not re.fullmatch(r'[A-Z]+-\d{3}', asset_id):
        raise ValueError('asset_id must look like LNX-001.')
    for asset in _load_records('pam_assets.json'):
        if asset['asset_id'] == asset_id:
            return deepcopy(asset)
    return {'error': 'asset_not_found', 'asset_id': asset_id,
            'message': 'No synthetic asset record exists. Request approved inventory details.'}


def search_past_tickets(query: str) -> list[dict]:
    """Return up to four independent synthetic historical incident records."""
    query = validate_text(query, 'query')
    return deepcopy(_search_index('pam_tickets.json').search(query, num_results=4))
