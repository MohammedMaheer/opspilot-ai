from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests


class LLMClient:
    """Small OpenAI-compatible client.

    Defaults are compatible with DeepSeek. Set LLM_BASE_URL / LLM_MODEL to use
    another provider. The app remains fully demoable without an API key.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "25"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _chat(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        if not self.enabled:
            raise RuntimeError("No LLM API key configured")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": messages, "temperature": temperature},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _json_from_text(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

    def structure_ticket(self, description: str, location: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        system = (
            "You structure facilities work orders. Return JSON only. Never invent asset IDs, people, or facts. "
            "Fields: summary (<=18 words), category (electrical|hvac|plumbing|elevator|housekeeping|security|it_av|civil|general), "
            "asset_or_area, symptoms (array), missing_information (array), confidence (0-1)."
        )
        prompt = f"Location: {location}\nUser report: {description}"
        try:
            return self._json_from_text(self._chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}]))
        except Exception:
            return None

    def plan_resolution(
        self,
        description: str,
        location: str,
        category: str,
        priority: str,
        sops: List[Dict[str, object]],
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        sop_text = "\n\n".join(
            f"[{x['id']}] {x['title']}\n{x['text']}" for x in sops
        )
        system = (
            "You are a facilities resolution planning assistant. Use only the supplied ticket and SOP excerpts. "
            "Do not override safety or SLA rules. If evidence is weak, ask for human review. Return JSON only with: "
            "recommended_actions (array, max 4), technician_brief, manager_update, cited_sops (array of SOP IDs), "
            "human_review_required (bool), uncertainty_note."
        )
        user = (
            f"Ticket: {description}\nLocation: {location}\nCategory: {category}\nPriority: {priority}\n\n"
            f"SOP excerpts:\n{sop_text}"
        )
        try:
            return self._json_from_text(self._chat([{"role": "system", "content": system}, {"role": "user", "content": user}]))
        except Exception:
            return None
