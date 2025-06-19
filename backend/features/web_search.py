import requests
from bs4 import BeautifulSoup
from typing import Optional

def web_search(query: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. Try Bing HTML scrape
    try:
        bing_url = f"https://www.bing.com/search?q={query}"
        res = requests.get(bing_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("li", class_="b_algo", limit=3)
        links: list[str] = []
        for r in results:
            a_tag: Optional[BeautifulSoup] = r.find("a")
            if a_tag and a_tag.get_text():
                links.append(a_tag.get_text())
        if links:
            return "\n".join(links)
    except Exception as e:
        print(f"[Bing Error] {e}")

    # 2. DuckDuckGo fallback (NEW METHOD - old html.duckduckgo.com is unstable)
    try:
        ddg_url = f"https://lite.duckduckgo.com/lite/?q={query}"
        res = requests.get(ddg_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.find_all("a", limit=3)
        texts = [a.get_text() for a in links if a and a.get_text()]
        if texts:
            return "\n".join(texts)
    except Exception as e:
        print(f"[DuckDuckGo Error] {e}")

    # 3. Ollama fallback
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": f"Search the web for: {query}", "stream": False},
            timeout=10
        )
        return res.json().get("response", "[Ollama fallback: No response]")
    except Exception as e:
        return f"[Web search error: {e}]"
