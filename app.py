"""ClaimPilot — Streamlit interface.

Run with:  .venv/bin/streamlit run app.py
"""

import io
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from claimpilot.models import ClaimPipelineResult

load_dotenv()  # pick up ANTHROPIC_API_KEY / OPENAI_API_KEY from .env

st.set_page_config(page_title="ClaimPilot", page_icon="🩺", layout="wide")

SAMPLE_DOC = Path(__file__).parent / "sample_docs" / "visit_amara_okafor.txt"

SEVERITY_BADGE = {"blocker": "🔴 Blocker", "warning": "🟡 Warning", "info": "🔵 Info"}


def read_uploaded_files(files) -> str:
    """Concatenate uploaded files into one text blob (txt directly, pdf via pypdf)."""
    chunks = []
    for f in files:
        if f.name.lower().endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(f.read()))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = f.read().decode("utf-8", errors="replace")
        chunks.append(f"===== FILE: {f.name} =====\n{text}")
    return "\n\n".join(chunks)


def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🩺 ClaimPilot")
    st.caption("AI that gets insurance claims approved the first time.")

    insurer = st.selectbox("Insurer", ["DentiCare Plus"], help="One insurer in the MVP; add more rule files to expand.")

    key_available = has_api_key()
    demo_mode = st.toggle(
        "Demo mode (no API key needed)",
        value=not key_available,
        help="Runs a canned pipeline so you can click through the whole flow.",
    )
    if not key_available and not demo_mode:
        st.warning("No ANTHROPIC_API_KEY or OPENAI_API_KEY found — only demo mode will work.")
    if key_available and not demo_mode:
        st.success("API key detected — live CrewAI agents will run.")

    st.divider()
    st.markdown(
        "**Pipeline**\n\n"
        "1. 📄 Extractor — reads the documents\n"
        "2. 🔍 Rule Checker — audits against insurer rules\n"
        "3. 🔧 Fixer — repairs what it can\n"
        "4. ✍️ Claim Writer — produces the clean claim\n"
        "5. 👤 **You** — review and approve"
    )

# ---------------------------------------------------------------- state
if "result" not in st.session_state:
    st.session_state.result = None
if "decision" not in st.session_state:
    st.session_state.decision = None

# ---------------------------------------------------------------- upload
st.header("1 · Upload visit documents")

col_up, col_sample = st.columns([3, 1])
with col_up:
    files = st.file_uploader(
        "Bill, clinical notes, lab results, prescriptions (.txt or .pdf)",
        type=["txt", "pdf"],
        accept_multiple_files=True,
    )
with col_sample:
    st.write("")
    st.write("")
    use_sample = st.button("📎 Use sample visit", use_container_width=True)

documents_text = None
if use_sample:
    st.session_state.documents_text = SAMPLE_DOC.read_text()
    st.session_state.doc_label = "Sample: Amara Okafor — crown, filling, whitening"
elif files:
    st.session_state.documents_text = read_uploaded_files(files)
    st.session_state.doc_label = ", ".join(f.name for f in files)

if st.session_state.get("documents_text"):
    with st.expander(f"Loaded: {st.session_state.doc_label}", expanded=False):
        st.text(st.session_state.documents_text[:4000])

    if st.button("🚀 Run claim check", type="primary"):
        st.session_state.result = None
        st.session_state.decision = None
        status = st.status("Running ClaimPilot pipeline…", expanded=True)

        try:
            if demo_mode:
                from claimpilot.demo import run_demo_pipeline

                result = run_demo_pipeline(
                    st.session_state.documents_text,
                    progress_callback=lambda msg: status.write(msg),
                )
            else:
                from claimpilot.crew import run_pipeline

                status.write("Spinning up CrewAI agents (this takes a minute or two)…")
                result = run_pipeline(st.session_state.documents_text)
            st.session_state.result = result
            status.update(label="Pipeline complete", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Error: {e}")

# ---------------------------------------------------------------- results
result: ClaimPipelineResult | None = st.session_state.result
if result:
    st.header("2 · What the AI found")

    ex = result.extracted
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Patient", ex.patient_name)
    m2.metric("Total billed", f"${ex.total_billed:,.2f}")
    m3.metric("Issues found", len(result.rule_check.issues))
    blockers = [i for i in result.rule_check.issues if i.severity == "blocker"]
    m4.metric("Blockers", len(blockers), delta_color="inverse")

    chance = result.rule_check.estimated_approval_chance
    chance_msg = {
        "high": ("✅ High chance of first-pass approval as-is.", st.success),
        "medium": ("⚠️ Medium chance of approval — fix the warnings.", st.warning),
        "low": ("🚫 Low chance of approval as-is — this claim would have been rejected.", st.error),
    }
    msg, fn = chance_msg[chance]
    fn(msg)

    tab_issues, tab_fixes, tab_extract = st.tabs(["🔍 Issues", "🔧 Fixes applied", "📄 Extracted data"])

    with tab_issues:
        for issue in result.rule_check.issues:
            with st.container(border=True):
                c1, c2 = st.columns([1, 5])
                c1.markdown(f"**{SEVERITY_BADGE[issue.severity]}**")
                c1.caption(f"Rule {issue.rule_reference}")
                c2.markdown(f"**{issue.field}** — {issue.problem}")
                c2.markdown(f"→ *{issue.suggested_fix}*")

    with tab_fixes:
        for fix in result.fixes.fixes:
            icon = "👤" if fix.needs_human else "🤖"
            with st.container(border=True):
                st.markdown(f"{icon} **{fix.issue_field}** — {fix.action_taken}")
                if fix.note_to_staff:
                    st.info(f"Action for staff: {fix.note_to_staff}")
        if result.fixes.remaining_blockers:
            st.error("**Unresolved blockers:**\n\n" + "\n".join(f"- {b}" for b in result.fixes.remaining_blockers))

    with tab_extract:
        st.json(json.loads(ex.model_dump_json()))

    # ------------------------------------------------------------ final claim
    st.header("3 · Review the claim")

    claim = result.claim
    with st.container(border=True):
        st.subheader(
            ("📋 Prior-Authorization Request" if claim.claim_type == "prior_authorization" else "📋 Insurance Claim")
            + f" — {claim.insurer}"
        )
        c1, c2 = st.columns(2)
        c1.markdown(
            f"**Patient:** {claim.patient_name}\n\n"
            f"**Member ID:** `{claim.member_id}`\n\n"
            f"**Provider:** {claim.provider_name}"
        )
        c2.markdown(
            f"**Visit date:** {claim.visit_date}\n\n"
            f"**Total claimed:** ${claim.total_claimed:,.2f}\n\n"
            f"**Diagnosis:** {claim.diagnosis}"
        )

        st.markdown("**Procedures**")
        st.table(
            [
                {"Code": p.code, "Description": p.description, "Tooth/site": p.tooth_or_site or "—", "Fee": f"${p.fee:,.2f}"}
                for p in claim.procedures
            ]
        )

        st.markdown("**Required attachments:** " + " · ".join(claim.attachments_required))
        st.markdown("**Cover note**")
        st.markdown(f"> {claim.cover_note}")

        if claim.ready_to_submit:
            st.success("Guardrail check passed — claim is complete and ready to submit.")
        else:
            st.warning("Guardrail: this claim is NOT ready to submit until the unresolved blockers above are cleared.")

    # ------------------------------------------------------------ human-in-the-loop
    st.header("4 · Your decision")
    st.caption("Nothing is sent anywhere without a human approving it.")

    d1, d2, d3 = st.columns(3)
    if d1.button("✅ Approve claim", type="primary", use_container_width=True):
        st.session_state.decision = "approved"
    if d2.button("↩️ Send back for correction", use_container_width=True):
        st.session_state.decision = "rejected"
    claim_json = claim.model_dump_json(indent=2)
    d3.download_button(
        "⬇️ Download claim (JSON)",
        data=claim_json,
        file_name=f"claim_{claim.patient_name.replace(' ', '_').lower()}.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.session_state.decision == "approved":
        if claim.ready_to_submit:
            st.success("Claim approved and queued for submission. 🎉")
        else:
            st.warning(
                "Approved with pending items — the claim is queued but will only be "
                "submitted once the missing attachments are added."
            )
    elif st.session_state.decision == "rejected":
        st.info("Sent back to the AI pipeline with staff feedback. (In the full product, your correction is stored and used as training signal — ‘this insurer always wants X attached’.)")
