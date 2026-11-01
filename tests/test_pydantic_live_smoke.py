"""Opt-in paid smoke tests. Each scenario runs once; no automatic rerun/revision.

Citation checks and language checks are heuristics. Review each answer against
returned synthetic records before claiming factual grounding.
"""
import json
import inspect
import os
from pathlib import Path
import re

import pytest
from pydantic_ai import capture_run_messages

from pam_diagnostics import failed_run_diagnostics, retry_activity, safe_error_metadata

import pam_tools
from pam_agent_pydantic import agent, investigate_with_evidence
from pam_evidence import DISCLAIMER, documentation_issues


SCENARIOS = {
    'A': 'What should an engineer check when onboarding a Linux privileged account into PAM?',
    'B': ('Password rotation failed for a privileged account on LNX-001 shortly after '
          'onboarding. Investigate the issue and check whether similar incidents were reported previously.'),
    'C': 'Investigate the password rotation failure on UNKNOWN-999.',
}


@pytest.fixture(scope='module')
def live_model(request):
    # Double guard: no client initialization or .env access without opt-in.
    if not request.config.getoption('--live'):
        pytest.skip('requires --live (paid API requests)')
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    try:
        load_dotenv(Path(__file__).resolve().parents[1] / '.env')
        if not os.environ.get('OPENAI_API_KEY', '').strip():
            raise RuntimeError('Required API key is missing')
        # Same production model; disable SDK transport retries only in this test.
        client = AsyncOpenAI(max_retries=0, timeout=60)
        return OpenAIChatModel('gpt-4o-mini', provider=OpenAIProvider(openai_client=client))
    except Exception as exc:
        print(json.dumps(safe_error_metadata(exc, 'environment_setup')), flush=True)
        pytest.exit('STOP: environment setup failed; no live scenarios executed.', returncode=1)


@pytest.fixture
def observed_tools(monkeypatch):
    """Record only synthetic results/asset-ID checks in memory; run real tools."""
    observed = []
    for name in ['search_documentation', 'get_asset_details', 'search_past_tickets']:
        original = getattr(pam_tools, name)
        def observe(*args, _name=name, _original=original, **arguments):
            result = _original(*args, **arguments)
            bound = inspect.signature(_original).bind(*args, **arguments)
            observed.append({
                'tool': _name,
                'asset_id': bound.arguments.get('asset_id'),
                'result': result,
            })
            return result
        monkeypatch.setattr(pam_tools, name, observe)
    return observed


def acknowledges_uncertainty(text):
    """Recognize uncertainty wording; this does not verify semantic grounding."""
    text = ' '.join(text.lower().split())
    return bool(re.search(
        r'(?:cause|diagnos).{0,100}(?:unknown|not established|not confirmed|cannot|insufficient|uncertain|unclear|not (?:yet )?been diagnosed|undiagnosed)'
        r'|(?:cannot|insufficient|not enough).{0,100}(?:cause|diagnos)'
        r'|\b(?:current (?:failure|incident|issue)|diagnosis).{0,60}'
        r'(?:not (?:yet )?been diagnosed|has no established diagnosis|is not established)'
        r'|insufficient diagnostic evidence', text))


def check_scenario(label, summary, observed, messages=()):
    """Return fixed review reasons without exposing arguments/provider payloads."""
    failures = []
    def require(condition, reason):
        if not condition:
            failures.append(reason)

    answer = summary['answer']
    text = ' '.join(answer.lower().split())
    tools = {event['tool'] for event in summary['trace']}
    cited = set(re.findall(r'\[([A-Z]+-\d{3})\]', answer))
    require(summary['citation_validation_passed'], 'Citation validation failed; see citation_issues.')
    require(answer.startswith(DISCLAIMER), 'Opening synthetic-training disclaimer is missing.')
    require(all(event['error'] is None or event['error'] == 'asset_not_found'
                for event in summary['trace']), 'Unexpected tool execution/trace error.')
    if label == 'A':
        require('search_documentation' in tools, 'Documentation tool was not called.')
        onboarding = {record['id'] for event in observed if event['tool'] == 'search_documentation'
                      for record in event['result'] if record['category'] == 'onboarding'}
        require(bool(onboarding), 'No onboarding documentation was retrieved.')
        require(bool(cited & onboarding), 'No retrieved onboarding article was cited.')
    elif label == 'B':
        inventory = json.loads((Path(__file__).resolve().parents[1] / 'data/pam_assets.json').read_text())
        expected_asset = next(record for record in inventory if record['asset_id'] == 'LNX-001')
        require({'get_asset_details', 'search_past_tickets'} <= tools,
                'Both current inventory lookup and historical search are required.')
        require(any(event['tool'] == 'get_asset_details' and event['asset_id'] == 'LNX-001'
                    and event['result'] == expected_asset
                    for event in observed), 'The actual LNX-001 record was not retrieved.')
        rotation_tickets = {record['ticket_id'] for event in observed
                            if event['tool'] == 'search_past_tickets'
                            for record in event['result'] if record['category'] == 'password_rotation'}
        require(bool(rotation_tickets), 'No historical rotation tickets were retrieved.')
        require('LNX-001' in cited, 'Current asset findings lack the LNX-001 citation.')
        require(bool(cited & rotation_tickets), 'No relevant historical rotation ticket was cited.')
        require(acknowledges_uncertainty(text),
            'No explicit acknowledgment that the current cause is unestablished.')
        require(bool(re.search(
            r'histor.{0,250}(?:not|cannot|doesn.t)|(?:not|cannot).{0,100}histor', text)),
            'No explicit separation of historical outcomes from current diagnosis.')
        failures.extend(documentation_issues(answer, messages))
    else:
        require('get_asset_details' in tools, 'Unknown asset was not looked up.')
        require(any(event['tool'] == 'get_asset_details' and event['asset_id'] == 'UNKNOWN-999'
                    and event['result'].get('error') == 'asset_not_found' for event in observed),
                'Requested UNKNOWN-999 lookup did not return asset_not_found.')
        require('UNKNOWN-999' not in summary['evidence_ids'] and '[UNKNOWN-999]' not in answer,
                'Nonexistent asset was treated as evidence.')
        require('unknown-999' in text and bool(re.search(
            r'not found|no (?:synthetic )?(?:asset |inventory )?record|does not exist|absent|no matching', text)),
            'Missing synthetic inventory record was not acknowledged.')
        require(not re.search(
            r'(?:platform|configuration|account type)\s*(?:is|:)\s*(?:linux|windows|local|domain)', text),
            'Answer appears to invent unknown-asset configuration details.')
    require(not re.search(r'(?:confirmed|definitive|exact) (?:root )?cause is (?:a |the )?'
                          r'(?:configuration|policy|dependency|account)', text),
            'Answer appears to claim a confirmed unsupported cause.')
    return failures


@pytest.mark.live
@pytest.mark.parametrize('label', ['A', 'B', 'C'])
def test_pydantic_live_smoke(label, live_model, observed_tools):
    try:
        with capture_run_messages() as messages, agent.override(model=live_model):
            summary = investigate_with_evidence(SCENARIOS[label])
    except Exception as exc:
        print(json.dumps(failed_run_diagnostics(exc, messages, 'agent_execution')), flush=True)
        pytest.exit('STOP: live execution failed; remaining scenarios not run.', returncode=1)
    try:
        failures = check_scenario(label, summary, observed_tools, messages)
    except Exception as exc:
        print(json.dumps(failed_run_diagnostics(exc, messages, 'result_validation')), flush=True)
        pytest.exit('STOP: result validation failed; remaining scenarios not run.', returncode=1)
    print(json.dumps({
        'scenario': label,
        **summary,
        **retry_activity(messages),
        'tools_observed': [event['tool'] for event in summary['trace']],
        'result': 'FAIL' if failures else 'PASS',
        'failure_reasons': failures,
        'grounding_review': 'Human review required; automated checks do not prove grounding.',
    }, indent=2), flush=True)
    if failures:
        pytest.fail('; '.join(failures), pytrace=False)
