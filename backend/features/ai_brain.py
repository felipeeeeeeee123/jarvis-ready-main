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
            # Try to fetch real-time data
            try:
                web_info = web_search(prompt)
                enriched_prompt = f"Web facts:\n{web_info}\n\nUser asked: {prompt}"
            except Exception:
                enriched_prompt = prompt  # If web search fails, use original prompt

            # Try to generate response from Ollama
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": enriched_prompt,
                    "stream": False,
                },
                timeout=10
            )
            data = response.json()
            answer = data.get("response", "").strip()
            if not answer:
                raise ValueError("Ollama returned empty response.")

        except Exception:
            # Final fallback if Ollama fails too
            answer = f"[Fallback: Web] {web_search(prompt)}"

        self.memory.memory["last_answer"] = answer
        self.memory.save()
        return answer
