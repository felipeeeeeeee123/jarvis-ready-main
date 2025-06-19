import json
import os
import time
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any


def _count_tokens(text: str) -> int:
    return len(text.split())


class KnowledgeBase:
    """Simple JSON-backed knowledge store."""

    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            path = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge.json')
        self.path = os.path.abspath(path)
        self.data: Dict[str, Any] = {"facts": [], "qa": []}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    self.data = {"facts": [], "qa": []}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def add_facts(self, topic: str, facts: List[str], source: str | None = None) -> bool:
        """Store new facts for a topic with timestamp.

        Returns True if any new fact was added. Facts that already exist will
        have their count increased."""

        ts = time.time()
        learned = False
        self.data.setdefault("facts", [])
        for fact in facts:
            if not fact:
                continue
            key = (topic.strip().lower(), fact.strip().lower())
            existing = None
            for f in self.data["facts"]:
                if key == (f.get("topic", "").lower(), f.get("fact", "").lower()):
                    existing = f
                    break
            if existing:
                existing["count"] = existing.get("count", 1) + 1
                existing["timestamp"] = ts
                existing["confidence"] = existing.get("confidence", 1.0) + 0.1
                learned = True
                continue
            entry = {
                "topic": topic,
                "fact": fact.strip(),
                "timestamp": ts,
                "count": 1,
                "tokens": _count_tokens(fact),
                "confidence": 1.0,
            }
            if source:
                entry["source"] = source
            self.data["facts"].append(entry)
            learned = True
        if learned:
            self.save()
        return learned

    def add_qa(self, question: str, answer: str, source: str | None = None) -> bool:
        """Store a new question/answer pair.

        Returns True if it was a new entry."""
        ts = time.time()
        self.data.setdefault("qa", [])
        normalized = question.strip().lower()
        for qa in self.data["qa"]:
            if qa.get("question", "").strip().lower() == normalized:
                return False
        entry = {
            "question": question.strip(),
            "answer": answer.strip(),
            "timestamp": ts,
            "tokens": _count_tokens(answer),
            "confidence": 1.0,
        }
        if source:
            entry["source"] = source
        self.data["qa"].append(entry)
        self.save()
        return True

    def find_similar_question(self, question: str, threshold: float = 0.6) -> Optional[Dict[str, str]]:
        """Return the most similar past QA pair if above threshold."""
        question = question.lower().strip()
        best_score = 0.0
        best_entry = None
        for entry in self.data.get("qa", []):
            q = entry.get("question", "").lower().strip()
            score = SequenceMatcher(None, question, q).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_entry = entry
        return best_entry

    def update_answer(self, question: str, new_answer: str, confidence: float | None = None) -> None:
        """Replace the stored answer for an existing question."""
        normalized = question.strip().lower()
        for qa in self.data.get("qa", []):
            if qa.get("question", "").strip().lower() == normalized:
                qa["answer"] = new_answer.strip()
                qa["timestamp"] = time.time()
                qa["tokens"] = _count_tokens(new_answer)
                if confidence is not None:
                    qa["confidence"] = confidence
                self.save()
                break

    def get_facts(self, topic: str) -> List[Dict[str, Any]]:
        """Return all facts stored for a topic."""
        return [f for f in self.data.get("facts", []) if f.get("topic", "").lower() == topic.strip().lower()]

    def prune(self, max_age_days: int = 30, min_count: int = 1) -> None:
        """Remove facts older than `max_age_days` with low count."""
        cutoff = time.time() - max_age_days * 86400
        new_facts = [
            f for f in self.data.get("facts", [])
            if f.get("timestamp", 0) >= cutoff or f.get("count", 1) > min_count
        ]
        if len(new_facts) != len(self.data.get("facts", [])):
            self.data["facts"] = new_facts
            self.save()

    def cleanup_low_quality(self, min_tokens: int = 3) -> None:
        """Remove entries with too few tokens."""
        changed = False
        facts = [f for f in self.data.get("facts", []) if f.get("tokens", _count_tokens(f.get("fact", ""))) >= min_tokens]
        if len(facts) != len(self.data.get("facts", [])):
            self.data["facts"] = facts
            changed = True
        qa = [q for q in self.data.get("qa", []) if q.get("tokens", _count_tokens(q.get("answer", ""))) >= min_tokens]
        if len(qa) != len(self.data.get("qa", [])):
            self.data["qa"] = qa
            changed = True
        if changed:
            self.save()

    def deduplicate(self) -> None:
        """Remove duplicate facts and questions."""
        seen_facts = set()
        unique_facts = []
        for f in self.data.get("facts", []):
            key = (f.get("topic", "").lower(), f.get("fact", "").strip().lower())
            if key not in seen_facts:
                seen_facts.add(key)
                unique_facts.append(f)
        self.data["facts"] = unique_facts

        seen_q = set()
        unique_qa = []
        for qa in self.data.get("qa", []):
            q = qa.get("question", "").strip().lower()
            if q not in seen_q:
                seen_q.add(q)
                unique_qa.append(qa)
        self.data["qa"] = unique_qa

        self.save()
