import requests
from backend.utils.memory import MemoryManager
from backend.features.web_search import web_search
from backend.features.knowledge import KnowledgeBase

class AIBrain:
    def __init__(self, model="mistral"):
        self.model = model
        self.memory = MemoryManager()
        self.knowledge = KnowledgeBase()

    def ask(self, prompt: str) -> str:
        self.memory.memory["last_prompt"] = prompt

        facts: list[str] = []
        learned = False
        try:
            search_text = web_search(prompt)
            facts = [line.strip() for line in search_text.splitlines() if line.strip()][:3]
            if facts:
                if self.knowledge.add_facts(prompt, facts):
                    learned = True
        except Exception:
            facts = []  # offline or search failed

        similar_entry = self.knowledge.find_similar_question(prompt)
        if similar_entry:
            learned = True

        parts = []
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

        # Persist answer
        self.memory.memory["last_answer"] = answer
        self.memory.memory.setdefault("knowledge", [])
        self.memory.memory["knowledge"].append({"prompt": prompt, "answer": answer})
        self.memory.save()

        if self.knowledge.add_qa(prompt, answer):
            learned = True
        self.knowledge.deduplicate()

        if learned:
            answer += "\n[Learned Memory]"

        return answer
