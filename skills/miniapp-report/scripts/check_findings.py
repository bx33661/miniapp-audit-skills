#!/usr/bin/env python3
"""Validate findings against the report quality gate.

Usage:
  python check_findings.py --findings findings.json
  python check_findings.py --findings findings.json --output report-check.json

The input may be a JSON array or an object with a "findings" array.
The script does not modify the findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_REQUIRED = ("finding_id", "title", "severity", "category", "locations")
CONFIRMED_REQUIRED = (
    "confidence",
    "evidence_level",
    "asset",
    "root_cause",
    "reproduction",
    "impact",
    "remediation",
)
SEVERITY = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
EVIDENCE = {"E0", "E1", "E2", "E3"}
CONFIRMED_STATUS = {"verified", "confirmed", "confirmed_vulnerability"}


def load(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: findings file is not valid JSON: {exc}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("findings"), list):
        return data["findings"]
    raise SystemExit('error: expected a JSON array or an object with a "findings" array')


def check(finding: dict, index: int) -> list[str]:
    errors = []
    prefix = f"finding[{index}]"
    for field in BASE_REQUIRED:
        if field not in finding or finding[field] in (None, "", [], {}):
            errors.append(f"{prefix}: missing {field}")

    locations = finding.get("locations")
    if not isinstance(locations, list) or not locations:
        errors.append(f"{prefix}: locations must be a non-empty array")
    else:
        for location_index, location in enumerate(locations):
            if not isinstance(location, dict):
                errors.append(f"{prefix}.locations[{location_index}]: expected object")
                continue
            if not location.get("file") or not location.get("line"):
                errors.append(
                    f"{prefix}.locations[{location_index}]: file and line are required"
                )

    severity = str(finding.get("severity", "")).upper()
    if severity and severity not in SEVERITY:
        errors.append(f"{prefix}: invalid severity '{finding.get('severity')}'")

    confidence = str(finding.get("confidence", "")).upper()
    if confidence and confidence not in CONFIDENCE:
        errors.append(f"{prefix}: invalid confidence '{finding.get('confidence')}'")

    evidence = str(finding.get("evidence_level", "")).upper()
    if evidence and evidence not in EVIDENCE:
        errors.append(f"{prefix}: invalid evidence_level '{finding.get('evidence_level')}'")

    status = str(finding.get("status", "")).lower()
    if status in CONFIRMED_STATUS:
        for field in CONFIRMED_REQUIRED:
            if field not in finding or finding[field] in (None, "", [], {}):
                errors.append(f"{prefix}: confirmed finding missing {field}")
        if evidence and evidence not in {"E2", "E3"}:
            errors.append(
                f"{prefix}: confirmed finding requires E2 or E3, got {evidence}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate findings against the report quality gate")
    parser.add_argument("--findings", required=True, help="findings JSON file")
    parser.add_argument("--output", help="write the check result to this path")
    args = parser.parse_args()

    findings = load(Path(args.findings))
    errors: list[str] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"finding[{index}]: expected object")
            continue
        errors.extend(check(finding, index))

    result = {
        "findings": len(findings),
        "errors": errors,
        "passed": not errors,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
