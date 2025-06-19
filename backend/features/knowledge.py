import json
import os
import time
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any


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

    def add_facts(self, topic: str, facts: List[str]) -> bool:
        """Store new facts for a topic with timestamp.

        Returns True if any new fact was added."""
        ts = time.time()
        learned = False
        self.data.setdefault("facts", [])
        for fact in facts:
            if not fact:
                continue
            key = (topic.strip().lower(), fact.strip().lower())
            if any(key == (f.get("topic", "").lower(), f.get("fact", "").lower()) for f in self.data["facts"]):
                continue
            self.data["facts"].append({
                "topic": topic,
                "fact": fact.strip(),
                "timestamp": ts
            })
            learned = True
        if learned:
            self.save()
        return learned

    def add_qa(self, question: str, answer: str) -> bool:
        """Store a new question/answer pair.

        Returns True if it was a new entry."""
        ts = time.time()
        self.data.setdefault("qa", [])
        normalized = question.strip().lower()
        for qa in self.data["qa"]:
            if qa.get("question", "").strip().lower() == normalized:
                return False
        self.data["qa"].append({
            "question": question.strip(),
            "answer": answer.strip(),
            "timestamp": ts
        })
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
