import requests
from backend.utils.memory import MemoryManager
from backend.features.web_search import web_search

class AIBrain:
    def __init__(self, model="mistral"):
        self.model = model
        self.memory = MemoryManager()

    def ask(self, prompt: str) -> str:
        self.memory.memory["last_prompt"] = prompt
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=10,
            )
            data = resp.json()
            answer = data.get("response", "").strip()
            if not answer:
                raise ValueError("Empty response from local model")
        except Exception as e:
            try:
                answer = web_search(prompt)
            except Exception:
                answer = f"[Error generating response: {e}]"

        self.memory.memory["last_answer"] = answer
        self.memory.save()
        return answer

