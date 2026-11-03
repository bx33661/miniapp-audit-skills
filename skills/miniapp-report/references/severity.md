# Severity and Confidence in Reports

Report severity and confidence separately. Severity describes potential impact; confidence describes the strength of the evidence.

## Severity levels

| Level | Meaning | Examples |
|---|---|---|
| Critical | Broad compromise of money, identity or sensitive data with low preconditions | Unauthenticated admin API; client-controlled payment amount; broad cloud credential |
| High | Significant data, money or privilege impact under realistic preconditions | Cross-user order access; hardcoded AppSecret; client-controlled order or refund state |
| Medium | Limited data or function impact, or a meaningful step in a chain | Identifier enumeration; verbose errors; missing rate limit |
| Low | Minor exposure or defense-in-depth gap | Internal path disclosure; non-sensitive configuration leak |
| Informational | Observation without demonstrated impact | Code-quality issue; unreachable deprecated dependency |

## Confidence

| Confidence | Evidence | Report language |
|---|---|---|
| High | E2/E3, stable reproduction, controlled variables | Confirmed |
| Medium | E2 with environmental limits, or E1 with a strong path | Confirmed with caveats, or likely |
| Low | E0/E1 with incomplete context | Pending or observation |

## Report rules

- Do not assign Critical because an asset is important; state the demonstrated or credible impact.
- Do not use a pattern match as confirmed evidence.
- Explain preconditions: role, account, environment, race window and rate limit.
- Quantify scope where possible: number of records, orders, users or amount.
- Map to CWE and OWASP API Top 10 or MASVS only as supporting context.
- Keep confirmed, suspected and not tested findings in separate sections.

## Review questions

1. What does the attacker gain?
2. What privilege is required?
3. How many users or records are exposed?
4. What evidence level supports the conclusion?
5. What would make the finding invalid?
6. What must be true after the fix?
