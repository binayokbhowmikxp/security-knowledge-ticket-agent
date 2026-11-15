# PAM Capstone — Synthetic Data Expansion: Source and Review Notes

**Integration status (2026-11-14):** Integrated locally on `feature/streamlit-ui` for review. Initial offline regressions were resolved by excluding new TKT-010/TKT-011/TKT-012; final counts are 25/12/15 and all 164 offline tests pass. The curated data and offline tests have been accepted for Question 1. See [review results](pam_expansion_review_results.md). The preparation notes below describe the supplied archive before integration.

## Scope and integrity

- The three expanded files are **complete replacements** for their respective JSON files, each containing all existing records **byte-for-byte equivalent at the parsed-record level**, followed by additional entries. Existing IDs, field names, types and values are unchanged.
- The new entries are **fictional training records** written in vendor-neutral language. They are not official guidance, real customer inventory, actual support tickets, tested remediation procedures, or copies of product documentation.
- Every item retains `"source_type": "synthetic"`; knowledge articles retain their existing explicit synthetic-training disclaimer.
- No credentials, customer-identifying details, actual endpoint addresses, production commands or instructions to bypass controls are included.
- No new JSON keys were introduced, and the source links are kept **outside** the agent's JSON datasets.

## Public technical references that informed the concepts

1. **Reference A — Privileged account discovery and onboarding:** [Official development guide](https://github.com/cyberark/Idira-Partner-Integration-Docs/blob/main/docs/discovery/privileged-accounts/development-guide.md), especially "Managing Discovered Accounts" and discovery inventory/onboard distinctions. The new data generalizes this into approved-inventory checks, discovered-versus-managed state and account-ownership review. Vendor-specific API routes, role names and product steps are intentionally omitted.
2. **Reference B — Managed credential lifecycle:** [Official credential-rotation development guide](https://github.com/cyberark/Idira-Partner-Integration-Docs/blob/main/docs/credential-rotation/cpm-rest-api/development-guide.md), particularly "Use Cases at a Glance" and workflow stages. The new data generalizes verify/change/recovery separation, operation-stage evidence and target connectivity. Vendor-specific workflow files, endpoints and commands are omitted.
3. **Reference C — Web login automation:** [Official web connection component development guide](https://github.com/cyberark/Idira-Partner-Integration-Docs/blob/main/docs/psm-connectors/web-connection-component/development-guide.md), especially multi-step login flows, validation of successful login, troubleshooting and certificate trust. The new data generalizes login-stage evidence and post-login verification; it does not describe how to access a real system.
4. **Reference D — Connector security and success checks:** [Official web connection component certification checklist](https://github.com/cyberark/Idira-Partner-Integration-Docs/blob/main/docs/psm-connectors/web-connection-component/certification-checklist.md), especially WebForm Robustness and Credential Handling. The new data generalizes the need for trustworthy login confirmation, safe handling of secrets and not disabling certificate validation.

These are **conceptual references**, not claim-by-claim citations for the fabricated case details. The synthetic accounts, error circumstances and ticket outcomes were authored for the capstone and **are not asserted to have occurred at the referenced vendors**. Official references may be implementation- or edition-specific, so the training articles do not treat vendor-specific behaviors as universal PAM requirements.

## New knowledge articles and conceptual source mapping

| Added ID | Topic | Background references |
|---|---|---|
| ONB-006 | Discovered inventory reconciliation and duplicates | A |
| ONB-007 | Windows local/domain onboarding approval and account type | A; existing generic onboarding baseline |
| ONB-008 | Verification separate from management enablement | A, B |
| ROT-006 | Verification, change and recovery as separate stages | B |
| ROT-007 | Post-change verification and uncertain credential state | B; original rotation baseline |
| ROT-008 | Windows policy rejections versus account restrictions | B; original generic policy baseline |
| ROT-009 | Rotation schedules and dependent services | B; original dependency baseline |
| WEB-006 | Multi-step or conditional web login pages | C |
| WEB-007 | Post-login success verification rather than form submission | C, D |
| WEB-008 | HTTPS trust, redirects and page availability | C, D |

### Added asset IDs

`LNX-004`, `LNX-005`, `WIN-002`, `WIN-003`, `APP-004`. These are wholly invented synthetic records; no source document supplied their account identifiers or statuses.

### Added incident IDs

`TKT-010`–`TKT-018`. Three onboarding, three rotation-related, and three web-connector cases. All are invented synthetic historical training cases. A past ticket's observations or outcomes **do not establish** a current incident's root cause.

## Structural checks completed

- Parsed record totals: **25 knowledge** (15 unchanged + 10 new), **12 assets** (7 unchanged + 5 new), **18 tickets** (9 unchanged + 9 new).
- Identical key names, key order and string value types for every record in each file.
- All existing parsed records preserved exactly, in their original order.
- New and existing IDs unique; new IDs match the repository's expected identifier patterns.
- Every ticket's `related_asset` points to an asset present in the expanded asset dataset.
- All new documentation articles use recognized `onboarding`, `password_rotation` or `web_connector` categories and supported platform values.
- New data does not contain vendor product names and contains no API endpoints or privileged-action commands.

## Required repository checks before adoption

**Not yet run:** this standalone preparation environment does not have the repository's `minsearch` dependency or local pytest environment. Adding new documents can change TF-IDF rankings, which could change which five articles or four tickets get retrieved.

After Codex integrates the JSON files into `feature/streamlit-ui`, it should run the full offline regression suite and inspect retrieval relevance for representative queries covering: Linux onboarding, Windows approval, Linux verification mismatch, Windows policy rejection, multi-step web login, unknown asset, and historical tickets. **Do not modify the original agent or adjust tests merely to force a pass**. Pause if an existing asserted retrieval result changes unexpectedly. Do not use paid OpenAI calls for this data-integration step.

## Next capstone milestone

After data integration and regression review, create at least 50 evaluation scenarios in `evals/scenarios.csv`, approve them, then separately authorize a real-model batch run. Keep evaluation questions and model outputs distinguishable from the synthetic source records.
