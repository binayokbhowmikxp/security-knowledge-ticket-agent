"""Question 3: one real agent run and one separate real judge evaluation.

Both are paid and require --live. No FunctionModel or mock responses are used.
"""
import asyncio
import json

import pytest
from pydantic_ai import capture_run_messages

from judge import assert_criteria
from pam_agent_pydantic import agent, investigate_asset
from pam_diagnostics import failed_run_diagnostics, retry_activity, safe_error_metadata
from pam_evidence import summarize_result
from test_pydantic_live_smoke import live_model


QUESTION = ('Password rotation failed for a privileged account on LNX-001 shortly after onboarding. '
            'Investigate the issue and check whether similar incidents were reported previously.')
CRITERIA = [
    'During the LNX-001 password rotation investigation, the agent calls both get_asset_details and search_past_tickets, retrieving the current LNX-001 asset record and relevant historical ticket evidence.',
    "The answer states that LNX-001's last password rotation failed, cites [LNX-001], and explicitly acknowledges that the current root cause is unconfirmed because the sanitized rotation error has not been collected.",
    'The answer cites [TKT-001] when discussing the historical account-configuration discrepancy and clearly distinguishes that historical incident from the current LNX-001 failure, without presenting the historical resolution as the confirmed current root cause.',
]


@pytest.mark.live
@pytest.mark.asyncio
async def test_pydantic_rotation_with_llm_judge(live_model):
    try:
        with capture_run_messages() as messages, agent.override(model=live_model):
            # Keep the exact production run_sync entry point and its native limits;
            # a worker thread lets the course-style async pytest test await it.
            result = await asyncio.to_thread(investigate_asset, QUESTION)
    except Exception as exc:
        print(json.dumps(failed_run_diagnostics(exc, messages, 'agent_execution'), indent=2), flush=True)
        pytest.fail('Main agent failed; judge was not called. See safe diagnostics.', pytrace=False)
    print(json.dumps({'agent_result': summarize_result(result), **retry_activity(messages)}, indent=2), flush=True)
    try:
        await assert_criteria(result, criteria=CRITERIA)
    except AssertionError:
        pytest.fail('Judge criteria or feedback-completeness assertion failed; see structured feedback.', pytrace=False)
    except Exception as exc:
        print(json.dumps(safe_error_metadata(exc, 'judge_execution'), indent=2), flush=True)
        pytest.fail('Judge execution failed; see safe diagnostics.', pytrace=False)
