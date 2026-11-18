"""Report differences between the lib/ copies of the skill repositories.

    python scripts/check_provider_libs.py [--all]

The skill repositories share conventions but no code: each has its own copy of lib/. A fix made in one copy
is easy to forget in the others. This lists every lib file that exists in more than one repository with
different content (line counts shown), so a person can decide whether the difference is wanted.
Read-only. Exit 0 = no differences, 2 = differences listed, 1 = no provider repository found.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def provider_repos() -> dict[str, Path]:
    repos = {}
    for path in sorted((ROOT / "providers").glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        repo = (ROOT / manifest["repo"]).resolve()
        if (repo / "lib").is_dir():
            repos[manifest["id"]] = repo
    return repos


def main() -> int:
    repos = provider_repos()
    if not repos:
        print("LIBS: no provider repository with a lib/ folder next to this project")
        return 1
    files: dict[str, dict[str, tuple[str, int]]] = {}
    for name, repo in repos.items():
        for path in sorted((repo / "lib").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                data = path.read_bytes().replace(b"\r\n", b"\n")
                files.setdefault(path.relative_to(repo).as_posix(), {})[name] = (hashlib.sha256(data).hexdigest()[:8], data.count(b"\n"))
    shared = {rel: held for rel, held in files.items() if len(held) > 1}
    different = {rel: held for rel, held in shared.items() if len({digest for digest, _ in held.values()}) > 1}
    for rel, held in sorted(different.items()):
        print(f"DIFF  {rel}: " + ", ".join(f"{name} {digest} ({lines} lines)" for name, (digest, lines) in held.items()))
    if "--all" in sys.argv:
        for rel, held in sorted(shared.items()):
            if rel not in different:
                print(f"same  {rel}: " + ", ".join(held))
    print(f"LIBS: {len(repos)} repositories, {len(shared)} shared files, {len(different)} differ")
    return 2 if different else 0


if __name__ == "__main__":
    sys.exit(main())
