# Encrypted and Obfuscated Bundles

Read this when the package is encrypted, heavily minified, or the page files are missing while `app-service.js` is present.

## V1MMWX packages

`V1MMWX` is a container format used by WeChat clients for cached packages. It is not a security boundary.

- Decryption derives a key from the mini program appid.
- The header uses AES-CBC; the remainder uses a single-byte XOR.
- A correct decryption starts with the standard wxapkg marker `0xBE`.
- Record the tool, version and appid used; verify the decrypted header and file index.
- Do not modify the original cache. Work on a copy.

If decryption fails, confirm the appid and package version before trying another tool. Do not brute-force unrelated appids.

## Bundle layout

A raw wxapkg unpack often contains:

- `app-config.json` — the real page, subpackage, permission and plugin configuration.
- `app-service.js` — application logic, often with modules registered through `define`.
- `page-frame.js` — runtime/frame code.
- `pages/*.html` — page templates; page logic may be in `app-service.js`, not in a separate `pages/*.js`.

Do not infer that a page has no logic because `pages/*.js` is absent. Check `app-service.js` and the `define` module table.

## Source maps

- `sourcesContent` may not align with `sources`; verify both indexes before trusting a mapping.
- A map may contain only some modules or an older version.
- Record whether a finding comes from original source, `sourcesContent`, or decompiled code.

## Sandbox execution (advanced, explicit exception)

Executing an obfuscated bundle is an optional technique, not a default step. Use it only when static inspection cannot recover the configuration or a critical branch, and only with explicit authorization.

Required conditions:

- Isolated VM or container, never the analyst workstation.
- No network access.
- Read-only copy of the package.
- Mock the `wx` runtime and only the APIs needed to load the bundle.
- Do not install or load untrusted dependencies.
- Hash the input and output; record commands and environment.
- Do not use real accounts, tokens or personal data.
- Stop if the bundle attempts network, file, process or credential access.

The goal is to observe configuration, page registration, hidden fields and branch conditions. Treat the output as E1 evidence until verified against a live authorized environment.

## Evidence

Record:

- Package version, appid, hash and decryption tool.
- Original and decrypted hashes.
- Bundle layout and the files actually inspected.
- Sandbox commands and runtime versions, if used.
- Which findings depend on decompiled or executed code.

## Safety

- Only analyze authorized packages.
- Never execute untrusted code on the host.
- Never put real credentials or user data into a sandbox.
- Do not publish decrypted bundles or embedded keys.
