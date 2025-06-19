import requests
from bs4 import BeautifulSoup
from typing import Optional

def web_search(query: str) -> str:
    """Return relevant search snippets for a query using DuckDuckGo, with fallback to Bing or local Ollama."""

    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. DuckDuckGo Primary Search
    try:
        res = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=5
        )
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("div", class_="result", limit=3)
        snippets: list[str] = []

        for r in results:
            title = r.find("a", class_="result__a")
            snippet = (
                r.find("a", class_="result__snippet")
                or r.find("div", class_="result__snippet")
                or r.find("span", class_="result__snippet")
            )
            text_parts = []
            if title and title.get_text():
                text_parts.append(title.get_text(" ", strip=True))
            if snippet and snippet.get_text():
                text_parts.append(snippet.get_text(" ", strip=True))
            if text_parts:
                snippets.append(" - ".join(text_parts))

        if snippets:
            return "\n".join(snippets)

    except Exception as e:
        print(f"[DuckDuckGo Error] {e}")

    # 2. Bing Fallback
    try:
        res = requests.get(
            f"https://www.bing.com/search?q={query}",
            headers=headers,
            timeout=5
        )
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("li", class_="b_algo", limit=3)
        links: list[str] = []

        for r in results:
            a_tag = r.find("a")
            snippet = r.find("p")
            text_parts = []
            if a_tag and a_tag.get_text():
                text_parts.append(a_tag.get_text(" ", strip=True))
            if snippet and snippet.get_text():
                text_parts.append(snippet.get_text(" ", strip=True))
            if text_parts:
                links.append(" - ".join(text_parts))

        if links:
            return "\n".join(links)

    except Exception as e:
        print(f"[Bing Error] {e}")

    # 3. Local Ollama Fallback
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": f"Search the web for: {query}",
                "stream": False
            },
            timeout=10
        )
        return res.json().get("response", "[Ollama fallback: No response]")

    except Exception as e:
        return f"[Web search failed: {e}]"
