from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .llm import LLMClient
from .retrieval import load_sops, retrieve_sops
from .rules import infer_category, infer_priority, routing_decision, safety_scan


class OpsPilot:
    def __init__(self, sop_path: str, audit_path: Optional[str] = None) -> None:
        self.sops = load_sops(sop_path)
        self.llm = LLMClient()
        self.audit_path = Path(audit_path) if audit_path else None

    def process_ticket(self, description: str, location: str, impact: str = "one person") -> Dict[str, object]:
        safety_hits = safety_scan(description)
        ai_structured = self.llm.structure_ticket(description, location)

        rule_category = infer_category(description)
        ai_category = ai_structured.get("category") if ai_structured else None
        category = ai_category if ai_category in {
            "electrical", "hvac", "plumbing", "elevator", "housekeeping", "security", "it_av", "civil", "general"
        } else rule_category

        priority = infer_priority(description, impact, safety_hits)
        route = routing_decision(category, priority)
        retrieved = retrieve_sops(f"{category} {description}", self.sops, top_k=3)
        ai_plan = self.llm.plan_resolution(description, location, category, priority, retrieved)

        if ai_structured:
            summary = ai_structured.get("summary") or description[:120]
            missing_information = ai_structured.get("missing_information", [])
            confidence = float(ai_structured.get("confidence", 0.6) or 0.6)
            asset_or_area = ai_structured.get("asset_or_area") or location
        else:
            summary = description.strip().split(".")[0][:120]
            missing_information = ["Exact asset ID / room number if available"]
            confidence = 0.55
            asset_or_area = location

        safety_labels = [f"{x.rule_id}: {x.label}" for x in safety_hits]
        human_review = bool(safety_hits) or confidence < 0.6

        if ai_plan:
            actions = ai_plan.get("recommended_actions", [])
            technician_brief = ai_plan.get("technician_brief", "")
            manager_update = ai_plan.get("manager_update", "")
            cited_sops = ai_plan.get("cited_sops", [])
            human_review = human_review or bool(ai_plan.get("human_review_required", False))
            uncertainty = ai_plan.get("uncertainty_note", "")
            mode = "llm_plus_rules"
        else:
            actions = self._fallback_actions(category, priority, bool(safety_hits))
            technician_brief = (
                f"{priority} {category} ticket at {location}. Verify the reported condition, follow the relevant SOP, "
                "record observations, action taken, and any parts/vendor dependency."
            )
            manager_update = (
                f"Ticket routed to {route['team']} with {priority} priority and a {route['sla_minutes']}-minute response target."
            )
            cited_sops = [x["id"] for x in retrieved[:2]]
            uncertainty = "LLM is disabled; generated using deterministic fallback and retrieved SOPs."
            mode = "deterministic_demo"

        result: Dict[str, object] = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "input": {"description": description, "location": location, "impact": impact},
            "mode": mode,
            "structured_ticket": {
                "summary": summary,
                "category": category,
                "asset_or_area": asset_or_area,
                "missing_information": missing_information,
                "confidence": round(confidence, 2),
            },
            "safety_gate": {
                "triggered": bool(safety_hits),
                "hits": safety_labels,
                "decision_source": "deterministic_rules",
            },
            "routing": route,
            "retrieval": retrieved,
            "resolution": {
                "recommended_actions": actions,
                "technician_brief": technician_brief,
                "manager_update": manager_update,
                "cited_sops": cited_sops,
                "human_review_required": human_review,
                "uncertainty_note": uncertainty,
            },
            "explainability": {
                "ai_used_for": ["unstructured ticket normalization", "SOP-grounded action synthesis"] if mode == "llm_plus_rules" else [],
                "ai_not_used_for": ["safety escalation", "priority/SLA", "team routing"],
            },
        }
        self._audit(result)
        return result

    def _audit(self, result: Dict[str, object]) -> None:
        if not self.audit_path:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    @staticmethod
    def _fallback_actions(category: str, priority: str, safety: bool) -> List[str]:
        if safety:
            return [
                "Do not attempt remote diagnosis as a substitute for on-site safety response.",
                "Escalate to the responsible emergency/facilities contact immediately.",
                "Isolate the affected area or equipment only if trained and safe to do so.",
                "Record the event and hand off to the designated technical team.",
            ]
        base = {
            "electrical": ["Verify affected circuit/area", "Check breaker/UPS status", "Record voltage or visible fault if trained"],
            "hvac": ["Confirm room temperature and affected zone", "Check BMS/thermostat alarms", "Inspect filter/airflow and unit status"],
            "plumbing": ["Locate source of leak/blockage", "Contain water where possible", "Check isolation valve and downstream impact"],
            "elevator": ["Confirm lift ID and current floor", "Check controller/alarm status", "Escalate to lift OEM if fault persists"],
            "housekeeping": ["Secure the affected area", "Remove spill/waste safely", "Record recurring source if applicable"],
            "security": ["Verify identity/access issue", "Check access-control/CCTV event logs", "Escalate suspicious activity to security lead"],
            "it_av": ["Reproduce issue", "Check power/network path", "Restart only where approved and document result"],
            "civil": ["Inspect affected element", "Make area safe if there is a trip/fall risk", "Record dimensions/photos for maintenance"],
            "general": ["Validate issue on site", "Capture asset/location details", "Route to specialist if a specific trade is identified"],
        }
        actions = base.get(category, base["general"])
        if priority in {"P0", "P1"}:
            actions = ["Acknowledge immediately and contact the on-duty facilities lead"] + actions
        return actions[:4]
