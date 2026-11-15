# Data expansion review — 2026-11-14

Current review status: curated locally on `feature/streamlit-ui`; all 164 existing offline tests pass after excluding three new tickets. The curated data and offline tests were subsequently accepted for Question 1. The initial integration and live-run results below are historical; see the resolution section for the final datasets.

## Integrity and scope

ZIP: `temp/pam_data_expansion_review.zip`, extracted to `temp/pam_expansion_inspected/`. Only the expected three datasets and source document were present. Every original parsed record, field name, field order, value, type, ID and record order is preserved. New records have the same keys and string types, unique IDs and synthetic source type. All ticket asset references resolve. Counts: knowledge 15 → 25; assets 7 → 12; tickets 9 → 18. Original data copies and raw test logs remain under `temp/pam_review/`. The supplied ZIP and temporary files remain untracked. Production Python, notebooks, monitoring, tools, validation and test assertions were unchanged.

## Offline results

Command: `.venv/bin/python -m pytest -q` (no `--live`). Original datasets: **164 passed, 5 skipped, 19 subtests passed**. Expanded datasets: **143 passed, 21 failed, 5 skipped, 19 subtests passed**. Both runs reported one existing event-loop deprecation warning. Original datasets were restored temporarily for the baseline run in a try/finally block; the expanded files are the final working-tree state.

Genuine regression: broad rotation/onboarding ticket queries lose TKT-001 from the top four and can retrieve only onboarding records. Scripted answers then cite an unretrieved ticket, causing citation rejection, script exhaustion or changed validation reason codes. No assertions were edited. These are retrieval regressions plus resulting contract failures, not evidence that production validation changed.

Failing tests:

- `tests/test_agent_notebook.py::AgentTests::test_tools_retrieve_real_records`
- `tests/test_agent_scenarios.py::test_password_rotation_investigation[asset-first]`
- `tests/test_agent_scenarios.py::test_password_rotation_investigation[tickets-first]`
- `tests/test_live_smoke_observer.py::test_live_scenario_b_uses_conservative_documentation_policy[basic-request]`
- `tests/test_live_smoke_observer.py::test_live_scenario_b_uses_conservative_documentation_policy[evidence-review]`
- `tests/test_live_smoke_observer.py::test_live_scenario_b_uses_conservative_documentation_policy[supported-procedure]`
- `tests/test_pam_agent_pydantic.py::test_framework_executes_real_retrieval[rotation-all-tools]`
- `tests/test_pam_agent_pydantic.py::test_framework_executes_real_retrieval[rotation-tickets-first]`
- `tests/test_pam_agent_pydantic.py::test_evidence_multiple_sources_and_repeated_calls[asset-first]`
- `tests/test_pam_agent_pydantic.py::test_evidence_multiple_sources_and_repeated_calls[tickets-first]`
- `tests/test_pydantic_correction.py::test_missing_citations_corrected_using_actual_multiple_sources`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_accepts_evidence_or_bounded_documentation_correction[valid-citations]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_accepts_evidence_or_bounded_documentation_correction[basic-evidence]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_accepts_evidence_or_bounded_documentation_correction[remove-procedure]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_accepts_evidence_or_bounded_documentation_correction[retrieve-docs]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes[Synthetic training guidance; not official vendor documentation. PRIVATE_REASON_MARKER no citations.-missing_citation]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes[draft1-unretrieved_citation]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes[draft2-invalid_citation_format]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes[draft3-missing_disclaimer]`
- `tests/test_pydantic_reliability_scenarios.py::test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes[draft4-unsupported_documentation_guidance]`
- `tests/test_pydantic_reliability_scenarios.py::test_reason_history_is_per_run_and_terminal_codes_are_not_invented`

## Representative retrieval rankings

Each sequence is in ranked order; full queries and all ticket rankings are in `pam_expansion_live_results.json`. All six query pairs changed.

| Query topic | Original documentation top five | Expanded documentation top five |
|---|---|---|
| linux_onboarding | ONB-001, ONB-004, ROT-001, ONB-003, ROT-002 | ONB-001, ONB-004, ONB-007, ROT-001, ONB-006 |
| windows_onboarding | ONB-004, ONB-003, ONB-002, ONB-001, ONB-005 | ONB-007, ROT-008, ONB-004, ONB-003, ONB-001 |
| password_rotation | ONB-004, ROT-001, ROT-002, ROT-004, ONB-001 | ROT-007, ONB-004, ROT-001, ROT-002, ROT-004 |
| windows_rotation | ROT-003, ROT-001, ONB-004, ROT-002, ROT-005 | ROT-008, ONB-007, ROT-003, ONB-004, ROT-001 |
| web_connectors | WEB-001, WEB-003, WEB-005, WEB-004, WEB-002 | WEB-006, WEB-001, WEB-003, WEB-005, WEB-004 |
| historical_tickets | ONB-004, ONB-003, ONB-002, ONB-005, ONB-001 | ONB-004, ONB-008, ONB-003, ONB-002, ONB-006 |

Windows onboarding now places ONB-007 first; verification mismatch places ROT-007 first; multi-step login places WEB-006 first. Linux onboarding retains ONB-001 first but admits Windows ONB-007 at rank three, showing lexical cross-platform noise. Historical query `LNX-001 password rotation failed shortly after onboarding` moves TKT-001 from rank two to one but loses TKT-003 from the top four. The test query `Linux password rotation onboarding` instead loses TKT-001 entirely. Better topical ranking on some queries does not offset the broad-query regression.

## Real API investigations

The initial three attempts inside the sandbox failed DNS resolution before model responses or tools; no token usage or cost was available, not asserted as zero. The approval mechanism permitted a separate network-enabled run after explaining the retry. No SDK transport retries were enabled (`max_retries=0`, timeout 60 seconds); each network-enabled investigation was called once. Real OpenAIChatModel gpt-4o-mini was supplied to the existing PydanticAI agent via a harness-only override, with `investigate_with_evidence(question, validate_output=False)`. No FunctionModel or mocks were used. Production budgets remained unchanged.

Actual full answers, exact questions, executed tool arguments, evidence IDs, citation issues, all informational validation findings, tokens, costs and trace IDs are preserved in [the live results](pam_expansion_live_results.json). Output validation findings did not trigger correction.

| Investigation | Executed tools | Input / output tokens | Estimated USD |
|---|---|---|---|
| linux_onboarding | search_documentation | 2013 / 212 | $0.00042915 |
| password_rotation | get_asset_details, search_past_tickets | 1981 / 396 | $0.00053475 |
| web_connector | search_documentation | 1968 / 286 | $0.00046680 |

Total: 5,962 input + 894 output = 6,856 tokens; six model requests and four tool calls. Estimated **$0.00143070**, using the existing monitoring constants ($0.15 input / $0.60 output per million), excluding cache discounts and billing adjustments; this is not an invoice or a newly verified price.

- Linux onboarding: citation and full informational checks passed; used new ONB-006 in its answer. Documentation-only tool selection suits a general knowledge question.
- Rotation: citation checks failed because the answer used bare IDs rather than bracketed citations. No documentation search occurred. It speculates about dependency/configuration causes from asset/ticket evidence; historical evidence does not prove those causes. The answer acknowledges the current incident is undiagnosed, but does not explicitly state historical outcomes cannot diagnose it. The lexical guard did not flag these gaps.
- Web connector: citation membership passed, but the full informational guard returned two unsupported-documentation findings (web connector and configuration). Multi-step guidance cites new WEB-006. No APP-001 inventory lookup occurred; it provided generic checks rather than verified inventory facts. Its final configuration check has no nearby source. These are review findings, not rejected outputs.

Tool selection effects cannot be attributed causally to data expansion: no paid original-data comparison was authorized/run. Replaying the actual live search queries offline against old/new indexes shows retrieval changes directly. New records reached all three runs; the rotation model retrieved TKT-013 and TKT-015 but did not use them in its answer. The JSON report records every old/new ranking.

## Monitoring and limitations

Existing Logfire instrumentation and root spans were preserved through the existing helpers. Network-enabled export returned eight HTTP 200 trace ingestion acknowledgements; dashboard visibility was not checked. Initial sandbox trace IDs represent failed local attempts and cannot be assumed exported. No raw provider history or credentials were persisted.

- linux_onboarding: `01a1dc1c9c68767c267664d0da2a5eeb`
- password_rotation: `01a1dc1cb5619679b4da69e96d1a9fd3`
- web_connector: `01a1dc1cd7b70e6f5e89f8b9b4147379`

This is three probabilistic observations, not a full evaluation or claim-level grounding proof. No behavior/test fixes were attempted. Review the retrieval regressions and live answer defects before accepting the expansion. No further paid calls, commits or pushes were made.

## Offline retrieval resolution — final local state

No further OpenAI requests were made. The previous live report remains unchanged and describes the original 18-ticket expansion, not a live retest of this 15-ticket revision.

### Root causes and exact failure groups

The 21 exact failing node IDs are listed in the initial Offline results section above. They share one upstream cause: new onboarding tickets change ticket TF-IDF statistics and compete for the four available result slots. Minsearch sums cosine similarities independently across indexed fields, without platform/category intent filtering. The `onboarding` category and repeated onboarding language in findings/outcomes can outweigh rotation intent in mixed queries. TKT-001 falls to rank seven in all three affected query variants. Its original record was neither changed nor deleted.

| Failure group | Exact tests (parameters as listed above) | Count | Immediate effect |
|---|---|---:|---|
| Direct notebook retrieval | `AgentTests::test_tools_retrieve_real_records` | 1 | Explicit TKT-001 membership assertion fails. |
| Notebook scripted rotation | `test_password_rotation_investigation`, both orders | 2 | Unretrieved TKT-001 citation triggers a revision; scripted responses exhaust with StopIteration. |
| Framework evidence contracts | `test_framework_executes_real_retrieval`, two rotation cases; `test_evidence_multiple_sources_and_repeated_calls`, both orders | 4 | Expected TKT-001 evidence is absent or the scripted answer fails citation checks. |
| Correction success contracts | `test_missing_citations_corrected_using_actual_multiple_sources`; `test_scenario_b_accepts_evidence_or_bounded_documentation_correction`, all four cases | 5 | Corrected or nominally valid scripted drafts still cite unretrieved TKT-001; expected successful correction cannot complete. |
| Smoke-observer policy contracts | `test_live_scenario_b_uses_conservative_documentation_policy`, basic-request, evidence-review, supported-procedure | 3 | Only onboarding tickets returned; expected rotation evidence and valid citations are absent. |
| Diagnostic reason contracts | `test_scenario_b_failed_correction_reports_fixed_initial_and_terminal_codes`, all five cases; `test_reason_history_is_per_run_and_terminal_codes_are_not_invented` | 6 | Missing/unretrieved citation reasons contaminate the intended isolated validation reasons. |

All 21 are consequences of historical-ticket retrieval. Knowledge articles have an independent index, and assets use direct ID lookup; neither can change ticket scores. Leaving all 25 articles and all 12 assets unchanged while restoring all tests with ticket-only exclusions confirms that neither requires modification to resolve these failures.

### Dataset decision

Excluded only TKT-010, TKT-011 and TKT-012. No retained record was rewritten, and no keywords were added. All original records, fields, values, types, IDs and order remain exactly preserved at the parsed-record level against Git HEAD. Retained records preserve the existing schema, string types, unique IDs and synthetic provenance; ID gaps deliberately record exclusions rather than renumbering history.

- TKT-010 adds a discovery/duplicate onboarding example overlapping original TKT-005; its distinct discovery concept remains in ONB-006 and LNX-004.
- TKT-011 adds a Windows authorization onboarding example overlapping the ownership/approval theme in TKT-004; its Windows-specific knowledge remains in ONB-007 and WIN-002.
- TKT-012 adds an initial-verification/management-state example; its concept remains in ONB-008 and WIN-003. Its outcome also discusses a present rotation failure in an onboarding case, broadening lexical overlap.

These are valid synthetic topics, not false records. Exclusion is a deliberate coverage tradeoff for this small, fixed-limit retriever, rather than cosmetic wording changes that conceal its ranking limits. The original supplied archive still contains all three for later evaluation/reintroduction. TKT-013 through TKT-018 remain unchanged, preserving the six new rotation and web examples.

Offline exclusion analysis evaluated every one-, two- and three-record subset of the nine new tickets against all three affected query variants. No one- or two-record exclusion restored TKT-001 to the top four for all variants. The only successful three-record subset was TKT-010/TKT-011/TKT-012. This establishes minimality among exclusions of up to three new records for these queries, not optimality across every possible question.

Final counts: **25 knowledge articles, 12 assets, 15 historical tickets** (all original 15/7/9 records plus 10/5/6 additions). All ticket related_asset IDs resolve in the inventory.

### Original / full expansion / curated rankings

Full documentation and historical-ticket comparisons for six representative topics, four regression-query variants and three coverage probes are in [the offline resolution artifact](pam_expansion_retrieval_resolution.json). Sequences below are ticket ranks, with the unchanged top-four limit.

| Query | Original | Full expansion | Curated final |
|---|---|---|---|
| Linux password rotation onboarding | TKT-004, TKT-005, TKT-003, TKT-001 | TKT-004, TKT-010, TKT-012, TKT-011 | TKT-004, TKT-005, TKT-003, TKT-001 |
| Linux password rotation failed onboarding | TKT-004, TKT-005, TKT-003, TKT-001 | TKT-004, TKT-010, TKT-012, TKT-011 | TKT-004, TKT-005, TKT-003, TKT-001 |
| Linux rotation failed onboarding | TKT-004, TKT-005, TKT-003, TKT-001 | TKT-004, TKT-010, TKT-011, TKT-012 | TKT-004, TKT-005, TKT-003, TKT-001 |
| Linux privileged account onboarding | TKT-004, TKT-005, TKT-001, TKT-002 | TKT-004, TKT-010, TKT-005, TKT-011 | TKT-004, TKT-005, TKT-001, TKT-002 |
| Windows local domain onboarding approval | TKT-004, TKT-005, TKT-001 | TKT-004, TKT-011, TKT-010, TKT-005 | TKT-004, TKT-005, TKT-014, TKT-001 |
| Linux password rotation failed verification mismatch | TKT-003, TKT-001, TKT-009, TKT-002 | TKT-013, TKT-003, TKT-001, TKT-012 | TKT-013, TKT-003, TKT-001, TKT-015 |
| Windows password rotation policy rejection | TKT-009, TKT-003, TKT-002, TKT-001 | TKT-009, TKT-014, TKT-003, TKT-015 | TKT-009, TKT-014, TKT-003, TKT-015 |
| custom web connector login element multi-step | TKT-006, TKT-007, TKT-008 | TKT-006, TKT-018, TKT-017, TKT-016 | TKT-006, TKT-018, TKT-017, TKT-016 |
| LNX-001 password rotation failed shortly after onboarding | TKT-004, TKT-001, TKT-005, TKT-003 | TKT-001, TKT-004, TKT-005, TKT-010 | TKT-004, TKT-001, TKT-005, TKT-003 |

Knowledge rankings are identical between the full expansion and this revision because the article corpus was not edited. Improvements such as ONB-007 for Windows onboarding, ROT-007 for verification mismatch and WEB-006 for multi-step login remain. Original-to-expanded article rankings and cross-platform noise are still visible in the artifact.

### Final verification and remaining limitations

`.venv/bin/python -m pytest -q`: **164 passed, 5 skipped, 19 subtests passed**, one existing event-loop deprecation warning, 3.10 seconds. Raw output: `temp/pam_review/offline_tests_after_fix.txt`. No tests, assertions, production Python, notebooks, search limits or validation rules were edited. Integrity checks compared originals against Git HEAD, checked matching keys/types and unique IDs, and confirmed inventory references. `git diff --check` passed.

Passing contracts do not establish ranking quality for arbitrary queries or real-model answer quality. Mixed onboarding/rotation queries still rank onboarding tickets highly. Excluding the three records reduces historical onboarding breadth; knowledge articles preserve the concepts but are not replacement historical evidence. Retained TKT-015 describes authorization before rotation, so broad rotation searches may still return a pre-operation case. Cross-platform retrieval remains lexical. The three prior real answers' citation/grounding defects are not fixed or retested by this data-only revision. No further API calls, commits or pushes. Stop for ChatGPT review.
