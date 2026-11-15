# Retrieval benchmark — draft relevance judgments

## Objective and scope

Compare unchanged production minsearch TF-IDF with a deterministic keyword-overlap baseline on the frozen synthetic collections. This is an offline retrieval experiment only: no OpenAI calls, agent runs, judge calls, retrieval changes or new dependencies.

Baseline repository commit: `18a8c9ff1dbeec50ef6eb6a65685d4ef2f9eb140` on `feature/streamlit-ui`. Corpus: 25 articles and 15 historical tickets. Inventory lookup is not benchmarked.

## Benchmark construction and draft relevance

Exactly **20 handcrafted queries: 10 documentation and 10 historical-ticket queries**. R01–R10 target documentation; R11–R20 target tickets. Questions cover Linux/Windows onboarding, initial versus post-change verification, authentication/permissions, minimum-age policy, connectivity/timeouts, conditional web screens, HTTPS trust and historical incident comparisons. Every curated ticket appears in at least one relevant set.

**These are handcrafted draft relevance judgments, not independently verified ground truth.** Queries and relevant IDs were written from the actual curated record content before either retrieval method was run for this benchmark. Existing tests/review artifacts were inspected for known limitations, so this is not a blinded or independently authored evaluation. The judgments were fingerprinted before ranking and were not revised after seeing scores. The coding assistant authored these draft queries/judgments from the record text; they have not been independently reviewed by a human relevance assessor. No external model or LLM judge calls were used.

Relevance is binary: a record must directly address a requested task/symptom/facet with compatible platform context, or provide explicitly applicable general guidance. Mere keyword overlap or an unrelated historical failure is insufficient. Multiple records are included when they address separate requested facets. Broad triage coverage versus topic-specific detail is subjective: the CSV gives a reason and selected exclusions for each query. All relevant IDs are existing curated sources; queries contain no source/asset IDs. IDs in relevant_ids are separated by semicolons.

Examples of judgment ambiguity:

- R01 includes general discovery/inventory reconciliation ONB-006 for identity matching, even though the query does not explicitly mention discovery. Another reviewer may judge that too broad.
- R03 spans initial verification, management enablement and the first failed change; four articles are judged relevant, including general operation-stage guidance.
- R07 treats general onboarding connectivity ONB-002 as applicable to rotation timeouts while excluding generic rotation triage that merely mentions connectivity. R05 accepts generic Linux triage for account-state/permissions coverage. Granularity decisions merit independent review.
- R08 asks about the approved login sequence; WEB-002 and WEB-006 are relevant, whereas a generic element/page-change article is not sufficient for that request under these judgments.
- R10 intentionally leaves login versus password-change completion ambiguous; WEB-005/006/007 cover different interpretations.
- R12 spans duplicate Windows inventory and a preparatory authorization gap: TKT-015 is relevant even though its category is password_rotation and no rotation actually ran. R19/R20 deliberately request multiple alternative historical findings.

Question/judgment file SHA-256 before rankings and after verification: `1b6040d51ec54c990d7356591c3670140e5a39ca17915671773e3e5a46fac012`. The reproducible JSON records hashes for questions, both corpora, production tools, benchmark code and uv.lock.

## Methods

| Collection | Identical searchable fields in both methods | K |
|---|---|---:|
| Documentation | title, content, category, platform | 5 |
| Historical tickets | issue_summary, category, related_asset, investigation_findings, documented_outcome | 4 |

**A — Production TF-IDF:** calls pam_tools.search_documentation and pam_tools.search_past_tickets unchanged. The installed minsearch builds a separate scikit-learn TfidfVectorizer per text field, using default TF-IDF weighting and L2 normalization. It sums field-level cosine similarities, with default field boosts of 1, no query-time filters and no platform routing. It sorts descending scores and omits zero-score records. Production uses NumPy argsort; exact score ties should not be treated as a portable relevance preference across runtime versions.

**B — Keyword baseline:** union the unique tokens from exactly the same text fields, then rank by the count of unique query tokens in that union. Lowercase Unicode word tokens of at least two characters use the same token rule as the production vectorizers. Neither method removes stop words or stems words. The baseline does not weight rare terms, repeated occurrences, fields or document length. It breaks ties by original JSON record order and omits zero-overlap records. IDs/source_type are not additional searchable fields. No relevance judgments enter either ranker.

Both methods use the same fixed maximum K; when fewer positive matches exist they return fewer, rather than padding irrelevant zero-score records. For all 20 measured queries they return the full K. Tests also verify zero-overlap behavior and stable ties. The comparison changes scoring, not source fields or query preprocessing.

## Metrics and results

For each query: Hit@1 = 1 if the first record is relevant; Hit@K = 1 if any top-K record is relevant; Recall@K = number of relevant top-K records / total judged relevant records; reciprocal rank@K = 1 / rank of the first relevant hit, or 0 if none. MRR@K averages reciprocal ranks. Results are unweighted macro-averages across queries, not document-weighted recall. Overall mixes documentation K=5 and ticket K=4; no shared-K claim is made.

| Collection | Method | Queries | Hit@1 | Hit@K | Recall@K | MRR@K |
|---|---|---:|---:|---:|---:|---:|
| documentation | tfidf | 10 | 90.00% | 100.00% | 74.17% | 0.9500 |
| documentation | keyword | 10 | 100.00% | 100.00% | 90.00% | 1.0000 |
| tickets | tfidf | 10 | 90.00% | 100.00% | 100.00% | 0.9333 |
| tickets | keyword | 10 | 90.00% | 100.00% | 100.00% | 0.9500 |
| overall | tfidf | 20 | 90.00% | 100.00% | 87.08% | 0.9417 |
| overall | keyword | 20 | 95.00% | 100.00% | 95.00% | 0.9750 |

**Measured winner: keyword overlap overall.** It improves Hit@1 by 5 percentage points, Recall@K by approximately 7.92 points and MRR@K by 0.0333; Hit@K ties. Keyword is better on documentation Hit@1, Recall@K and MRR@K. Ticket Hit@1 and Recall@K tie, with keyword slightly ahead on ticket MRR. TF-IDF has a per-query advantage on one query, keyword on six, with 13 metric ties. No measured metric establishes TF-IDF as the overall winner.

## Representative successes and failures

The table shows ordered returned IDs. Complete rankings and all four individual scores for every query are saved in the CSV/JSON artifacts linked below.

| Query | Relevant | TF-IDF top-K | Keyword top-K | Finding |
|---|---|---|---|---|
| R01 — Linux privileged account identity checks: hostname, account name, purpose and local versus centrally managed account. | ONB-001, ONB-006 | ONB-001, ROT-001, ROT-002, ROT-004, ONB-004 | ONB-001, ROT-001, ONB-007, ROT-008, ROT-002 | Both have a relevant first hit but miss ONB-006: Recall only 0.5 for both. Platform-specific distractors remain in results. |
| R02 — Windows local versus domain account onboarding: who approves the permission scope and management configuration? | ONB-003, ONB-007 | ONB-007, ROT-008, ONB-004, ONB-008, ONB-001 | ONB-007, ROT-008, ONB-001, ONB-004, ONB-005 | Both find Windows onboarding ONB-007 first but miss general owner/permission guidance ONB-003: Recall only 0.5 for both. |
| R04 — A Linux credential update was attempted, then verification reported a mismatch. Can we know which password is valid? | ROT-006, ROT-007 | ROT-007, ONB-004, ROT-002, ROT-001, ROT-004 | ROT-007, ROT-006, ONB-001, ONB-004, ONB-005 | Both rank post-change mismatch ROT-007 first; only keyword also retrieves the relevant operation-stage article ROT-006 (Recall 1 vs 0.5). |
| R07 — Linux password rotation times out. Which DNS, firewall, port and target-availability evidence should we examine? | ONB-002, ROT-004 | ROT-004, ONB-004, ROT-001, ROT-002, ONB-001 | ROT-004, ONB-002, ONB-004, ROT-001, WEB-008 | Both find Linux timeout guidance first; keyword also retrieves applicable general connectivity checks ONB-002 (Recall 1 vs 0.5). |
| R08 — How should we check the approved sequence when a custom web connector reaches a second login page before showing the password field? | WEB-002, WEB-006 | WEB-001, WEB-002, WEB-008, WEB-006, WEB-007 | WEB-006, WEB-002, WEB-008, WEB-001, WEB-007 | Keyword ranks sequence-specific WEB-006 first. TF-IDF ranks generic page-change WEB-001 first, with the first judged relevant source second (MRR 1 vs 0.5). |
| R13 — Find previous Linux password rotation failures soon after onboarding where the selected local-account configuration did not match the approved record. | TKT-001 | TKT-004, TKT-005, TKT-001, TKT-013 | TKT-001, TKT-013, TKT-002, TKT-004 | Keyword ranks the configuration-mismatch incident first; TF-IDF ranks it third after two onboarding cases (MRR 1 vs 0.3333). This is consistent with strong field-level onboarding/category overlap. |
| R15 — Show previous Linux rotation incidents where authentication failed because the account was restricted. | TKT-002 | TKT-002, TKT-015, TKT-003, TKT-001 | TKT-015, TKT-002, TKT-001, TKT-004 | Only strict TF-IDF advantage: restricted Linux authentication case ranks first versus second (MRR 1 vs 0.5). Keyword puts a Windows preparatory authorization case first, although no rotation ran there. |

Neither method has a complete top-K miss on this set. The shared poor cases are incomplete recall (R01/R02), not failed Hit@K. Reporting 100% Hit@K alone would conceal those missing complementary sources. TF-IDF additionally misses useful secondary sources on R03/R04/R07/R10. Keyword can favor word-rich unrelated records, as R15 demonstrates; count overlap ignores intent, platform and whether a workflow actually ran.

## Limitations and recommendation

- Small purposive sample: only 10 queries per collection, with draft ungraded relevance and source-informed wording. There is no independent adjudication, held-out set, real enterprise incident sample or statistical-significance test.
- Platform applicability, generic-versus-specific guidance and alternative interpretations affect the relevant sets. The result is conditional on these recorded judgments. No labels were tuned after scoring; another review should create a separately versioned set instead of overwriting this record.
- K covers 20% of the article corpus and roughly 27% of the ticket corpus; every relevant set fits within K. This and topic-aligned wording make Hit@K saturation unsurprising. There are no unanswerable/zero-relevance queries in the scored set; no claims about abstention follow.
- TF-IDF sums independently normalized fields, so a short category/platform match can weigh heavily relative to detailed content. Adding/removing records changes IDF and ranking. Earlier expansion regressions are documented separately; this run does not re-test every possible corpus variant.
- The baseline retains common words and favors records with many distinct overlaps; ties inherit corpus order. Baseline success here is not semantic understanding. Production tie ordering is runtime-dependent; recorded dependency versions and hashes bound reproducibility.
- These are retrieval metrics only, not answer grounding, tool selection, security compliance, latency, cost, or end-to-end agent quality. No performance timing benchmark or LLM experiment was run.

**Recommendation:** retain the existing production TF-IDF implementation unchanged for this assessment as an interim engineering decision, not because it won the comparison. The small draft benchmark favors keyword overlap and does not substantiate a claim that TF-IDF is superior. Independently review relevance and broaden the query set before deciding on a production switch; keyword overlap is a credible candidate for that later comparison. No retrieval change is made in this step.

Suggested capstone README wording: “An offline 20-query draft benchmark compared production TF-IDF with unique keyword overlap. Both achieved 100% Hit@K; keyword overlap scored higher overall on Hit@1 (95% vs 90%), Recall@K (95% vs 87.08%) and MRR@K (0.9750 vs 0.9417). Results are conditional on handcrafted relevance judgments and do not establish general superiority; production retrieval remains unchanged.”

## Reproduce and inspect

```sh
uv run python evals/retrieval_benchmark.py
uv run pytest evals/test_retrieval_benchmark.py -q
uv run pytest -q
```

Only new benchmark result files are written. The runner never edits the draft judgments or prior agent/judge artifacts. It imports the local retrieval module, not an agent or provider client, and requires no .env or API key. Repeat runs are deterministic under the recorded inputs/runtime; JSON has no varying timestamp.

- [Handcrafted questions and relevance reasons](../evals/retrieval_questions.csv)
- [Benchmark runner](../evals/retrieval_benchmark.py)
- [Per-query CSV](../evals/retrieval_benchmark_results.csv)
- [JSON rankings, individual scores, macro-summary and fingerprints](../evals/retrieval_benchmark_results.json)
- [Focused tests](../evals/test_retrieval_benchmark.py)
- [Prior ranking/curation review](pam_expansion_review_results.md)
- [Existing saved ranking comparisons](pam_expansion_retrieval_resolution.json)

Runtime: Python 3.13.15; minsearch 0.2.0, numpy 2.5.3, scikit-learn 1.9.1.

Verification: 17 focused benchmark tests passed. The full offline suite also passed: **219 passed, 5 skipped, 19 subtests passed**, with one existing event-loop deprecation warning. No existing assertion was changed to force a pass.
