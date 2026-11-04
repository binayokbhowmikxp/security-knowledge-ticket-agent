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
