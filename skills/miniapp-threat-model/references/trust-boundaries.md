# Trust Boundaries

A trust boundary is a place where data or authority crosses from a less trusted context into a more trusted one. For mini programs, the client is always the less trusted side.

For each boundary, ask:

1. What crosses the boundary?
2. Who can influence it?
3. What does the receiving side verify?
4. What happens if verification is missing?

## Client to WeChat platform

| Question | Typical failure | Test idea |
|---|---|---|
| Is identity derived from `code2session` on the server? | Client sends `openid` or `unionid` as identity | Replay with a modified identity field; compare server response |
| Is `session_key` kept server-side? | `session_key` returned to the client | Inspect login responses and storage |
| Is `encryptedData` verified and decrypted server-side? | Client-supplied decrypted data trusted | Modify encrypted payload or IV; observe acceptance |
| Is the login code single-use and time-bound? | Replay of an old code succeeds | Replay a captured login request |

## Client to backend

| Question | Typical failure | Test idea |
|---|---|---|
| Are object identifiers authorized per user? | Sequential `orderId` or `userId` exposes other objects | Multi-account request with another object ID |
| Are tenant or organization identifiers derived from the session? | Client-supplied `tenantId` or `unitCode` trusted | Change the identifier; compare scope |
| Are roles and permissions server-side? | Client sends `role`, `isAdmin` or `userType` | Modify the role field; test protected functions |
| Are prices and totals server-calculated? | Client sends `amount`, `totalPrice` or `discount` | Modify amount or quantity; compare order total |
| Are state transitions authorized? | Client sends `status=paid` or `refunded` | Attempt illegal transition; observe acceptance |

## Client to cloud development

| Question | Typical failure | Test idea |
|---|---|---|
| Does the cloud function verify `OPENID`/`APPID` from `cloud.getWXContext()`? | Function trusts event data | Call the function with modified event fields |
| Are database rules least-privilege? | Collection readable or writable by all users | Query another user's records with a low-privilege account |
| Are storage paths isolated per user? | File IDs enumerable or shared | Access another user's file ID |
| Is one function handling multiple operations? | Create/read/update/delete share one authorization path | Call an operation the role should not perform |
| Is the environment ID or admin credential exposed? | Client contains cloud env or secret | Inspect client bundle and configuration |

## Backend to payment and third parties

| Question | Typical failure | Test idea |
|---|---|---|
| Is the callback signature verified? | Client success callback treated as payment | Forge or replay a callback; observe order state |
| Is the callback amount checked against the local order? | Callback amount trusted directly | Compare callback amount with order amount |
| Is the callback idempotent and replay-safe? | Duplicate callback grants value twice | Replay a valid callback; observe duplicate effects |
| Is the merchant ID, AppID and order number checked? | Cross-merchant or cross-order confusion | Modify merchant or order fields in a controlled test |
| Is reconciliation using the same checks as the callback? | Manual reconciliation bypasses verification | Review reconciliation code path |

## Web-view to mini program

| Question | Typical failure | Test idea |
|---|---|---|
| Is the `web-view` URL restricted to an allowlist? | User-controlled URL loads arbitrary content | Modify the URL parameter; observe navigation |
| Is `postMessage` validated for origin and schema? | Any page can invoke privileged actions | Send malformed or unauthorized messages from a test page |
| Are JSSDK navigation APIs constrained? | Open redirect or unauthorized page access | Manipulate `navigateTo` parameters |
| Is sensitive data passed into the web-view? | Tokens or PII exposed to third-party pages | Inspect URL, storage and bridge messages |

## Boundary review checklist

- Every critical flow crosses at least one boundary.
- Every boundary has a named verification point.
- Every verification point has an evidence requirement.
- Client-side checks are treated as UX, not security.
- Missing boundaries are recorded as limitations, not assumed secure.
