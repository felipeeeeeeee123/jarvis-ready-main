from dotenv import load_dotenv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.features.ai_brain import AIBrain
from backend.features.web_search import web_search
from backend.features.autotrade import run_autotrader

load_dotenv()

def main():
    brain = AIBrain()
    print("🤖 JARVIS is online. Type 'exit' to quit.")
    online_mode = True  # Set to False to disable web search

    while True:
        prompt = input("🧠 You: ").strip()
        if prompt.lower() == "exit":
            print("👋 JARVIS shutting down.")
            break

        if online_mode and prompt.lower().startswith("search:"):
            query = prompt.split("search:", 1)[-1].strip()
            response = web_search(query)

        elif prompt.lower().startswith("trade"):
            _, *symbols = prompt.split()
            run_autotrader(symbols or None)
            response = "✅ Trade executed."

        else:
            response = brain.ask(prompt)

        print(f"🤖 JARVIS: {response}")

if __name__ == "__main__":
    main()
