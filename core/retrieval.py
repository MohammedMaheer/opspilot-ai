from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_sops(path: str | Path) -> List[Dict[str, str]]:
    text = Path(path).read_text(encoding="utf-8")
    chunks: List[Dict[str, str]] = []
    current_id = None
    current_title = None
    current_lines: List[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_id:
                chunks.append({"id": current_id, "title": current_title or current_id, "text": "\n".join(current_lines).strip()})
            header = line[3:].strip()
            parts = header.split(" — ", 1)
            current_id = parts[0].strip()
            current_title = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_id:
        chunks.append({"id": current_id, "title": current_title or current_id, "text": "\n".join(current_lines).strip()})
    return chunks


def retrieve_sops(query: str, sops: List[Dict[str, str]], top_k: int = 3) -> List[Dict[str, object]]:
    if not sops:
        return []
    corpus = [f"{x['title']} {x['text']}" for x in sops]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(corpus + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = scores.argsort()[::-1][:top_k]
    results = []
    for idx in ranked:
        results.append({**sops[idx], "score": round(float(scores[idx]), 3)})
    return results
