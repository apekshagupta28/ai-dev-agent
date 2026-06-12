"""
dashboard.py
Streamlit dashboard for the Autonomous AI Dev Agent.

Run with:
    streamlit run dashboard.py
"""

import streamlit as st
import threading
import queue
import time
import json
from datetime import datetime

# Pipeline import — guarded so dashboard loads even if deps are missing
try:
    from main import run_pipeline, build_graph
    PIPELINE_AVAILABLE = True
except ImportError as _e:
    PIPELINE_AVAILABLE = False
    _IMPORT_ERROR = str(_e)


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Dev Agent",
    page_icon="🤖",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title   { font-size: 2.2rem; font-weight: 700; }
    .sub-title    { color: #888; font-size: 0.95rem; margin-top: -10px; }
    .card         { background: #1e1e2e; border-radius: 12px; padding: 20px;
                    border: 1px solid #313244; margin-bottom: 16px; }
    .step-done    { color: #a6e3a1; font-weight: 600; }
    .step-running { color: #89b4fa; font-weight: 600; }
    .step-pending { color: #585b70; }
    .step-error   { color: #f38ba8; font-weight: 600; }
    .badge-success{ background:#a6e3a1; color:#1e1e2e; border-radius:6px;
                    padding:2px 10px; font-size:0.8rem; font-weight:700; }
    .badge-fail   { background:#f38ba8; color:#1e1e2e; border-radius:6px;
                    padding:2px 10px; font-size:0.8rem; font-weight:700; }
    .badge-info   { background:#89b4fa; color:#1e1e2e; border-radius:6px;
                    padding:2px 10px; font-size:0.8rem; font-weight:700; }
    .log-box      { background:#181825; border-radius:8px; padding:12px;
                    font-family:monospace; font-size:0.82rem; max-height:260px;
                    overflow-y:auto; border: 1px solid #313244; }
    code-block    { background:#313244; border-radius:6px; padding:2px 6px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "running":          False,
    "final_state":      None,
    "logs":             [],
    "current_step":     None,
    "run_history":      [],   # list of past run summaries
    "log_queue":        None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline steps metadata
# ─────────────────────────────────────────────────────────────────────────────
STEPS = [
    ("read_jira",     "📋", "Read Jira Issue"),
    ("generate_code", "🤖", "Generate Code"),
    ("execute_code",  "▶️",  "Execute Code"),
    ("self_correct",  "🔧", "Self-Correct (if needed)"),
    ("push_github",   "🚀", "Push to GitHub & Create PR"),
    ("close_jira",    "🎯", "Close Jira Issue"),
]

STEP_NAMES = [s[0] for s in STEPS]


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([4, 1])
with col_title:
    st.markdown('<div class="main-title">🤖 Autonomous AI Dev Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">LangGraph · Groq llama-3.3-70b · PyGithub · Jira · Streamlit</div>', unsafe_allow_html=True)

with col_status:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.running:
        st.markdown('<span class="badge-info">● RUNNING</span>', unsafe_allow_html=True)
    elif st.session_state.final_state:
        ok = st.session_state.final_state.get("jira_closed")
        badge = "badge-success" if ok else "badge-fail"
        label = "✓ DONE" if ok else "✗ FAILED"
        st.markdown(f'<span class="{badge}">{label}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#585b70">● IDLE</span>', unsafe_allow_html=True)

st.divider()

if not PIPELINE_AVAILABLE:
    st.error(f"⚠️ Pipeline modules not importable: `{_IMPORT_ERROR}`\n\nMake sure all dependencies are installed and .env is configured.")


# ─────────────────────────────────────────────────────────────────────────────
# Main layout: left panel (controls + steps) | right panel (output)
# ─────────────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="large")


# ── LEFT: Controls ────────────────────────────────────────────────────────────
with left:
    st.subheader("⚙️ Configuration")

    issue_key = st.text_input(
        "Jira Issue Key",
        value="SCRUM-5",
        placeholder="e.g. SCRUM-5",
        disabled=st.session_state.running,
    )
    max_corrections = st.slider(
        "Max Self-Correction Attempts",
        min_value=1, max_value=5, value=3,
        disabled=st.session_state.running,
    )

    run_clicked = st.button(
        "🚀 Run Pipeline",
        type="primary",
        disabled=st.session_state.running or not PIPELINE_AVAILABLE,
        use_container_width=True,
    )
    if st.session_state.running:
        st.button("⏹ Running…", disabled=True, use_container_width=True)

    st.divider()

    # ── Pipeline steps tracker ───────────────────────────────────────────────
    st.subheader("🗺 Pipeline Steps")
    final = st.session_state.final_state
    current = st.session_state.current_step

    for step_id, icon, label in STEPS:
        if final:
            # Colour based on result fields
            if step_id == "read_jira" and final.get("issue_summary"):
                cls = "step-done";  indicator = "✅"
            elif step_id == "generate_code" and final.get("generated_code"):
                cls = "step-done";  indicator = "✅"
            elif step_id == "execute_code" and final.get("execution_success"):
                cls = "step-done";  indicator = "✅"
            elif step_id == "execute_code" and not final.get("execution_success"):
                cls = "step-error"; indicator = "❌"
            elif step_id == "self_correct" and final.get("correction_attempts", 0) > 0:
                cls = "step-done";  indicator = "✅"
            elif step_id == "push_github" and final.get("push_success"):
                cls = "step-done";  indicator = "✅"
            elif step_id == "close_jira" and final.get("jira_closed"):
                cls = "step-done";  indicator = "✅"
            else:
                cls = "step-pending"; indicator = "○"
        elif current == step_id:
            cls = "step-running"; indicator = "⟳"
        else:
            cls = "step-pending"; indicator = "○"

        st.markdown(
            f'<div class="{cls}">{indicator} {icon} {label}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Run history ──────────────────────────────────────────────────────────
    if st.session_state.run_history:
        st.subheader("📜 Run History")
        for run in reversed(st.session_state.run_history[-5:]):
            icon = "✅" if run["success"] else "❌"
            st.markdown(
                f"`{run['time']}` {icon} **{run['issue']}** — {run['pr'] or 'No PR'}",
                unsafe_allow_html=False,
            )


# ── RIGHT: Output ─────────────────────────────────────────────────────────────
with right:

    # Tabs
    tab_output, tab_code, tab_logs, tab_graph = st.tabs(
        ["📊 Output", "💻 Generated Code", "📝 Logs", "🗺 Graph Viz"]
    )

    with tab_output:
        if final:
            # Summary cards ──────────────────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Issue", final.get("issue_key", "—"))
            c2.metric("Corrections", final.get("correction_attempts", 0))
            c3.metric("PR Created", "✅" if final.get("push_success") else "❌")
            c4.metric("Jira Closed", "✅" if final.get("jira_closed") else "❌")

            st.markdown("---")

            if final.get("issue_summary"):
                st.markdown(f"**📋 Issue:** {final['issue_summary']}")

            if final.get("pr_url"):
                st.markdown(f"**🔗 Pull Request:** [{final['pr_url']}]({final['pr_url']})")

            if final.get("branch_name"):
                st.markdown(f"**🌿 Branch:** `{final['branch_name']}`")

            if final.get("execution_output"):
                with st.expander("▶️ Execution Output"):
                    st.code(final["execution_output"], language="text")

            if final.get("execution_error") and not final.get("execution_success"):
                with st.expander("❌ Execution Error"):
                    st.code(final["execution_error"], language="text")
        else:
            st.info("Run the pipeline to see results here.")

    with tab_code:
        if final and final.get("generated_code"):
            st.markdown(f"**File:** `{final.get('filename', 'generated.py')}`")
            st.code(final["generated_code"], language="python")
            st.download_button(
                "⬇️ Download Code",
                data=final["generated_code"],
                file_name=final.get("filename", "generated.py"),
                mime="text/plain",
            )
        else:
            st.info("Generated code will appear here after a run.")

    with tab_logs:
        if st.session_state.logs:
            log_text = "\n".join(st.session_state.logs)
            st.markdown(
                f'<div class="log-box">{log_text.replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True,
            )
            st.download_button("⬇️ Download Logs", data=log_text, file_name="agent_logs.txt")
        else:
            st.info("Pipeline logs will appear here during/after a run.")

    with tab_graph:
        st.markdown("### Pipeline Graph")
        # Simple ASCII / markdown graph since mermaid isn't always available
        st.markdown("""
```
read_jira
    ↓
generate_code
    ↓
execute_code ──── (error + attempts left) ──→ self_correct
    │                                               ↓
    │ (success)                              execute_code (retry)
    ↓
push_github
    ↓
close_jira
    ↓
  [END]
```
        """)
        st.caption("Conditional edge: after execute_code — route to self_correct if error, else push_github.")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline execution (synchronous with spinner)
# ─────────────────────────────────────────────────────────────────────────────

if run_clicked and PIPELINE_AVAILABLE:
    st.session_state.final_state  = None
    st.session_state.running      = True
    st.session_state.logs         = [f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline started for {issue_key}"]
    st.session_state.current_step = "read_jira"

    with st.spinner(f"⚙️ Running pipeline for {issue_key} — please wait …"):
        try:
            final_state = run_pipeline(issue_key, max_corrections=max_corrections)
            st.session_state.final_state  = final_state
            st.session_state.running      = False
            st.session_state.current_step = None
            st.session_state.logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Pipeline complete"
            )
            st.session_state.run_history.append({
                "time":    datetime.now().strftime("%H:%M"),
                "issue":   final_state.get("issue_key", issue_key),
                "pr":      final_state.get("pr_url", ""),
                "success": final_state.get("jira_closed", False),
            })
        except Exception as e:
            st.session_state.running = False
            st.session_state.logs.append(f"[ERROR] {str(e)}")
            st.error(f"Pipeline error: {e}")
    st.rerun()