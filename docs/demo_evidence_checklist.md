# Demo evidence checklist — genuine manual capture only

**Step 3A planning artifact. No screenshots have been captured or verified for
this checklist.** No app was launched, agent/judge rerun, paid request made or new
Logfire trace created. Baseline: `265c4f942ef45b0fb03844dfcc47404a279de684`,
`feature/streamlit-ui`. Follow the [4½-minute walkthrough](demo_walkthrough.md).

The representative password-rotation case is **S009 / WIN-003**, a previously
completed approved synthetic scenario. Its answer is not human-approved or
citation-valid. It is deliberately useful for showing both observable retrieval
and the limits of generated guidance. All capture items below are **pending**.

## Capture inventory

| ID / genuine screenshot | What should be visible | Capability / assessment evidence | Hide or redact | Capture source and new-request requirement |
|---|---|---|---|---|
| E1 — Streamlit agent interface | Actual title “PAM Knowledge & Ticket Agent”, synthetic/read-only caption, independent-question notice, model name, chat input and unverified-output banner | Working chat interface, clear operating scope and honest validation mode | Browser profile/account, unrelated tabs, terminal username/path, credentials or private desktop content. Keep the safety banner visible. | Future local app launch with Logfire disabled; **no paid call** if no question is submitted. A blank interface is not a completed investigation. |
| E2 — Representative completed investigation | In the **PAM Agent Evaluation Console**, select S009; include question, category/type, completed execution status, full unchanged answer and saved-label state | A real previously collected model output available for manual review | Unrelated browser/account details; keep “historical saved result” caption and any errors visible. Do not crop away problematic answer sections while implying the complete answer is shown. | Existing saved artifact + future local console launch; **no paid call**. Use multiple honest crops if the full answer is too tall. Do not click Confirm label or modify notes. |
| E3 — Distinct retrieved sources | S009 reconstructed WIN-003 asset record, ROT-003/ROT-008 documentation and TKT-009/TKT-014 historical records; keep “reconstructed” labels and saved IDs visible | Inventory facts, technical guidance and historical analogies are different evidence roles; saved trace confirms retrieval membership | Organization/account details unrelated to this public synthetic project. Keep synthetic source IDs and uncertainty intact. | Existing records + console evidence expanders; **no paid call**. Corresponding frozen dataset records are reconstructions, not exact captured raw historical tool bodies. |
| E4 — Citations and informational findings | Original `[LNX-001]` beside the WIN-003 claim; saved unretrieved-citation/missing-citation findings; show LNX-001 as mentioned, not retrieved. A valid returned historical reference such as `[TKT-014]` can be contrasted. | Citation diagnostics expose a real error; successful execution does not mean factual correctness or enforced rejection | No fabricated replacement citation or edited answer. Retain enough context to see that the wrong citation is a defect, not an endorsed source. | Saved answer/checks in console or artifact viewer; **no paid call**. Never label these checks “enforced validation” or “grounding passed.” |
| E5 — Actual tool activity and usage | S009 safe trace: documentation search, WIN-003 lookup, past-ticket search; saved 4 model requests, 3 tools, 5,383 input/421 output/5,804 total tokens, estimated $0.00106005 and trace ID | Dynamic three-tool execution and measured historical usage/cost | Raw provider messages, raw arguments, secrets, local prompt paths. Saved trace IDs and synthetic IDs may remain when needed for verification. | Existing JSON/CSV, optionally the walkthrough's read-only extraction. Console does not render usage or Logfire root trace ID. **No paid call**. Do not present historical numbers as current session totals. |
| E6 — Existing Logfire trace | If retained/access permitted: service pam-agent, S009 trace `01a1dc9d50b3fbcafdafa593a3450593`, time, investigation root, agent, model and tool span tree, usage/duration attributes actually visible | Observability linking a historical execution to model/tool activity and reported usage | Write/read tokens, setup panels, user email/avatar, private project/workspace names, unrelated traces and any unexpected content payloads. Inspect before sharing. | Read-only access to an **existing** trace; **no model call or new trace**. Dashboard visibility/retention is not verified. If absent, mark unavailable; do not replace it with a newly generated trace. |
| E7 — Architecture and boundaries | Rendered README Mermaid, three tools, 25/12/15 synthetic sources, optional Logfire and validation-mode explanation | Architectural clarity and explicit absence of live enterprise integrations/remediation | Unrelated browser/IDE content; do not relabel OpenAI inference as fully local | Existing README preview/GitHub; **no paid call**. No new rendering dependencies should be installed for this step. |
| E8 — Evaluation and corrected judgment | Batch summary (50 completions, 27 citation failures, 33 informational flags); human 20/10/10; V1/V2 comparison with Bad-positive metrics and in-sample caveat; optional S028 corrected example | Real collection, human evaluation and a targeted judge iteration with transparent limits | Personal review-session identity, unrelated notes/tabs; retain failures, selected-subset caveat and six remaining disagreements | Existing reports/labels/comparison artifacts; **no agent/judge call**. Judge accuracy is agreement with the same selected 20 labels, not overall answer accuracy or held-out generalization. |
| E9 — Retrieval benchmark | Both method names, documentation K=5/tickets K=4, overall metrics and handcrafted-draft warning; include representative failure if space permits | Baseline comparison with an honest result favoring keyword overlap | Unrelated desktop material. Do not remove the small-sample/draft-judgment caveat or frame TF-IDF as the measured winner. | Existing benchmark report/JSON/CSV; **no paid call and no benchmark rerun needed**. Overall Hit@1 95% vs 90%, Recall@K 95% vs 87.08%, MRR@K 0.9750 vs 0.9417 (keyword vs TF-IDF). |

A concise deck can combine E3/E4/E5 and E8/E9, provided each screenshot is an
actual capture and the captions retain the distinctions. A recorded demo must
label any historical view as historical throughout—not introduce it as a live
run and disclose its age only afterward.

## Completed chat UI screenshot: conditional, not a required new paid test

The chat app stores history in its original Streamlit session; it does not load
batch journal results. An already-open original session might provide a genuine
completed-chat screenshot, but its existence/content was not inspected. Do not
claim it shows S009 unless the original scenario and matching run details confirm it.

If no such session survives, E2–E5 can be captured in the saved-result console
and artifact viewer instead. Label the screen accurately; do not paste saved
answers into chat, inject session state or use mocked responses to create a
completed UI screenshot.

If an assessment specifically insists on a **new completed chat** interaction,
a separately authorized real paid request would be needed; enabling Logfire for
that interaction would create a new trace and also needs authorization. That
conditional option is not necessary for the proposed artifact-based walkthrough,
not approved here, and not part of Step 3A. No request, recording or Step 3B work
should be initiated from this checklist.

## Capture safety and provenance

Before any later manual capture:

- Verify the branch, scenario ID, exact screen identity and whether the view is
  live, a historical saved output, a reconstructed source or a report. Caption it
  accordingly. Mark capture time separately from the saved run's UTC completion.
- Use existing installed dependencies. For a later app-shell capture, use the
  walkthrough's `LOGFIRE_TOKEN=` override to disable this project's monitoring
  startup; never submit a question just to populate the screen. The saved-result
  console does not load credentials or initialize the agent/Logfire.
- Close `.env`, key managers, private terminals, provider account pages and other
  customer/project tabs. Never photograph API keys or Logfire write-token setup.
  The console/app contain synthetic records; do not substitute customer material.
- Review an actual Logfire screen before capture even though instrumentation is
  configured with content excluded. Do not assume the whole dashboard is free of
  unrelated private data. An ingestion HTTP 200 is not a dashboard screenshot.
- Redaction may hide personal/account details; it must not manufacture evidence,
  hide material failures or replace text. Keep original public synthetic record
  content and warnings unchanged. If a crop omits part of an answer, say it is a
  crop and retain the full result link.
- Do not press Confirm label, edit labels, change frozen artifacts, rerun models
  or modify retrieval to improve a screenshot. Read-only navigation is sufficient.
- A later capture ledger should record the actual filename, capture date, source
  scenario/trace/report and redactions. No screenshot paths or completed capture
  statuses are assigned now because no files exist for these items.

## Readiness review

| Evidence | Already available? | Remaining action / limitation |
|---|---|---|
| Runnable chat UI and offline UI contracts | Yes, in app.py and tests | Actual screen capture pending; tests use offline stubs and are not live screenshot evidence |
| S009 real model answer, tools, IDs, usage and trace ID | Yes, terminal result in Question 1 artifacts | Show as historical; full answer and its citation errors remain unchanged |
| Retrieved documentation, asset and historical records | Yes, corresponding frozen synthetic JSON | Capture via reconstruction UI, explicitly marked as reconstructed |
| S009 original chat session | Unknown | Do not assume it survives; batch outputs cannot be replayed into chat by current code |
| Existing Logfire root/agent/model/tool dashboard view | Unverified | Manually confirm retained trace and access; record absence rather than generating another trace |
| 50 recorded batch trace IDs and ingestion acknowledgements | Yes, saved results and batch report | Support recorded observability, not independent dashboard visibility |
| Human review, V1/V2 metrics and S028 correction | Yes | Capture saved reports with selected-subset and in-sample limitations |
| 20-query retrieval comparison | Yes | Preserve the keyword-baseline advantage and subjective relevance caveats |
| Demo screenshots or recording | No verified files found in the repository | All visual captures remain pending manual work after planning review |

## Source links for preparation

- [README and architecture](../README.md)
- [Project context](../PROJECT_CONTEXT.md)
- [Chat interface](../app.py) and [UI contract tests](../tests/test_streamlit_app.py)
- [Monitoring helpers](../pam_monitoring.py)
- [Saved results journal](../evals/results.jsonl) / [CSV export](../evals/results.csv)
- [Saved-result console](../evals/label_evals.py)
- [Batch report](../evals/batch_report.md) / [human labels](../evals/labels.csv)
- [V1 report](../evals/judge_v1_report.md) / [V2 report](../evals/judge_v2_report.md)
- [V1/V2 comparison](../evals/judge_v2_comparison.json)
- [Retrieval benchmark](retrieval_benchmark.md)
- [Synthetic-source provenance](pam_expansion_sources.md)
