from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SafetyHit:
    rule_id: str
    label: str
    severity: str
    matched_phrase: str


SAFETY_RULES = [
    ("SAFE-001", "Fire / smoke", "P0", r"\b(fire|smoke|burning smell|sparks?)\b"),
    ("SAFE-002", "Gas leak", "P0", r"\b(gas leak|lpg smell|gas smell)\b"),
    ("SAFE-003", "Electrical exposure", "P0", r"\b(exposed wire|live wire|electric shock|electrocution|short circuit)\b"),
    ("SAFE-004", "Elevator entrapment", "P0", r"\b(stuck (?:in|inside) (?:the )?(?:lift|elevator)|trapped (?:in|inside) (?:the )?(?:lift|elevator)|(?:lift|elevator) entrapment)\b"),
    ("SAFE-005", "Flooding near electrical", "P0", r"\b(flood|flooding|water leak)\b.*\b(electrical|panel|socket|wire)\b|\b(electrical|panel|socket|wire)\b.*\b(flood|flooding|water leak)\b"),
    ("SAFE-006", "Major structural concern", "P0", r"\b(ceiling collapse|wall collapse|structural crack|falling debris)\b"),
]

CATEGORY_RULES = [
    ("electrical", r"\b(power|electric|electrical|socket|light|breaker|mcb|ups|generator)\b"),
    ("hvac", r"\b(ac|air.?condition|hvac|cooling|chiller|temperature|ventilation)\b"),
    ("plumbing", r"\b(water|leak|tap|pipe|drain|toilet|flush|plumbing)\b"),
    ("elevator", r"\b(lift|elevator)\b"),
    ("housekeeping", r"\b(clean|spill|garbage|waste|housekeeping|odou?r|dirty)\b"),
    ("security", r"\b(access card|security|intruder|cctv|door lock|badge)\b"),
    ("it_av", r"\b(wifi|internet|network|projector|display|av |audio|video|lan)\b"),
    ("civil", r"\b(door|window|wall|ceiling|floor|tile|carpentry|paint|civil)\b"),
]

TEAM_BY_CATEGORY: Dict[str, str] = {
    "electrical": "Electrical & Utilities",
    "hvac": "HVAC / MEP",
    "plumbing": "Plumbing / MEP",
    "elevator": "Lift Operations / OEM",
    "housekeeping": "Housekeeping",
    "security": "Security Operations",
    "it_av": "IT / AV Support",
    "civil": "Civil / General Maintenance",
    "general": "Facilities Helpdesk",
}

SLA_MINUTES = {"P0": 5, "P1": 30, "P2": 240, "P3": 1440}


def safety_scan(text: str) -> List[SafetyHit]:
    normalized = text.lower().strip()
    hits: List[SafetyHit] = []
    for rule_id, label, severity, pattern in SAFETY_RULES:
        match = re.search(pattern, normalized, re.I)
        if match:
            hits.append(SafetyHit(rule_id, label, severity, match.group(0)))
    return hits


def infer_category(text: str) -> str:
    normalized = text.lower()
    for category, pattern in CATEGORY_RULES:
        if re.search(pattern, normalized, re.I):
            return category
    return "general"


def infer_priority(text: str, impact: str, safety_hits: List[SafetyHit]) -> str:
    if safety_hits:
        return "P0"

    normalized = text.lower()
    impact = impact.lower()

    if any(p in normalized for p in ["entire building", "whole floor", "no power", "server room", "main gate"]):
        return "P1"
    if impact in {"many people", "business critical"}:
        return "P1"
    if impact in {"several people", "multiple rooms"}:
        return "P2"
    return "P3"


def routing_decision(category: str, priority: str) -> Dict[str, object]:
    return {
        "team": TEAM_BY_CATEGORY.get(category, TEAM_BY_CATEGORY["general"]),
        "priority": priority,
        "sla_minutes": SLA_MINUTES[priority],
        "source": "deterministic_rules",
    }
