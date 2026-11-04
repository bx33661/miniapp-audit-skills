#!/usr/bin/env python3
"""Validate an audit evidence directory using local schemas and cross-record IDs."""
from __future__ import annotations

import hashlib
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable

SKILLS = Path(__file__).resolve().parents[1] / "skills"
ARTIFACT_SCHEMAS = {
    "material-check.json": "miniapp-recon/assets/material-check-output.schema.json",
    "attack-surface.json": "miniapp-static-audit/assets/attack-surface-output.schema.json",
    "secret-scan.json": "miniapp-static-audit/assets/secret-scan-output.schema.json",
    "authz-findings.json": "miniapp-static-audit/assets/authz-findings.schema.json",
    "payment-findings.json": "miniapp-static-audit/assets/payment-findings.schema.json",
    "dataflow-analysis.json": "miniapp-static-audit/assets/dataflow-output.schema.json",
    "privacy-compliance.json": "miniapp-static-audit/assets/privacy-compliance-output.schema.json",
    "dynamic-test-results.json": "miniapp-dynamic/assets/dynamic-test-output.schema.json",
    "replay-run.json": "miniapp-dynamic/assets/replay-run.schema.json",
    "audit-session.json": "miniapp-audit/assets/audit-session.schema.json",
}
ARRAY_SCHEMAS = {
    "findings.json": "miniapp-report/assets/finding.schema.json",
    "evidence.json": "miniapp-report/assets/evidence.schema.json",
}


def unavailable_resource(uri: str) -> Resource:
    """Schema identifiers never trigger network or arbitrary filesystem reads."""
    raise NoSuchResource(ref=uri)


def schema_registry() -> Registry:
    resources = []
    for path in sorted(SKILLS.rglob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        resources.append((path.resolve().as_uri(), Resource.from_contents(schema)))
    return Registry(retrieve=unavailable_resource).with_resources(resources)


def record_ids(records: object, field: str, label: str, errors: list[str]) -> set[str]:
    known: set[str] = set()
    if not isinstance(records, list):
        return known
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get(field), str):
            continue
        identifier = record[field]
        if identifier in known:
            errors.append(f"{label}/{index}/{field}: duplicate ID {identifier}")
        known.add(identifier)
    return known


def referenced_evidence(value: object, path: str):
    if isinstance(value, dict):
        refs = value.get("evidence_refs")
        if isinstance(refs, list):
            for index, ref in enumerate(refs):
                if isinstance(ref, str):
                    yield f"{path}/evidence_refs/{index}", ref
        for key, child in value.items():
            if key != "evidence_refs":
                yield from referenced_evidence(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from referenced_evidence(child, f"{path}/{index}")


def validate_directory(directory: Path) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    documents: dict[str, object] = {}
    registry = schema_registry()
    for filename, relative_schema in {**ARRAY_SCHEMAS, **ARTIFACT_SCHEMAS}.items():
        path = directory / filename
        if not path.is_file():
            if filename in ARRAY_SCHEMAS:
                errors.append(f"{filename}: required final array is missing")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{filename}: cannot read JSON: {exc}")
            continue
        documents[filename] = payload
        schema = {"$ref": (SKILLS / relative_schema).resolve().as_uri()}
        if filename in ARRAY_SCHEMAS:
            schema = {"type": "array", "items": schema}
        validator = Draft7Validator(schema, registry=registry, format_checker=FormatChecker())
        for error in sorted(validator.iter_errors(payload), key=lambda e: str(list(e.absolute_path))):
            pointer = "/".join(map(str, error.absolute_path))
            errors.append(f"{filename}/{pointer}: {error.message}")

    evidence_ids = record_ids(documents.get("evidence.json"), "evidence_id", "evidence.json", errors)
    record_ids(documents.get("findings.json"), "finding_id", "findings.json", errors)
    for filename, payload in documents.items():
        for pointer, identifier in referenced_evidence(payload, filename):
            if identifier not in evidence_ids:
                errors.append(f"{pointer}: unknown evidence ID {identifier}")
        if filename in ("authz-findings.json", "payment-findings.json", "dataflow-analysis.json") and isinstance(payload, dict):
            record_ids(payload.get("findings"), "finding_id", filename + "/findings", errors)
        if filename == "replay-run.json" and isinstance(payload, dict):
            record_ids(payload.get("results"), "id", filename + "/results", errors)
        if filename == "secret-scan.json" and isinstance(payload, dict) and isinstance(payload.get("secrets"), list):
            for index, secret in enumerate(payload["secrets"]):
                if isinstance(secret, dict) and isinstance(secret.get("evidence_id"), str):
                    if secret["evidence_id"] not in evidence_ids:
                        errors.append(f"{filename}/secrets/{index}/evidence_id: unknown evidence ID {secret['evidence_id']}")
    return errors, documents


def verify_artifacts(directory: Path, documents: dict[str, object]) -> list[str]:
    """Verify retained execution artifacts, without following references outside the bundle."""
    errors: list[str] = []
    records = documents.get("evidence.json")
    if not isinstance(records, list):
        return errors
    root = directory.resolve()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("artifact"), dict):
            continue
        artifact = record["artifact"]
        label = f"evidence.json/{index}/artifact"
        if not isinstance(artifact.get("file"), str) or not isinstance(artifact.get("hash"), str):
            errors.append(f"{label}: artifact verification requires a relative file and SHA256 hash")
            continue
        relative = Path(artifact["file"])
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{label}: artifact path must stay inside the evidence directory")
            continue
        path = root / relative
        try:
            if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
                errors.append(f"{label}: artifact is not a retained regular file inside the bundle")
                continue
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    digest.update(chunk)
            if digest.hexdigest() != artifact["hash"].lower():
                errors.append(f"{label}: artifact SHA256 does not match retained bytes")
        except (OSError, ValueError):
            errors.append(f"{label}: artifact could not be verified")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True, help="directory containing findings.json and evidence.json")
    parser.add_argument("--verify-artifacts", action="store_true", help="verify retained files and SHA256 hashes inside the evidence directory")
    args = parser.parse_args()
    if not args.evidence_dir.is_dir():
        print("error: evidence directory does not exist", file=sys.stderr)
        return 2
    try:
        errors, documents = validate_directory(args.evidence_dir)
        if args.verify_artifacts:
            errors.extend(verify_artifacts(args.evidence_dir, documents))
    except (OSError, UnicodeError, ValueError, Unresolvable) as exc:
        print(f"error: cannot load local output schemas: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    findings = documents["findings.json"]
    counts = {state: sum(record["status"] == state for record in findings) for state in ("confirmed", "needs_validation", "rejected")}
    print(f"Validated {len(documents)} documents: " + ", ".join(f"{state}={count}" for state, count in counts.items()))
    print("Schema and reference checks passed; evidence truth and demonstrated impact still require review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
