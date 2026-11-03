# Evidence Standard

Evidence must let a reviewer understand what was tested, what was observed and how the conclusion was reached.

## Evidence levels

| Level | Definition | Report use |
|---|---|---|
| E0 | Keyword or pattern match without a code path | Observation only |
| E1 | Static path with a missing guard, not dynamically verified | Pending or hypothesis |
| E2 | Dynamic reproduction with a controlled request and response | Confirmed finding |
| E3 | E2 plus demonstrated impact on data, money, privilege or state | Confirmed finding with impact |

## Required fields

Each evidence record contains:

- Evidence identifier and finding identifier.
- Target, environment, account role and timestamp.
- Tool and version used to capture or replay.
- Exact request: method, URL, headers and body, with secrets redacted.
- Exact response: status, headers and relevant body, with personal data redacted.
- Baseline request and response, when a mutation is involved.
- Reproduction steps that another tester can follow.
- Observed result and expected secure behavior.
- Evidence level and residual uncertainty.
- Retention and deletion status.

## Reproducibility

A reviewer should be able to:

1. Identify the affected asset.
2. Recreate the precondition and account role.
3. Send the same request.
4. Observe the same class of result.
5. Understand why the result is a security failure.

If the result depends on a race, time window or one-time token, state that explicitly and record the number of attempts.

## Redaction

- Remove or mask tokens, cookies, authorization headers and API keys.
- Mask personal data: names, phone numbers, identity numbers, addresses, student or employee identifiers.
- Keep enough context to prove the issue without exposing the data.
- Store unredacted evidence only when necessary and in a restricted directory.

## Retention

- Define a retention period before testing.
- Delete raw personal data when it is no longer needed.
- Keep a minimal reproduction and the report.
- Record the deletion in the audit log.

## Integrity

- Record hashes for exported artifacts where practical.
- Do not edit raw evidence; create derived, redacted copies.
- Keep timestamps and tool versions.
- Note any evidence that was lost, truncated or could not be captured.

## Anti-patterns

- A screenshot without the request or reproduction steps.
- A response body without the request that produced it.
- A pattern match presented as a confirmed vulnerability.
- A finding that depends on data from another user without a test account.
- A report that omits failed attempts and limitations.
