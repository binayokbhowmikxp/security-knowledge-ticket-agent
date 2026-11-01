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
proof of a current cause. The notebook's citation validator/revision and redacted
trace interface have not yet migrated; prompt instructions alone do not enforce
citation correctness or claim-level grounding.

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
human review of messages and evidence. No real PydanticAI model calls have been
made. Avoid printing raw messages in routine logs. Next, migrate citation checks
and safe tracing, then consolidate notebook retrieval in a separately verified
increment. No judge or monitoring is implemented.
