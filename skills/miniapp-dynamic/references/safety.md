# Dynamic Testing Safety

Dynamic testing can change state, consume resources and expose personal data. The rules below are strict because the impact is real.

## Authorization

- Obtain written authorization that names the target, environment and time window.
- Confirm whether production testing is allowed; default to read-only.
- Confirm the accounts and roles that may be used.
- Confirm data handling, retention and deletion requirements.

If authorization is unclear, do not send requests.

## Scope

- Test only the hosts, mini programs and cloud environments in scope.
- Do not pivot to internal services, third-party systems or other tenants.
- Do not test payment, refund, deletion or privilege changes without explicit approval and a controlled environment.
- Record out-of-scope observations without testing them.

## Accounts and data

- Use dedicated test accounts and synthetic data.
- Do not use another person's credentials or personal data.
- If a test returns real user data, stop, record the minimum evidence and delete the data.
- Do not enumerate identifiers beyond what is necessary to prove the issue.
- Redact tokens, cookies, phone numbers, identity numbers and addresses in notes.

## Rate and impact

- Use the lowest request rate that produces a valid result.
- Respect published or observed rate limits.
- Stop on 5xx spikes, timeouts, instability or signs of resource exhaustion.
- Do not run denial-of-service, stress or high-concurrency tests without explicit approval.

## State changes

- Prefer read-only requests.
- If a write is required, use a test account and a reversible action.
- Never complete a real payment, refund or settlement.
- Record the original state and the cleanup action.
- Verify cleanup after the test.

## Evidence handling

- Store raw evidence in a restricted directory.
- Redact secrets and personal data before sharing.
- Keep a minimal reproduction; do not retain bulk personal data.
- Record the tool, timestamp, account role and request identifier.
- Delete evidence according to the agreed retention period.

## Stop conditions

Stop immediately when:

- Authorization is missing or exceeded.
- Real user data is exposed.
- A payment, refund or destructive action would execute.
- The service becomes unstable or returns repeated 5xx errors.
- The target shows signs of production impact.
- The test requires bypassing a control beyond the agreed scope.

Record the stop condition and notify the authorized contact.
