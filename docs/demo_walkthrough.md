# Demo walkthrough — PAM investigation with visible evidence

**Step 3B: supplied captures reviewed and organized.** The seven genuine PNGs
in [the screenshot checklist](demo_evidence_checklist.md) document a separate
real **LNX-001 Streamlit investigation**, not the historical S009/WIN-003 result.
They were supplied after Step 3A (commit `2f1d342947bcf87a41662289b09f6f52776e9e0d`).
No API call, new trace or screenshot capture was performed while organizing them;
images were copied unchanged from existing temp/ files. Review date: 2026-11-16.
The captured execution is already completed—do not describe static images as a
new live run happening during the presentation.

## Recommended format: 4 minutes 30 seconds

Use a current product overview plus the **completed LNX-001 run shown in supplied
Streamlit/Logfire screenshots**. Keep S009 as an optional, separately identified
historical comparison, not the source of these images.
This works for capstone peers, a portfolio walkthrough or an enterprise security
architect. It is a local synthetic-data prototype demonstration, not a production
customer deployment or a promise of verified time savings.

| Time | Show | Suggested narration |
|---|---|---|
| 0:00–0:25 | Project title and the README problem/scope | “A PAM engineer often needs account configuration, troubleshooting knowledge and earlier incidents together. This assistant demonstrates gathering that context while making evidence gaps visible. All enterprise records here are synthetic; it cannot access or change your PAM environment.” |
| 0:25–0:55 | README architecture and screenshot 01 | “One PydanticAI agent can choose three read-only tools: documentation, inventory and historical tickets. Each question is independent. The pictured run chose inventory and tickets only; documentation was not searched.” |
| 0:55–2:10 | Screenshots 02–05: LNX-001 findings, historical outcomes, tools and citation diagnostics | “These are supplied screenshots of a completed real Streamlit run, not a new request now. Inventory and historical retrieval are observable, but the response still has citation issues. We preserve that warning. Past ticket outcomes cannot establish the current root cause, and no documentation tool was called to support technical procedures.” |
| 2:10–2:45 | Screenshots 06–07: captured LNX-001 usage and matching Logfire view | “This run reports two model requests, two tool executions and 2,314 tokens, estimated at $0.00055140. The UI trace ID and the Logfire suffix/usage agree. The captured view shows the root investigation, model/tool operation counts and metadata, not a new trace generated for this talk.” |
| 2:45–3:45 | Saved batch report, human labels, V1/V2 comparison and retrieval benchmark summary | “Fifty real investigations completed, but completion is not correctness. Twenty were reviewed by a human. Judge agreement improved on those same examples, and an honest retrieval comparison favored a simple keyword baseline on this small draft set. These measurements expose limitations rather than certify production quality.” |
| 3:45–4:30 | Limitations and next opportunities | “The chat currently displays unverified answers: citation checks are informational. Human review, independent relevance judgments and held-out judge validation remain important. The system is read-only, has no enterprise integration or completed cloud deployment, and has not demonstrated customer savings. A next conversation can define evidence and approval requirements for further assessment.” |

Do not fill time by submitting additional prompts or rerunning a disappointing
answer. If a screen is unavailable, use the saved artifact and describe exactly
what it establishes. Keep the spoken walkthrough under five minutes; detailed
metrics and failure analysis can remain in supporting documents.

## Primary captured investigation: LNX-001

The screenshot question is:

> Password rotation failed for a privileged account on LNX-001 shortly after onboarding. Investigate the issue and check whether similar incidents were reported previously.

This is the separate live Streamlit execution supplied for Step 3B. It is not
S009, S006 or S020, and no new scenario/result was inserted into the frozen
50-case journal. Screenshots 01–06 show successive views/crops of the same
conversation; they are not a raw machine-readable response export or independent
claim-by-claim validation. Keep all warning text and original answer wording.

| Observed captured fact | LNX-001 demo run |
|---|---|
| Model | gpt-4o-mini |
| Model requests / tool calls | 2 / 2 |
| Actual tools | get_asset_details; search_past_tickets |
| Documentation search | Not called |
| Retrieved evidence IDs | LNX-001; TKT-001; TKT-003; TKT-004; TKT-015 |
| Input / output / total tokens | 1,860 / 454 / 2,314 |
| Estimated cost | $0.00055140 USD, not an invoice |
| UI Logfire trace ID | `01a1e18cc5002c02491bcee2c117955d` |
| Matching Logfire screenshot | Supplied crop shows suffix `17955d` and the same usage/cost/request/tool values |
| Validation mode | validate_output=False; custom final-answer validation not enforced |
| Informational checks | Issues found, including missing bracketed asset/ticket citations and an opening-disclaimer diagnostic |

The Logfire screenshot displays a root investigation and grouped operations for
one agent invocation, two model operations and the two tool executions. Its
parent/child tree is not fully expanded. It shows a Nov 15 time, but no new UTC
capture timestamp is inferred from that display. The visible trace suffix and
usage corroborate the user's matching-trace provenance; no backend query or
independent provider replay was performed.

Explain the distinct evidence roles accurately: LNX-001 supplies current recorded
state; the returned tickets supply historical cases with varying relevance.
Documentation could supply technical guidance but **was not retrieved in this
run**. Do not show a documentation record as if it had been returned here.
The response discusses TKT-001 yet also says no prior incidents specifically
aligned; preserve that ambiguity instead of endorsing it as verified history.
A visible formatted disclaimer also coexists with a diagnostic asking for the
exact opening disclaimer; screenshots do not establish the raw-format cause.

Suggested narration: “This is genuine execution evidence, not a validated
technical diagnosis. The model retrieved two kinds of evidence and the UI
reported citation issues without rejecting the answer. An engineer must still
assess relevance, missing diagnostic evidence and historical-versus-current claims.”

## Historical reference only: S009 / WIN-003

For an optional historical comparison, use the original saved question unchanged:

> WIN-003 reports minimum password age rejection. What policy and schedule evidence should be reviewed before drawing a conclusion, and are there relevant historical cases?

Source: terminal `event="result"`, `scenario_id="S009"` in
[results.jsonl](../evals/results.jsonl), also exported in
[results.csv](../evals/results.csv). Recorded completion:
`2026-11-15T00:31:09.116762+00:00` (UTC).

S009 belongs to the approved 50-scenario set. Its **execution completed**; that
is not a claim that its answer was validated or human-rated Good. S009 is not
among the 20 human-labeled responses. The complete original answer must remain
visible and unchanged in a screenshot or recording; do not repair its citations,
add a “validated” badge or edit out its uncertainty/failure notices.

### What was actually observed

| Evidence kind / actual tool | Saved returned IDs | What to explain |
|---|---|---|
| Documentation / search_documentation | ONB-008, ROT-001, ROT-003, ROT-008, WEB-005 | ROT-003 and ROT-008 are relevant policy/restriction guidance. Other returned articles include less relevant material: retrieval is not an automatic relevance guarantee. |
| Current inventory / get_asset_details | WIN-003 | The synthetic domain account has an hourly training schedule, passed initial validation and a failed last rotation. Its sanitized error mentions minimum age; approved policy evidence remains pending. |
| Historical incidents / search_past_tickets | TKT-003, TKT-009, TKT-014, TKT-015 | TKT-009/TKT-014 record earlier minimum-age cases and owner policy/schedule review. They do not prove the present cause. TKT-015 is a preparatory authorization gap, not an executed rotation; TKT-003 is a different Linux timeout case. |

Documentation defines checks; inventory supplies current recorded state; tickets
supply historical analogies. Do not conflate these roles or claim every retrieved
item supports the final answer. The console reconstructs corresponding records
from fingerprint-matched JSON datasets using saved IDs—it does not contain an
exact capture of each historical raw tool-response body.

**Use the citation error as a concrete reliability example.** S009's answer uses
`[LNX-001]` beside a current WIN-003 claim, although LNX-001 was not retrieved.
The saved checks report that unretrieved citation and missing valid documentation
and current-asset citations. Some historical references, such as `[TKT-014]`, do
match retrieved IDs. Membership is still not proof of support for every claim.
The answer also states a cause more strongly than the pending policy evidence
supports. Do not repeat that diagnosis as established fact.

Suggested narration: “Here the retrieval and execution are observable, but the
answer still has a wrong asset citation. The warning is useful evidence for the
reviewer; it does not block or fix the response in this UI mode.”

### Actual saved execution metadata

| Field | Observed S009 value |
|---|---|
| Model | gpt-4o-mini |
| Custom final-output validation | Disabled (`validate_output=False`) |
| Model requests / executed tools | 4 / 3 |
| Input / output / total tokens | 5,383 / 421 / 5,804 |
| Estimated API cost | $0.00106005 USD at existing repository rates |
| Logfire trace ID | `01a1dc9d50b3fbcafdafa593a3450593` |
| Informational citation status | Failed; answer preserved as generated |

These numbers belong to that **historical saved execution**, not a future rerun
or a new browser session's totals. A future model run can choose different tools,
return a different answer, use more/fewer tokens or fail within the existing
six-request/eight-tool budgets.

## Screens available without another investigation

Use [the seven supplied captures](demo_evidence_checklist.md#reviewed-capture-ledger)
for the primary LNX-001 walkthrough. The following S009-only sequence remains
an optional artifact-based comparison; no S009 console/dashboard screenshot has
been supplied or marked captured. Do not confuse its values with the LNX-001 run:

1. Show the [README architecture](../README.md#architecture) and existing app
   interface. The chat app does **not** load completed batch results into its
   history. Its original browser session may or may not still exist; this was
   not inspected.
2. Open the local saved-result console using `uv run streamlit run evals/label_evals.py`
   and navigate directly to S009. Say “historical execution reviewed now.” Open
   the evidence and findings expanders. Do not press **Confirm label**, change
   notes or relabel examples for the presentation.
3. Show S009's usage and trace ID in the saved JSON/CSV or the read-only metadata
   command below. The console shows tools, evidence and checks; it does **not**
   currently render run token/cost totals or the Logfire root trace ID. Do not
   imply those are console features.
4. If accessible, open **the existing** S009 trace in Logfire, filter service
   `pam-agent`, and inspect the actual investigation/agent/model/tool spans.
   Do not generate a replacement trace to satisfy the plan. The repository
   records IDs and HTTP 200 ingestion acknowledgements, not a captured dashboard
   view or independent proof that this particular trace is still retained.
5. End with the saved evaluation reports and retrieval benchmark. Do not rerun
   the batch, benchmark or judge merely to refresh a presentation screen.

For a later offline interface capture, the following commands avoid dependency
installation; the empty environment variable also prevents this project's chat
startup from enabling Logfire via the local .env (dotenv does not override an
already-set variable):

```sh
LOGFIRE_TOKEN= uv run --offline --no-sync streamlit run app.py
uv run --offline --no-sync streamlit run evals/label_evals.py
```

Do not submit a chat question. A blank chat screen demonstrates the interface,
not successful runtime execution. Opening the existing Logfire dashboard is a
read-only observation; account access, retention and visibility need manual checks.

Optional read-only extraction for a later metadata screenshot (stdlib only; no
.env, agent import, inference or instrumentation):

```sh
uv run --offline --no-sync python - <<'PY'
import json
from pathlib import Path
rows = (json.loads(line) for line in Path('evals/results.jsonl').read_text().splitlines())
row = next(r for r in rows if r.get('event') == 'result' and r['scenario_id'] == 'S009')
keys = ('scenario_id', 'timestamp_utc', 'status', 'executed_tools', 'trace',
        'evidence_ids', 'citation_issues', 'usage', 'estimated_api_cost_usd', 'trace_id')
print(json.dumps({key: row[key] for key in keys}, indent=2))
PY
```

## Evaluation talking points (approximately one minute)

- **Collection:** 50 real-model investigations completed, zero execution errors;
  27 answers failed informational citation checks and 33 had full informational
  findings. These findings overlap. The latest offline suite passed 219 tests,
  skipped five paid tests and passed 19 subtests, with one existing warning.
- **Human review:** 20 reviewed: 10 Good, 10 Bad; 30 remain unlabeled. The main Bad
  category was wrong evidence/citation (5), followed by hallucination (3), incorrect
  tool use (1) and incomplete response (1). This is a selected subset.
- **Judge:** V1 → V2 accuracy against those human labels rose 55% → 70%; Bad
  precision 52.63% → 62.5%, recall stayed 100%. False positives fell 9 → 6, with
  S028/S044/S048 corrected and no prediction regressions. V2 distinguishes
  investigation from clarification/refusal before requiring citations. S028's
  honest missing-asset reply is the [documented corrected example](../evals/judge_v2_report.md).
  These are in-sample agreement metrics; six disagreements remain.
- **Retrieval:** a 20-query draft benchmark favors keyword overlap overall:
  Hit@1 95% vs TF-IDF 90%, Recall@K 95% vs 87.08%, MRR@K 0.9750 vs 0.9417;
  both reached 100% Hit@K at documentation K=5/ticket K=4. Judgments are
  handcrafted drafts, not independently verified ground truth. Production
  TF-IDF is unchanged; do not claim the benchmark proved it superior.

Evidence: [batch report](../evals/batch_report.md), [human labels](../evals/labels.csv),
[judge comparison](../evals/judge_v2_comparison.json),
[retrieval benchmark](retrieval_benchmark.md).

## Readiness and claims boundary

All seven supplied PNGs are present, readable and reviewed; originals remain in
ignored temp/ and the documentation copies are byte-identical. The separate
LNX-001 chat and matching Logfire **captured view** now have visual evidence.
S009's original dashboard visibility remains unverified; its saved IDs/usage and
historical three-tool result still exist separately. No console/evaluation-report
screenshots or presentation recording were supplied, and no more paid call is
needed to present the existing evidence.

The captured LNX-001 answer is not independently verified as technically correct.
Do not guarantee correct citations, use of all three tools, a confirmed cause,
specific future wording/latency/cost or perpetual dashboard retention. Current
chat still uses validate_output=False. There is no enterprise authentication,
customer data, live PAM integration, automated remediation, production readiness,
held-out judge performance, measured customer savings or completed cloud deployment
to demonstrate. Broader review, independent retrieval judgments and held-out
validation remain future opportunities. No further milestone work is included.
