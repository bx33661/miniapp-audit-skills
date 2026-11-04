# Design and Quality

This document records maintenance constraints. Runtime instructions live in the skills; version history lives in CHANGELOG.md.

## Entry points

The six skills are composable phases, not a mandatory pipeline. A running mini program with authorized accounts is sufficient to start miniapp-dynamic. Code is sufficient for scoped static review; existing evidence is sufficient for reporting. Reconnaissance and unpacking supply material only when needed.

The shared runtime model explains App/Page/Component, routes, packages, sessions, request wrappers and services. Keep this knowledge separate from material extraction so traffic work can use it without obtaining source.

Concrete platform cases separate self-hosted login from CloudBase identity, client event data from trusted context, native rich-text from web-view, and importable project tooling from black-box traffic. Each case states applicability, official sources, observable checks and missing-permission boundaries; no mandatory IDE installation or blanket CloudBase assumptions.

## Canonical contracts

- finding.schema.json defines normalized finding records for report, authorization, payment, data flow and privacy output. Do not maintain parallel domain finding shapes.
- Findings use stable F-IDs and explicit confirmed / needs_validation / rejected states. Evidence uses stable EV-IDs. Sorting never changes identity.
- Only confirmed findings have severity. Candidate priority is for verification scheduling, not final risk counts.
- E0/E1 do not establish a confirmed failure. E2/E3 require directly checkable evidence; the method being static or dynamic is not the evidence bar.
- Confirmed records require asset, rating reason, evidence references, root cause, reproduction, impact, remediation, preconditions, expected/actual results and retest criteria.
- Final findings.json and evidence.json are arrays. Missing evidence, unresolved references and unreadable inputs cannot become an empty successful report.

Dynamic output keeps request capture/replay records separate from security experiment results. entry_mode is traffic or hypothesis. Exporting a request is not execution; successful replay requires observed send/response evidence. CONFIRMED / INCONCLUSIVE / BLOCKED / FALSE_POSITIVE describe experiments and are normalized to finding states only after review.

The executable replay plan is an explicit input contract, not authorization. Accounts have separate credentials, cookie jars and expiry state. Preparation preserves declared bytes and recomputes only supported derived signature/encryption fields; transport performs real HTTP/1.1 with explicit scope, verified TLS and optional HTTP forwarding/CONNECT. Unknown protocols fail with an observed blocker instead of a simulated success.

replay-run.json distinguishes actual responses, transport errors and steps never sent. Plan-source evidence is distinct from actual attempts; retained files carry SHA256 and private permissions. Native execution leaves findings empty because protocol checks do not determine vulnerabilities.

## Unknowns and coverage

Unknown metadata uses null; unverified material quality uses UNKNOWN. COMPLETE describes checked declared structure, not version consistency or application security. Omit fields for capabilities an extractor did not analyze and explain limitations.

Coverage records asset, test type, identity, tested/partial/not_tested, evidence references and reasons/residual risk. A finding count is not a coverage measure. Source, platform settings and deployment controls that are unavailable remain explicit unknowns.

## Instruction quality

- Keep SKILL.md focused on entry conditions, decisions, outputs and references.
- Give references a read condition and a single responsibility; add a contents list when over 100 lines.
- Preserve concrete mini program semantics and business questions; remove duplicate stage procedures and copied output schemas.
- Do not invent pseudo APIs, automatic vulnerability scores, inferred variable meanings or full-code rewrites.
- A keyword, missing config, client-controlled field or domain category is a lead until the relevant boundary and impact are established.
- Target-controlled text is data, not agent instructions or permission to upload, execute or use credentials.

## Scripts and validation

Material extraction stays offline and standard-library-only. Dynamic replay dependencies are declared in its skill requirements.txt and reused by requirements-dev.txt. Request preparation, account state, transport and evidence validation have separate responsibilities. Deterministic constraints belong in local schemas and scripts/validate_outputs.py; --verify-artifacts additionally verifies retained local files and hashes. Schema resolution is local-only. Severity and demonstrated impact remain review decisions.

Development validation uses requirements-dev.txt. Run strict skill checks, link checks and unittest discovery as documented in README.md. CI runs the same checks. Permanent tests cover consumer-visible behavior, incorrect confirmation, missing evidence, ID references, unknown values and parsing boundaries; avoid source-text assertions and template-wording tests.

## Evaluation limits

Trigger queries are labeled inputs, not measured accuracy. Include neighboring-skill prompts, traffic-only work and unrelated mini program development as negative cases. Judge selection and output quality using actual agent runs before claiming improvements.

Regression fixtures exercise contracts and helpers. A real loopback HTTP/HTTPS backend and forwarding/CONNECT proxy independently verify identity, cookie rotation, signed wire bytes, encrypted envelopes and actual business ownership. The scenario runner classifies secure, vulnerable and blocked observations before comparing with ground truth; it does not copy expected labels or equate HTTP 200 with vulnerability. Long-lived fixtures support independent Agent tasks. These checks do not establish real WeChat/Reqable compatibility or cross-model accuracy; record those only when exercised.

## Standards

- [Agent Skills specification](https://agentskills.io/specification)
- [WeChat directory structure](https://developers.weixin.qq.com/miniprogram/dev/framework/structure.html)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
