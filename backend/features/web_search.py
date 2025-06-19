import re
from urllib.parse import urlparse

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

def _keyword_overlap(text: str, keywords: list[str]) -> float:
    """Return fraction of query keywords appearing in text."""
    if not keywords:
        return 0.0
    tokens = _extract_keywords(text)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in keywords)
    return hits / len(keywords)

def _domain_relevant(url: str, keywords: list[str]) -> bool:
    """Check if any query keyword appears in the URL domain."""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return False
    tokens = re.findall(r"[a-z0-9]+", domain)
    return any(t in keywords for t in tokens)

def _domain_score(url: str) -> float:
    """Return extra weight for reputable domains."""
    if not url:
        return 0.0
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return 0.0
    if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".org"):
        return 0.3
    return 0.0

_MIN_SNIPPET_LEN = 30

def web_search(query: str) -> str:
    """Return relevant search snippets for a query using DuckDuckGo, with
    fallback to Bing or local Ollama. Results are filtered by keyword
    overlap, minimum length and domain relevance."""

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
        snippets: list[tuple[float, str]] = []

        for r in results:
            title = r.find("a", class_="result__a")
            snippet = (
                r.find("a", class_="result__snippet")
                or r.find("div", class_="result__snippet")
                or r.find("span", class_="result__snippet")
            )
            url = title.get("href") if title else ""
            text_parts = []
            if title and title.get_text():
                text_parts.append(title.get_text(" ", strip=True))
            if snippet and snippet.get_text():
                text_parts.append(snippet.get_text(" ", strip=True))
            if text_parts:
                combined = " - ".join(text_parts)
                if len(combined) < _MIN_SNIPPET_LEN:
                    continue
                overlap = _keyword_overlap(combined, keywords)
                domain_ok = _domain_relevant(url, keywords)
                if not keywords or overlap >= 0.3 or domain_ok:
                    score = overlap + _domain_score(url)
                    print(f"[DuckDuckGo snippet] {combined}")
                    snippets.append((score, combined))

        if snippets:
            snippets.sort(key=lambda x: x[0], reverse=True)
            last_used_source = "duckduckgo"
            return "\n".join([s for _, s in snippets[:3]])

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
        links: list[tuple[float, str]] = []

        for r in results:
            a_tag = r.find("a")
            snippet = r.find("p")
            url = a_tag.get("href") if a_tag else ""
            text_parts = []
            if a_tag and a_tag.get_text():
                text_parts.append(a_tag.get_text(" ", strip=True))
            if snippet and snippet.get_text():
                text_parts.append(snippet.get_text(" ", strip=True))
            if text_parts:
                combined = " - ".join(text_parts)
                if len(combined) < _MIN_SNIPPET_LEN:
                    continue
                overlap = _keyword_overlap(combined, keywords)
                domain_ok = _domain_relevant(url, keywords)
                if not keywords or overlap >= 0.3 or domain_ok:
                    score = overlap + _domain_score(url)
                    print(f"[Bing snippet] {combined}")
                    links.append((score, combined))

        if links:
            links.sort(key=lambda x: x[0], reverse=True)
            last_used_source = "bing"
            return "\n".join([s for _, s in links[:3]])

    except Exception as e:
        print(f"[Bing Error] {e}")

    # 3. Local Ollama Fallback
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": f"Explain this in detail: {query}",
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

