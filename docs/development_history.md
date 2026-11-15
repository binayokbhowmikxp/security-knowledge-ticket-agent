# Development history and archived implementation notes

This document preserves the README and project context from commit
`c269dbfd83c98af83ae15dd7b948051c09e7142d`, before the capstone presentation cleanup.
The archived text is historical: words such as "planned", "current", "next" and
"not yet implemented" refer to the milestone at which each paragraph was written.
Dataset counts, validation settings and test counts changed over time. Do not use
these snapshots as the current setup guide or as authorization for paid calls.
See the [current README](../README.md) and [current project context](../PROJECT_CONTEXT.md).
Commands in the archive assume the repository root, not the docs directory.

## Documentation audit and relocation

The presentation audit found:

- A planned-assistant introduction despite a working PydanticAI agent and Streamlit UI.
- Conflicting dataset counts: 15/7/9 in the older Data section versus curated 25/12/15.
- Claims that evaluation, a judge or monitoring were pending despite completed artifacts.
- Notebook-first setup that omitted a clear current application path and Python requirement.
- Output-validation/correction descriptions that did not distinguish Python defaults from the Streamlit validation opt-out.
- Repeated test, evidence, tracing, setup and evaluation explanations across migration increments.
- A legacy notebook loop budget described as if it were the current PydanticAI per-run budget.
- Historical course exercise numbering that could be confused with completed capstone evaluation stages.
- Vendor examples and anecdotal investigation times that could obscure the vendor-neutral synthetic scope or imply measured business benefits.

The current README consolidates these into an overview, architecture, quick start,
verification commands, evaluation evidence and limitations. This archive retains
technical teaching details: notebook/scripted-model parity, tool-call linkage,
independent record copies, lazy indexes, evidence membership, bounded correction,
lexical documentation guards, retry diagnostics, usage redaction, early live runs,
monitoring, atomic label storage and versioned judge execution. Historical reports
and source-provenance files are unchanged.

## Archived README (verbatim content, relative link targets adjusted)

# Enterprise Security Knowledge & Ticket Resolution Agent

A planned read-only assistant for evidence-grounded Privileged Access Management (PAM) knowledge Q&A and synthetic support-ticket investigation. Built as a capstone for Alexey Grigorev's AI Engineering Buildcamp: From RAG to Agents.

## The Problem

Modern organizations rely on hundreds or thousands of servers, databases, applications, and cloud services to run their business. Many of these systems use privileged accounts — accounts with elevated permissions that can perform sensitive operations, such as administering servers, managing databases, or accessing critical infrastructure.

Privileged Access Management (PAM) solutions, such as CyberArk, help organizations secure and manage these powerful accounts. They provide capabilities such as credential management, password rotation, privileged session monitoring, and controlled access to critical systems.

However, managing and troubleshooting a PAM environment can be challenging.

### The Knowledge Problem

In a large enterprise, technical knowledge is often scattered across multiple sources:

- Vendor documentation: Product configurations, integration guides, troubleshooting procedures, and best practices.
- Internal knowledge bases: Organization-specific instructions, security policies, and onboarding procedures.
- Environment information: Details about servers, applications, databases, privileged accounts, and their configurations.
- Historical support tickets: Previously encountered issues, investigations, and resolutions.
- Custom integrations: Documentation for application-specific connectors and configurations.

Although this information may already exist, finding the right information at the right time is often difficult.

Experienced engineers may know exactly where to look, while newer engineers may spend hours or even days searching documentation, consulting colleagues, and investigating issues.

### A Real-World Example

Imagine a security engineer receives the following support ticket:

> "The automated password rotation for a privileged account on a Linux server has failed. Please investigate."

Before recommending a solution, the engineer may need to:

1. Identify the affected server and privileged account.
2. Understand how the account is configured in the PAM system.
3. Locate the relevant vendor troubleshooting documentation.
4. Search for similar incidents and their previous resolutions.
5. Identify possible causes and determine appropriate troubleshooting steps.

Completing this investigation can require searching multiple systems and manually connecting information from different sources.

### Why This Matters

Inefficient knowledge discovery and troubleshooting can lead to:

- Longer incident investigation and resolution times.
- Increased dependency on experienced engineers.
- Repeated investigations of previously encountered problems.
- Inconsistent troubleshooting approaches.
- Delays in supporting business-critical systems.

This project aims to reduce the time engineers spend searching for information and investigating common PAM issues.

It will explore how Retrieval-Augmented Generation (RAG) and tool-calling AI agents can bring relevant knowledge together, investigate support tickets, and provide evidence-backed troubleshooting guidance.

The system is intended to assist engineers, not replace their judgment or automatically modify critical infrastructure.

## Planned Workflows

- **Knowledge Q&A:** Ask a PAM question and receive an answer grounded in documentation, with source citations and explicit gaps where evidence is missing.
- **Ticket investigation:** Provide a synthetic support ticket and receive an issue category, relevant findings, suggested checks, citations, missing information, uncertainties, and escalation advice when evidence is insufficient.

The initial MVP will cover **account onboarding, password rotation, and custom web connector troubleshooting**. One tool-calling agent will use three read-only tools: `search_documentation(query)`, `get_asset_details(asset_id)`, and `search_past_tickets(query)`.

For example, a ticket might ask: "Password rotation failed for a Linux privileged account on LNX-001 shortly after onboarding. What should I check?"

## Current Status

The repository contains setup and Week 1 RAG notebooks, plus a Week 2 agent notebook using the OpenAI Responses API. One agent dynamically selects among three read-only tools over 25 synthetic knowledge articles, 12 synthetic assets, and 15 historical tickets. The agent notebook includes concise traces and three live smoke scenarios; offline regression tests cover validation, missing evidence, conversation handling, and loop limits. Full labelled evaluation remains planned.

The MVP will use only permitted public documentation and synthetic asset records and tickets. It will not access real customer data or credentials, connect to live vendor systems, or change accounts or passwords.

## Setup

1. Install uv if you don't have it yet: https://docs.astral.sh/uv/getting-started/installation/

2. Clone this repository (or download the zip and extract it).

3. Create a `.env` file from the template and add your API key:

       cp .env.example .env

4. Install dependencies:

       uv sync

5. Start Jupyter:

       uv run jupyter notebook

## Notebooks

- `notebooks/01-setup.ipynb` - smoke test that confirms your environment works
- `notebooks/02-rag.ipynb` - a minimal RAG baseline you can adapt to your own data
- `notebooks/03-agent.ipynb` - the self-contained read-only agent, tool definitions, tracing, and live smoke tests

Run `03-agent.ipynb` from first cell to last using the project's `.venv` kernel, with Jupyter launched from the repository root or `notebooks/`. Its final code cell makes paid API calls using the existing `.env` configuration and defaults to `gpt-4o-mini`. API errors propagate rather than producing simulated answers. Notebook outputs are cleared in the repository.

Run offline tests without API requests:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Week 1 always retrieves documents and then calls the model. Week 2 lets the model request documentation, asset details, or prior tickets, read their results, and request more evidence before answering. The loop allows at most six model turns and eight tool calls per turn. Tools use only local JSON data; no new dependencies are needed. Traces show argument lengths and returned IDs without printing raw query text.

## Data

`data/pam_knowledge.json` contains 15 synthetic training articles covering account onboarding, password rotation failures, and custom web connector troubleshooting. `data/pam_assets.json` contains 7 synthetic inventory records; `data/pam_tickets.json` contains 9 synthetic historical cases. None are official vendor guidance or validated production procedures. Historical outcomes do not confirm the cause of a current incident. Permitted public documentation remains a future addition.

Search uses minsearch word matching, without embeddings. Citation checks confirm that cited IDs were returned by a tool; they do not establish that every claim is supported. Model tool choices and answer quality still require review against the records. See `notebooks/03-agent.ipynb` for the three tools and live examples.

## Pytest scenario tests

Install development dependencies with `uv sync --group dev`. Pytest provides plain
`assert` tests and fixtures (shared test setup); it adds no runtime agent framework.

```sh
# Five scenarios; rotation runs in both tool-call orders. No API requests.
uv run pytest tests/test_agent_scenarios.py -v
# All pytest tests, including the original unittest cases; live is skipped.
uv run pytest -q
# Original 20 unittest regression tests only.
uv run python -m unittest discover -s tests -v
```

`tests/test_agent_scenarios.py` is the suggested Question 2 submission file;
`tests/conftest.py` and the existing `tests/test_agent_notebook.py` helpers are also
required to run it. The five scenarios cover Linux onboarding, rotation with prior
incidents, web connector investigation, an unknown asset, and insufficient evidence.

The offline tests **predetermine model tool choices, search queries, and final
answers**. They execute the real `run_agent()` loop and local tools, checking returned
records, trace entries, tool-result `call_id` linkage, and citation membership. They
do not measure genuine LLM tool selection or answer quality. Rotation is tested in
both asset-first and tickets-first order; documentation search is optional for that
scenario's missing-evidence answer.

The `agent_namespace` fixture loads only tagged notebook definitions and synthetic
data with `.env` loading disabled. The `tool_records` fixture observes actual tool
arguments/results in memory while calling the original functions; it restores the
function mapping after each test. This allows argument checks without weakening the
production trace's redaction. Existing unittest helpers and tests are unchanged.

To deliberately enable the paid live Scenario 2 integration test, configure your
OpenAI key in `.env`, then run:

```sh
uv run pytest tests/test_agent_scenarios.py -m live --live -v --tb=short
# Optionally save the redacted trace/evidence IDs as JUnit test properties:
uv run pytest tests/test_agent_scenarios.py -m live --live -v --tb=short --junitxml=/tmp/pam-live-results.xml
```

The live test uses the actual model (the agent's default `gpt-4o-mini`), real tool
choices, and the same rotation assertions as the offline test. It has a per-request
60-second timeout and disables API retries; the agent still bounds model turns and
may make one citation-revision request. Failures propagate. `--live` is required,
including when using `-m live`; otherwise the test skips before client creation.
Only the redacted trace and evidence IDs are recorded as report properties. Avoid
`--showlocals` or debug logging when handling credentials or raw API responses.

Citation membership, relevant search terms, uncertainty wording, and a few obvious
unsafe command markers can be checked automatically. These are heuristics: human
review must still assess every claim against the retrieved records, historical
versus current causality, invented procedures, and authorization boundaries. A
scripted safe answer passing is not evidence that the LLM will produce one. The
live test is opt-in and was not run as part of this offline implementation.

## PydanticAI migration: three-tool prototype

`pam_agent_pydantic.py` now registers all three real read-only tools on one
`Agent` using `openai:gpt-4o-mini`. The existing manual notebook remains the
working baseline. PydanticAI 2.64.0 is already installed via
`pydantic-ai-slim[openai]`; this increment adds no dependencies.

`@agent.tool_plain` uses each function's signature and docstring to describe a
model-facing tool. The registered functions delegate to `pam_tools.py`, which
validates inputs, reads the existing synthetic JSON, builds the same minsearch
TF-IDF indexes, and returns independent record copies. Article searches return
at most five records, ticket searches at most four. IDs are case insensitive for
asset lookup; unknown assets retain the exact existing `asset_not_found` response.
Data and indexes load lazily and are cached for the process lifetime. Restart the
process after changing datasets. Importing the modules needs no API key, creates
no provider client, and does not load `.env` or make requests.

When a model requests a tool, PydanticAI validates its argument schema, executes
the Python function, links its return value to the tool-call ID, and continues the
conversation. We do not manage a manual Responses API loop. Python value checks
(such as a blank query or malformed asset ID) currently raise `ValueError` and
stop a run; they are not converted into corrective model retries. Schema errors
are handled by PydanticAI, with one retry configured.

The existing `investigate_asset(question)` entry-point name is preserved and now
supports knowledge questions and three-tool investigations. It rejects blank,
non-string, and over-8,000-character questions, then trims whitespace. Each run
allows six model turns and eight total tool executions, accommodating evidence
search refinement. `UsageLimitExceeded` stops runs exceeding either budget.
These limits are not monetary caps or counts of SDK transport retries. Direct
`agent.run*` calls require their own question validation and usage limits.

Instructions require documentation for guidance, current inventory for asset
findings, historical tickets for comparisons, bracketed evidence IDs, synthetic
labeling, and explicit uncertainty. Historical resolutions must not be used as
proof of a current cause. Phase 3 adds post-run citation validation and a redacted execution summary,
described below. The current agent also uses native bounded output correction;
the original notebook's manual orchestration remains unchanged.

The notebook retains its self-contained retrieval implementation in this increment
because its indexes, loaded records, and helper variables remain part of existing
teaching cells and tests. This is temporary duplication: PydanticAI retrieval has
one reusable implementation in `pam_tools.py`, while parity tests compare it with
the preserved notebook. Week 1 notebooks and synthetic datasets are unchanged.

Run verification without API requests:

```sh
uv run python -m pytest tests/test_pam_agent_pydantic.py -v
uv run pytest -q
uv run python -m unittest discover -s tests -v
```

Tests follow the [official PydanticAI testing guidance](https://pydantic.dev/docs/ai/guides/testing/):
`Agent.override(model=FunctionModel(...))` scripts model calls while the framework
executes real tools. A fixture explicitly blocks provider requests. Tests cover
onboarding retrieval, rotation investigation in both independent-call orders,
web connector evidence, unknown assets, public tool schemas, call/result linkage,
retrieval parity, independent copies, validation, and both usage budgets.
Predetermined calls and prose do not prove genuine LLM choices, citation
correctness, or answer grounding. The existing opt-in live test targets the manual
notebook, not PydanticAI.

The prototype is ready for a deliberately authorized three-tool live smoke test
using `investigate_asset`, with `OPENAI_API_KEY` supplied by the caller, followed by
human review of messages and evidence. No real PydanticAI model calls were
made during Phases 1–3. Phase 4 live testing subsequently found citation omissions
and an unretrieved asset citation. Native bounded correction is now implemented
offline and awaits a separately authorized live retest. Notebook retrieval
consolidation remains separate. No judge or monitoring is implemented.


## Evidence validation and redacted tracing (Phase 3)

`investigate_asset(question)` still returns the original PydanticAI
`AgentRunResult[str]`. The new `investigate_with_evidence(question)` calls it once
with the same limits, then returns a dictionary containing:

- `answer`: the accepted final answer, unredacted, possibly after one correction.
- `evidence_ids`: unique IDs from successful, linked tool results.
- `trace`: minimal redacted tool-result events.
- `citation_issues`: actionable validation errors, or an empty list.
- `citation_validation_passed`: explicitly false when any citation issue exists.
- `usage`: actual model requests, tool calls, input/output tokens, and total tokens.

`pam_evidence.py` inspects `result.all_messages()`. `ToolCallPart` describes a tool
request; `ToolReturnPart` holds the actual result Python returned. Calls and results
are linked by raw `tool_call_id` and matching tool name internally, independent of
return order. Only successful returns from our three tools supply evidence: article
`id`, inventory `asset_id`, or incident `ticket_id`. Failed/missing lookups, retries,
unmatched returns, and empty searches supply no IDs. Repeated retrieval deduplicates
evidence while retaining separate trace events. Source IDs are never extracted
from the user prompt or final model prose.

Validation checks the full opening synthetic-training disclaimer, bracketed source
format, membership in retrieved evidence, and at least one valid citation for each
retrieved evidence kind (documentation, current assets, historical tickets).
It reports fabricated IDs, unknown source categories, wrong case/ID length, and
grouped source IDs. It does not require a citation for a failed asset lookup. An
uncited insufficient-evidence response can pass when no successful records exist.
The conservative per-kind rule can flag an answer that omits irrelevant retrieved
evidence; it does not decide which findings the answer actually uses. Recognition
of malformed source-like brackets is heuristic, not a universal citation parser.

A passing result is **citation-validated, not proven factually grounded**. Membership
does not show that a source supports the adjacent claim, that every factual claim
has a citation, that historical outcomes are interpreted correctly, or that an
uncited answer honestly reflects missing evidence. Human review is still required.
The agent now permits one native output correction, described below. Persistent
validation failure raises an exception instead of returning a successful summary.
The standalone `summarize_result` helper can still report issues in arbitrary raw
results for offline review; it does not itself request correction.

Trace events contain only sequence, an allowlisted tool name, a local call alias,
returned source IDs, and a fixed error code. Actual call IDs are mapped to aliases
like `call_1` because model-controlled IDs could contain private text. Sequence is
message-history return order, not measured parallel execution timing. Unknown tool
names and arbitrary error payloads are never copied. Queries, arguments, questions,
record bodies, raw messages, and exceptions are excluded. **Only the trace and
aggregate usage are intended for routine logging; the answer and raw result are
not privacy-redacted.** No helper prints or sends data to an external backend.
Execution exceptions still propagate normally; do not log arbitrary exception text.

Usage comes from PydanticAI 2.64.0's `result.usage` property, not reconstructed
message counts. Token metrics depend on provider reporting; FunctionModel tests
supply deterministic token usage and verify aggregation. These metrics are not an
invoice or wall-clock timing. No dependency update is required for this increment.
The existing upstream Python 3.13 event-loop deprecation warning remains.

The new deterministic tests exercise real retrieval and orchestration, with
provider requests blocked. They check valid/invalid citations, missing evidence
kinds, unknown assets, empty searches, repeated and reordered calls, redaction,
failed/unlinked results, and actual usage. They do not measure real LLM choices or
answer quality. The code is ready for an explicitly authorized controlled live
three-tool retest using bounded correction; no live retest is run in this increment.


## Bounded native citation correction

Both existing entry points now validate proposed final answers through
`@agent.output_validator`. Its `RunContext.messages` contains the same run's actual
tool executions. The validator reuses `collect_evidence` and `citation_issues`,
never derives evidence from model prose, and raises PydanticAI `ModelRetry` with
specific correction feedback when checks fail. The exact opening disclaimer is
required, and source-shaped Markdown links are rejected in favor of plain IDs.

`AgentRetries(tools=1, output=1)` separates tool retries from the single allowed
output-validation retry. A second invalid proposed answer raises
`UnexpectedModelBehavior`; `investigate_with_evidence` does not return a passing
summary in that case. Six model requests and eight total tool executions still
bound the entire run, including correction. A run already at its request budget
can fail with `UsageLimitExceeded` before correction is possible.

A small fresh `CitationRunState` is passed per run. Tool `prepare` functions use
it to hide inventory and ticket tools after a rejected draft. If documentation has
not yet been attempted, only `search_documentation` remains available for genuinely
missing guidance; after that attempt it is hidden too. A model request to a hidden
tool does not execute Python. This is not necessarily exactly one extra API call:
missing documentation can require a tool-request turn followed by a corrected
answer, all inside the same budgets. The guard does not semantically determine
whether documentation is needed, or forbid multiple documentation calls in one
batch; the overall tool limit still applies.

The returned summary shape is unchanged. Evidence and trace derive from actual
messages, and usage includes all correction-related requests/tokens/tools. A
successful summary contains the accepted answer and no citation issues. Failure
raises; it does not provide a partial success summary. Raw draft histories and
exception contents are not privacy-safe diagnostics.

Instructions now emphasize nearby claim citations, current versus historical
sources, documentation before procedures, no unrelated history searches for an
unknown asset, and recommending escalation rather than claiming the agent can
perform it. These instructions and citation membership checks still do not enforce
semantic support, per-claim coverage, tool-selection correctness, or capability
claims. A syntactically valid but unsupported answer can still pass.

`tests/test_pydantic_correction.py` tests the default validator with FunctionModel
and provider requests blocked: no-retry success, corrected missing/fabricated/link
citations and disclaimer, missing assets, exhausted output retries, restricted
correction tools, missing-documentation retrieval, redaction, and both budgets.
The earlier `tests/test_pam_agent_pydantic.py` protocol and draft-reporting tests
explicitly override run state to report-only (`validate_output=False`) so their
predetermined invalid drafts remain inspectable with all prior assertions intact.
Normal entry points always create validation-enabled state. Direct `agent.run*`
users must supply `deps=CitationRunState()` and their own limits/validation.

Live Scenario B's uncertainty-wording checks now also recognize “exact cause
remains unclear”, “current diagnosis is not established”, and “insufficient
diagnostic evidence”. They remain language heuristics, separate from objective
citation validation and human grounding review. No real-model correction success
is claimed from these deterministic tests.

## Offline reliability and failed-run diagnostics

The latest live results before this increment were: B passed citation membership
but supplied undocumented technical guidance; C raised `UnexpectedModelBehavior`
without a retained result. Its exception chain alone does **not** establish whether
output validation or tool retry activity caused termination. No new live requests
were made while implementing the changes below.

The live smoke harness now wraps the existing entry point with the supported
`capture_run_messages()` context. `pam_diagnostics.py` derives redacted diagnostics
before the in-memory history goes out of scope. It never prints, serializes, or
persists raw histories, drafts, arguments, retry content, exception messages,
response bodies, or traceback text. Only allowlisted tool/source metadata, fixed
error categories, exception type names, integer HTTP status, and execution stage
are emitted. Successful tool returns are distinguished from requested, retried,
or incomplete calls; only completed successful results supply evidence IDs.

PydanticAI 2.64.0 exposes typed `RetryFeedbackPart` for output feedback and retried
`ToolReturnPart` for tool feedback. Diagnostics retain only scope, allowlisted cause,
and available attempt/budget integers. Terminal `ToolRetryError.tool_retry` metadata
is also inspected when present because the last rejected retry may not reach the
history. `ModelRetry` or `UnexpectedModelBehavior` class names alone are not treated
as proof of output-retry exhaustion. When only prior tool-retry context is known,
the category says `framework_failure_after_tool_retry`, not an invented root cause.

`output_validation_retry_observed` and `tool_retry_observed` refer to feedback
actually visible in captured history. Terminal retry metadata is reported separately.
Absence of observed feedback is not proof that no validation was attempted. Partial
usage is the sum of reported tokens on captured responses and their recorded-response
count, clearly marked `partial`; it excludes unreturned requests and is not a total
request count, total bill, or accepted result. No usage is invented for empty capture.
The agent entry points still raise on failure; capture/reporting belongs to the
caller, and successful result fields are unchanged. Successful live reports also
include typed retry activity rather than guessing correction from request counts.

The output validator additionally applies `documentation_issues` from
`pam_evidence.py`. This is a conservative lexical procedure policy: explicit
technical action verbs paired with vocabulary for dependencies, configuration,
networking, password policy, permissions, web connectors, or timing require a nearby
returned documentation citation. The cited article must contain the same topic
vocabulary. An unrelated article or an asset/ticket citation alone is insufficient.
The model may instead omit the procedure, explain unavailable documentation, and
request sanitized errors, timestamps, or approved diagnostic evidence. These basic
requests, and generic owner/evidence review, do not trigger the technical guard.
Simple explicit negation such as “cannot review configuration” is excluded.

This policy intentionally covers a testable subset of procedural language. It can
miss paraphrases or misread complex negation, quotation, and narrative sentences;
shared vocabulary is not semantic relevance or proof of support. It is **not** a
universal grounding validator. Citation issues remain separate from documentation
policy issues internally. Either can trigger the same single output retry. Missing
documentation is available during correction under the existing tool-preparation
rules. Six requests, eight tool executions, and one output retry remain unchanged.

Offline FunctionModel regressions cover double output rejection, hidden-tool
attempts, argument-validation retry failure, missing assets, partial usage and
private-marker exclusion. Additional tests distinguish undocumented procedures,
retrieval-based correction, removal of unsupported procedures, basic evidence
requests, and unrelated citations. The uncertainty heuristic now recognizes “the
current failure has not been diagnosed” and equivalents while retaining negative
confirmed-cause examples. It remains a language check, separate from citation
validation and human grounding review.

## Fixed validation reasons and offline scenario coverage

Validation checks now produce `(fixed_code, existing_message)` pairs at the failing
branch, without parsing free-text errors. The public `citation_issues` and
`documentation_issues` functions still return the same human-readable messages.
Codes are limited to `missing_citation`, `unretrieved_citation`,
`invalid_citation_format`, `missing_disclaimer`, and
`unsupported_documentation_guidance`.

Each run owns its rejection-code history. If execution fails, the entry point
attaches an immutable code-only snapshot to the original exception and re-raises
it unchanged. The rejecting `ModelRetry` also carries that rejection's codes.
`failed_run_diagnostics` reports an allowlisted `validation_rejections` history and
adds `terminal_validation_reason_codes` only when those codes are actually present
in the terminal exception chain. A later tool/usage failure may retain the initial
rejection history without exposing a terminal output rejection reason; the helper
omits that terminal field rather than guessing. Accepted-result fields and both
entry-point signatures are unchanged. No draft text or source records are added to
safe diagnostics, and no global run history is retained.

`tests/test_pydantic_reliability_scenarios.py` covers rotation with current and
historical evidence, both documentation-correction choices, persistent rejection,
fixed-code privacy/isolation, web connector investigation in either independent
call order, and an honest response to a definitive-diagnosis request. FunctionModel
predetermines choices and prose while PydanticAI executes real retrieval. These
contracts do not establish genuine LLM reasoning, per-claim entailment, reliable
historical interpretation, or consistent real-model correction. The six-request,
eight-tool and one-output-retry budgets, retrieval data/ranking, and original
notebooks are unchanged. No paid retest was performed in this increment.

## Question 3: live LLM judge test

`tests/test_pydantic_judge.py` runs the existing rotation agent once, then awaits
`assert_criteria(result, criteria=[...])` from `tests/judge.py`. Both use real
OpenAI `gpt-4o-mini`; the separate judge receives only the accepted answer, executed
tool names, successful evidence IDs, and the three assignment criteria. Structured
feedback must cover every exact criterion once with a nonempty explanation; missing,
duplicate, altered, or failed evaluations raise an assertion. The judge has one
request and no output-repair retries. Main-agent limits/correction are unchanged.

```sh
# Collect/skip without any API requests:
uv run pytest tests/test_pydantic_judge.py -q
# Deliberately enable the paid agent run plus one paid judge evaluation:
uv run pytest tests/test_pydantic_judge.py --live -v -s --tb=short
```

Pytest-asyncio is a development dependency for the course's async test pattern.
The synchronous production entry point runs in a worker thread; the async judge
uses a separate client. Feedback is probabilistic and does not prove source-level
entailment: inventory/ticket bodies are deliberately withheld from the judge.
No cost tracker, monitoring, or Logfire integration is added.

## Optional Streamlit chat UI

`app.py` provides a small native Streamlit chat interface for the existing
PydanticAI PAM agent. Every submitted question calls
`investigate_with_evidence(question)` with the real `gpt-4o-mini` model and its
existing correction and usage limits. Failed requests display a short safe error;
the UI does not automatically retry them. Agent activity shows only redacted tool
names, returned evidence IDs, and status. A second expander shows actual evidence,
citation status, request/tool counts, and total tokens.

From the repository root:

```sh
uv sync
# Only if .env does not already exist:
cp .env.example .env
# Add your OPENAI_API_KEY locally; never commit the key or .env.
uv run streamlit run app.py
```

Keep an already configured `.env`; the app loads it without displaying credentials.
Open the local URL printed by Streamlit (normally http://localhost:8501).
Submitting a question makes paid OpenAI API requests; merely starting the app does
not. The sidebar's Clear conversation button removes displayed session history.
History is **visual only**: each question executes independently, without previous
turns being sent to the model. There is no streaming, persistent history, judge, authentication or deployment
layer in this UI. Optional metadata-only monitoring is described below.

To manually verify one real UI investigation, submit this once:

> Password rotation failed for a privileged account on LNX-001 shortly after onboarding. Investigate the issue and check whether similar incidents were reported previously.

Review the accepted answer, citations, Agent activity, and Evidence and usage.
If it fails, preserve the safe error for review rather than repeatedly submitting.
Offline UI tests use Streamlit AppTest with a test-only stub to check interface
behavior without costs; no simulated responses are included in the application.

```sh
uv run python -m pytest tests/test_streamlit_app.py -q
```

The Streamlit UI currently uses **experimental unvalidated output mode**:
`investigate_with_evidence(question, validate_output=False)`. The actual generated
answer is displayed without custom final-answer rejection or correction. Post-run
citation checks are informational only, and answers are not verified. Both Python
entry points retain `validate_output=True` by default; tool validation and the
six-request/eight-tool limits are unchanged.

### Monitoring (capstone Question 1)

Run `uv sync`, then set `OPENAI_API_KEY` and the Logfire project's write token
`LOGFIRE_TOKEN` in your local `.env` (never commit either). Start the UI with
`uv run streamlit run app.py`. Missing `LOGFIRE_TOKEN` disables telemetry export;
the agent can still run. No read token, querying or trace replay is required.

Open your project's Logfire live view and filter service `pam-agent`. Each submitted
question creates a `PAM investigation` root span with an anonymous session UUID,
with nested agent, model-request and tool spans. Durations, reported token usage,
execution status and typed retry metadata are available. The UI shows the trace ID
for successful runs; use it to locate that investigation. Errors retain safe
classification, not exception messages or stack traces. Experimental UI output
validation remains disabled; monitoring does not verify answer quality.

The UI shows successful request input/output tokens and estimated USD cost, plus
session totals. Rates in `pam_monitoring.py` are **$0.15/million input tokens** and
**$0.60/million output tokens**, from the
[official gpt-4o-mini pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini).
Cost = `(input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000`.
These are list-price estimates, not invoices; cache discounts and billing adjustments
are excluded. Partial failed-run usage is counted when reported, with an incomplete
usage warning; unavailable usage is never claimed as zero actual cost. Rerendering
history does not add usage. Clearing chat keeps session totals; a new browser session
starts new totals. No persistent accounting database is added.

Privacy: official PydanticAI instrumentation disables content, binary content and
model request parameters. Default Logfire scrubbing stays enabled; no HTTP body
instrumentation is enabled. Exception events and status descriptions are suppressed
because they can contain provider payloads. Metadata such as tool names, model,
tokens, timing and anonymous session IDs still leaves the process. Chat answers and
existing redacted diagnostics remain in Streamlit session memory; this is not a
promise that all application memory is free of sensitive text. Use synthetic data.

Monitoring dashboard screenshot: **TODO — add a reviewed screenshot with no secrets
or question/answer content after verifying the live trace.**

## Accepted curated data

The curated knowledge base contains **25 synthetic articles, 12 assets and 15
historical tickets**. Every original record and schema is preserved. Three new
onboarding tickets were excluded after retrieval review; the original 164 offline
contracts then passed. The data and 50 evaluation scenarios have been reviewed
and accepted. See [the expansion review](../docs/pam_expansion_review_results.md) and
[source notes](../docs/pam_expansion_sources.md) for provenance and ranking tradeoffs.

## Capstone Evaluation — Question 1: Design Scenarios and Collect Data

Question 1 is complete. Its purpose is to collect reproducible examples of how
one read-only PAM agent selects tools, retrieves evidence and answers realistic
engineering questions, including insufficient-evidence and adversarial requests.
It does not measure answer correctness or assign gold labels.

[The approved scenarios](../evals/scenarios.csv) contain exactly 50 questions with
columns `question,category,type`; CSV row order defines IDs S001–S050.

| Scenario type | Count |
|---|---:|
| happy_path | 15 |
| varied_phrasing | 12 |
| edge_case | 10 |
| out_of_scope | 6 |
| breaking | 7 |

Topic coverage is 13 onboarding, 16 password rotation, 15 web connector and six
out-of-scope questions. It includes Linux and Windows account onboarding,
verification and policy failures, historical incident comparisons, ambiguous or
missing assets, insufficient diagnostics, and attempts to obtain unsupported
root causes, fabricated citations or unauthorized privileged actions.

The real batch reused the existing PydanticAI `gpt-4o-mini` agent through
`investigate_with_evidence(question, validate_output=False)`, matching Streamlit.
The existing six-request/eight-tool budgets and tool-validation behavior were
preserved. Each scenario was investigated once; SDK transport retries were disabled.
No mocks or LLM judge were used for collection.

Validate locally without API calls (after installing the project dependencies):

```sh
.venv/bin/python evals/run_batch.py --dry-run
.venv/bin/python -m pytest -q
```

To execute only unstarted scenarios, the explicit `--live` flag is required and
makes paid OpenAI requests. The runner requires `feature/streamlit-ui`. Configure
`OPENAI_API_KEY` locally and optionally `LOGFIRE_TOKEN`; never commit `.env`.

```sh
.venv/bin/python evals/run_batch.py --live
```

The committed batch is already complete: dry-run reports **0 unstarted** scenarios,
and the live command does not repeat its investigations. The same command on a
fresh collection without a journal would incur API costs. Preserve the committed
results; a deliberately separate new collection requires separate authorization.
Exact model wording is nondeterministic even with identical inputs.

[The runner](../evals/run_batch.py) validates columns, types, nonempty questions,
uniqueness and the approved distribution. Its append-only
[JSONL journal](../evals/results.jsonl) contains one durable `started` reservation
before each call and one `result` afterward: **100 events, 50 answers**. Resume
skips every started scenario, including failures and interrupted attempts, to avoid
repeating an uncertain request. A process lock prevents concurrent batches.
Changed scenario/data/code SHA-256 fingerprints or a malformed journal stop resume
for manual review. Fingerprints, dependency versions, UTC timestamps, model and
validation mode are saved with each event.

[The CSV export](../evals/results.csv) contains the 50 terminal results for manual
review. Both formats retain generated answers, executed tools, safe traces,
evidence IDs, informational checks, reported usage, cost estimates and trace IDs.
[The batch report](../evals/batch_report.md) records detailed findings and limitations.

| Observed execution statistic | Result |
|---|---:|
| Investigations completed / execution failures | 50 / 0 |
| Model requests / executed tool calls | 88 / 52 |
| Input / output tokens | 80,382 / 11,727 |
| Total tokens | 92,109 |
| Estimated API cost (USD) | $0.01909350 |
| Informational citation checks failed | 27 answers |
| Full informational checks flagged | 33 scenarios |
| Recorded Logfire trace IDs | 50 |
| Final offline tests | 172 passed, 5 skipped |

Tool execution totals were 14 documentation searches, 24 asset lookups and 14
historical-ticket searches. No execution failures or output/tool retries were
observed. The cost uses existing monitoring rates of $0.15 input and $0.60 output
per million tokens; it is an estimate, not an invoice, and excludes cache discounts
and billing adjustments. Offline verification also passed 19 subtests, with one
existing event-loop deprecation warning; the five skipped tests require paid opt-in.

**Successful execution is not proof of a correct answer.** Citation membership
checks found omitted/malformed citations and unretrieved references; documentation
checks also flagged guidance needing nearby supporting evidence. These checks
were informational and did not reject or repair answers. They do not prove
claim-level support, safe advice, correct tool selection or a current root cause.
Historical incidents cannot establish current causes. The 33 flags include the
citation findings and are not 33 additional failures. Manual answer review remains
necessary; no gold answers, answer-quality scores or new judge were produced.

Logfire provides metadata-only root, agent, model and tool spans for monitoring
usage, timing and tool activity. Saved trace IDs help locate individual
investigations. Existing instrumentation excludes question/answer contents, raw
provider history, credentials and exception payloads. The retained rolling export
buffer showed HTTP 200 ingestion acknowledgements; dashboard visibility was not
independently verified. Temporary monitoring exports, locks, caches, ZIP files and
`.env` are excluded from version control. This completes the Question 1 collection milestone.

## Capstone Evaluation — Question 2: Human evaluation (completed)

The separate Streamlit **PAM Agent Evaluation Console**
([labeling app](../evals/label_evals.py)) supports review of all 50 Question 1 answers.
The human reviewer completed **20 responses: 10 Good and 10 Bad**, persisted in
[evals/labels.csv](../evals/labels.csv). The remaining 30 responses are unlabeled.

| Primary failure category among the 10 Bad responses | Count |
|---|---:|
| Wrong evidence or citation | 5 |
| Hallucination | 3 |
| Incorrect tool use | 1 |
| Incomplete response | 1 |

Wrong evidence or citation was the most common reviewed failure. Labels and notes
were selected by the human reviewer, not generated from automated checks. Launch
the console from the repository root:

```sh
uv run streamlit run evals/label_evals.py
```

It reads only terminal `result` events from `evals/results.jsonl`, preserving
S001–S050. No agent, API key, monitoring connection or LLM judge is used by this
app. The original full answers, questions, types, categories, executed tools,
safe traces and informational findings are displayed unchanged. Citation findings
are context for a human decision and never assign a label.

Retrieved evidence records are reconstructed from saved evidence IDs against the
fingerprint-matched 25/12/15 synthetic datasets, and explicitly labeled as
reconstructed rather than exact captured tool responses. IDs merely mentioned
or cited without retrieval are shown separately and never promoted to evidence.
If the local datasets no longer match the batch fingerprints, review stops rather
than displaying changed records as frozen evidence.

Select **Good** or **Bad**, add reviewer notes, then click **Confirm label**.
Bad requires one primary failure category: hallucination,
wrong_evidence_or_citation, wrong_scope, incomplete, incorrect_tool_use,
unsafe_recommendation or other. No decision is preselected for an unlabeled row.
The app creates `evals/labels.csv` only on the first human-confirmed save, with
columns `scenario_id,label,primary_failure_category,reviewer_notes,updated_at`.
The timestamp records confirmation time, not an independent quality review.

Previous, Next, Next Unlabeled and direct ID navigation are available; navigation
does not save drafts. Progress shows labeled/50, Good and Bad counts, with Bad
labels grouped by primary failure category. Labels survive browser reloads and
application restarts. Updating a label replaces that scenario's row without
creating duplicates. Each save reloads existing rows under a file lock and uses
atomic file replacement; a stale edit of the same scenario is rejected until the
reviewer reloads its saved label. Invalid or duplicate existing label files fail
closed; there is no reset or delete-all control. Keep a backup of human labels
as with any local review artifact. Lock and temporary-write files are ignored.

The navigation/display/confirmation pattern follows the
[course manual labeling reference](https://github.com/alexeygrigorev/ai-engineering-buildcamp-code/blob/main/documentation-agent/evals/manual/app.py).
The PAM tool adds frozen evidence reconstruction and failure categories without
importing the reference's judge or resetting saved labels.

Run focused offline checks:

```sh
.venv/bin/python -m pytest evals/test_label_evals.py -q
```

No human labels were generated during implementation. Test labels exist only in
pytest temporary directories. Question 1 results and scenarios remain unchanged.

## Capstone Evaluation — Question 3: LLM judge validation (completed)

The structured PydanticAI judge uses `gpt-4o-mini` with output fields `reasoning`
followed by `label` (`good` or `bad`). Both versions evaluated the same 20 manually
reviewed responses using unchanged saved answers and evidence.

### Judge V1

V1 evaluates saved responses with a separate PydanticAI `gpt-4o-mini` structured
judge ([criteria](../evals/judge_prompts/v1.txt), [implementation](../evals/judge.py)).
Human labels are joined by scenario_id; their decisions, notes and failure
categories are never supplied to the judge. Saved successful tool traces identify
retrieved evidence; reference inventory facts are separately marked NOT RETRIEVED.
Citation diagnostics are explicitly nonauthoritative. The original agent is not run.

```sh
.venv/bin/python evals/run_judge.py --dry-run
.venv/bin/python -m pytest evals/test_judge_v1.py -q
# V1 is frozen: this command verifies inputs without model calls or artifact writes.
.venv/bin/python evals/run_judge.py --version v1 --dry-run
```

The completed V1 batch used exactly 20 paid evaluations with no execution errors.
The runner verifies the authorized 20 labels (10 Good/10 Bad and approved category
counts) before live calls, disables transport/output/tool retries and permits one
model request per evaluation. Durable started/result events prevent silent repeats;
changed prompt/data/code/label fingerprints or malformed journals stop resume.
Preserve the saved journal; running on the completed batch makes no new evaluations.

[CSV results](../evals/judge_v1_results.csv) retain predictions, reasoning, human labels,
notes, status, usage and estimated cost. [The report](../evals/judge_v1_report.md) lists
every disagreement. The manifest and event journal in evals retain reproducibility
metadata. API errors never become Good/Bad predictions and are excluded from metrics.

With Bad positive: TP=10, FP=9, FN=0, TN=1; accuracy 55%, precision 52.63%, recall
100%. Nine disagreements were all human Good / judge Bad. Usage was 33,535 tokens
and estimated USD 0.00618405 at existing monitoring rates. This measures agreement
on a small selected subset, not judge correctness or original-agent answer quality.
The V1 prompt was not refined after results. Its disagreements were reviewed
before preparing the targeted V2 prompt below; the V1 artifacts remain frozen.

### Judge V2 — targeted response-type iteration

[The targeted V2 prompt](../evals/judge_prompts/v2.txt) first assesses response type:
evidence-based investigation, clarification/missing information, security refusal,
general procedural guidance, or out-of-scope response. It then applies evidence
and citation requirements to the claims actually made. Honest missing-asset replies,
pure clarifications and security refusals can be Good without unnecessary retrieval
or citations; unsupported facts or substantive technical procedures within them
still require proper evidence and citations. Diagnostics never automatically fail
an answer. Hallucination, unsafe guidance, injection and unsupported-diagnosis
checks are retained. There are no scenario-specific passing rules.

```sh
.venv/bin/python evals/run_judge.py --version v2 --dry-run
.venv/bin/python -m pytest evals/test_judge_v1.py evals/test_judge_v2.py -q
```

Dry-run verifies exactly the same 20 labeled examples and the same model-input
SHA-256 values used by V1. Human labels, notes, categories and V1 predictions are
excluded from model input. The structured output stays `reasoning`, then `label`.
V1's historical manifest still records the original runner/code hashes; the
versioned runner verifies unchanged V1 data/prompt and per-input hashes without
rewriting that manifest. V1 commands are now verification-only and cannot rerun
or export over the frozen batch.

The user subsequently authorized exactly 20 real evaluations. V2 completed all 20
once with zero execution errors and no automatic retries. Dry-run now reports zero
unstarted cases. Separate [V2 predictions](../evals/judge_v2_results.csv),
[comparison report](../evals/judge_v2_report.md), manifest, event journal and
[comparison JSON](../evals/judge_v2_comparison.json) preserve the outcomes.

V1 → V2: accuracy 55% → 70%, Bad precision 52.63% → 62.5%, recall 100% → 100%.
V2 TP=10, FP=6, FN=0, TN=4. S028, S044 and S048 were corrected, supported by
inspection of the saved answers/traces. No previously correct prediction regressed.
Six disagreements remain: S001, S005, S023, S029, S035 and S049. The report selects
S028 as a course-submission candidate and preserves the remaining policy questions.

V2 used 44,359 tokens at estimated USD 0.00773745. Relevant offline tests: 17 passed.
The V2 prompt, V1 artifacts, human labels, original agent/results and datasets are
unchanged. These are same-subset agreement metrics after targeted review, not
held-out validation or proof of correctness. No further iteration was started.
Questions 2 and 3 have been reviewed and approved; no further judge iteration is included.

### Final judge comparison and corrected example

Bad is the positive class. Both versions completed 20 real evaluations without
execution errors or automatic retries.

| Metric | V1 | V2 |
|---|---:|---:|
| Accuracy | 55% | 70% |
| Precision (Bad) | 52.63% | 62.5% |
| Recall (Bad) | 100% | 100% |
| TP / FP / FN / TN | 10 / 9 / 0 / 1 | 10 / 6 / 0 / 4 |

False positives decreased from **9 to 6**. Corrected disagreements were **S028,
S044 and S048**, with **no prediction regressions** relative to the unchanged human
labels. V2 explicitly assesses whether the response is an investigation,
clarification, security refusal, procedural answer or out-of-scope response before
applying evidence/citation requirements. Unsupported factual claims and technical
procedures retain strict evidence requirements; safe refusals and basic requests
for missing information do not automatically require irrelevant retrieval.

**S028 illustrates a genuine correction:** the LNX-999 lookup returned
`asset_not_found` with no evidence IDs. The saved answer honestly stated that no
synthetic inventory record existed and requested identifying information. Human:
Good; V1: Bad (unnecessary citation demand); V2: Good (recognition that a missing
record cannot supply a citation). The [V2 report](../evals/judge_v2_report.md) preserves
the original question, answer, trace and both judge reasonings.

**V2 metrics are in-sample.** These same 20 human-labeled examples informed the
prompt improvement, so the gains do not establish held-out accuracy or judge
correctness. Six disagreements remain, including legitimate source-relevance and
citation-placement questions. All judgments require interpretation against the
saved evidence; human labels, frozen prompts and predictions were not changed to
force agreement. Question 1 reproduction instructions and original results remain
available above and unchanged.


## Archived PROJECT_CONTEXT.md (verbatim content)

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
