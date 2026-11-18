"""Durable drafts, explicit proposal acceptance and Requirement -> Design packages."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import uuid
import zipfile
from pathlib import Path

import jsonschema

from .capabilities import capability_options, render_markdown, utc_now

SCHEMA = "0.3"


def data_directory() -> Path:
    return Path(os.environ.get("FWLC_DATA_DIR", str(Path.home() / ".firmware-dev-life-cycle"))).expanduser()


def new_project(snapshot: dict, name: str = "Firmware requirement experiment") -> dict:
    return {"schema_version": SCHEMA, "project_id": str(uuid.uuid4()), "name": name, "workspace_revision": 0,
            "baseline_revision": 0, "updated_at_utc": utc_now(), "snapshot_id": snapshot["snapshot_id"],
            "board_id": "", "constraints": [], "stories": [], "messages": [], "proposals": [],
            "next_story_number": 1, "handoffs": []}


def project_file(project_id: str, directory: Path | None = None) -> Path:
    if str(uuid.UUID(project_id)) != project_id:
        raise ValueError("Invalid project ID")
    return (directory or data_directory()) / "projects" / project_id / "state.json"


def save_project(project: dict, directory: Path | None = None, artifact: tuple[Path, bytes] | None = None) -> None:
    path = project_file(project["project_id"], directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive file creation is cross-process; do not silently race two browser tabs.
    lock = path.with_suffix(".lock")
    artifact_created = False
    committed = False
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError("Project is being saved elsewhere. Retry; if a crashed process left the lock, inspect it first.") from exc
    try:
        os.close(fd)
        if path.exists():
            current = json.loads(path.read_text(encoding="utf-8"))
            if current["workspace_revision"] != project["workspace_revision"]:
                raise ValueError("Another tab changed this draft. Reload the saved project before editing.")
        value = copy.deepcopy(project)
        value["workspace_revision"] += 1
        value["updated_at_utc"] = utc_now()
        temp = path.with_suffix(".pending")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if artifact:
            artifact[0].parent.mkdir(parents=True, exist_ok=True)
            with artifact[0].open("xb") as output:
                output.write(artifact[1])
            artifact_created = True
        temp.replace(path)
        committed = True
        project.update(value)
    finally:
        if artifact_created and not committed:
            artifact[0].unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def load_projects(directory: Path | None = None) -> list[dict]:
    values = []
    for path in ((directory or data_directory()) / "projects").glob("*/state.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schema_version") == SCHEMA:
                values.append(value)
        except (ValueError, OSError):
            continue
    return sorted(values, key=lambda p: p["updated_at_utc"], reverse=True)


def add_story(project: dict) -> dict:
    number = project["next_story_number"]
    project["next_story_number"] += 1
    story = {"id": f"US-{number:03d}", "revision": 1, "title": "", "role": "", "want": "", "benefit": "",
             "acceptance_criteria": [], "open_questions": [], "feasibility": "unknown", "feasibility_reason": "",
             "capability_refs": [], "reviewed": False, "source_turn_ids": [], "origin": "manual", "next_ac_number": 1}
    project["stories"].append(story)
    return story


def update_story(story: dict, values: dict) -> None:
    for key in ("title", "role", "want", "benefit", "feasibility_reason"):
        if key in values:
            story[key] = str(values[key]).strip()
    if "feasibility" in values:
        if values["feasibility"] not in {"unknown", "supported", "needs-spike", "unsupported"}:
            raise ValueError("Invalid feasibility status")
        story["feasibility"] = values["feasibility"]
    for key in ("open_questions", "capability_refs", "source_turn_ids"):
        if key in values:
            story[key] = list(dict.fromkeys(str(v).strip() for v in values[key] if str(v).strip()))
    if "acceptance_criteria" in values:
        old_ids = {r["id"] for r in story["acceptance_criteria"]}
        criteria, seen = [], set()
        for item in values["acceptance_criteria"]:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            cid = str(item.get("id") or "").strip()
            if cid not in old_ids or cid in seen:
                cid = f"{story['id']}-AC-{story['next_ac_number']:03d}"
                story["next_ac_number"] += 1
            seen.add(cid)
            criteria.append({"id": cid, "text": text, "test_intent": str(item.get("test_intent") or "").strip(),
                             "requires_hardware": bool(item.get("requires_hardware", True))})
        story["acceptance_criteria"] = criteria
    story["reviewed"] = bool(values.get("reviewed", False))
    story["revision"] += 1


def rebind_snapshot(project: dict, snapshot: dict) -> None:
    if project["snapshot_id"] == snapshot["snapshot_id"]:
        return
    project["snapshot_id"] = snapshot["snapshot_id"]
    project["proposals"] = []
    if project["board_id"] not in {b["id"] for b in snapshot["boards"]}:
        project["board_id"] = ""
    for story in project["stories"]:
        story["reviewed"] = False
        story["feasibility"] = "unknown"
        story["revision"] += 1


def update_context(project: dict, name: str, board_id: str, constraints: list[str]) -> None:
    constraints = [x.strip() for x in constraints if x.strip()]
    if project["board_id"] != board_id or project["constraints"] != constraints:
        for story in project["stories"]:
            story["reviewed"] = False
            story["feasibility"] = "unknown"
            story["revision"] += 1
        project["proposals"] = []
    project.update(name=name.strip(), board_id=board_id, constraints=constraints)


def readiness(project: dict, snapshot: dict) -> list[str]:
    issues = []
    if project["snapshot_id"] != snapshot["snapshot_id"]:
        issues.append("Capability snapshot does not match the draft.")
    if not project["name"].strip():
        issues.append("Project name is required.")
    board_ids = {b["id"] for b in snapshot["boards"]}
    if project["board_id"] not in board_ids:
        issues.append("Select a target board from the capability snapshot.")
    if not project["stories"]:
        issues.append("At least one user story is required.")
    valid_refs = capability_options(snapshot, project["board_id"])
    for story in project["stories"]:
        sid = story["id"]
        for key in ("title", "role", "want", "benefit"):
            if not str(story.get(key, "")).strip():
                issues.append(f"{sid}: missing {key}.")
        if not story["reviewed"]:
            issues.append(f"{sid}: user review is pending.")
        if story["feasibility"] != "supported":
            issues.append(f"{sid}: feasibility is {story['feasibility']}; resolve or remove from the offered scope.")
        if not story["feasibility_reason"].strip():
            issues.append(f"{sid}: feasibility rationale is required.")
        if not story["capability_refs"]:
            issues.append(f"{sid}: at least one capability reference is required.")
        if any(ref not in valid_refs for ref in story["capability_refs"]):
            issues.append(f"{sid}: capability reference is unknown or does not match the target board.")
        if story["open_questions"]:
            issues.append(f"{sid}: unresolved questions remain.")
        if not story["acceptance_criteria"]:
            issues.append(f"{sid}: acceptance criteria are required.")
        for ac in story["acceptance_criteria"]:
            if not ac["text"].strip() or not ac["test_intent"].strip():
                issues.append(f"{ac['id']}: criterion and test intent must both be filled.")
    return issues


def make_handoff(project: dict, snapshot: dict, freshness: dict) -> dict:
    issues = readiness(project, snapshot)
    if freshness["status"] == "changed":
        issues.append("Provider sources changed. Refresh the snapshot and review the affected requirements first.")
    if issues:
        raise ValueError("\n".join(issues))
    revision = project["baseline_revision"] + 1
    handoff = {"contract_version": SCHEMA, "phase": "requirement", "handoff_status": "offered",
               "consumer": "design", "consumer_acceptance": "pending", "project_id": project["project_id"],
               "project_name": project["name"], "baseline_id": f"REQ-{project['project_id']}", "revision": revision,
               "created_at_utc": utc_now(), "board_id": project["board_id"], "constraints": copy.deepcopy(project["constraints"]),
               "stories": copy.deepcopy(project["stories"]), "capability_snapshot": {
                   k: snapshot[k] for k in ("snapshot_id", "captured_at_utc", "fingerprint", "provider_revision")},
               "source_freshness": freshness, "readiness": "not_probed",
               "design_checks": ["Review requirement meaning, feasibility and measurable acceptance criteria.",
                                 "Validate recipe composition, interfaces and exact configuration.",
                                 "Refresh current tools/hardware readiness before execution."]}
    if freshness["status"] == "unavailable":
        handoff["design_checks"].insert(0, "Provider source is unavailable here; verify the pinned snapshot against the actual provider before accepting.")
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "requirements-handoff.schema.json"
    jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(handoff)
    return handoff


def handoff_markdown(value: dict) -> str:
    lines = [f"# Requirement handoff: {value['project_name']}", "", f"Baseline: `{value['baseline_id']}` revision **{value['revision']}**", "",
             f"Created UTC: {value['created_at_utc']}", "", "Status: **offered to Design; consumer acceptance pending**", "",
             f"Target board: `{value['board_id']}`", "", f"Capability snapshot: `{value['capability_snapshot']['snapshot_id']}`", "",
             f"Source freshness at export: **{value['source_freshness']['status']}**. Bench readiness: **not probed**.", "",
             "## Constraints", ""]
    lines += [f"- {x}" for x in value["constraints"]] or ["No additional constraints recorded."]
    for s in value["stories"]:
        lines += ["", f"## {s['id']}: {s['title']}", "", f"Story revision: {s['revision']}", "",
                  f"As a **{s['role']}**, I want to **{s['want']}**, so that **{s['benefit']}**.", "",
                  "### Acceptance criteria and test intent", ""]
        for ac in s["acceptance_criteria"]:
            lines += [f"- **{ac['id']}**: {ac['text']}", f"  - Test intent: {ac['test_intent']}",
                      f"  - Requires hardware: {ac['requires_hardware']}"]
        lines += ["", f"Feasibility: **{s['feasibility']}** — {s['feasibility_reason']}", "",
                  "Capability references: " + ", ".join(f"`{r}`" for r in s["capability_refs"]), "",
                  "Source turns: " + (", ".join(s["source_turn_ids"]) or "manual editor")]
    lines += ["", "## Checks required from Design", ""] + [f"- {x}" for x in value["design_checks"]]
    return "\n".join(lines) + "\n"


def handoff_bundle(value: dict, snapshot: dict) -> bytes:
    files = {"requirements.json": json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"),
             "requirements.md": handoff_markdown(value).encode("utf-8"),
             "capability_snapshot.json": json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"),
             "capability_snapshot.md": render_markdown(snapshot).encode("utf-8"),
             "requirements-handoff.schema.json": (Path(__file__).resolve().parents[1] / "schemas/requirements-handoff.schema.json").read_bytes(),
             "README.md": ("# Requirement to Design handoff\n\n"
                           "Check manifest.json hashes, validate requirements.json with the bundled schema, and inspect requirements.md and the pinned capability snapshot.\n\n"
                           "This is an offered requirements baseline. Design acceptance is pending. Schema validity does not prove engineering feasibility or hardware behavior.\n\n"
                           "Design must preserve the exact baseline/snapshot references, resolve blockers, map interfaces and recipes/configuration, and return findings through change requests.\n").encode("utf-8")}
    manifest = {"created_at_utc": value["created_at_utc"], "baseline_id": value["baseline_id"], "revision": value["revision"],
                "sha256": {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}}
    files["manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def store_handoff(project: dict, value: dict, snapshot: dict, directory: Path | None = None) -> bytes:
    data = handoff_bundle(value, snapshot)
    folder = project_file(project["project_id"], directory).parent / "handoffs"
    target = folder / f"requirements-r{value['revision']:03d}.zip"
    updated = copy.deepcopy(project)
    updated["baseline_revision"] = value["revision"]
    updated["handoffs"].append({"revision": value["revision"], "created_at_utc": value["created_at_utc"], "file": target.name})
    save_project(updated, directory, artifact=(target, data))
    project.update(updated)
    return data


def apply_proposal(project: dict, proposal: dict, snapshot: dict) -> dict:
    if proposal.get("snapshot_id", snapshot["snapshot_id"]) != project["snapshot_id"] or proposal.get("board_id", project["board_id"]) != project["board_id"]:
        raise ValueError("Proposal belongs to an older snapshot/target context. Ask for a new proposal.")
    if proposal["operation"] == "update":
        story = next((s for s in project["stories"] if s["id"] == proposal["story_id"]), None)
        if not story or story["revision"] != proposal["base_revision"]:
            raise ValueError("Proposal is stale; the story changed after the model saw it.")
    else:
        story = None
    valid = capability_options(snapshot, project["board_id"])
    if any(ref not in valid for ref in proposal.get("capability_refs", [])):
        raise ValueError("Model proposed an unknown capability reference; edit the draft manually or ask again.")
    if story is None:
        story = add_story(project)
    values = {**proposal, "reviewed": False}
    values["source_turn_ids"] = list(dict.fromkeys(story["source_turn_ids"] + proposal.get("source_turn_ids", [])))
    # An update can preserve explicit AC IDs; new model criteria receive new IDs.
    update_story(story, values)
    story["origin"] = "llm_proposal"
    return story
