#!/usr/bin/env python3
"""Check relative Markdown links and code-path references.

Usage:
  python scripts/check_links.py
  python scripts/check_links.py --root . --verbose

Only paths beginning with ./, ../, assets/, references/ or scripts/ are checked.
External URLs, anchors and template placeholders are skipped.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"`([^`\n]+)`|\]\(([^)\n]+)\)")
CHECK_PREFIXES = ("./", "../", "assets/", "references/", "scripts/")
SKIP_TOKENS = ("{", "}", "*", "<", ">", "...", "http://", "https://", "mailto:")


def references(text: str) -> list[str]:
    found = []
    for match in LINK_RE.finditer(text):
        ref = (match.group(1) or match.group(2) or "").strip()
        if not ref:
            continue
        ref = ref.split("#", 1)[0]
        if not ref.startswith(CHECK_PREFIXES):
            continue
        if ref.endswith("/"):
            continue
        if any(token in ref for token in SKIP_TOKENS):
            continue
        found.append(ref)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Check relative links in Markdown")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--verbose", action="store_true", help="print every checked file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    files = []
    for pattern in ("README.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md"):
        path = root / pattern
        if path.is_file():
            files.append(path)
    for folder in ("docs", "skills"):
        folder_path = root / folder
        if folder_path.is_dir():
            files.extend(folder_path.rglob("*.md"))

    broken = []
    for path in sorted(set(files)):
        if args.verbose:
            print(f"checking {path.relative_to(root)}")
        for ref in references(path.read_text(encoding="utf-8")):
            target = (path.parent / ref).resolve()
            if not target.exists():
                target = (root / ref).resolve()
            if not target.exists():
                broken.append((path.relative_to(root), ref))

    for path, ref in broken:
        print(f"broken: {path} -> {ref}")
    print(f"{len(files)} files checked, {len(broken)} broken")
    return 0 if not broken else 1


if __name__ == "__main__":
    raise SystemExit(main())
