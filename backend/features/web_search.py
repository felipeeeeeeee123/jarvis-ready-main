import re
import requests
from bs4 import BeautifulSoup

# Track which source successfully provided results
last_used_source: str | None = None

# Very small list of stopwords for naive keyword filtering
_STOPWORDS = {
    "the", "is", "a", "an", "and", "or", "of", "to", "in", "on",
    "for", "if", "are", "as", "with", "was", "were", "by", "at", "be",
    "this", "that", "it", "from", "did"
}

def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]

def _contains_keyword(snippet: str, keywords: list[str]) -> bool:
    snippet_l = snippet.lower()
    return any(k in snippet_l for k in keywords)

def web_search(query: str) -> str:
    """Return relevant search snippets for a query using DuckDuckGo, with
    fallback to Bing or local Ollama. Results that don't contain any of the
    query keywords are discarded."""

    global last_used_source
    last_used_source = None

    headers = {"User-Agent": "Mozilla/5.0"}
    keywords = _extract_keywords(query)

    # 1. DuckDuckGo Primary Search
    try:
        res = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=5
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("div", class_="result", limit=5)
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
                combined = " - ".join(text_parts)
                if not keywords or _contains_keyword(combined, keywords):
                    print(f"[DuckDuckGo snippet] {combined}")
                    snippets.append(combined)

        if snippets:
            last_used_source = "duckduckgo"
            return "\n".join(snippets[:3])

    except Exception as e:
        print(f"[DuckDuckGo Error] {e}")

    # 2. Bing Fallback
    try:
        res = requests.get(
            f"https://www.bing.com/search?q={query}",
            headers=headers,
            timeout=5
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("li", class_="b_algo", limit=5)
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
                combined = " - ".join(text_parts)
                if not keywords or _contains_keyword(combined, keywords):
                    print(f"[Bing snippet] {combined}")
                    links.append(combined)

        if links:
            last_used_source = "bing"
            return "\n".join(links[:3])

    except Exception as e:
        print(f"[Bing Error] {e}")

    # 3. Local Ollama Fallback
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": query,
                "stream": False
            },
            timeout=10
        )
        text = res.json().get("response", "").strip()
        if not text:
            raise ValueError("Empty response from Ollama")
        last_used_source = "ollama"
        if keywords and not _contains_keyword(text, keywords):
            return f"[No web access \u2013 Ollama fallback] {text}"
        return f"[No web access \u2013 Ollama fallback] {text}"
    except Exception as e:
        last_used_source = "ollama"
        print(f"[Ollama Error] {e}")
        return "[No web access \u2013 Ollama fallback]"

