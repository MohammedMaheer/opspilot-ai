from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.orchestrator import OpsPilot

ROOT = Path(__file__).resolve().parent
SOP_PATH = ROOT / "data" / "sops.md"
AUDIT_PATH = ROOT / "data" / "audit_log.jsonl"
SAMPLES_PATH = ROOT / "data" / "sample_tickets.csv"

st.set_page_config(page_title="OpsPilot AI", page_icon="🛠️", layout="wide")

st.title("OpsPilot AI")
st.caption("AI-assisted facilities work-order triage, grounded in SOPs with deterministic safety and SLA controls.")

engine = OpsPilot(str(SOP_PATH), str(AUDIT_PATH))

with st.sidebar:
    st.subheader("Runtime")
    if engine.llm.enabled:
        st.success(f"LLM enabled · {engine.llm.model}")
    else:
        st.warning("Deterministic demo mode")
        st.caption("Add LLM_API_KEY (or DEEPSEEK_API_KEY) to enable AI normalization and SOP-grounded planning.")
    st.markdown("**What AI does**")
    st.caption("Normalizes messy tickets and synthesizes next actions from retrieved SOPs.")
    st.markdown("**What AI does not decide**")
    st.caption("Safety escalation, priority/SLA, and team routing are rule-controlled.")

new_tab, batch_tab, architecture_tab = st.tabs(["New work order", "Demo queue", "Why this architecture"])

with new_tab:
    with st.form("ticket_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            description = st.text_area(
                "Issue description",
                value="There is water leaking from the ceiling near an electrical panel on floor 3.",
                height=120,
            )
        with c2:
            location = st.text_input("Location", value="Commercial Tower - Floor 3")
            impact = st.selectbox("Operational impact", ["one person", "several people", "multiple rooms", "many people", "business critical"])
        submitted = st.form_submit_button("Run triage", use_container_width=True)

    if submitted and description.strip():
        result = engine.process_ticket(description.strip(), location.strip() or "Unknown", impact)
        st.session_state["latest_result"] = result

    result = st.session_state.get("latest_result")
    if result:
        routing = result["routing"]
        structured = result["structured_ticket"]
        safety = result["safety_gate"]
        resolution = result["resolution"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Priority", routing["priority"])
        m2.metric("Response target", f"{routing['sla_minutes']} min")
        m3.metric("Route", routing["team"])
        m4.metric("Confidence", structured["confidence"])

        if safety["triggered"]:
            st.error("Safety gate triggered: " + "; ".join(safety["hits"]))
        if resolution["human_review_required"]:
            st.warning("Human review required before treating the AI plan as an operational instruction.")

        left, right = st.columns(2)
        with left:
            st.subheader("Structured ticket")
            st.write(f"**Summary:** {structured['summary']}")
            st.write(f"**Category:** {structured['category']}")
            st.write(f"**Asset / area:** {structured['asset_or_area']}")
            if structured["missing_information"]:
                st.write("**Missing information:**")
                for item in structured["missing_information"]:
                    st.write(f"- {item}")

            st.subheader("Recommended next actions")
            for i, action in enumerate(resolution["recommended_actions"], 1):
                st.write(f"{i}. {action}")

        with right:
            st.subheader("Technician handoff")
            st.info(resolution["technician_brief"])
            st.subheader("Manager update")
            st.info(resolution["manager_update"])
            st.write("**Grounding:** " + ", ".join(resolution["cited_sops"]) if resolution["cited_sops"] else "**Grounding:** none")
            if resolution["uncertainty_note"]:
                st.caption("Uncertainty: " + resolution["uncertainty_note"])

        with st.expander("Show retrieved SOP evidence and decision trace"):
            st.json({
                "mode": result["mode"],
                "safety_gate": result["safety_gate"],
                "routing": result["routing"],
                "retrieval": result["retrieval"],
                "explainability": result["explainability"],
            })

with batch_tab:
    samples = pd.read_csv(SAMPLES_PATH)
    st.dataframe(samples, use_container_width=True, hide_index=True)
    selected = st.selectbox("Pick a sample", samples["id"].tolist())
    if st.button("Process selected sample"):
        row = samples.loc[samples["id"] == selected].iloc[0]
        batch_result = engine.process_ticket(row["description"], row["location"], row["impact"])
        st.json(batch_result)

with architecture_tab:
    st.markdown(
        """
### The judgment call

A facilities triage system should **not** let an LLM freely decide whether a safety event is urgent or what SLA applies. OpsPilot therefore splits the workflow:

1. **Safety gate — deterministic:** catches explicit high-risk patterns and forces escalation.
2. **Ticket normalizer — AI when available:** turns messy natural language into a consistent structure.
3. **SOP retrieval — deterministic:** retrieves the most relevant approved procedures.
4. **Resolution planner — AI when available:** summarizes only from the ticket + retrieved SOP context.
5. **Routing/SLA — deterministic:** assigns team, priority, and response target through policy rules.
6. **Handoff + audit:** produces technician/manager summaries and stores a trace of what was decided and why.

This is intentionally a thin prototype. In production, the biggest work would be integrations, approved SOP ingestion, role-based access, feedback measurement, and site-specific policy configuration—not adding more agents for the sake of it.
        """
    )
