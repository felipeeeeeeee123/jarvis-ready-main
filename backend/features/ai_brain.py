import re
import requests
from collections import deque

from backend.utils.memory import MemoryManager
from backend.features.web_search import (
    web_search,
    _extract_keywords,
    _contains_keyword,
    _keyword_overlap,
)
from backend.features.knowledge import KnowledgeBase

class AIBrain:
    def __init__(self, model="mistral"):
        self.model = model
        self.memory = MemoryManager()
        self.knowledge = KnowledgeBase()
        self.history = deque(self.memory.memory.get("history", []), maxlen=5)

    def ask(self, prompt: str) -> str:
        self.memory.memory["last_prompt"] = prompt
        self.history.append({"prompt": prompt, "answer": ""})
        self.knowledge.prune()
        self.knowledge.cleanup_low_quality()
        keywords = _extract_keywords(prompt)
        source = None

        facts: list[str] = []
        learned = False
        try:
            search_text = web_search(prompt)
            source = getattr(web_search, "last_used_source", None)
            raw_lines = [line.strip() for line in search_text.splitlines() if line.strip()]
            # ignore placeholder lines and filter for relevance
            all_facts = [l for l in raw_lines if not l.startswith('[')]
            facts = [f for f in all_facts if _keyword_overlap(f, keywords) >= 0.3]
            if facts:
                if self.knowledge.add_facts(prompt, facts[:3], source=source):
                    learned = True
        except Exception:
            facts = []  # offline or search failed

        stored_facts = self.knowledge.get_facts(prompt)
        unique_facts = {}
        for f in stored_facts:
            unique_facts.setdefault(f["fact"], []).append(f)
        if len(unique_facts) > 1:
            majority = max(
                unique_facts.items(),
                key=lambda x: (
                    sum(e.get("confidence", 1.0) for e in x[1]),
                    len(x[1]),
                ),
            )[0]
            facts.insert(0, f"[CONFLICT] Multiple facts known, majority: {majority}")

        similar_entry = self.knowledge.find_similar_question(prompt)
        if similar_entry:
            learned = True

        parts = []
        if len(self.history) > 1:
            for h in list(self.history)[-5:-1]:
                if h.get("prompt") and h.get("answer"):
                    parts.append(f"Prev Q: {h['prompt']}\nPrev A: {h['answer']}")
        if facts:
            parts.append("Web facts:\n" + "\n".join(facts))
        if similar_entry:
            parts.append("Past answer:\n" + similar_entry["answer"])
        parts.append(f"User asked: {prompt}")
        enriched_prompt = "\n\n".join(parts)

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": enriched_prompt,
                    "stream": False,
                },
                timeout=10
            )
            answer = response.json().get("response", "").strip()
            if not answer:
                raise ValueError("Ollama returned empty response.")
        except Exception:
            if similar_entry:
                answer = similar_entry["answer"]
            elif facts:
                answer = "\n".join(facts)
            else:
                answer = "[No answer available]"

        if answer == "[No answer available]":
            try:
                res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"Summarize the topic: {prompt}",
                        "stream": False,
                    },
                    timeout=10,
                )
                summary = res.json().get("response", "").strip()
                if summary:
                    answer = f"[Ollama summary] {summary}"
            except Exception:
                pass

        # Determine if the answer is valid and on-topic
        invalid_markers = [
            "[No answer available]",
            "[Ollama fallback",
            "[Web search failed",
            "[No relevant news found]",
            "[No web access",
        ]
        is_valid = not any(m in answer for m in invalid_markers)
        if is_valid:
            is_valid = _contains_keyword(answer, keywords)

        # Persist answer
        self.memory.memory["last_answer"] = answer
        self.memory.memory.setdefault("knowledge", [])
        self.memory.memory["knowledge"].append({"prompt": prompt, "answer": answer})
        if self.history:
            self.history[-1]["answer"] = answer
        self.memory.memory["history"] = list(self.history)
        self.memory.save()

        if is_valid:
            qa_source = source or "ollama"
            if similar_entry and len(answer) > len(similar_entry.get("answer", "")):
                self.knowledge.update_answer(similar_entry["question"], answer)
                learned = True
            else:
                if self.knowledge.add_qa(prompt, answer, source=qa_source):
                    learned = True
        self.knowledge.deduplicate()

        if learned:
            answer += "\n[Learned Memory]"

        return answer
