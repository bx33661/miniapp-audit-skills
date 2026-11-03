# Reqable Capture Layer

Reqable is the capture sensor for dynamic verification. It decrypts HTTPS traffic, exposes request and response details, and can forward mobile traffic to the desktop client.

The Agent remains the actuator: it reads captured requests and performs replay and mutation in its own HTTP client. Reqable rewrite, breakpoint and script features are optional and not required for this workflow.

## Desktop setup

- Start Reqable and enable its proxy on `127.0.0.1:9000`.
- Enable the system proxy when testing desktop clients, or configure the target client to use the proxy explicitly.
- Install and trust the Reqable CA certificate in every client that will be inspected.
- Confirm capture works with a known HTTPS request before testing the target.

## macOS WeChat

- The mini program container application is named `微信` with bundle identifier `com.tencent.flue.WeChatAppEx`.
- Filtering by `WeChat` may miss records; use the Chinese application name or the bundle identifier.
- The mini program container may use the system proxy even when the main WeChat process uses a TUN interface. Verify with a short capture before adding Proxifier.
- If the container bypasses the proxy, use Proxifier to force `WeChatAppEx` traffic to the Reqable port, or move to a gateway capture.

## Mobile WeChat

- Desktop QR code, mobile Reqable collaboration mode, scan and connect.
- Install and trust the CA certificate on the device.
- Enable debugging and allow the VPN service.
- iOS does not expose application attribution; filter by host and User-Agent. Android can filter by application.
- If a mini program refuses to work under the VPN, use a hotspot gateway with mitmproxy or a device-level proxy.

## MCP read surface

The free MCP surface is sufficient for capture and reading:

- `capture_live_set_enabled` — start or stop capture.
- `capture_live_filter` — filter by application, host, method, status, URL or keyword.
- `capture_live_get_by_id` — read the full request and response.
- `capture_live_generate_curl` — export a request for replay.
- `proxy_set` — control the desktop system proxy.

Rewrite, breakpoint and script creation through MCP require a paid plan. Do not depend on them; mutation belongs in the Agent HTTP client.

## Request template

When reading a record, retain:

- Method, URL and path.
- Headers that identify the mini program: `User-Agent`, `Referer`, `xweb_xhr`, content type.
- Body, preserving form field order where relevant.
- Cookies and session tokens, stored separately from the template.
- Volatile fields: `sign`, `timestamp`, `nonce`, one-time tokens.

Remove hop-by-hop headers that the HTTP client recalculates: `Host`, `Content-Length`, `Connection`, `Accept-Encoding`.

## Replay constraints

- Prefer a request generated during the current session.
- Replaying an old request may fail due to timestamp, nonce, session or signature binding.
- If a request fails, compare it with the original before concluding that the endpoint is secure.
- If the signature covers the field under test, static analysis or a hook is required; do not brute-force.

## Free and paid features

| Capability | Free | Required for this workflow |
|---|---|---|
| Capture, decrypt, filter, detail, curl export | Yes | Yes |
| MCP read tools | Yes | Yes |
| Rewrite, breakpoint, script | Limited in GUI; MCP creation is paid | No |
| History | 30 days | Export important evidence |
| Remote devices | One | Sufficient for a single test device |

## Safety

- Capture only authorized targets.
- Stop capture and disable the system proxy after testing.
- Redact tokens and personal data from notes.
- Clear captured history when it contains sensitive data.
