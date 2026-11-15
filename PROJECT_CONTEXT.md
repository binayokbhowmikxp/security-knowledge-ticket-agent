# Project Context — Enterprise Security Knowledge & Ticket Resolution Agent

## Purpose
This is a beginner-friendly AI Engineering Buildcamp capstone project for a professional with enterprise security architecture and Privileged Access Management (PAM) domain knowledge. The developer is learning AI engineering while working full-time. Primary goals are learning, career development, and enterprise credibility through a finished GitHub portfolio project.

## Problem
Enterprise security engineers often struggle to find reliable documentation and investigate support tickets because vendor guides, internal procedures, asset details, and past solutions are scattered. A customer described that experienced engineers may locate information in minutes, whereas engineers new to an environment may need 3–5 days. That is anecdotal motivation, not a validated performance baseline.

## Product vision
Build ONE read-only agent with TWO closely related user workflows that use shared data and retrieval:
1. **Knowledge Q&A:** A user asks about PAM concepts, onboarding, password rotation, web connectors, or configuration. Return an evidence-grounded response with source citations.
2. **Ticket investigation:** A user provides a synthetic support ticket. Classify the issue, use tools to investigate technical docs and simulated environment/incident records, and return a structured investigation with next checks, citations, and uncertainties.

## Illustrative ticket
"Password rotation failed for a Linux privileged account on LNX-001 shortly after onboarding. What should I check?"

## Narrow MVP
- One LLM agent with direct tool/function calling (not multiple agents).
- Three read-only tools:
  - `search_documentation(query)`: retrieve passages and source metadata from an indexed, permitted documentation collection.
  - `get_asset_details(asset_id)`: retrieve a synthetic application/server/account record.
  - `search_past_tickets(query)`: retrieve similar synthetic support cases.
- Support three categories only: account onboarding, password rotation, and custom web connector troubleshooting.
- Inputs: natural-language question or support ticket.
- Outputs: issue category when relevant, relevant findings, cited passages, suggested checks, missing information, uncertainty, and escalation advice when evidence is insufficient.
- Start with public documents that can be used appropriately, plus synthetic (never real customer) enterprise records and tickets.
- Build a simple UI if time permits; prioritize tested functionality.

## Engineering learning objectives
RAG and embeddings; retrieval/chunking; LLM function calling; bounded multi-step tool use; structured outputs; evaluation of retrieval, answer grounding, tool choice and classification; basic tracing; Docker/reproducibility.

## Evaluation
Create a labelled set of about 20–30 synthetic questions/tickets for the MVP (expand if time permits). Measure answer correctness and citation support, issue-classification correctness, and appropriate tool selection. Include unanswerable cases. Report actual measurements, not claimed savings or fabricated results.

## Proposed stack (suggestions, not fixed requirements)
Python; course-supported LLM API; direct function calling; a simple local vector store (e.g., Chroma or FAISS); Streamlit for the UI; pytest; basic logging/tracing; optional Docker. Prefer course patterns over extra frameworks where practical.

## Schedule and constraints
Aim for a modest working MVP in roughly 2–3 weeks only if time and course progress permit; allow longer for evaluation and polish. Developer has a full-time job and is new to building AI projects. Work in small, demonstrable increments. Do not broaden scope to enterprise deployment.

## Excluded from v1
Real CyberArk/IDIRA authentication or APIs; access to privileged credentials; actions that change accounts or passwords; production ticketing integrations; multi-agent orchestration; advanced compliance certification; live customer data; broad vendor comparisons.

## Source-of-truth rule
This file captures the conclusions of a longer ChatGPT project-selection interview. It is a curated handoff, not an automatic live synchronization with ChatGPT. Update this document when scope or decisions change.

## GitHub portfolio deliverables
Clear README and setup instructions; architecture diagram; runnable code; synthetic test data; evaluation examples/results; meaningful tests; transparent limitations; optional Docker and demo.

## Current testing increment

Five pytest scenarios now exercise the real notebook agent and local tools using
scripted model messages; rotation is checked in either tool-call order. These are
offline Python contract tests, not measurements of LLM tool selection or grounding.
An explicitly enabled `--live` rotation test exercises real OpenAI model choices;
it is skipped by default. Citation and uncertainty checks remain heuristics, with
claim-level factual support and safe recommendations requiring human review. The
original unittest suite and production agent remain unchanged. See README for commands.

## Incremental PydanticAI migration

The intended agent framework is PydanticAI, following the Buildcamp. The manual
Responses API notebook remains the working three-tool baseline during migration.
Phase 2 registers all three read-only tools on one `openai:gpt-4o-mini` Agent in
`pam_agent_pydantic.py`, delegating real retrieval to reusable `pam_tools.py`.
Shared retrieval preserves notebook fields, TF-IDF ranking, result limits,
validation, missing-asset responses, and independent return objects. Cached
synthetic data/indexes load lazily. The notebook retains its self-contained
implementation temporarily to preserve teaching variables and tests; parity tests
compare both implementations.

The preserved `investigate_asset` entry point now supports all three workflows,
validates questions up to 8,000 characters, and bounds runs to six model turns and
eight total tool executions. Offline FunctionModel tests verify actual framework
execution, result linkage, retrieval parity, validation, and budgets, not genuine
LLM tool selection or grounding. Phase 4 live tests later completed all three
original scenarios: A passed automated checks with attribution gaps; B omitted
citations/documentation, and C invented an unretrieved asset citation. B/C failed.

Phase 3 adds `pam_evidence.py` and a backward-compatible higher-level entry point,
`investigate_with_evidence`. It derives successful evidence IDs from linked actual
framework messages, validates disclaimer/citation format, membership and retrieved
kinds, and explicitly reports citation pass/failure. It returns redacted tool-result
traces with local call aliases and aggregate usage from the framework. Trace order
reflects history order, not wall-clock parallel execution. The original answer is
preserved unredacted for review; it is not safe to treat the whole summary as a log.
Citation checks do not establish claim-level grounding.

Native bounded correction now uses an output validator and ModelRetry on the same
agent, validating successful evidence from RunContext.messages. A maximum of one
output retry is enforced by AgentRetries(output=1); another invalid final answer
raises UnexpectedModelBehavior. Both entry points preserve return types on success;
the higher-level function no longer returns a successful summary after persistent
citation failure. The six-request/eight-tool budgets include correction. During
correction, tool preparation hides inventory/ticket tools and permits only a not-yet-
attempted documentation search. Instructions address nearby source attribution,
unknown assets, historical uncertainty, and the absence of escalation capabilities.

Default validation and restricted correction tools are tested offline separately
from legacy protocol/draft-reporting tests, which explicitly disable correction
through a test-only state override. Usage and safe traces still derive from actual
framework messages. No live retest of correction has been run or authorized in this
increment. Claim-level grounding and required retrieval are not semantically
validated. No judge, Logfire, or other monitoring has been added.

## Reliability and diagnostic increment after the correction retest

A subsequent controlled live B retest passed citation membership but still gave
technical advice without documentation; its uncertainty wording was missed by a
heuristic. C raised UnexpectedModelBehavior without retained messages, so its exact
failure mechanism is unknown. The earlier exception chain does not establish
output-retry exhaustion.

The live harness now captures failed-run messages in memory using PydanticAI's
supported capture_run_messages context. `pam_diagnostics.py` emits only redacted
evidence/tool metadata, typed output/tool retry categories, safe exception metadata,
and explicitly partial reported-response usage. It never emits or persists drafts,
raw arguments/history, exceptions, or sensitive content. Entry-point return types
and successful fields are unchanged; failures still raise. Offline cases show that
output rejection, invalid tool arguments, and repeated hidden-tool requests can all
terminate a run, with different safely observable retry evidence. No live diagnostic
retest has been performed in this increment.

The existing output validator now rejects a conservative, documented subset of
explicit technical actions without nearby returned documentation matching the topic
vocabulary. It permits basic missing-evidence requests. Correction may retrieve
missing documentation or omit procedures; budgets remain six requests/eight tools/
one output retry. This lexical guard does not establish semantic grounding and may
miss paraphrases or flag complex narrative wording. The uncertainty heuristic now
recognizes undiagnosed-current-incident phrasing with negative cases retained.
The next step is a separately authorized single live C diagnostic retest; no judge,
Logfire, new framework, original-notebook, or dataset changes are included.

## Consolidated offline reliability increment

The latest controlled C run passed with an observed output correction. B retrieved
asset/ticket evidence but terminated after output validation; its earlier diagnostics
could not identify the failed checks. Validation now emits fixed reason codes at
the check branches, preserving existing readable messages. Each run retains only
its own rejection-code history for safe failure reporting. Terminal codes are
reported only when carried by the terminal validation exception; otherwise omitted.
Both entry points and successful result fields remain compatible.

New offline B/D/E tests execute real framework tools with scripted model messages:
rotation evidence and both documentation-correction paths, explicit persistent
failure, custom web connector evidence in either order, and insufficient evidence
for a definitive diagnosis. These are deterministic contracts, not proof of LLM
reasoning or semantic grounding. The next justified live step is a separately
authorized single B verification with code-level failure reasons; no live requests,
new tools/frameworks, budget increases, dataset changes, or notebook rewrites are
part of this increment.

## Question 3 live judge test

The opt-in `tests/test_pydantic_judge.py` homework test evaluates one real rotation
agent run with a separate PydanticAI gpt-4o-mini judge. It uses the course's structured
criterion/feedback and async assert_criteria pattern. Only the accepted answer,
actual tools, successful evidence IDs, and three fixed criteria go to the judge;
raw arguments and record bodies are withheld. Every criterion must be evaluated
exactly once; failures propagate without rerunning either agent. Judge results
remain probabilistic and cannot replace source-level human grounding review.
Production agent behavior, tools and budgets are unchanged. No monitoring added.

## Optional Streamlit frontend

`app.py` is a small native Streamlit chat frontend calling the unchanged
`investigate_with_evidence(question)` entry point. It loads the existing local
.env, uses real gpt-4o-mini requests on submission, and preserves agent budgets and
validation. Answers and redacted activity/evidence/usage are displayed in the
current browser session, with a clear-history button and safe failure messages.
Chat history is visual only; questions run independently. There is no streaming,
new agent/tool, authentication, persistence, monitoring, or deployment infrastructure.
Offline AppTest tests use interface-only stubs; the app itself always calls the real
agent. See README for startup and a single manual paid test procedure.

The optional Streamlit UI temporarily disables custom final-answer rejection and
correction via validate_output=False for manual experimentation. It displays an
explicit unverified-output notice and labels post-run citation checks informational.
Both agent entry points default to validation enabled; tools and usage limits are
unchanged. No paid requests were made to verify this UI-mode change.

Monitoring Question 1 increment: the Streamlit branch uses official Logfire
instrumentation on the existing single PydanticAI agent, with content and exception
payloads excluded. Each UI investigation has an anonymous-session root span. Reported
usage drives in-memory session totals and gpt-4o-mini list-price cost estimates;
partial failures are explicitly incomplete. Experimental UI validation remains off.
No replay, evaluation, database, remediation or additional agent is introduced.

Live monitoring verification (2026-11-04): one real onboarding question through
Streamlit's existing entry point completed with 2 model requests and 1 documentation
tool call; 1,926 input / 283 output tokens, estimated $0.00045870. Root, agent, two
model and one tool span were observed under one trace, with HTTP 200 trace-ingestion
acknowledgements. Dashboard visibility was not independently inspected. Informational
citation checks passed; this does not establish claim-level factual correctness.

## Data expansion review (2026-11-14)

On feature/streamlit-ui, the supplied synthetic expansion increases knowledge/assets/tickets to 25/12/18 while preserving every original record. Offline baseline: 164 passed, 5 skipped; expanded: 143 passed, 21 failed, 5 skipped. Broad-query historical retrieval regressed. Three authorized real gpt-4o-mini investigations used the existing Streamlit validation opt-out; citation/documentation issues remain. See docs/pam_expansion_review_results.md and docs/pam_expansion_live_results.json. No production behavior or assertions were changed; this describes the initial review before the accepted curation below.

Data-only resolution: excluded new TKT-010/TKT-011/TKT-012 to restore mixed-query historical retrieval without rewriting records or changing production behavior/tests. Final counts: 25/12/15. Full offline suite: 164 passed, 5 skipped, 19 subtests passed; one existing warning. No additional API calls. Review report and pam_expansion_retrieval_resolution.json document exact failure groups, exclusion analysis, rankings and coverage limitations. The curated datasets and offline contracts were subsequently reviewed and accepted.

## Capstone Question 1 batch execution

The approved evaluation set contains exactly 50 scenarios: 15 happy_path, 12
varied_phrasing, 10 edge_case, 6 out_of_scope and 7 breaking. The small
`evals/run_batch.py` runner validates offline by default and requires `--live` for
paid execution. It reuses the existing PydanticAI agent in Streamlit's
validate_output=False mode and existing metadata-only monitoring. Durable
started/result JSONL events prevent automatic repetition after failure or
interruption; resume requires matching scenario, data and code fingerprints.
This increment records real executions, not gold labels or answer-quality scores;
no LLM judge or production behavior changes are included. See evals/batch_report.md
for the completed batch outcome.

Question 1 batch completed: 50/50 real-model investigations returned answers, no
execution failures, 88 model requests and 52 tool calls. Reported usage totals
80,382 input/11,727 output tokens; estimated USD 0.01909350 at existing monitoring
rates. Informational citation checks failed on 27 answers, and full informational
checks flagged 33 scenarios; these are not gold labels or quality scores. All
results and traces are preserved in evals/results.jsonl and the 50-row results.csv
export. No retries, judge calls or further experiments were launched.
Question 1 collection is complete; answer-level review remains necessary. See evals/batch_report.md.

## Question 1 finalized (2026-11-15)

Question 1 designs scenarios and collects real-agent outputs for later review;
it does not establish correctness or create gold labels. The accepted 50-row set
covers 13 onboarding, 16 password_rotation, 15 web_connector and six out_of_scope
questions, including Windows/Linux, historical comparisons, missing evidence and
safety/grounding boundaries. The curated data remains 25 articles/12 assets/15
tickets, with all original records intact.

Execution returned 50 answers, zero execution failures, 92,109 reported tokens
and an estimated USD 0.01909350. All 50 have Logfire trace IDs. Citation checks
failed on 27 answers; full informational checks flagged 33 scenarios including
citation findings. Execution success is not answer correctness. Existing Logfire
spans support tool/usage investigation without sending question/answer contents;
ingestion acknowledgements do not prove dashboard visibility or answer quality.

Reproduction and safe resume commands, scenario distribution, artifact links and
limitations are documented in README.md. `evals/results.jsonl` preserves started
and terminal events; `evals/results.csv` provides 50 review rows. The runner hashes
scenarios, datasets and code, preserves validation opt-out and existing agent
budgets, and skips all previously started investigations. Offline verification:
172 passed, 5 skipped and 19 subtests passed, with one existing warning. No new
API calls, gold labels or judge implementation are part of finalization. Question 2
has not started.

## Question 2 — Human evaluation (completed)

`evals/label_evals.py` implements the course's human review workflow separately
from production app.py. It reads all 50 saved terminal results, shows full answers
and safe tool/evidence metadata, and reconstructs source records only from saved
retrieved IDs and fingerprint-matched datasets. Merely mentioned/cited IDs are
listed separately. It never imports or executes the agent or invokes a judge.

Human-confirmed Good/Bad decisions, required primary Bad categories and notes
persist in evals/labels.csv keyed by scenario_id. Navigation and progress do not
label anything. Atomic replacement, a file lock, read/merge on save and stale-edit
checks protect prior labels, including edits from different browser sessions.
There is no automatic labeling or reset control. No labels.csv was generated by
implementation; offline UI/storage tests use temporary test fixtures only.
The professional interface title is PAM Agent Evaluation Console. Launch with
`uv run streamlit run evals/label_evals.py`. The human reviewer subsequently
completed 20 responses: 10 Good and 10 Bad, persisted in evals/labels.csv. The most
common Bad category is wrong_evidence_or_citation (5), followed by hallucination
(3), incorrect_tool_use (1) and incomplete (1). Thirty responses remain unlabeled.
No human labels were fabricated by the coding assistant. Question 1 outputs,
production behavior and curated datasets are unchanged.

## Question 3 — Judge V1 (historical baseline)

The human-reviewed subset was verified as exactly 20 rows: 10 Good, 10 Bad;
Bad categories 5 wrong_evidence_or_citation, 3 hallucination, 1 incorrect_tool_use,
1 incomplete. Judge V1 joins by scenario_id, normalizes case, withholds all human
review fields from model input and separates trace-confirmed reconstructed evidence
from reference inventory. The existing synthetic datasets and primary agent remain
unchanged. Prompt v1.txt and execution code were frozen before paid execution.

Twenty real gpt-4o-mini structured evaluations completed without execution errors,
with no automatic retries. Bad-positive TP=10, FP=9, FN=0, TN=1: accuracy 55%,
precision 52.63%, recall 100%; nine human-Good/judge-Bad disagreements. Usage:
30,971 input/2,564 output tokens; estimated USD 0.00618405. Complete reasoning,
human notes, provisional disagreement observations, metrics and limitations are in
evals/judge_v1_report.md and judge_v1_results.csv. The manifest/event journal retain
fingerprints and incremental execution records. These are subset agreement metrics,
not gold adjudication or original-agent quality scores. V1 was not refined after
execution; V2 and further paid experiments are explicitly deferred to ChatGPT review.

## Targeted Judge V2 preparation (historical pre-execution milestone)

Following human/ChatGPT review of V1 disagreements, v2.txt adds explicit response-type
assessment before applying evidence and citation criteria. Clarification, honest
asset_not_found and pure security refusals are not failed for missing unnecessary
citations; factual claims and substantive procedures retain evidence requirements,
and all safety/grounding boundaries remain. No scenario-specific labels are embedded.
The output schema and prepared model inputs are unchanged.

The runner supports --version v2 with separate output files and post-execution
comparison against V1, including corrected/regressed agreement with human labels.
Dry-run validates the same 20 cases and identical input hashes; V1 prompt/results,
labels and original datasets/outputs are unchanged. V1 is verification-only. Paid
V2 execution requires a later explicit user authorization; no V2 predictions or
metrics exist yet. See README.md for offline commands and the planned artifacts.

## Authorized Judge V2 execution completed

Exactly 20 explicitly authorized real gpt-4o-mini V2 evaluations completed once,
without execution errors or automatic retries. Bad-positive TP=10, FP=6, FN=0,
TN=4: accuracy 70%, precision 62.5%, recall 100%. S028, S044 and S048 corrected
V1 disagreements, supported by inspection of saved missing-asset/refusal responses;
no previously correct prediction regressed. Six disagreements remain (S001, S005,
S023, S029, S035, S049). S028 is the selected course-submission candidate.

Usage: 41,951 input/2,408 output tokens (44,359 total), estimated USD 0.00773745.
Separate V2 results/report/manifest/events and comparison JSON preserve outcomes.
Relevant offline tests: 17 passed. Approved V2 prompt, V1 artifacts, labels, primary
outputs, production agent and datasets remain unchanged. Same-subset agreement
improvement is not held-out validation. No further prompt iteration, agent run or
judge evaluation is part of this task. Stop for ChatGPT review.

## Questions 2 and 3 finalized

ChatGPT reviewed and approved the human evaluation and both judge iterations.
The structured PydanticAI gpt-4o-mini output remains reasoning then label. V1:
accuracy 55%, Bad precision 52.63%, recall 100%, TP/FP/FN/TN 10/9/0/1. V2:
accuracy 70%, precision 62.5%, recall 100%, TP/FP/FN/TN 10/6/0/4. False positives
fell from 9 to 6; S028/S044/S048 were corrected, with no prediction regressions.

The targeted V2 change assesses response type before citations, distinguishing
clarifications and security refusals from source-based investigations while retaining
safety/grounding checks. S028 is the corrected example: an honest asset_not_found
response cannot cite a nonexistent record. Both reasoning versions and its saved
trace are preserved in evals/judge_v2_report.md. V2 is in-sample: the same 20 human
examples informed improvement, so these are not held-out performance claims.
Six disagreements remain. No new calls, label/result changes or further iterations
are part of finalization. Question 1 reproduction instructions remain in README.md.

Final full offline verification: 202 passed, 5 skipped, 19 subtests passed, with
one existing event-loop deprecation warning. Finalization verified unchanged
human labels and frozen V1/V2 prompts/predictions, metric consistency, professional
console title and a credential scan. No additional OpenAI requests were made.
