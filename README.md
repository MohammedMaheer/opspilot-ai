# OpsPilot AI — Facilities Work-Order Triage & Resolution Copilot

**DivyaSree Group — Forward Deployed Engineer, Open Track submission**

OpsPilot AI is a thin, deployable prototype for turning messy facilities complaints into a structured, auditable work order with the right priority, team, SOP evidence, and handoff.

The core design decision is deliberate: **LLMs help with language and synthesis; rules own safety, SLA, and routing.**

> This repository uses synthetic sample tickets and synthetic SOP excerpts created for the assignment. It does not contain or claim access to DivyaSree internal data.

## Problem

A multi-asset organisation receives operational issues in inconsistent language: “AC not working”, “water near panel”, “card not opening”, “two people stuck in lift”. A human helpdesk must understand the issue, judge urgency, find the right SOP, send it to the correct team, and explain the response to stakeholders.

That workflow is repetitive, but it is also safety-sensitive. A pure chatbot is the wrong architecture.

## What OpsPilot does

1. **Safety gate (rules):** catches high-risk reports such as smoke, sparks, exposed wires, gas, lift entrapment, or water near electrical equipment.
2. **Ticket normalization (LLM, optional):** converts free text into a category, short summary, symptoms, missing info, and confidence.
3. **SOP retrieval (deterministic):** finds relevant procedure excerpts from the local SOP library.
4. **Resolution planning (LLM, optional):** creates next actions using only the ticket and retrieved SOP evidence.
5. **Routing + SLA (rules):** assigns the responsible team, priority, and response target.
6. **Handoff + audit:** generates technician and manager summaries and records the full decision trace.

With no API key, the app still runs end-to-end in deterministic demo mode. With an OpenAI-compatible LLM key, AI normalization and SOP-grounded planning switch on automatically.

## Architecture

```text
User / Helpdesk Ticket
        |
        v
[Deterministic Safety Gate] ---- high risk ----> Human / emergency escalation
        |
        v
[AI Ticket Normalizer]  (optional; fallback available)
        |
        +----> [Deterministic Category / Priority / SLA rules]
        |
        v
[TF-IDF SOP Retriever]
        |
        v
[AI Resolution Planner] (ticket + SOP excerpts only)
        |
        v
[Technician Handoff + Manager Update + Audit Log]
```

### Why not make everything agentic?

Because “more agents” is not the goal. Safety escalation and policy decisions should be predictable, testable, and reviewable. AI is used where it genuinely helps: understanding messy text and compressing relevant SOP context into a usable action plan.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

### Enable an LLM

Copy `.env.example` values into your shell/environment. For example:

```bash
export LLM_API_KEY="your-key"
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_MODEL="deepseek-chat"
streamlit run app.py
```

Any provider exposing an OpenAI-compatible `/chat/completions` endpoint can be substituted with environment variables.

## Demo path

Use the included samples under **Demo queue**:

- HVAC issue affecting multiple rooms → normal triage and HVAC routing.
- Lift entrapment → P0 safety escalation; AI cannot downgrade it.
- Burning socket → P0 electrical safety escalation.
- Single access-card issue → low-priority security routing.

Then enter a deliberately ambiguous ticket such as:

> "Something is leaking near the utility area and the lights flickered once."

The useful behaviour is not pretending certainty: the system should route conservatively, surface missing information, and require review where confidence is low.

## Tests

```bash
pytest -q
```

The included tests focus on the non-negotiable deterministic layer: safety detection, priority, and category routing.

## What I would add before production

- Real CMMS/helpdesk integration (ServiceNow, Jira, custom FM system, email/WhatsApp intake).
- Approved DivyaSree SOPs with versioning, permissions, and site-level policy overrides.
- Asset master data and BMS/IoT context.
- RBAC, SSO, PII controls, audit retention, and escalation matrices.
- Human feedback capture: accepted/overridden priority, route, and resolution plan.
- Evaluation against historical tickets: routing accuracy, false-negative safety rate, mean acknowledgement time, repeat-ticket rate, and technician acceptance.
- Model fallback and cost/latency routing across providers.

## Known failure modes

- Users omit critical context or describe hazards indirectly.
- Site-specific terminology can break generic category rules.
- SOP retrieval can surface the wrong procedure if the knowledge base is poorly structured.
- LLM output can still be wrong even when grounded; it must not become the source of truth for safety or policy.
- Real deployment depends more on integrations and change management than the UI shown here.

## Scope choice

I intentionally did **not** build predictive maintenance, computer vision, BMS ingestion, voice intake, or a full CMMS. Those could be valuable later, but they would reduce signal for this build. The narrow question here is: *can an underspecified facilities issue become a safer, faster, traceable work order?*

## Author

**Mohammed Maheer** — Bengaluru, India  
GitHub: https://github.com/MohammedMaheer  
LeadSign AI: https://leadsignai.duckdns.org/
