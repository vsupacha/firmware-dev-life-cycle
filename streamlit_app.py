"""Run with: python -m streamlit run streamlit_app.py"""
from __future__ import annotations

import copy
import difflib
import json
import os
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from reqstudio import capabilities as cap
from reqstudio import contracts as contract
from reqstudio import llm
from reqstudio import bridge
from reqstudio import worker

st.set_page_config(page_title="Firmware · Requirements", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {padding-top:1.4rem;max-width:1500px}
h1,h2,h3 {letter-spacing:-.025em}
[data-testid="stSidebar"] {border-right:1px solid #dce6eb}
[data-testid="stMetric"] {background:#fff;border:1px solid #e2e8ee;border-radius:12px;padding:12px}
div.stButton > button {border-radius:8px}
</style>""", unsafe_allow_html=True)
if "next_story_choice" in st.session_state:
    st.session_state.story_choice = st.session_state.pop("next_story_choice")


def commit(mutator):
    updated = copy.deepcopy(st.session_state.project)
    mutator(updated)
    try:
        contract.save_project(updated)
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        st.stop()
    st.session_state.project = updated
    return updated


def activate_project(value):
    """Called before widget construction; keep URL, selector and data on one draft."""
    st.session_state.project = value
    st.session_state.workspace_choice = value["project_id"]
    st.query_params["project"] = value["project_id"]
    st.session_state.opened_request_project = value["project_id"]
    for key in ("story_choice", "next_story_choice", "bundle", "freshness", "agent_error"):
        st.session_state.pop(key, None)


def create_draft():
    value = contract.new_project(cap.load_snapshot(cap.list_snapshots()[0]))
    value["name"] = "Draft · " + value["project_id"][:8]
    contract.save_project(value)
    activate_project(value)


def select_draft():
    chosen = st.session_state.workspace_choice
    value = next(p for p in contract.load_projects() if p["project_id"] == chosen)
    activate_project(value)


def story_table(items, key):
    rows = []
    for item in items:
        identity = (item.get("story_id") or "ใหม่") if "operation" in item else item["id"]
        rows.append({"Story": identity + " · " + item.get("title", ""),
                     "As a": item.get("role", ""), "want to": item.get("want", ""),
                     "so that": item.get("benefit", ""),
                     "acceptance criteria": "\n".join(str(i) + ". " + ac["text"] for i, ac in enumerate(item.get("acceptance_criteria", []), 1)),
                     "ambiguity": "\n".join(item.get("open_questions", [])) or "ไม่มีคำถามค้างที่บันทึก"})
    st.dataframe(pd.DataFrame(rows, columns=["Story", "As a", "want to", "so that", "acceptance criteria", "ambiguity"]),
                 hide_index=True, width="stretch", row_height=180, key=key,
                 column_config={"Story": st.column_config.TextColumn(width=120),
                                "As a": st.column_config.TextColumn(width=95),
                                "want to": st.column_config.TextColumn(width=160),
                                "so that": st.column_config.TextColumn(width=130),
                                "acceptance criteria": st.column_config.TextColumn(width=240),
                                "ambiguity": st.column_config.TextColumn(width=200)})


st.caption("FIRMWARE LIFECYCLE · REQUIREMENT → DESIGN")
st.title("เตรียมความต้องการสำหรับ Design")
st.caption("ทำทีละขั้น: กำหนดขอบเขต → สนทนา → ตรวจทาน → ส่งต่อ")
intro_tab, scope_tab, chat_tab, review_tab, handoff_tab = st.tabs([
    "เริ่มต้น", "1 · ขอบเขต", "2 · สนทนา", "3 · ตรวจทาน", "4 · ส่งต่อ Design"
])
with intro_tab:
    st.subheader("จากสิ่งที่ต้องการ สู่ข้อกำหนดที่ตรวจสอบได้")
    st.write("พื้นที่นี้ช่วยเก็บความต้องการของอุปกรณ์ แล้วจัดเป็น user stories และเงื่อนไขยอมรับ เพื่อให้ขั้น Design นำไปออกแบบต่อได้")
    st.markdown("""
| ขั้นตอน | คุณทำอะไร | ได้อะไร |
| --- | --- | --- |
| **1 · ขอบเขต** | ตั้งชื่อ เลือกบอร์ดถ้าทราบ และระบุข้อจำกัด | ขอบเขตร่วมกับ agent |
| **2 · สนทนา** | เล่างานจริงด้วยภาษาปกติ และตอบคำถามเพิ่มเติม | ข้อเสนอ user stories จาก agent |
| **3 · ตรวจทาน** | อ่านข้อเสนอ กดรับเป็น draft และตรวจเงื่อนไขยอมรับ | Stories ที่สะท้อนความต้องการจริง |
| **4 · ส่งต่อ Design** | แก้ประเด็นที่ยังขาด แล้วสร้างและดาวน์โหลด baseline | ชุดเอกสารอ้างอิงสำหรับ Design |
""")
    st.markdown("**เริ่มใช้อย่างไร**")
    st.write("เปิดแท็บ 1 · ขอบเขต กรอกเท่าที่ทราบ แล้วไปแท็บ 2 · สนทนา เช่น ‘ต้องการกดปุ่มเพื่อบันทึกรายชื่อ Wi-Fi ลง SD card สำหรับผู้สำรวจพื้นที่’ หากยังไม่ทราบบอร์ด ให้เริ่มคุยก่อนได้")
    with st.expander("User story และ acceptance criteria คืออะไร?", expanded=False):
        st.write("User story อธิบายว่า ใครต้องการทำอะไร และเพื่ออะไร: ในฐานะผู้สำรวจ ฉันต้องการบันทึกรายชื่อ Wi-Fi เพื่อกลับมาวิเคราะห์ภายหลัง")
        st.write("Acceptance criteria คือเงื่อนไขที่ตรวจสอบได้ เช่น กดปุ่มหนึ่งครั้งแล้วได้หนึ่งแถวต่อเครือข่าย พร้อมเวลาและ RSSI ส่วนวิธีพิสูจน์อธิบายว่าจะตรวจเงื่อนไขนั้นอย่างไร")
    st.info("Agent เสนอร่างเท่านั้น คุณเป็นผู้กดรับและตรวจทาน เอกสารส่งต่อสร้างจาก stories ที่บันทึกแล้ว ไม่ได้สร้างจากข้อความสนทนาโดยตรง")
    st.caption("ไม่ต้องเขียนหรือแก้ JSON เอง ระบบสร้าง artifact ให้เมื่อส่งต่อ · การสร้าง baseline คือเสนอให้ Design ตรวจรับ")
    st.caption("หากยังไม่ได้เชื่อม agent ให้เปิด ตั้งค่า ใน sidebar เลือก Background agent / CLI และตรวจสถานะ worker")

with st.sidebar:
    st.markdown("### ◈ Firmware lifecycle")
    st.caption("REQUIREMENT WORKSPACE · LOCAL PROTOTYPE")
    draft_area = st.container()
    settings_area = st.expander("ตั้งค่า", expanded=False)
with settings_area:
    st.markdown("**Agent และข้อมูลอ้างอิง**")
    st.caption("ตั้งค่าเมื่อเริ่มใช้งานหรือเปลี่ยนเครื่อง จากนั้นกลับไปทำงานในแท็บ 1–4")
    with st.expander("Capability source", expanded=False):
        provider_path = Path(st.text_input("Provider folder", value=os.environ.get("FWLC_PROVIDER_ROOT", str(cap.DEFAULT_PROVIDER))))
        if st.button("นำเข้า snapshot ใหม่", width="stretch"):
            try:
                paths = cap.write_snapshot(cap.capture(provider_path))
                st.success(f"บันทึก {paths[0].stem} แล้ว · draft เดิมยังไม่เปลี่ยน snapshot")
            except (ValueError, OSError) as exc:
                st.error(str(exc))

snapshot_paths = cap.list_snapshots()
if not snapshot_paths:
    st.title("เริ่มจาก capability snapshot")
    st.info("เปิด Capability source ทางซ้าย แล้วนำเข้าข้อมูลจาก automated-firmware-skills แบบอ่านอย่างเดียว")
    st.stop()
snapshots = {p.stem: p for p in snapshot_paths}
if "project" not in st.session_state:
    projects = contract.load_projects()
    if projects:
        st.session_state.project = projects[0]
    else:
        st.session_state.project = contract.new_project(cap.load_snapshot(snapshot_paths[0]))
        contract.save_project(st.session_state.project)

requested_project = st.query_params.get('project')
if requested_project and st.session_state.get('opened_request_project') != requested_project:
    requested = next((p for p in contract.load_projects() if p['project_id'] == requested_project), None)
    if requested:
        st.session_state.project = requested
        for key in ('workspace_choice', 'story_choice', 'bundle', 'freshness'):
            st.session_state.pop(key, None)
    st.session_state.opened_request_project = requested_project

with draft_area:
    projects = contract.load_projects()
    project_lookup = {p["project_id"]: p for p in projects}
    pid = st.session_state.project["project_id"]
    ids = list(project_lookup)
    if st.session_state.get("workspace_choice") not in ids:
        st.session_state.workspace_choice = pid
    st.selectbox("Draft ที่บันทึกไว้", ids,
                 format_func=lambda x: project_lookup[x]["name"] or x,
                 key="workspace_choice", on_change=select_draft)
    a, b = st.columns(2)
    a.button("Draft ใหม่", width="stretch", on_click=create_draft)
    if b.button("โหลดล่าสุด", width="stretch"):
        st.session_state.project = next(p for p in contract.load_projects() if p["project_id"] == pid)
        st.session_state.pop("bundle", None)
        st.rerun()

project = st.session_state.project
if project["snapshot_id"] not in snapshots:
    st.error("ไม่พบ snapshot ที่ draft นี้อ้างอิง ให้นำไฟล์ snapshot กลับมาด้วยก่อนทำต่อ")
    st.stop()
snapshot = cap.load_snapshot(snapshots[project["snapshot_id"]])

with settings_area:
    snapshot_choice = st.selectbox("Capability snapshot", list(snapshots), index=list(snapshots).index(project["snapshot_id"]), key="snapshot_" + project["project_id"])
    st.caption(f"Pinned: {snapshot['captured_at_bangkok']}\n\nProvider: {(snapshot['provider_revision'] or 'no Git')[:12]}")
    if snapshot_choice != project["snapshot_id"]:
        st.warning("เปลี่ยน snapshot แล้วทุก story ต้องตรวจ feasibility/review ใหม่")
        if st.button("ใช้ snapshot ที่เลือกกับ draft"):
            commit(lambda p: contract.rebind_snapshot(p, cap.load_snapshot(snapshots[snapshot_choice])))
            st.session_state.pop("bundle", None)
            st.session_state.pop("freshness", None)
            st.rerun()
    st.divider()
    mode = st.selectbox("Agent", ["Manual / offline", "Background agent / CLI", "Host agent / interactive", "Ollama", "OpenAI-compatible"],
                        index=1 if st.query_params.get('agent') in {'host', 'background'} or worker.status()['responsive'] else 0)
    endpoint, model, api_key = "", "", ""
    context_size, max_tokens, timeout = 4096, 1024, 180
    json_mode, thinking = True, False
    if mode == 'Host agent / interactive':
        st.info('รับส่งกับ agent ในแชตที่กำลังทำงานอยู่ ไม่ใช่ Ollama หรือ worker ที่รันตลอดเวลา')
    if mode == 'Background agent / CLI':
        st.caption('ใช้ Codex CLI และ login ที่มีอยู่ · ไม่ต้องตั้ง LLM API endpoint')
        cli_timeout = st.select_slider('Agent timeout (seconds)', [60, 120, 180, 300, 600], value=180)
        granted = worker.authorized(project)
        allow = st.checkbox('อนุญาตให้ส่งบทสนทนา stories และ capability context ของ draft นี้ไปยังบริการ OpenAI Codex ผ่าน CLI', value=granted, key='background_consent_' + project['project_id'] + '_' + project.get('background_agent_consent', {}).get('updated_at_utc', 'unset'))
        if allow != granted:
            commit(lambda p: p.update(background_agent_consent={'granted': allow, 'destination': 'OpenAI Codex service', 'updated_at_utc': cap.utc_now()}))
            st.rerun()
        if not granted:
            st.warning('Worker จะไม่ส่งข้อมูล draft นี้จนกว่าจะอนุญาต สามารถถอนการอนุญาตได้ที่นี่')
        ws = worker.status()
        st.caption(f"Worker: {ws['state']} · {'พร้อม' if ws['responsive'] else 'ยังไม่พร้อม'}")
        start_col, stop_col = st.columns(2)
        if start_col.button('เริ่ม worker', width='stretch', disabled=not granted):
            try:
                with st.spinner('กำลังเริ่ม background agent…'):
                    worker.start(cli_timeout)
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if stop_col.button('หยุด worker', width='stretch', disabled=not ws['alive']):
            worker.stop()
            st.rerun()
        if ws.get('last_error'):
            st.error(ws['last_error'])
    if mode in {"Ollama", "OpenAI-compatible"}:
        endpoint = st.text_input("Local server URL", value="http://127.0.0.1:11434" if mode == "Ollama" else "http://127.0.0.1:1234/v1")
        api_key = st.text_input("API key (ถ้า server ต้องใช้)", type="password")
        if st.button("ดูโมเดลที่ติดตั้ง"):
            try:
                st.session_state.installed_models = llm.list_models(mode, endpoint, api_key)
            except ValueError as exc:
                st.error(str(exc))
        installed = st.session_state.get("installed_models", [])
        preset = st.selectbox("Model preset", list(llm.MODEL_PRESETS))
        default_model = llm.MODEL_PRESETS[preset]
        if installed:
            st.caption("Installed: " + ", ".join(installed))
        model = st.text_input("Model name / tag", value=default_model, key=f"model_{mode}_{preset}")
        with st.expander("Inference settings"):
            context_size = st.select_slider("Ollama context", [2048, 4096, 8192, 16384], value=4096)
            max_tokens = st.slider("Max output tokens", 256, 2048, 1024, step=256)
            timeout = st.slider("Timeout (seconds)", 30, 300, 180, step=30)
            json_mode = st.checkbox("JSON response mode", True)
            thinking = st.checkbox("Ollama thinking (ใช้ output budget เพิ่ม)", False)
        st.caption("RTX 4060 8GB: ทดลอง E4B แบบ quantized และ context สั้น; E2B เป็น fallback ที่เล็กกว่า ต้องวัด VRAM จริงบน office")
    st.caption("API key อยู่ใน session เท่านั้น · ไม่มีการดาวน์โหลดโมเดลอัตโนมัติ")

# Opening a pending legacy-host request in background mode is an explicit backend handover.
if mode == 'Background agent / CLI' and project.get('agent_request', {}).get('status') == 'pending' and project['agent_request'].get('backend', 'host') == 'host':
    commit(lambda p: p['agent_request'].update(backend='background'))
    st.rerun()

with scope_tab:
    st.subheader("1 · กำหนดขอบเขต")
    st.caption("กรอกเท่าที่ทราบ · ชื่อและบอร์ดต้องระบุก่อนส่งต่อ Design ข้อจำกัดเว้นว่างได้หากยังไม่มี")
    board_ids = [""] + [b["id"] for b in snapshot["boards"]]
    board_names = {b["id"]: b.get("name", b["id"]) for b in snapshot["boards"]}
    with st.form("project_context_" + project["project_id"]):
        name = st.text_input("ชื่อโครงการ", project["name"])
        board = st.selectbox("Target board", board_ids, index=board_ids.index(project["board_id"]) if project["board_id"] in board_ids else 0,
                             format_func=lambda x: board_names.get(x, "ยังไม่เลือก"))
        constraints = st.text_area("Constraints / quality requirements (หนึ่งข้อต่อบรรทัด)", "\n".join(project["constraints"]), height=90)
        if st.form_submit_button("บันทึกขอบเขต"):
            commit(lambda p: contract.update_context(p, name, board, constraints.splitlines()))
            st.session_state.pop("bundle", None)
            st.rerun()

# Render the editor first so chat observes the selected story on each rerun.
with review_tab:
    st.subheader("3 · ตรวจทานความต้องการ")
    st.caption("หนึ่งแถวต่อหนึ่งเป้าหมายของผู้ใช้ · ambiguity คือคำถามที่ยังไม่ชัดเจน ไม่ใช่ผลประเมิน feasibility")
    proposal_area = st.container()
    st.divider()
    st.markdown("**Stories ที่บันทึกแล้ว**")
    story_table(project["stories"], "saved_stories_" + project["project_id"])
    story_editor = st.expander("Stories ที่บันทึก · เลือกแก้ไขหรือเพิ่มเอง", expanded=False)
with story_editor:
    new_col, example_col = st.columns(2)
    if new_col.button("＋ เพิ่ม story", width="stretch"):
        updated = commit(lambda p: contract.add_story(p))
        st.session_state.story_choice = updated["stories"][-1]["id"]
        st.rerun()
    if example_col.button("ตัวอย่างปุ่ม / LED", width="stretch"):
        def example(p):
            s = contract.add_story(p)
            contract.update_story(s, {"title": "ตรวจปุ่มและ LED", "role": "ผู้ทดสอบบอร์ด", "want": "กดและปล่อยปุ่มเพื่อควบคุม LED", "benefit": "ตรวจสอบ input/output ได้",
                "acceptance_criteria": [{"text": "กดปุ่มค้างแล้ว LED ที่กำหนดติด", "test_intent": "กดปุ่มและสังเกต LED จริง พร้อมอ่านสถานะ output", "requires_hardware": True},
                                        {"text": "ปล่อยปุ่มแล้ว LED ดับ", "test_intent": "ปล่อยปุ่มและสังเกต LED จริง พร้อมอ่านสถานะ output", "requires_hardware": True}],
                "open_questions": ["ใช้ปุ่มและ LED ใด และต้องกำหนดเวลาตอบสนองหรือไม่?"], "reviewed": False})
        updated = commit(example)
        st.session_state.story_choice = updated["stories"][-1]["id"]
        st.rerun()
    project = st.session_state.project
    story_map = {s["id"]: s for s in project["stories"]}
    selected_id = None
    if story_map:
        selected_id = st.selectbox("Story ที่กำลังทำงาน", list(story_map), key="story_choice",
                                  format_func=lambda x: f"{x} · {story_map[x]['title'] or 'Untitled'} · {story_map[x]['feasibility']}")
        story = story_map[selected_id]
        st.caption(f"Revision {story['revision']} · {'ตรวจทานแล้ว' if story['reviewed'] else 'Draft / ยังไม่ตรวจทาน'}")
        options = cap.capability_options(snapshot, project["board_id"])
        all_refs = list(dict.fromkeys(list(options) + story["capability_refs"]))
        with st.form(f"story_{project['project_id']}_{selected_id}_{story['revision']}"):
            title = st.text_input("ชื่อ story", story["title"], help="สรุปพฤติกรรมสั้น ๆ เช่น บันทึกเครือข่าย Wi-Fi")
            role = st.text_input("ผู้ใช้เป็นใคร · As a …", story["role"], placeholder="เช่น ผู้สำรวจพื้นที่")
            want = st.text_area("ต้องการทำอะไร · I want to …", story["want"], height=70, placeholder="เช่น กดปุ่มเพื่อบันทึกเครือข่าย Wi-Fi")
            benefit = st.text_input("เพื่ออะไร · So that …", story["benefit"], placeholder="เช่น นำข้อมูลไปวิเคราะห์ภายหลัง")
            st.markdown("**เงื่อนไขยอมรับและวิธีพิสูจน์**")
            st.caption("หนึ่งแถวต่อเงื่อนไขที่วัดหรือตรวจได้ · วิธีพิสูจน์ = จะตรวจอย่างไร · Hardware = ต้องใช้บอร์ดจริง")
            rows = story["acceptance_criteria"] or [{"id": "", "text": "", "test_intent": "", "requires_hardware": True}]
            frame = pd.DataFrame(rows, columns=["id", "text", "test_intent", "requires_hardware"])
            criteria = st.data_editor(frame, num_rows="dynamic", hide_index=True, width="stretch",
                                      disabled=["id"], key=f"ac_{project['project_id']}_{selected_id}_{story['revision']}",
                                      column_config={"id": st.column_config.TextColumn("ID", width="small"),
                                          "text": st.column_config.TextColumn("เงื่อนไขยอมรับ", width="large"),
                                          "test_intent": st.column_config.TextColumn("วิธีพิสูจน์", width="large"),
                                          "requires_hardware": st.column_config.CheckboxColumn("Hardware")})
            questions = st.text_area("คำถามค้าง (หนึ่งข้อต่อบรรทัด)", "\n".join(story["open_questions"]), height=75)
            with st.expander("การประเมินความเป็นไปได้ · ทำก่อนส่งต่อ", expanded=False):
                st.caption("เทียบพฤติกรรมกับ capabilities/recipes ที่นำเข้า ระบุเหตุผลและสิ่งที่ยังต้องทดลอง หากไม่แน่ใจให้คุยกับ agent ก่อน")
                feasibility = st.selectbox("Feasibility", ["unknown", "supported", "needs-spike", "unsupported"],
                                           index=["unknown", "supported", "needs-spike", "unsupported"].index(story["feasibility"]))
                refs = st.multiselect("Candidate capabilities / recipes", all_refs, default=story["capability_refs"],
                                      format_func=lambda r: options.get(r, "⚠ อ้างอิงเดิมไม่ตรง target: " + r))
                rationale = st.text_area("เหตุผล / ข้อจำกัดของ feasibility", story["feasibility_reason"], height=75)
            reviewed = st.checkbox("ฉันตรวจทานความหมายและ criteria ของ story นี้แล้ว", story["reviewed"])
            if st.form_submit_button("บันทึก story", type="primary"):
                values = {"title": title, "role": role, "want": want, "benefit": benefit,
                          "acceptance_criteria": criteria.fillna("").to_dict("records"),
                          "open_questions": questions.splitlines(), "feasibility": feasibility,
                          "capability_refs": refs, "feasibility_reason": rationale, "reviewed": reviewed}
                commit(lambda p: contract.update_story(next(s for s in p["stories"] if s["id"] == selected_id), values))
                st.session_state.pop("bundle", None)
                st.rerun()
        with st.expander("ถอด story ออกจาก offered scope"):
            st.caption("Baseline ที่ export ไว้ก่อนหน้ายังคงอยู่")
            if st.checkbox("ยืนยันถอด story ที่เลือก", key=f"remove_confirm_{project['project_id']}_{selected_id}") and st.button("ถอด story", key=f"remove_{project['project_id']}_{selected_id}"):
                commit(lambda p: p.update(stories=[s for s in p["stories"] if s["id"] != selected_id], proposals=[]))
                st.session_state.pop("story_choice", None)
                st.session_state.pop("bundle", None)
                st.rerun()
    else:
        st.info("ยังไม่มี story · ไปแท็บ 2 · สนทนา เพื่อให้ agent เสนอร่าง หรือกดเพิ่ม story เพื่อกรอกเอง")

with chat_tab:
    st.subheader("2 · สนทนาเพื่อเก็บความต้องการ")
    st.caption("เล่างานด้วยภาษาปกติ ไม่ต้องกรอก template · ข้อเสนอที่ได้จะอยู่ในแท็บ 3 · ตรวจทาน")
    selected_id = st.selectbox("หัวข้อสนทนา", [None] + [item["id"] for item in project["stories"]],
                               format_func=lambda value: "ภาพรวม · แยกเป้าหมายเป็น stories" if value is None else value + " · " + next(x["title"] for x in project["stories"] if x["id"] == value),
                               key="chat_focus_" + project["project_id"])
    st.caption("หัวข้อที่เลือกเป็นบริบท ไม่บังคับให้รวมทุกความต้องการไว้ใน story เดียว · agent เสนอร่างให้ตรวจเท่านั้น")
    with st.container(height=430, border=True):
        if not project["messages"]:
            st.markdown("**เริ่มด้วยสิ่งที่อยากให้อุปกรณ์ทำ**\n\nใครเป็นผู้ใช้ ต้องการพฤติกรรมอะไร และจะรู้ได้อย่างไรว่าทำถูกต้อง?")
        for message in project["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    queued_mode = mode in {'Host agent / interactive', 'Background agent / CLI'}
    pending = queued_mode and project.get('agent_request', {}).get('status') in {'pending', 'processing'}
    if prompt := st.chat_input("บอกความต้องการ หรืออธิบาย story ที่เลือก…", disabled=pending):
        turn_id = "TURN-" + uuid.uuid4().hex[:10]
        project = commit(lambda p: p["messages"].append({"id": turn_id, "role": "user", "content": prompt}))
        if queued_mode:
            commit(lambda p: bridge.enqueue(p, turn_id, selected_id, backend='background' if mode == 'Background agent / CLI' else 'host'))
        elif mode == "Manual / offline":
            commit(lambda p: p["messages"].append({"id": "TURN-" + uuid.uuid4().hex[:10], "role": "assistant",
                "content": "บันทึกข้อมูลแล้วครับ โหมด Manual ไม่เรียก LLM — เพิ่มหรือปรับ story ในแท็บ 3 · ตรวจทานได้ และเปิด Local LLM เมื่อต้องการให้ agent ช่วยสรุป"}))
        else:
            try:
                with st.spinner(f"กำลังคุยกับ {model}…"):
                    result = llm.acquire(mode, endpoint, model, project, snapshot, selected_id, api_key,
                                         context_size, max_tokens, timeout, json_mode, thinking)
                def keep_result(p):
                    reply = result["reply"] + ("\n\n" + "\n".join(f"- {q}" for q in result["questions"]) if result["questions"] else "")
                    p["messages"].append({"id": "TURN-" + uuid.uuid4().hex[:10], "role": "assistant", "content": reply})
                    for proposal in result["proposals"]:
                        proposal.update(id=uuid.uuid4().hex, source_turn_ids=[turn_id], model=model,
                                        snapshot_id=snapshot["snapshot_id"], board_id=p["board_id"])
                        p["proposals"].append(proposal)
                commit(keep_result)
            except ValueError as exc:
                st.session_state.agent_error = str(exc)
        st.rerun()
    if queued_mode:
        @st.fragment(run_every=2)
        def host_status():
            current = st.session_state.project
            path = contract.project_file(current['project_id'])
            latest = json.loads(path.read_text(encoding='utf-8'))
            if latest['workspace_revision'] != current['workspace_revision']:
                # External replies append chat/proposals only; never auto-apply them to stories.
                st.session_state.project = latest
                st.rerun()
            request = latest.get('agent_request', {})
            if mode == 'Background agent / CLI':
                live_worker = worker.status()
                st.caption(f"Background worker: {live_worker['state']} · {'online' if live_worker['responsive'] else 'offline'}")
                if not live_worker['responsive']:
                    st.warning('Worker ยังไม่พร้อม กด เริ่ม worker ใน sidebar ตั้งค่า เพื่อประมวลผลคิวอัตโนมัติ')
            if request.get('status') in {'pending', 'processing'}:
                st.info('Agent กำลังประมวลผล…' if request['status'] == 'processing' else 'ส่งคำขอเข้าคิวแล้ว · รอ agent รับงาน')
                if st.button('ยกเลิกคำขอที่รอ', key='cancel_host_request'):
                    commit(lambda p: p['agent_request'].update(status='cancelled'))
                    st.rerun()
            elif request.get('status') == 'stale':
                st.warning('บริบทเปลี่ยนระหว่างรอ กรุณาส่งคำขอใหม่')
            elif request.get('status') == 'completed':
                st.caption('Agent ตอบกลับแล้ว · ข้อเสนอใด ๆ ยังต้องกดรับเป็น draft')
            elif request.get('status') == 'failed':
                st.error(request.get('error', 'Agent request failed'))
            if request.get('status') in {'failed', 'stale', 'cancelled'}:
                if st.button('ลองคำขอเดิมด้วยบริบทปัจจุบัน', key='retry_agent_request'):
                    def retry(p):
                        old = p.get('agent_request', {})
                        p.setdefault('agent_request_history', []).append(dict(old))
                        last = next(m for m in reversed(p['messages']) if m['role'] == 'user')
                        bridge.enqueue(p, last['id'], selected_id, backend='background' if mode == 'Background agent / CLI' else 'host')
                    commit(retry)
                    st.rerun()
        host_status()
    if error := st.session_state.pop("agent_error", None):
        st.error(error)
    st.caption("ส่งบริบท story ที่เลือก + สรุป stories อื่น + บทสนทนาล่าสุดสูงสุด 8 ข้อความ ไม่ส่ง snapshot ทั้งเล่ม")
with proposal_area:
    st.subheader("ข้อเสนอจาก agent")
    st.caption("รับข้อเสนอเป็น draft ทีละรายการ · ตารางเป็นมุมมองสรุป เลือกข้อเสนอด้านล่างเพื่ออ่าน criteria/ambiguity ฉบับเต็ม")
    if not project["proposals"]:
        st.info("ไม่มีข้อเสนอรอรับ · สนทนาต่อในแท็บ 2 หรือแก้ story ที่มีอยู่")
    story_table(project["proposals"], "proposed_stories_" + project["project_id"])
    if project["proposals"]:
        proposal_map = {item["id"]: item for item in project["proposals"]}
        choice_key = "proposal_choice_" + project["project_id"]
        if st.session_state.get(choice_key) not in proposal_map:
            st.session_state[choice_key] = next(iter(proposal_map))
        proposal_id = st.selectbox("ข้อเสนอที่ต้องการตรวจ", list(proposal_map),
                                   format_func=lambda value: proposal_map[value]["title"] + " · " + proposal_map[value]["operation"],
                                   key="proposal_choice_" + project["project_id"])
        proposal = proposal_map[proposal_id]
        with st.container():
            with st.expander("อ่าน acceptance criteria และ ambiguity ฉบับเต็ม"):
                for criterion in proposal.get("acceptance_criteria", []):
                    st.write("• " + criterion["text"])
                    st.caption("วิธีพิสูจน์: " + criterion["test_intent"])
                for question in proposal.get("open_questions", []):
                    st.write("คำถามค้าง: " + question)
                st.caption("ความเป็นไปได้: " + proposal.get("feasibility", "unknown") + " · " + proposal.get("feasibility_reason", ""))
            with st.expander("รายละเอียดการเปลี่ยนแปลง · สำหรับตรวจเชิงเทคนิค"):
                old = next((item for item in project["stories"] if item["id"] == proposal.get("story_id")), {})
                before = json.dumps(old, ensure_ascii=False, indent=2).splitlines()
                after = json.dumps({k: v for k, v in proposal.items() if k not in {"id", "model"}}, ensure_ascii=False, indent=2).splitlines()
                st.code("\n".join(difflib.unified_diff(before, after, fromfile="Current", tofile="Proposed", lineterm="")), language="diff")
            yes, no = st.columns(2)
            if yes.button("รับเป็น draft", key=f"accept_{proposal['id']}"):
                try:
                    def accept(p):
                        contract.apply_proposal(p, proposal, snapshot)
                        p["proposals"] = [x for x in p["proposals"] if x["id"] != proposal["id"]]
                    updated = commit(accept)
                    if proposal["operation"] == "create":
                        st.session_state.next_story_choice = updated["stories"][-1]["id"]
                    st.session_state.pop("bundle", None)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            if no.button("ไม่ใช้ข้อเสนอนี้", key=f"reject_{proposal['id']}"):
                commit(lambda p: p.update(proposals=[x for x in p["proposals"] if x["id"] != proposal["id"]]))
                st.rerun()

with handoff_tab:
    st.subheader("4 · ตรวจความพร้อมและส่งต่อ Design")
    st.caption("ตรวจรายการที่ยังขาดก่อน เมื่อครบแล้วระบบจะสร้าง artifact จากข้อมูลที่บันทึก โดยไม่ต้องกรอก JSON")
    project = st.session_state.project
    issues = contract.readiness(project, snapshot)
    with st.expander(f"ความครบถ้วน: {'พร้อมตรวจส่งต่อ' if not issues else str(len(issues)) + ' ประเด็นต้องแก้'}", expanded=bool(issues)):
        if issues:
            for issue in issues:
                st.write("• " + issue)
        else:
            st.success("ข้อมูลที่จำเป็นครบ — ยังต้องให้ Design ตรวจรับและประเมินทางวิศวกรรม")
        st.caption("การตรวจนี้ไม่รับรอง feasibility ทางกายภาพ ความครบถ้วนเชิงความหมาย หรือผลทดสอบ firmware")

    if st.button("ตรวจความต่างจาก provider ตอนนี้"):
        try:
            st.session_state.freshness = cap.compare(snapshot, provider_path)
        except OSError as exc:
            st.error(str(exc))
    freshness = st.session_state.get("freshness")
    if freshness:
        st.caption(f"Source check: {freshness['status']} · {freshness['checked_at_utc']}")
        if freshness["status"] == "changed":
            st.warning("ต้นทางเปลี่ยนแล้ว: นำเข้า snapshot ใหม่ แล้วเลือกใช้กับ draft และ review ใหม่ก่อนส่งต่อ")
            st.json({k: freshness[k] for k in ("changed", "added", "removed")}, expanded=False)

    if st.button("สร้าง baseline และส่งเสนอให้ Design", disabled=bool(issues), type="primary"):
        try:
            current = cap.compare(snapshot, provider_path)
            value = contract.make_handoff(project, snapshot, current)
            updated = copy.deepcopy(project)
            data = contract.store_handoff(updated, value, snapshot)
            st.session_state.project = updated
            st.session_state.bundle = {"value": value, "data": data}
            st.session_state.freshness = current
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))

    if bundle := st.session_state.get("bundle"):
        value = bundle["value"]
        st.success(f"สร้าง baseline revision {value['revision']} แล้ว · Offered / Design acceptance pending")
        st.download_button("ดาวน์โหลด Design handoff (.zip)", bundle["data"], f"requirements-r{value['revision']:03d}.zip", mime="application/zip")
        with st.expander("ไฟล์แยกสำหรับเครื่องมือ · JSON / Markdown"):
            st.download_button("Requirements JSON", json.dumps(value, ensure_ascii=False, indent=2), "requirements.json", mime="application/json")
            st.download_button("Requirements Markdown", contract.handoff_markdown(value), "requirements.md", mime="text/markdown")
        with st.expander("อ่านเอกสารที่จะส่งต่อ"):
            st.markdown(contract.handoff_markdown(value))

    with st.expander("Capability reference และประวัติ handoff"):
        st.download_button("ดาวน์โหลด snapshot Markdown", cap.render_markdown(snapshot), snapshot["snapshot_id"] + ".md", mime="text/markdown")
        st.json({"snapshot_id": snapshot["snapshot_id"], "active_milestones": snapshot["active_milestones"], "readiness": "not_probed"}, expanded=False)
        for record in project["handoffs"]:
            file = contract.project_file(project["project_id"]).parent / "handoffs" / record["file"]
            if file.is_file():
                st.download_button(f"Baseline r{record['revision']} · {record['created_at_utc']}", file.read_bytes(), file.name,
                                   mime="application/zip", key=f"history_{record['revision']}")
