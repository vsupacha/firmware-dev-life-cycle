"""Stage runner: executes the provider scripts of one run, in its own process.

    python -m runstudio.runner <run_id>          run stages until one stops (fail / waiting / done)
    python -m runstudio.runner <run_id> --one    run only the next stage

Rules (the UI cannot override them):
  - a stage is PASSED only when its script exits 0 and prints a line matching the manifest gate;
  - exit 10 or an "ACTION:" line means WAITING: nothing more runs until the developer acts;
  - the approval flag (e.g. --yes) is added only when a recorded approval exists for that stage,
    the approval names the same image hash as now, and it is used once;
  - a stage that was interrupted is FAILED, never passed.
"""
from __future__ import annotations

import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import store

ACTION_RE = re.compile(r"^ACTION:\s*([A-Z_]+)\s*(.*)$")
GATE_LINE_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,20}: \S")
STAMP_RE = re.compile(r"^\[\s*\d+\.\d+\]\s*")


def classify(spec: dict, exit_code: int, lines: list[str]) -> tuple[str, str, dict | None, str]:
    """(state, gate line, action, note) from the script's exit code and output."""
    lines = [STAMP_RE.sub("", line.strip()) for line in lines]   # fwtest prefixes its lines with "[   2.937] "
    actions = [m for m in (ACTION_RE.match(line.strip()) for line in lines) if m]
    gate_re = re.compile(spec["gate"])
    gate = next((line.strip() for line in reversed(lines) if gate_re.search(line.strip())), "")
    last_gate = next((line.strip() for line in reversed(lines)
                      if GATE_LINE_RE.match(line.strip()) and not line.startswith("ACTION:")), "")
    if exit_code == 10 or (actions and exit_code != 0):
        if actions:
            action = {"kind": actions[-1].group(1), "text": actions[-1].group(0)}
        else:
            action = {"kind": "UNKNOWN", "text": "exit code 10 without an ACTION: line - read the log"}
        return "waiting", last_gate, action, ""
    if exit_code == 0:
        if gate:
            return "passed", gate, None, ""
        return "failed", last_gate, None, f"exit 0 but no gate line matching /{spec['gate']}/"
    if exit_code == spec.get("warn_exit"):
        return "warnings", gate or last_gate, None, f"exit {exit_code}: passed with warnings"
    return "failed", last_gate, None, f"exit {exit_code}"


def kill_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        process.kill()


def run_stage(run: dict, record: dict, approved: bool, beat) -> None:
    spec = store.stage_spec(run, record["id"])
    argv = store.command(run, record["id"], approved)
    record["attempts"] += 1
    index = [s["id"] for s in run["stages"]].index(record["id"]) + 1
    log_name = f"{index:02d}-{record['id']}-a{record['attempts']}.log"
    log_path = store.run_dir(run["run_id"]) / "logs" / log_name
    record.update(state="running", started=store.now(), ended="", seconds=None, gate="", exit=None, action=None,
                  note="", log=log_name)
    store.save_run(run)
    shown = [a if a else '""' for a in argv]
    store.append_event(run["run_id"], {"event": "stage_started", "stage": record["id"], "attempt": record["attempts"],
                                       "approved": approved, "command": " ".join(shown)})
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    repo = store.provider_repo(store.load_manifests()[run["provider"]])
    started, lines, cancelled, timed_out = time.monotonic(), [], False, False
    cancel_file = store.run_dir(run["run_id"]) / "cancel.request"
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        log.write(f"$ {' '.join(shown)}\n")
        log.flush()
        try:
            process = subprocess.Popen(argv, cwd=str(repo), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, env=env, text=True, encoding="utf-8", errors="replace",
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError as exc:
            log.write(f"could not start: {exc}\n")
            record.update(state="failed", ended=store.now(), seconds=0, note=f"could not start: {exc}")
            store.save_run(run)
            store.append_event(run["run_id"], {"event": "stage_ended", "stage": record["id"], "state": "failed"})
            return
        pipe: queue.Queue = queue.Queue()

        def pump():
            for text in process.stdout:
                pipe.put(text)
            pipe.put(None)

        threading.Thread(target=pump, daemon=True).start()
        open_pipe = True
        while open_pipe:
            try:
                text = pipe.get(timeout=0.5)
            except queue.Empty:
                text = ""
            if text is None:
                open_pipe = False
            elif text:
                lines.append(text.rstrip("\r\n"))
                log.write(text if text.endswith("\n") else text + "\n")
                log.flush()
            beat()
            if cancel_file.exists():
                cancelled = True
                kill_tree(process)
            elif time.monotonic() - started > spec.get("timeout_s", 900):
                timed_out = True
                kill_tree(process)
        exit_code = process.wait()
        log.write(f"[exit {exit_code}]\n")
    seconds = round(time.monotonic() - started, 1)
    if cancelled:
        cancel_file.unlink(missing_ok=True)
        state, gate, action, note = "cancelled", "", None, "cancelled by the developer; the stage did not finish"
    elif timed_out:
        state, gate, action, note = "failed", "", None, f"timeout after {spec.get('timeout_s', 900)} s; the process was stopped"
    else:
        state, gate, action, note = classify(spec, exit_code, lines)
    record.update(state=state, gate=gate, action=action, note=note, exit=exit_code, ended=store.now(), seconds=seconds)
    store.save_run(run)
    store.append_event(run["run_id"], {"event": "stage_ended", "stage": record["id"], "state": state, "exit": exit_code,
                                       "gate": gate, "seconds": seconds, "action": action["text"] if action else ""})


def approval_valid(run: dict, record: dict) -> tuple[bool, str]:
    approval = run["approvals"].get(record["id"])
    if not approval:
        return False, ""
    bound = store.bound_file(run, record["id"])
    current = store.file_sha256(bound) if bound else ""
    if approval["sha256"] != current or approval["board"] != run["board"]:
        return False, "the image or board changed after the approval; approve again"
    return True, ""


def serve(run_id: str, one: bool = False) -> int:
    folder = store.run_dir(run_id)
    lock = folder / "runner.lock"
    if lock.exists() and store.runner_alive(run_id) and lock.read_text(encoding="utf-8").strip() != str(os.getpid()):
        if time.time() - lock.stat().st_mtime > 2:          # another live runner owns this run
            print("another runner is active for this run")
            return 3
    lock.write_text(str(os.getpid()), encoding="utf-8")
    heartbeat = store.heartbeat_file(run_id)

    def beat():
        heartbeat.write_text(store.now(), encoding="utf-8")

    beat()
    (folder / "cancel.request").unlink(missing_ok=True)
    try:
        while True:
            run = store.load_run(run_id)
            record = store.next_stage(run)
            if record is None:
                store.append_event(run_id, {"event": "run_complete"})
                return 0
            approved = False
            if record["state"] == "waiting":
                approved, note = approval_valid(run, record)
                if not approved:
                    if note:
                        run["approvals"].pop(record["id"], None)
                        record["note"] = note
                        store.save_run(run)
                    return 0
            elif record["state"] != "queued":
                return 0                                       # failed / warnings / cancelled: the developer decides
            if approved:
                run["approvals"].pop(record["id"])             # one approval = one execution
            run_stage(run, record, approved, beat)
            if one or record["state"] != "passed":
                return 0
    finally:
        heartbeat.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument("--one", action="store_true", help="run only the next stage")
    args = parser.parse_args()
    return serve(args.run_id, args.one)


if __name__ == "__main__":
    sys.exit(main())
