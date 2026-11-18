"""Read-only provider inspection, immutable snapshots and content drift detection."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER = ROOT.parent / "automated-firmware-skills"
SNAPSHOT_DIR = ROOT / "docs" / "capabilities"
OPERATIONS = {
    "check_tools": "check_tools.sh", "create": "new_app.sh", "regenerate": "regen.sh",
    "build": "build.sh", "discover": "discover.sh", "flash": "flash.sh",
    "serial_test": "serial_test.py", "unit_test": "unit_test.sh", "debug": "debug.sh",
    "runtime_inspection": "msh_status.py", "recipe_check": "recipe.sh",
    "tool_updates": "update_tools.sh", "open_ide": "open_ide.sh",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files(provider: Path) -> list[Path]:
    """Allowlisted engineering sources only; never read apps, benches or private handoffs."""
    found: set[Path] = set()
    for name in ("README.md", "README_TH.md", "CHANGELOG.md", "CONTRIBUTING.md", "milestones.env", ".claude-plugin/marketplace.json"):
        if (provider / name).is_file():
            found.add(provider / name)
    for folder in ("docs", "boards", "skills", "lib", "tools"):
        for path in (provider / folder).rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".json", ".env", ".sh", ".py", ".txt", ".c", ".h", ".cpp", ".hpp", ".ioc", ".xml", ".ini", ".toml"}:
                continue
            relative = path.relative_to(provider)
            if any(part.startswith(".") or part in {"__pycache__", "reports", "logs"} for part in relative.parts):
                continue
            if path.stat().st_size <= 1_000_000:
                found.add(path)
    return sorted(found, key=lambda p: p.relative_to(provider).as_posix())


def git_revision(provider: Path) -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=provider, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def fingerprint(records: list[dict]) -> str:
    payload = "\n".join(f"{r['path']}:{r['sha256']}" for r in records)
    return digest(payload.encode("utf-8"))


def capture(provider: Path) -> dict:
    provider = Path(provider).resolve()
    if not (provider / "boards/index.json").is_file():
        raise ValueError("Provider must contain boards/index.json")
    head = git_revision(provider)
    paths = source_files(provider)
    blobs = {p.relative_to(provider).as_posix(): p.read_bytes() for p in paths}
    records = [{"path": p.relative_to(provider).as_posix(), "sha256": digest(blobs[p.relative_to(provider).as_posix()]),
                "modified_at_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")}
               for p in paths]
    # Reject a mixed capture when another session changes a source during acquisition.
    if paths != source_files(provider) or head != git_revision(provider) or any(p.read_bytes() != blobs[p.relative_to(provider).as_posix()] for p in paths):
        raise ValueError("Provider changed during capture; retry after its current write completes.")
    read = lambda name: blobs[name].decode("utf-8-sig")
    index = json.loads(read("boards/index.json"))
    boards = index["boards"]
    skills = []
    for name in sorted(k for k in blobs if re.fullmatch(r"skills/[^/]+/SKILL\.md", k)):
        skill_id = name.split("/")[1]
        board_profiles = [{"board_id": b["id"], "name": b.get("name", b["id"]), **b["profiles"][skill_id]}
                          for b in boards if skill_id in b.get("profiles", {})]
        description = re.search(r"(?m)^description:\s*(.+)", read(name))
        templates = sorted({k.split("/")[3] for k in blobs if k.startswith(f"skills/{skill_id}/templates/")
                            and len(k.split("/")) > 4 and not k.split("/")[3].startswith("_")})
        skills.append({"id": skill_id, "kind": "board" if board_profiles else "tool",
                       "description": description.group(1).strip() if description else "",
                       "source": name, "boards": board_profiles, "templates": templates,
                       "operations": {op: f"skills/{skill_id}/scripts/{script}" in blobs for op, script in OPERATIONS.items()}})
    recipes = []
    for name in blobs:
        if re.fullmatch(r"skills/[^/]+/recipes/drivers/[^/]+\.json", name):
            recipes.append({"skill_id": name.split("/")[1], "source": name, **json.loads(read(name))})
    milestone_text = read("milestones.env") if "milestones.env" in blobs else ""
    active = re.search(r'(?m)^ACTIVE_MILESTONES="([^"]*)"', milestone_text)
    captured = utc_now()
    fp = fingerprint(records)
    notes = []
    for name in ("docs/milestones.md", "docs/workflow.md", "skills/scons-rtthread-visionboard/recipes/README.md"):
        if name in blobs:
            notes.append({"path": name, "content": read(name)})
    return {"schema_version": 1, "snapshot_id": f"CAP-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{fp[:8]}",
            "captured_at_utc": captured, "captured_at_bangkok": datetime.fromisoformat(captured).astimezone(timezone(timedelta(hours=7))).isoformat(),
            "provider": "automated-firmware-skills", "provider_revision": head,
            "fingerprint": fp, "active_milestones": active.group(1).split() if active else [],
            "readiness": "not_probed", "evidence_policy": "Imported provider claims, not independently reverified. Script presence is not runtime proof.",
            "skills": skills, "boards": boards, "driver_recipes": recipes, "sources": records, "source_notes": notes}


def render_markdown(snapshot: dict) -> str:
    board_skills = [s for s in snapshot["skills"] if s["kind"] == "board"]
    lines = ["# Firmware capability snapshot", "", f"Snapshot: `{snapshot['snapshot_id']}`", "",
             f"Captured UTC: **{snapshot['captured_at_utc']}**", "", f"Captured Bangkok: **{snapshot['captured_at_bangkok']}**", "",
             f"Provider revision: `{snapshot['provider_revision']}`", "", f"Content fingerprint: `{snapshot['fingerprint']}`", "",
             f"Active provider milestones: {', '.join(snapshot['active_milestones'])}", "",
             "Immutable import of provider documents, catalog data and script-presence facts. No firmware was built, flashed or tested during import. Current tools/hardware readiness was not probed.", "",
             "File content hashes, rather than document dates or Git HEAD alone, determine drift. Uncommitted changes are included. A changed source invalidates freshness, not the historical snapshot. Refresh creates a new snapshot; existing requirement baselines keep their original reference.", "",
             "## Board skills and imported evidence", "", "| Skill | Board | Profile level / date | Templates and evidence | Operations present |", "| --- | --- | --- | --- | --- |"]
    for s in board_skills:
        for b in s["boards"]:
            templates = "; ".join(f"{k}: {v}" for k, v in b.get("templates", {}).items())
            operations = ", ".join(k for k, present in s["operations"].items() if present)
            lines.append(f"| {s['id']} | {b['board_id']} | {b.get('level', 'unknown')} / {b.get('date', '?')} | {templates} | {operations} |")
    lines += ["", "## Shared tool skills", ""]
    lines += [f"- **{s['id']}**: {s['description']}" for s in snapshot["skills"] if s["kind"] == "tool"]
    lines += ["", "## Driver recipes", "", "Recipe status is imported literally. Prepared/checked/built/tested are separate facts; read the dated source notes for qualified or partial evidence. A successful recipe check does not apply FSP/port/package changes or prove physical behavior.", "",
              "| Skill / recipe | Declared status | Dependencies | Resources | Runtime expectations |", "| --- | --- | --- | --- | --- |"]
    for r in snapshot["driver_recipes"]:
        runtime = json.dumps(r.get("msh", {}), ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| {r['skill_id']} / {r['recipe']} | {r.get('status', '?')} | {', '.join(r.get('requires', [])) or '-'} | {', '.join(r.get('peripherals', [])) or '-'} | {runtime} |")
    lines += ["", "## Integration limits", "", "- The catalog is suitable for requirement feasibility assessment, not automatic hardware acceptance.",
              "- Provider milestones still gate execution. The importer never enables them.",
              "- Script presence does not imply supported options, available tools or a completed board run.",
              "- Recipe checks may need an existing app/configuration. They are distinct from initial catalog discovery.",
              "- Lifecycle adapters still need structured generation requests, complete source/candidate provenance and per-case test results.",
              "- Partial/filtered/skipped provider tests cannot establish full requirement acceptance.", "", "## Imported source notes", ""]
    for note in snapshot["source_notes"]:
        fence = "`" * max(4, 1 + max((len(x) for x in re.findall(r"`+", note["content"])), default=0))
        lines += [f"### {note['path']}", "", "<details>", "<summary>Source text at capture time</summary>", "", fence + "text", note["content"].rstrip(), fence, "", "</details>", ""]
    lines += ["## Source document timestamps and hashes", "", "All allowlisted source hashes are in the JSON sidecar. Document timestamps below are filesystem metadata; they do not replace content comparisons.", "",
              "| Source Markdown | Modified UTC | SHA256 |", "| --- | --- | --- |"]
    lines += [f"| {s['path']} | {s['modified_at_utc']} | `{s['sha256']}` |" for s in snapshot["sources"] if s["path"].endswith(".md")]
    return "\n".join(lines) + "\n"


def write_snapshot(snapshot: dict, directory: Path = SNAPSHOT_DIR) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = snapshot["snapshot_id"]
    if not re.fullmatch(r"CAP-[A-Za-z0-9-]+", name):
        raise ValueError("Invalid snapshot ID")
    json_path, md_path = directory / f"{name}.json", directory / f"{name}.md"
    if json_path.exists() or md_path.exists():
        raise ValueError("Snapshot exists; immutable snapshots cannot be overwritten.")
    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(render_markdown(snapshot), encoding="utf-8", newline="\n")
    return json_path, md_path


def list_snapshots(directory: Path = SNAPSHOT_DIR) -> list[Path]:
    return sorted(Path(directory).glob("CAP-*.json"), reverse=True)


def load_snapshot(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or fingerprint(value["sources"]) != value["fingerprint"]:
        raise ValueError("Invalid capability snapshot manifest")
    return value


def compare(snapshot: dict, provider: Path) -> dict:
    provider = Path(provider)
    if not (provider / "boards/index.json").is_file():
        return {"status": "unavailable", "checked_at_utc": utc_now(), "changed": [], "added": [], "removed": []}
    old = {r["path"]: r["sha256"] for r in snapshot["sources"]}
    current = {p.relative_to(provider).as_posix(): digest(p.read_bytes()) for p in source_files(provider)}
    changed = sorted(k for k in old.keys() & current.keys() if old[k] != current[k])
    added, removed = sorted(current.keys() - old.keys()), sorted(old.keys() - current.keys())
    head = git_revision(provider)
    return {"status": "changed" if changed or added or removed or head != snapshot["provider_revision"] else "current",
            "checked_at_utc": utc_now(), "provider_revision": head, "changed": changed, "added": added, "removed": removed}


def capability_options(snapshot: dict, board_id: str = "") -> dict[str, str]:
    options = {}
    for skill in snapshot["skills"]:
        if skill["kind"] != "board" or (board_id and not any(b["board_id"] == board_id for b in skill["boards"])):
            continue
        for template in skill["templates"]:
            key = f"template:{skill['id']}/{template}"
            options[key] = f"{template} · {skill['id']}"
    for recipe in snapshot["driver_recipes"]:
        if not board_id or recipe.get("board") == board_id:
            key = f"driver:{recipe['skill_id']}/{recipe['recipe']}"
            options[key] = f"{recipe['recipe']} ({recipe.get('status', '?')}) · {recipe['skill_id']}"
    return options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["refresh", "check"])
    parser.add_argument("--provider", type=Path, default=DEFAULT_PROVIDER)
    parser.add_argument("--directory", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "refresh":
        paths = write_snapshot(capture(args.provider), args.directory)
        print("\n".join(str(p) for p in paths))
    else:
        candidates = list_snapshots(args.directory)
        path = args.snapshot or (candidates[0] if candidates else None)
        if not path:
            parser.error("No snapshot found; run refresh first")
        result = compare(load_snapshot(path), args.provider)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["status"] == "current" else 2)


if __name__ == "__main__":
    main()
