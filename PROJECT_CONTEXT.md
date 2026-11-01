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
LLM tool selection or grounding. No live PydanticAI calls have been made. Citation
validation/revision and the redacted trace interface have not yet migrated; these
are the next recommended increment before broader evaluation. No judge, Logfire,
or other monitoring has been added.
