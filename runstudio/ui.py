"""Shared page body of the Auto and IDE pages: execute and watch the provider stages of one flow.

The page only reads and writes run records (runstudio.store); stages execute in the detached
runner process (runstudio.runner), so a run goes on when the browser closes. A stage shows
"passed" only from its script's exit code and gate line.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from runstudio import store

TEXT = {
    "auto": {"name": "Auto", "caption": "AUTO · CREATE, BUILD, FLASH, TEST BY SCRIPT", "prefix": "ui",
             "title": "Auto: run the scripted firmware workflow",
             "intro": "Choose platform, board and template on the left, then **Create run**. Nothing is executed until you press a "
                      "Run button; steps that change a board or delete files stop and ask first.",
             "done": "All stages ended."},
    "ide": {"name": "IDE", "caption": "IDE · CREATE THE APP, THEN OPEN IT IN THE IDE", "prefix": "ide",
            "title": "IDE: create an app and open it in the IDE",
            "intro": "Choose platform, board and template on the left, then **Create run**. The flow checks the tools, creates the "
                     "app and opens it in the skill's IDE; build, flash and debug are then yours, with the IDE's own buttons.",
            "done": "The app is open in the IDE: edit, build, flash and debug there."},
}

COLORS = {"passed": ("#e6f4ea", "#1e6b34"), "failed": ("#fdecea", "#9b2c2c"), "waiting": ("#fff4d6", "#8a5a00"),
          "warnings": ("#fff4d6", "#8a5a00"), "running": ("#e6f1fb", "#0c447c"), "queued": ("#f1f3f5", "#55606b"),
          "skipped": ("#f1f3f5", "#55606b"), "cancelled": ("#fdecea", "#9b2c2c"), "done": ("#e6f4ea", "#1e6b34"),
          "idle": ("#f1f3f5", "#55606b")}
ICONS = {"passed": "✓", "failed": "✕", "waiting": "‖", "warnings": "!", "running": "…", "queued": "·",
         "skipped": "↷", "cancelled": "■"}


def pill(state: str) -> str:
    background, color = COLORS.get(state, COLORS["queued"])
    return f'<span class="fw-pill" style="background:{background};color:{color}">{state}</span>'


def act(function, *args):
    try:
        function(*args)
    except (ValueError, OSError) as exc:
        st.session_state.run_error = str(exc)


def render(flow: str) -> None:
    text, rid = TEXT[flow], f"run_id_{flow}"
    st.set_page_config(page_title=f"Firmware · {text['name']}", page_icon="◈", layout="wide")
    st.markdown("""<style>
    .block-container {padding-top:1.4rem;max-width:1500px}
    div.stButton > button {border-radius:8px}
    .fw-stage {border:1px solid #dce6eb;border-radius:10px;padding:8px 10px;min-height:86px}
    .fw-stage.current {border:2px solid #b7791f}
    .fw-stage small {color:#6b7785}
    .fw-pill {font-size:12px;padding:1px 8px;border-radius:8px}
    </style>""", unsafe_allow_html=True)

    try:
        manifests = store.load_manifests()
    except (ValueError, OSError) as exc:
        st.error(f"Provider manifests could not be read: {exc}")
        st.stop()

    # ---- sidebar: target and runs --------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### ◈ Firmware lifecycle")
        st.caption(text["caption"])
        st.markdown("**New run**")
        provider_id = st.selectbox("Platform", list(manifests), format_func=lambda k: manifests[k]["label"])
        manifest = manifests[provider_id]
        boards = [t["board"] for t in manifest["targets"]]
        board = st.selectbox("Board", boards, format_func=lambda b: store.target_of(manifest, b).get("label", b))
        target = store.target_of(manifest, board)
        template = st.selectbox("Template", target["templates"])
        app = st.text_input("App name", value=f"{text['prefix']}-{template[:2]}-{board.split('-')[-1][:6]}".lower(),
                            help="2-20 characters: lower-case letters, digits, '-'. The app folder is created in this PC's apps workspace.")
        repo = store.provider_repo(manifest)
        workspace = store.workspace()
        st.caption(f"Skill: `{target['skill']}`")
        st.caption("Stages: " + " → ".join(store.flow_stages(manifest, flow)))
        st.caption(f"Apps workspace: `{workspace}`" if workspace else "Apps workspace: not chosen on this PC (the create stage will ask)")
        if not repo.is_dir():
            st.warning(f"Provider folder not found: {repo}")
        if st.button("Create run", type="primary", width="stretch", disabled=not repo.is_dir()):
            try:
                st.session_state[rid] = store.new_run(provider_id, board, template, app.strip(), flow)["run_id"]
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        st.divider()
        st.markdown("**Runs**")
        runs = store.list_runs(flow)
        if runs:
            ids = [r["run_id"] for r in runs]
            if st.session_state.get(rid) not in ids:
                st.session_state[rid] = ids[0]
            labels = {r["run_id"]: f"{r['board_label']} · {r['template']} · {r['app']} — {store.summary(r)}" for r in runs}
            st.radio("Runs", ids, key=rid, format_func=lambda k: labels[k], label_visibility="collapsed")
        else:
            st.caption("No run yet. Choose a target above and create one.")

    if not st.session_state.get(rid):
        st.title(text["title"])
        st.info(text["intro"])
        st.stop()


    @st.fragment(run_every=1)
    def live(run_id: str):
        run = store.load_run(run_id)
        if run is None:
            st.error("This run's record could not be read.")
            return
        store.recover(run)
        alive = store.runner_alive(run_id)
        overall = store.summary(run)
        head, meta = st.columns([3, 2])
        head.markdown(f"### {run['board_label']} · {run['template']} &nbsp; {pill(overall)}", unsafe_allow_html=True)
        head.caption(f"{run['provider_label']} · skill `{run['skill']}` · app `{run['app']}` → `{run['app_dir'] or 'workspace not chosen'}`")
        meta.markdown(f"Evidence reached: **{store.evidence(run)}**")
        meta.caption("created ≠ built ≠ flashed ≠ tested ≠ seen by a person. Run " + run_id)
        if st.session_state.get("run_error"):
            st.error(st.session_state.pop("run_error"))

        current = store.next_stage(run)
        columns = st.columns(len(run["stages"]))
        for column, record in zip(columns, run["stages"]):
            background, color = COLORS[record["state"]]
            timing = f"{record['seconds']} s" if record["seconds"] is not None else "&nbsp;"
            mark = " current" if current and record["id"] == current["id"] and record["state"] != "queued" else ""
            column.markdown(
                f'<div class="fw-stage{mark}"><small>{record["label"]}</small><br>'
                f'<span style="color:{color};font-weight:600">{ICONS[record["state"]]} {record["state"]}</span><br>'
                f'<small>{timing}</small></div>', unsafe_allow_html=True)

        # ---- controls -------------------------------------------------------------------------------
        b1, b2, b3, _ = st.columns([1.2, 1.4, 1, 3])
        can_run = bool(current) and not alive and current["state"] == "queued"
        if b1.button("Run next stage", disabled=not can_run, width="stretch", key=f"one-{run_id}"):
            act(store.start_runner, run_id, True)
            st.rerun()
        if b2.button("Run until a stop", disabled=not can_run, width="stretch", key=f"all-{run_id}",
                     help="Runs stage after stage and stops at the first failure or at anything that needs you."):
            act(store.start_runner, run_id, False)
            st.rerun()
        if b3.button("Cancel", disabled=not alive, width="stretch", key=f"cancel-{run_id}"):
            act(store.request_cancel, run_id)

        # ---- action panel ---------------------------------------------------------------------------
        if current and not alive and current["state"] in ("waiting", "failed", "warnings", "cancelled"):
            spec = store.stage_spec(run, current["id"])
            action = current.get("action") or {}
            kind = action.get("kind", "")
            with st.container(border=True):
                if current["state"] == "waiting":
                    st.markdown(f"**Stage `{current['label']}` needs you: {kind or 'action'}**")
                    st.code(action.get("text", ""), language=None, wrap_lines=True)
                    if current.get("note"):
                        st.caption(current["note"])
                    if kind == "APPROVE" and spec.get("approve_flag"):
                        bound = store.bound_file(run, current["id"])
                        if bound:
                            st.caption(f"Image: `{bound.name}` · sha256 `{store.file_sha256(bound)[:16]}…` · board `{run['board']}`")
                        if spec.get("deletes_app"):
                            st.caption("This deletes the app folder on this PC (sources, tests, logs, build outputs). "
                                       "The board is not changed. The approval is used once.")
                        if spec.get("changes_board"):
                            st.caption("This step changes the board. The approval is for this image and this board only, and is used once.")
                        c1, c2, c3 = st.columns([1.6, 1, 4])
                        if c1.button(f"Approve and run {current['label']}", type="primary", key=f"approve-{run_id}"):
                            act(store.approve, run, current["id"])
                            act(store.start_runner, run_id, True)
                            st.rerun()
                        if c2.button("Skip stage", key=f"skip-{run_id}"):
                            act(store.skip, run, current["id"])
                            st.rerun()
                    else:
                        st.caption("Do what the line says (for example plug the board or run the named set-up step), then retry the stage.")
                        c1, c2, _ = st.columns([1.2, 1, 4])
                        if c1.button("Retry stage", type="primary", key=f"retry-{run_id}"):
                            act(store.retry, run, current["id"])
                            act(store.start_runner, run_id, True)
                            st.rerun()
                        if c2.button("Skip stage", key=f"skip-{run_id}"):
                            act(store.skip, run, current["id"])
                            st.rerun()
                else:
                    st.markdown(f"**Stage `{current['label']}` {current['state']}** — {current.get('note') or 'see the log'}")
                    if current.get("gate"):
                        st.code(current["gate"], language=None, wrap_lines=True)
                    c1, c2, _ = st.columns([1.2, 1, 4])
                    if c1.button("Retry stage", type="primary", key=f"retry-{run_id}"):
                        act(store.retry, run, current["id"])
                        act(store.start_runner, run_id, True)
                        st.rerun()
                    if c2.button("Skip stage", key=f"skip-{run_id}", help="A skipped stage stays visible and adds no evidence."):
                        act(store.skip, run, current["id"])
                        st.rerun()
        elif overall == "done":
            st.success(text["done"] + f" Evidence reached: {store.evidence(run)}. Skipped stages add no evidence.")

        # ---- log + artifacts ------------------------------------------------------------------------
        log_column, artifact_column = st.columns([3, 2])
        with log_column:
            with_logs = [s for s in run["stages"] if s["log"]]
            st.markdown("**Log**")
            if not with_logs:
                st.caption("No stage has run yet.")
            else:
                ids = [s["id"] for s in with_logs]
                running = next((s["id"] for s in with_logs if s["state"] == "running"), None)
                if running:
                    st.session_state[f"log-{run_id}"] = running          # follow the stage that is running
                elif st.session_state.get(f"log-{run_id}") not in ids:
                    st.session_state[f"log-{run_id}"] = ids[-1]
                chosen = st.radio("Stage", ids, key=f"log-{run_id}", horizontal=True, label_visibility="collapsed",
                                  format_func=lambda k: store.stage(run, k)["label"])
                record = store.stage(run, chosen)
                path = store.run_dir(run_id) / "logs" / record["log"]
                log_text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
                if record["gate"]:
                    st.markdown(f"Gate: `{record['gate']}` &nbsp; exit `{record['exit']}` &nbsp; attempt {record['attempts']}", unsafe_allow_html=True)
                lines = log_text.splitlines()
                st.code("\n".join(lines[-60:]) or "(no output yet)", language=None, wrap_lines=True)
                st.caption(f"{len(lines)} lines · showing the last 60 · {path}")
        with artifact_column:
            st.markdown("**Artifacts**")
            rows = store.artifacts(run)
            if rows:
                frame = pd.DataFrame([{"stage": r["stage"], "file": r["file"], "bytes": r["bytes"],
                                       "sha256": r["sha256"][:12], "modified": r["modified"]} for r in rows])
                st.dataframe(frame, hide_index=True, width="stretch", height=min(38 + 35 * len(rows), 360))
                st.caption(f"In `{run['app_dir']}`. Full hashes are in the files; raw stage logs are in the run folder.")
            else:
                st.caption("No artifact yet. They appear when the create and build stages have run.")
            with st.expander("History"):
                for event in reversed(store.events(run_id)[-40:]):
                    detail = " · ".join(str(event[k]) for k in ("stage", "state", "gate", "seconds") if event.get(k) not in (None, ""))
                    st.caption(f"{event['at']} · {event['event']}" + (f" · {detail}" if detail else ""))


    live(st.session_state[rid])
