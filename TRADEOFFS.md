# Short Note — Tradeoffs, Scale Limits, and AI Judgment

I chose a facilities work-order triage problem because it is narrow enough to finish, but common across commercial assets, residences, co-living, hospitality, campuses, and workplace operations.

The main tradeoff was **not** making the whole workflow agentic. An LLM is useful for converting vague complaints into structure and summarising relevant SOPs, but I would not trust it to independently decide whether a situation is safe, what SLA applies, or who owns the incident. In this prototype, safety checks, priority, SLA, and team routing are deterministic and testable. The LLM can add context; it cannot downgrade those controls.

I also used a simple TF-IDF retriever instead of a vector database. For a small demo knowledge base it is fast, transparent, cheap, and good enough to prove the workflow. At production scale I would move to versioned, permission-aware retrieval over approved SOPs and asset data, but only after measuring retrieval quality on real tickets.

Where this breaks: users may omit critical details, site terminology may differ, rules may miss indirect safety language, and an LLM can still produce a plausible but wrong plan. Real deployment therefore needs historical-ticket evaluation, site-specific rule configuration, human overrides, approved escalation matrices, RBAC/SSO, and integrations with the existing FM/helpdesk system.

I deliberately left out predictive maintenance, BMS/IoT ingestion, vision, voice, and a full CMMS. Those are possible extensions, but building them now would hide the core signal: whether we can turn an unstructured complaint into a faster, safer, auditable handoff without pretending AI should own every decision.
