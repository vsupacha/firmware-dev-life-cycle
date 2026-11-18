"""Stages the manager runs itself, because no provider script does exactly this for ONE app.

    python builtin.py delete_app <app_dir> <workspace> <marker> [--yes]

delete_app removes one app folder on this PC (the provider clean.sh scripts work on the whole apps
workspace, which is too wide for a per-app run). It follows the provider rules: without --yes it only
lists and prints "ACTION: APPROVE ..." with exit 10; it deletes only a folder that is a direct child
of the apps workspace and holds the skill's marker file (so it was made by new_app). The board is
not touched. Gate: "DELETE: done (...)".
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path


def fail(text: str) -> int:
    print(f"DELETE: FAIL ({text})")
    return 1


def delete_app(app_dir: str, workspace: str, marker: str, yes: bool) -> int:
    if not app_dir or not workspace:
        return fail("no app folder or apps workspace is known for this run")
    folder, ws = Path(app_dir), Path(workspace)
    if not folder.exists():
        print(f"DELETE: done (nothing to delete: {folder.as_posix()} does not exist)")
        return 0
    if folder.is_symlink() or not folder.is_dir():
        return fail(f"{folder.as_posix()} is not a plain folder")
    if folder.resolve().parent != ws.resolve() or folder.resolve() == ws.resolve():
        return fail(f"{folder.as_posix()} is not directly inside the apps workspace {ws.as_posix()}")
    if not (folder / marker).is_file():
        return fail(f"{folder.as_posix()} has no {marker}: not an app made by this skill, left alone")
    files = size = 0
    for root, _, names in os.walk(folder):
        for name in names:
            files += 1
            try:
                size += (Path(root) / name).stat().st_size
            except OSError:
                pass
    print(f"App folder: {folder.as_posix()}")
    print("Contains:   " + ", ".join(sorted(p.name + ("/" if p.is_dir() else "") for p in folder.iterdir())))
    print(f"Size:       {files} files, {size / 1e6:.1f} MB (sources, tests, logs and build outputs)")
    print("The board is not changed: it keeps the image that was flashed.")
    if not yes:
        print(f"ACTION: APPROVE delete the app folder {folder.as_posix()} ({files} files, {size / 1e6:.1f} MB) on this PC; "
              "it cannot be undone")
        return 10

    def writable(function, path, _):
        os.chmod(path, stat.S_IWRITE)
        function(path)

    shutil.rmtree(folder, onerror=writable)
    if folder.exists():
        return fail(f"{folder.as_posix()} still exists (a file is open in another program?)")
    print(f"DELETE: done ({folder.as_posix()} removed)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[0] == "delete_app":
        return delete_app(argv[1], argv[2], argv[3], "--yes" in argv[4:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
