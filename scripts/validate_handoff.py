"""Validate an exported handoff's integrity and structure, not engineering acceptance."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import jsonschema
from reqstudio import capabilities as cap
from reqstudio import contracts


def validate_bundle(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        expected = {"requirements.json", "requirements.md", "capability_snapshot.json", "capability_snapshot.md", "requirements-handoff.schema.json", "README.md"}
        if set(manifest["sha256"]) != expected or set(archive.namelist()) != expected | {"manifest.json"}:
            raise ValueError("Unexpected or missing handoff files")
        for name, digest in manifest["sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Content hash mismatch: {name}")
        value = json.loads(archive.read("requirements.json"))
        snapshot = json.loads(archive.read("capability_snapshot.json"))
    schema = json.loads((ROOT / "schemas/requirements-handoff.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(value)
    if cap.fingerprint(snapshot["sources"]) != snapshot["fingerprint"]:
        raise ValueError("Invalid capability source fingerprint")
    if any(value["capability_snapshot"][key] != snapshot[key] for key in value["capability_snapshot"]):
        raise ValueError("Requirements and capability snapshot references differ")
    if manifest["baseline_id"] != value["baseline_id"] or manifest["revision"] != value["revision"]:
        raise ValueError("Manifest baseline identity differs")
    project = {"name": value["project_name"], "snapshot_id": snapshot["snapshot_id"], "board_id": value["board_id"], "stories": value["stories"]}
    issues = contracts.readiness(project, snapshot)
    if issues:
        raise ValueError("\n".join(issues))
    return {"baseline_id": value["baseline_id"], "revision": value["revision"], "status": "offered", "consumer_acceptance": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        result = validate_bundle(args.bundle.read_bytes())
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, jsonschema.ValidationError) as exc:
        print(f"VALIDATE: FAIL ({exc})")
        raise SystemExit(1)
    print("VALIDATE: PASS (integrity and structure; Design acceptance pending)")
    print(json.dumps(result, indent=2))
