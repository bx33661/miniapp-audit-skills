# Severity and Confidence

Severity and confidence answer different questions. Severity describes potential impact; confidence describes how strongly the evidence supports the finding. Do not use confidence to inflate severity, or severity to imply evidence.

## Severity levels

| Level | Meaning | Mini program examples |
|---|---|---|
| Critical | Broad compromise of money, identity or sensitive data with low preconditions | Unauthenticated administrative API; payment amount accepted from client; cloud credential with broad bucket access |
| High | Significant data, money or privilege impact under realistic preconditions | Horizontal access to orders or personal data; plaintext AppSecret in client; refund or order state controlled by client |
| Medium | Limited data or function impact, or a meaningful step in a chain | Enumeration of public identifiers; verbose errors; missing rate limit on sensitive queries |
| Low | Minor information exposure or defense-in-depth gap | Internal path disclosure; non-sensitive configuration leakage; missing security header |
| Informational | Observation without demonstrated security impact | Code-quality issue; deprecated dependency without a reachable exploit |

## Impact dimensions

Assess impact across:

- **Confidentiality:** personal data, credentials, business data, internal documents.
- **Integrity:** orders, payments, refunds, inventory, reviews, approvals.
- **Availability:** service disruption, resource exhaustion, abuse of paid resources.
- **Financial:** direct loss, refund abuse, coupon or points abuse, settlement errors.
- **Regulatory:** privacy, consent, retention, cross-border transfer, minors.

State the dimension and, where possible, the quantity or scope. "Leaks data" is weaker than "returns another user's order list for any sequential order ID".

## Confidence

| Confidence | Evidence | Use |
|---|---|---|
| High | E2/E3 with a stable reproduction and controlled variables | Confirmed finding |
| Medium | E2 with environmental limits, or E1 with a strong code path | Confirmed with caveats, or likely |
| Low | E0/E1 with incomplete path or missing context | Hypothesis; requires verification |

Confidence must be justified in the finding, not asserted.

## Severity calculation

Use impact and likelihood, then adjust for scale:

- **Impact:** what the attacker gains if the issue is exploited.
- **Likelihood:** prerequisites, required role, race window, user interaction, rate limits.
- **Scale:** number of users, records, orders or amount exposed.

A high-impact issue with an unrealistic precondition may be lower than a medium-impact issue that any authenticated user can trigger at scale. Explain the reasoning.

## Mapping

Use CWE for the weakness class and OWASP API Top 10 or MASVS for the control area where applicable. Mapping is supporting context, not a substitute for impact analysis.

## Anti-patterns

- Labeling every missing header or verbose error as High.
- Treating a pattern match as confirmed.
- Assigning Critical because the asset is "important" without evidence of reachability.
- Using CVSS without explaining the mini program-specific preconditions.
- Reporting a client-side check as a server-side vulnerability.
