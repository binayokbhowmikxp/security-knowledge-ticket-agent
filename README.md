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

The repository contains setup and Week 1 RAG notebooks, plus a Week 2 agent notebook using the OpenAI Responses API. One agent dynamically selects among three read-only tools over 15 synthetic knowledge articles, 7 synthetic assets, and 9 historical tickets. The agent notebook includes concise traces and three live smoke scenarios; offline regression tests cover validation, missing evidence, conversation handling, and loop limits. Full labelled evaluation remains planned.

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
