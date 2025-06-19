import csv
import os
import random
import time
from datetime import datetime

from backend.features.ai_brain import AIBrain
from backend.features import web_search

SEED_TOPICS = [
    "global warming",
    "AI technology",
    "space exploration",
    "medical advances",
    "financial markets",
    "renewable energy",
    "quantum computing",
    "blockchain",
    "robotics",
    "cybersecurity",
]

DYNAMIC_KEYWORDS = [
    "impact",
    "future",
    "benefits",
    "challenges",
    "recent breakthroughs",
    "in 2024",
    "applications",
    "importance",
    "risks",
    "trends",
]

TEMPLATES = [
    "What are the {keyword} of {topic}?",
    "Explain the {keyword} regarding {topic}.",
    "How does {topic} relate to {keyword}?",
    "What is new about {topic} concerning {keyword}?",
]

LOG_PATH = "autotrain_log.csv"


def init_log(path: str) -> csv.writer:
    exists = os.path.exists(path)
    f = open(path, "a", newline="", encoding="utf-8")
    writer = csv.writer(f)
    if not exists:
        writer.writerow(["timestamp", "question", "answer", "source"])
    return writer


def generate_question(asked: set[str]) -> str:
    for _ in range(10):
        topic = random.choice(SEED_TOPICS)
        keyword = random.choice(DYNAMIC_KEYWORDS)
        template = random.choice(TEMPLATES)
        q = template.format(topic=topic, keyword=keyword)
        if q not in asked:
            asked.add(q)
            return q
    asked.add(q)
    return q


def shorten(text: str, limit: int = 80) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def main() -> None:
    brain = AIBrain()
    asked_questions: set[str] = set()
    writer = init_log(LOG_PATH)
    counter = 0
    try:
        while True:
            counter += 1
            question = generate_question(asked_questions)
            try:
                answer = brain.ask(question)
            except Exception as e:
                print(f"[Error] {e}")
                time.sleep(1)
                continue
            source = getattr(web_search, "last_used_source", "unknown")
            print(f"[{counter}] {question} -> {shorten(answer)}")
            writer.writerow([
                datetime.utcnow().isoformat(),
                question,
                answer,
                source,
            ])
            time.sleep(random.uniform(1, 2))
    except KeyboardInterrupt:
        print("Autotrain interrupted by user.")


if __name__ == "__main__":
    main()
