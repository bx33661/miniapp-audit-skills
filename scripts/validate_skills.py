#!/usr/bin/env python3
"""Validate Agent Skills in this repository.

Checks the open Agent Skills spec plus a few local quality rules:
  - name/description present and valid
  - name matches the parent directory
  - allowed-tools is a space-separated string (not a YAML list)
  - metadata values are strings (not lists/maps)
  - SKILL.md body under 500 lines (warning)
  - balanced code fences
  - relative references resolve
  - description contains a trigger phrase (warning)

Usage:
  python scripts/validate_skills.py
  python scripts/validate_skills.py --root skills --strict
  python scripts/validate_skills.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIGGER_RE = re.compile(r"(use when|when |trigger|当|用于|触发|审计|review)", re.I)
REF_RE = re.compile(r"`([^`\n]+)`|\]\(([^)\n]+)\)")


@dataclass
class SkillReport:
    path: Path
    name: str | None = None
    description: str | None = None
    lines: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_frontmatter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    return match.group(1) if match else None


def scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.+)$", frontmatter, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def is_list_field(frontmatter: str, key: str) -> bool:
    """Return True if key is written as a YAML list (block or inline)."""
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", frontmatter, re.M)
    if not match:
        return False
    inline = match.group(1).strip()
    if inline.startswith("["):
        return True
    if inline:
        return False
    # Look at the immediately following indented lines.
    tail = frontmatter[match.end():]
    for line in tail.splitlines():
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            break
        if line.lstrip().startswith("-"):
            return True
        break
    return False


def metadata_list_keys(frontmatter: str) -> list[str]:
    """Find metadata keys whose value is a list instead of a string."""
    lines = frontmatter.splitlines()
    in_metadata = False
    keys: list[str] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if line == "metadata:":
            in_metadata = True
            continue
        if in_metadata:
            if line and not line.startswith((" ", "\t")):
                break
            match = re.match(r"^  ([A-Za-z0-9_-]+):\s*(.*)$", line)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if value.startswith("["):
                keys.append(key)
                continue
            if value:
                continue
            for nxt in lines[idx + 1:]:
                if not nxt.strip():
                    continue
                if not nxt.startswith(("    ", "\t")):
                    break
                if nxt.lstrip().startswith("-"):
                    keys.append(key)
                break
    return keys


def relative_refs(text: str) -> list[str]:
    refs: list[str] = []
    for match in REF_RE.finditer(text):
        ref = (match.group(1) or match.group(2) or "").strip()
        if not ref:
            continue
        ref = ref.split("#", 1)[0]
        if ref.startswith(("http://", "https://", "mailto:")):
            continue
        if not ref.startswith(("./", "../", "scripts/", "references/", "assets/")):
            continue
        if any(token in ref for token in ("{", "}", "*", "<", ">", "...")):
            continue
        refs.append(ref)
    return refs


def validate(path: Path) -> SkillReport:
    report = SkillReport(path=path)
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        report.errors.append("missing YAML frontmatter")
        return report

    name = scalar(frontmatter, "name")
    desc = scalar(frontmatter, "description")
    report.name = name
    report.description = desc

    if not name:
        report.errors.append("missing name")
    else:
        if not NAME_RE.match(name):
            report.errors.append(
                "name must be lowercase letters/numbers/hyphens, no leading/trailing/consecutive hyphens"
            )
        if len(name) > 64:
            report.errors.append("name exceeds 64 characters")
        if name != path.parent.name:
            report.errors.append(
                f"name '{name}' must match parent directory '{path.parent.name}'"
            )

    if not desc:
        report.errors.append("missing description")
    else:
        if len(desc) > 1024:
            report.errors.append("description exceeds 1024 characters")
        if "<" in desc or ">" in desc:
            report.warnings.append("description contains '<' or '>'; avoid XML-like tags")
        if not TRIGGER_RE.search(desc):
            report.warnings.append(
                "description does not contain an explicit trigger phrase (e.g. 'Use when ...')"
            )

    for key in ("description", "compatibility"):
        match = re.search(rf"^{key}:[ \t]*(.*)$", frontmatter, re.M)
        if match:
            value = match.group(1).strip()
            if value and not (value[0] in "\"'" and value[-1] == value[0]) and ": " in value:
                report.errors.append(
                    f"{key} contains an unquoted ': '; quote the entire value"
                )

    if is_list_field(frontmatter, "allowed-tools"):
        report.errors.append(
            "allowed-tools must be a space-separated string, not a YAML list"
        )

    for key in metadata_list_keys(frontmatter):
        report.errors.append(f"metadata.{key} must be a string, not a list")

    body = text.split("---", 2)[2] if text.startswith("---") else text
    report.lines = len(body.splitlines())
    if report.lines > 500:
        report.warnings.append(
            f"SKILL.md body has {report.lines} lines; move detail to references/ (target < 500)"
        )

    if text.count("```") % 2:
        report.errors.append("unbalanced code fences")

    if re.search(r"^#+\s*when to use\b", body, re.I | re.M):
        report.warnings.append(
            "'When to use' belongs in the description, not the body"
        )

    skill_dir = path.parent
    broken: list[str] = []
    for ref in relative_refs(body):
        target = (skill_dir / ref).resolve()
        if not target.exists():
            broken.append(ref)
    if broken:
        report.errors.append("broken relative references: " + ", ".join(sorted(set(broken))))

    if not (skill_dir / "scripts").exists():
        report.infos.append("no scripts/ directory")
    if not (skill_dir / "references").exists():
        report.infos.append("no references/ directory")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Agent Skills")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1] / "skills"),
        help="skills root directory (default: <repo>/skills)",
    )
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="output JSON")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"error: skills root not found: {root}", file=sys.stderr)
        return 2

    reports = [validate(p) for p in sorted(root.rglob("SKILL.md"))]
    if not reports:
        print(f"error: no SKILL.md found under {root}", file=sys.stderr)
        return 2
    errors = sum(len(r.errors) for r in reports)
    warnings = sum(len(r.warnings) for r in reports)

    if args.json:
        payload = {
            "root": str(root),
            "skills": len(reports),
            "errors": errors,
            "warnings": warnings,
            "reports": [
                {
                    "path": str(r.path),
                    "name": r.name,
                    "lines": r.lines,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "infos": r.infos,
                }
                for r in reports
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in reports:
            status = "FAIL" if r.errors else ("WARN" if r.warnings else "OK")
            print(f"\n[{status}] {r.path}  ({r.lines} body lines)")
            for item in r.errors:
                print(f"  E  {item}")
            for item in r.warnings:
                print(f"  W  {item}")
            for item in r.infos:
                print(f"  I  {item}")
        print(f"\n{len(reports)} skills, {errors} errors, {warnings} warnings")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
