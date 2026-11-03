# Abuse Case Patterns

An abuse case describes how a legitimate feature can be used for an unintended purpose. Write abuse cases next to use cases, before testing.

Each pattern below is a prompt, not a checklist requirement. Select the patterns that fit the business model.

## Identity and session

- Can the client choose its own identity (`openid`, `userId`, `role`)?
- Can an old login code, token or session be replayed?
- Does logout or account deletion invalidate server-side sessions?
- Is the token stored in plaintext local storage, and can another context read it?

Evidence: a modified identity field returning another user's data, or a replayed session remaining valid.

## Object-level authorization

- Are object identifiers sequential, predictable or enumerable?
- Does the server check ownership on every read, update and delete?
- Are tenant, organization or unit identifiers derived from the session?
- Do batch, export and search endpoints apply the same authorization as single-object endpoints?

Evidence: user A receives user B's object with the same privileges.

## Function-level authorization

- Are administrative endpoints reachable by ordinary users?
- Does the client-side menu hide a function without a server-side check?
- Can a low-privilege account call a cloud function or HTTP trigger directly?
- Are internal or debug endpoints exposed in production?

Evidence: a low-privilege account performs a protected action.

## Payment and money

- Is the amount calculated on the server from product, quantity and coupon data?
- Can quantity, price, discount, points or currency be negative, fractional or overflowing?
- Is the payment result based on the server-side callback rather than the client success callback?
- Are callbacks verified, amount-checked, idempotent and replay-safe?
- Can refunds, cancellations or partial payments be repeated or combined?

Evidence: an order total or payment state changes contrary to the server-side business rules.

## Coupons, points and rewards

- Can a coupon be reused, stacked or applied outside its scope?
- Are eligibility, validity and usage limits checked server-side?
- Can points, sign-in rewards or invitation rewards be farmed by automation?
- Does a race condition allow multiple redemptions?

Evidence: value is granted more than once or outside the intended eligibility.

## State machines

- Can the client set `paid`, `shipped`, `refunded`, `approved` or `cancelled` directly?
- Are transitions validated against the current state and the actor's role?
- Can a terminal state be reopened or a refunded order be shipped?
- Do asynchronous jobs and manual operations use the same state rules?

Evidence: an illegal transition succeeds.

## Data exposure

- Does an endpoint return more fields than the page needs?
- Are internal identifiers, phone numbers, addresses or identity data exposed?
- Do error messages reveal stack traces, SQL, internal hosts or keys?
- Are exports, logs or debug pages accessible?

Evidence: sensitive fields or records are returned to an unauthorized context.

## Upload and file handling

- Is the file type validated by content, not only extension?
- Is the storage path user-controlled or enumerable?
- Can a user read or overwrite another user's file?
- Are uploaded files scanned for content safety where required?

Evidence: unauthorized file read, write or execution.

## Web-view and navigation

- Is the loaded URL allowlisted and independent of user input?
- Can `postMessage` invoke privileged actions without origin/schema checks?
- Can navigation parameters cause open redirect or unauthorized page access?
- Is sensitive data passed into a third-party page?

Evidence: arbitrary URL load, unauthorized bridge action or data leak.

## Cloud development

- Does the cloud function authenticate the caller with `cloud.getWXContext()`?
- Are database and storage rules scoped to the owner?
- Does one function expose multiple operations with a single authorization path?
- Are environment IDs, admin credentials or internal endpoints exposed?

Evidence: a low-privilege caller reads or mutates another user's cloud data.

## Automation and resource consumption

- Are sensitive endpoints rate-limited?
- Can identifiers be enumerated at scale?
- Can SMS, email, OCR, map or AI endpoints be abused for cost or spam?
- Are anti-automation controls enforceable server-side?

Evidence: repeated requests produce value, cost or data beyond the intended limit.

## Writing the abuse case

State:

- Preconditions and required role.
- The client-controlled field or action.
- The server-side check that should exist.
- The observable signal of failure.
- The evidence level required for confirmation.
