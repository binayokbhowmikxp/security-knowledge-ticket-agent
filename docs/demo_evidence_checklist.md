# Demo evidence checklist — reviewed supplied captures

**Step 3B status: seven supplied PNGs inspected and copied without alteration.**
Review date: 2026-11-16. Originals were found directly in the existing, gitignored
root temp/ directory; no additional temporary directory was created. The copies
are in docs/screenshots/. This task performed no app launch, model/judge execution,
screenshot generation or new Logfire trace creation. See the
[updated walkthrough](demo_walkthrough.md) and [README gallery](../README.md#demo-screenshots).

## Two distinct investigations — never combine their evidence

| Identity | Historical S009 / WIN-003 | Separate captured LNX-001 Streamlit run |
|---|---|---|
| Source | Existing terminal result in the 50-case evaluation journal | Seven user-supplied screenshots of a real completed chat and matching trace |
| Tools executed | search_documentation, get_asset_details, search_past_tickets | get_asset_details, search_past_tickets |
| Documentation search | Called | Not called |
| Model requests / tools | 4 / 3 | 2 / 2 |
| Input / output / total tokens | 5,383 / 421 / 5,804 | 1,860 / 454 / 2,314 |
| Estimated cost | $0.00106005 | $0.00055140 |
| UI/saved trace ID | `01a1dc9d50b3fbcafdafa593a3450593` | `01a1e18cc5002c02491bcee2c117955d` |
| Citation limitations | Known wrong `[LNX-001]` citation beside WIN-003 claim; missing valid citations | Informational checks reported opening-disclaimer and missing bracketed asset/ticket citation issues |
| Dashboard evidence | Saved trace ID, no S009 dashboard screenshot supplied | Matching cropped Logfire view supplied and inspected |

Both used gpt-4o-mini and validate_output=False. S009 is not the new photographed
execution. The LNX-001 run is not appended to the frozen results.jsonl/results.csv
or counted as another case in the 50-case evaluation or the 20 human labels.

The captured question is:

> Password rotation failed for a privileged account on LNX-001 shortly after onboarding. Investigate the issue and check whether similar incidents were reported previously.

Captured retrieved IDs: **LNX-001, TKT-001, TKT-003, TKT-004, TKT-015**.
These demonstrate successful asset and ticket retrieval, not that every ticket
is relevant or that recommendations are supported by documentation. No article
IDs were retrieved in this run. Historical outcomes do not establish its root cause.

## Reviewed capture ledger

All seven below are **captured (supplied), visually reviewed, valid PNG, copied
byte-for-byte**. Links open the unmodified copies; inline README images feature
01, 04, 06 and 07, with the others linked as supplementary evidence.

| File | Dimensions | What is actually visible / assessment evidence |
|---|---|---|
| [01_streamlit_app_question.png](screenshots/01_streamlit_app_question.png) | 2048 × 1249 | Real question and start of generated LNX-001 answer; model, synthetic/read-only scope, independent questions and experimental unverified-output banner. This is the chat app, not the human evaluation console. |
| [02_asset_findings_possible_causes.png](screenshots/02_asset_findings_possible_causes.png) | 2048 × 1024 | Synthetic current-asset findings, pending error/policy evidence and possible-cause language. These claims are shown as generated, not independently validated inventory analysis. |
| [03_historical_tickets_recommendations.png](screenshots/03_historical_tickets_recommendations.png) | 2048 × 881 | Historical ticket discussion and recommendations. The current cause remains unestablished; the statement that no prior incidents specifically aligned sits alongside discussion of TKT-001 and is preserved for review. |
| [04_agent_activity_citation_warning.png](screenshots/04_agent_activity_citation_warning.png) | 2048 × 1096 | Completed get_asset_details and search_past_tickets calls with returned IDs; visible citation warning explicitly says output validation is not enforced. |
| [05_evidence_ids_citation_diagnostics.png](screenshots/05_evidence_ids_citation_diagnostics.png) | 2048 × 1241 | All five retrieved IDs and informational diagnostics: opening-disclaimer requirement, no bracketed citations, missing valid current-asset and historical-ticket citations. Diagnostics are not a human label. |
| [06_usage_cost_trace_id.png](screenshots/06_usage_cost_trace_id.png) | 2048 × 1241 | 2 requests, 2 tools, 1,860 input/454 output/2,314 total tokens, $0.00055140 estimate and full UI trace ID. Shows per-investigation data rather than only sidebar session totals. |
| [07_logfire_trace_redacted.png](screenshots/07_logfire_trace_redacted.png) | 1919 × 897 | Supplied account/organization crop: root PAM investigation, pam-agent service, model/tool operation facets, matching token/cost/request/tool attributes and trace suffix 17955d. Root/operation view is visible; the full parent/child tree is not expanded. |

The Logfire view's model/tool operation counts and 1,860/454/2,314 usage agree
with the chat capture. Its shortened trace ID ends in `17955d`, matching the
full UI ID. This corroborates the user's matching-run provenance; no backend
request, provider replay or further trace was created to verify it. Dashboard
displays a Nov 15 time, but an exact capture timestamp/timezone has not been
independently established. Review date is separate from execution/capture time.

## Privacy and authenticity review

- Each image was opened and visually inspected at its native size for readable
  text, keys/tokens, email/avatar, account/organization names, private URLs and
  unrelated customer data. No such sensitive information was identified. Visible
  account identifiers are fictional synthetic records; localhost is a local URL.
- The Logfire image arrived already cropped; no account email, organization
  identifier, API key or authentication token is visible. Operational labels such
  as pam-agent and the trace ID are retained for verification. The scrubbed session
  value is visible as scrubbed, not exposed. No additional cropping, redrawing,
  generated content, image enhancement or redaction was applied.
- PNG signature, Pillow verification and full pixel decoding passed for all seven.
  The six Streamlit files have no exposed metadata entries; the Logfire PNG has
  only an ICC color profile. No account/credential text was identified in metadata.
- SHA-256 comparisons confirm every documentation copy equals its source; original
  temp/ bytes are unchanged. The source hashes below allow later copy verification.
- Provenance is the user's supplied, ChatGPT-reviewed real execution captures,
  corroborated by consistent visible model/tool usage and trace identifiers. Byte
  equality/PNG checks establish copy integrity, not independent forensic proof of
  screen origin. No fake screenshots or newly rendered replacements were created.
- Captures are scroll views/crops. They do not constitute a full machine-readable
  response export or independently validated technical answer. Existing warnings,
  potentially unsupported interpretations and ambiguous statements have not been hidden
  or corrected to make performance look better.

| Source filename (directly under temp/) | SHA-256 (identical documentation copy) |
|---|---|
| 01_streamlit_app_question.png | `efc1d1adec72d9aa125afe363893f5412fa069884e3aba2800ac553ff3cfc9f6` |
| 02_asset_findings_possible_causes.png | `e9c65d1ba0031a86ab90eb826c1d8da8686e2a83f38f3a9d66beac0ee25d2051` |
| 03_historical_tickets_recommendations.png | `8e7c6290b1a8f23e13d5f983037949467a58e0c7306dfa3ac7ce7b63243ff713` |
| 04_agent_activity_citation_warning.png | `c2d4e1bf8d7b803120698354ecca13a2d2fb11cfb8b435f76dcfb8d44e519b7f` |
| 05_evidence_ids_citation_diagnostics.png | `99393647f9d3606c37fec86ff97c2781a4325253cdced3d9311985f9531e4b9a` |
| 06_usage_cost_trace_id.png | `d31d368bc46f0b64fa2e8102b337bea3a1b40df7eb50a64683f296ab37ce39da` |
| 07_logfire_trace_redacted.png | `54449e85c4eae130fb8ce8e2ad35612ec7c8ad17861fd394ce56c4393e52a0a2` |

## Assessment coverage and remaining gaps

| Evidence item | Current status | What not to imply |
|---|---|---|
| Streamlit interface and a completed real chat | Captured: 01–03 | Not a fresh request happening now; no guarantee a future run has the same answer |
| Two-tool execution and returned IDs | Captured: 04–05 | Not three-tool execution or documentation-backed troubleshooting in this run |
| Citation issues and validation mode | Captured: 01/04/05/06 | Not enforced output rejection or a grounded-answer pass |
| Usage, estimate and trace correlation | Captured: 06–07 | Not an invoice, performance benchmark or permanent dashboard access |
| Root/agent/model/tool activity | Root detail and grouped operations captured in 07 | Not a fully expanded parent/child span-tree screenshot |
| Full corresponding source-record contents | Existing frozen JSON, not shown in these seven pictures | Evidence-ID list is not the full record body; any console reconstruction must be labeled as such |
| S009 three-tool result and incorrect citation | Existing saved evaluation artifacts only | No S009 screenshot was supplied; do not label LNX-001 images S009 |
| README architecture, human labels, judge comparison, retrieval benchmark | Existing documentation/data | No dedicated screenshots of those reports/console were supplied |
| Recorded presentation video | Not supplied | Static images are not a completed recording |

No additional paid call, model run, dashboard refresh or trace is necessary to
present these existing images. Do not rerun a model or edit a label for a better
screenshot. An optional expanded trace tree or report image would be separate
future capture work, not performed here. Do not start the next milestone.

## Safe presentation captions

Say “a real completed LNX-001 Streamlit run, shown in supplied captures,” not
“the S009 evaluation run” or “a live execution now.” Explain that current chat uses
validate_output=False, citation checks only report findings, technical correctness
is unverified and past fixes cannot establish today's root cause. The underlying
three-tool architecture is real, but the photographed run called only two tools.

The formatted disclaimer visible in 01/02 coexists with an opening-disclaimer
warning in 05/06. Exact raw formatting is not recoverable from the screenshots
alone; do not invent a checker explanation or remove the diagnostic. Likewise,
03's potentially confusing historical comparison is retained rather than endorsed.

All screenshots can be reopened at original resolution via their links. Avoid
cropping out failures or presenting supplementary scroll views as separate runs.
No production readiness, customer savings, autonomous remediation or cloud
deployment is demonstrated by these images.

## Supporting sources

- [Updated walkthrough](demo_walkthrough.md)
- [README architecture and gallery](../README.md)
- [Chat implementation](../app.py) and [monitoring helpers](../pam_monitoring.py)
- [Historical S009 and the frozen batch](../evals/results.jsonl)
- [Batch report](../evals/batch_report.md), [human labels](../evals/labels.csv)
- [Judge comparison](../evals/judge_v2_comparison.json)
- [Retrieval benchmark](retrieval_benchmark.md)
- [Synthetic-source provenance](pam_expansion_sources.md)
