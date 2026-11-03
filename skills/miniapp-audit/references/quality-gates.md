# Quality Gates

Quality gates prevent an audit from producing confident but unsupported conclusions. Apply them before analysis, before confirmation and before reporting.

## Gate definitions

| Gate | Question | Pass criteria | Failure handling |
|---|---|---|---|
| Authorization | Is the target authorized, and are the rules of engagement explicit? | Written scope, accounts, environment, time window, data rules | Stop; do not test |
| Material | Is the material complete enough to support the conclusion? | Main package, subpackages, plugins and versions accounted for; missing items recorded | Limit conclusions or stop |
| Coverage | Is the tested surface explicit? | Every asset type marked tested, partial or not tested, with a reason | Do not claim comprehensive coverage |
| Evidence | Is the finding confirmed or still a hypothesis? | E2/E3 for confirmed; E0/E1 labeled as hypothesis | Downgrade or verify |
| Report | Can a reviewer reproduce and act on the finding? | Root cause, reproduction, impact, remediation, references, evidence level | Return for completion |
| Compliance | Did testing avoid unauthorized access and destructive changes? | No other users' data, no real payments, no destructive writes | Stop and record |

## Material gate

Check before static or dynamic conclusions:

- `app.json` and `app.js` are present or their absence is explained.
- Declared subpackages and plugins are present or marked missing.
- Client version, account and artifact hashes are recorded.
- Encrypted or failed packages are recorded as limitations.

A conclusion about a flow that lives in a missing subpackage is not supported.

## Coverage gate

Mark each asset type:

- `tested`: exercised with evidence.
- `partial`: some paths or roles tested; state what is missing.
- `not tested`: not exercised; state why.

Asset types include HTTP APIs, WebSocket, cloud functions, cloud database/storage, web-view, plugins, payment, local storage, navigation and QR entry points.

## Evidence gate

- E0: pattern or keyword only. Not a finding.
- E1: static path and missing guard. Hypothesis; requires verification.
- E2: dynamic reproduction. Confirmed.
- E3: demonstrated impact. Confirmed with impact evidence.

A confirmed finding must include the exact request or steps, the observed response and the expected secure behavior.

## Report gate

Every reportable finding must answer:

1. What is the affected asset?
2. What does the client control?
3. Which server-side or cloud-side check is missing?
4. How can the issue be reproduced?
5. What is the impact?
6. How should it be fixed?
7. What evidence level supports the conclusion?
8. What was not tested that could change the conclusion?

## Compliance gate

Stop immediately if testing:

- Requires another user's credentials or personal data.
- Would execute a real payment, refund, deletion or privilege change.
- Causes instability, data loss or service degradation.
- Exceeds the authorized scope or rate limits.

Record the stop condition and the minimum evidence collected.
