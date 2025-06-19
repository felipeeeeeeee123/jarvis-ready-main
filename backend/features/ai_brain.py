import requests
from backend.utils.memory import MemoryManager
from backend.features.web_search import web_search

class AIBrain:
    def __init__(self, model="mistral"):
        self.model = model
        self.memory = MemoryManager()

    def ask(self, prompt: str) -> str:
        self.memory.memory["last_prompt"] = prompt

        # 🔍 Check if prompt already answered (exact match)
        for entry in self.memory.memory.get("knowledge", []):
            if prompt.lower().strip() == entry["prompt"].lower().strip():
                return f"[Learned Memory] {entry['answer']}"

        try:
            # 🕸️ Get real-time web context
            try:
                web_info = web_search(prompt)
                enriched_prompt = f"Web facts:\n{web_info}\n\nUser asked: {prompt}"
            except Exception:
                enriched_prompt = prompt  # If web fails, go without

            # 🧠 Local model generation (Ollama)
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
            # 🌐 Final fallback to web if Ollama fails
            answer = f"[Fallback: Web] {web_search(prompt)}"

        # 💾 Save answer to memory
        self.memory.memory["last_answer"] = answer
        self.memory.memory.setdefault("knowledge", [])
        self.memory.memory["knowledge"].append({
            "prompt": prompt,
            "answer": answer
        })
        self.memory.save()

        return answer
