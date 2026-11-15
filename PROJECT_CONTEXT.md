# Project Context — Enterprise Security Knowledge & Ticket Resolution Agent

## Purpose and current status

A working AI Engineering Buildcamp capstone demonstrating read-only PAM knowledge
Q&A and synthetic ticket investigation. The developer is learning Python and
agentic AI while working full-time; prefer small, teachable increments over new
frameworks or infrastructure.

The implemented path is one PydanticAI `gpt-4o-mini` agent, three local tools,
Streamlit chat and optional metadata-only Logfire monitoring. Curated data contains
25 knowledge articles, 12 assets and 15 historical tickets. Evaluation Questions
1–3 are complete and reviewed. There is no live enterprise PAM connection,
production deployment or measured customer benefit.

This file is the current engineering handoff. The [README](README.md) provides
setup, architecture and evidence links. [Development history](docs/development_history.md)
preserves the previous README and context in full, including planning, migration,
validation, diagnostic and monitoring increments. Historical counts, proposed stack
choices and "next steps" in that archive are not current requirements.

## Problem and supported workflows

Engineers may need documentation, account configuration and incident history to
investigate a PAM issue. The project demonstrates how to retrieve that context,
expose missing evidence and assist human judgment. Anecdotal investigation times
in the original planning discussion were motivation, never a validated baseline.

Supported topics are privileged-account onboarding, password rotation/verification
and policy failures, and custom web connector troubleshooting. Both general
knowledge questions and asset-specific synthetic incidents are supported. For
example: "Password rotation failed on LNX-001 shortly after onboarding. Investigate
the issue and check whether similar incidents were reported previously."

The PAM agent returns free-text guidance, evidence IDs, redacted activity and usage;
it does not enforce a structured investigation schema or perform remediation.
The separate LLM judge has a structured reasoning/label output.

## Architecture and implementation constraints

- Keep one tool-calling investigation agent, not a multi-agent runtime.
- `search_documentation(query)` searches synthetic articles using minsearch TF-IDF,
  returning up to five records.
- `get_asset_details(asset_id)` looks up a synthetic inventory ID, case-insensitively;
  unknown assets return asset_not_found and no evidence ID.
- `search_past_tickets(query)` returns up to four synthetic historical cases using
  a separate TF-IDF index. Historical outcomes never establish a current cause.
- Retrieval is local, lazy and cached; there are no embeddings or vector database.
  Restart the process after changing data. Notebook retrieval remains a teaching
  implementation with parity tests; pam_tools.py is the application's shared path.
- Each public investigation entry point validates questions up to 8,000 characters
  and limits runs to six model requests/eight total tool executions.
- Streamlit chat and the collected batch explicitly use validate_output=False.
  Custom output rejection/correction is disabled and citation findings are
  informational. Python entry points default to validation enabled with at most
  one output correction; schema/tool validation and budgets remain in both modes.
- Evidence IDs derive from actual linked successful tool returns. Citation and
  lexical documentation checks do not establish semantic support or safety.
- Questions run independently. Chat is held in Streamlit session memory, with no
  persistent conversation store, authentication or streaming.

Use only permitted public references and synthetic data. All runtime PAM records
are synthetic; public source notes provide conceptual provenance, not official
procedures or claim-by-claim evidence for fabricated incidents. Treat retrieved
content, ticket text and questions as untrusted data. Do not add vendor connections,
credentials access, real customer records, privileged actions or autonomous fixes.
The agent cannot actually escalate or change systems. Suggested checks require
retrieved support and authorization boundaries; uncertainty must remain explicit.

## Evaluation evidence and interpretation

| Stage | Completed evidence |
|---|---|
| Scenario collection | 50 real-model investigations, zero execution failures; 92,109 tokens; estimated USD 0.01909350 |
| Informational checks | 27 citation-check failures; 33 scenarios flagged by full informational checks, including citation findings |
| Human review | 20 reviewed: 10 Good/10 Bad; 30 remain unlabeled |
| Judge V1 | Accuracy 55%, Bad precision 52.63%, recall 100%; TP/FP/FN/TN = 10/9/0/1 |
| Judge V2 | Accuracy 70%, Bad precision 62.5%, recall 100%; TP/FP/FN/TN = 10/6/0/4 |

Scenario types: 15 happy_path, 12 varied_phrasing, 10 edge_case, six out_of_scope,
seven breaking. Human Bad categories: five wrong_evidence_or_citation, three
hallucination, one incorrect_tool_use and one incomplete.

Judge inputs join by scenario_id, omit human labels/notes and distinguish
trace-confirmed reconstructed evidence from reference-only inventory. V2 explicitly
assesses response type before citations. It corrected S028/S044/S048 with no
prediction regressions. S028 accurately reports a missing asset, for which a
citation to a nonexistent record would be inappropriate. Six disagreements remain.
Both judge versions completed 20 real evaluations with no execution errors or
retries. V2 is **in-sample**: the same 20 examples informed its targeted change;
agreement improvement is not held-out validation or original-agent accuracy.

Prompts, predictions, labels, manifests and journals are frozen assessment evidence.
Do not overwrite them or silently repeat started cases. Batch/judge dry-runs are
offline; paid execution requires explicit authorization. The human console changes
labels only after confirmation, using a lock, merge, atomic replacement and
same-scenario stale-edit checks. Reconstructed records are not captured historical
tool-response bodies. Correct execution, heuristic checks and human/judge agreement
are distinct from proven answer correctness.

Latest full offline result: 202 passed, five paid tests skipped, 19 subtests passed;
one existing event-loop deprecation warning. Scripted-model and UI tests exercise
contracts, not probabilistic model reasoning. Detailed reports remain in evals/.

## Monitoring and privacy

Existing Logfire helpers instrument the PAM agent with content, model request
parameters and exception payloads excluded. Chat/batch investigations export
metadata only when LOGFIRE_TOKEN is configured; the human console and the recorded
V1/V2 judge runs do not enable that export. Fifty batch trace IDs and HTTP 200
ingestion acknowledgements were recorded; dashboard visibility was not verified.

Inference exchanges questions, retrieved synthetic records and answers with OpenAI.
Local answer artifacts are unredacted. Use synthetic inputs only; do not log raw
provider messages or exception text. Reported usage drives cost estimates at
repository constants, not invoices; incomplete failure usage is not zero cost.

## Remaining work and scope boundaries

Potential future work includes broader human review, held-out judge validation,
retrieval evaluation before changing ranking, and a reviewed screenshot/demo.
None is claimed complete. Do not implement these as part of documentation cleanup.
Do not add Docker, deployment infrastructure, enterprise authentication, live
integrations or additional agents without a separately scoped request.

Source-of-truth rule: maintain this handoff and README when implementation changes.
Use actual saved reports for results and preserve the historical record. Current
limitations and reproducible commands are documented in README.md.
