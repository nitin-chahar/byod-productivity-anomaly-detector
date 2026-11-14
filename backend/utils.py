"""
Web scraping and URL parsing utilities for BYOD Productivity Logger.
Extracts HTML meta-tags or normalized lexical tokens for NLP classification.
"""

import re
from typing import Optional
import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT_SECONDS = 5

GENERIC_DESCRIPTIONS = (
    "enjoy the videos and music you love",
    "upload original content, and share it all",
    "before you continue to youtube",
)


def _fetch_youtube_metadata(url: str) -> Optional[str]:
    """Retrieves video title and author via public oEmbed endpoint."""
    try:
        encoded = requests.utils.quote(url)
        oembed_url = f"https://www.youtube.com/oembed?url={encoded}&format=json"
        response = requests.get(oembed_url, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            data = response.json()
            title = data.get("title", "").strip()
            author = data.get("author_name", "").strip()
            if title:
                return f"{title} {author}".strip()
    except Exception:
        pass
    return None


def extract_meta_data(url: str) -> Optional[str]:
    """Fetches target URL and extracts title and descriptive metadata."""
    # YouTube specific handler
    if "youtube.com" in url or "youtu.be" in url:
        yt_meta = _fetch_youtube_metadata(url)
        if yt_meta:
            return yt_meta

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title_text = ""
            title_tag = soup.find("title")
            if title_tag and title_tag.text:
                title_text = title_tag.text.strip()

            og_title = soup.find("meta", attrs={"property": "og:title"})
            if og_title and og_title.get("content"):
                title_text = og_title["content"].strip()

            # Extract description
            desc_text = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                candidate = meta_desc["content"].strip()
                if not any(g in candidate.lower() for g in GENERIC_DESCRIPTIONS):
                    desc_text = candidate

            if not desc_text:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    candidate = og_desc["content"].strip()
                    if not any(g in candidate.lower() for g in GENERIC_DESCRIPTIONS):
                        desc_text = candidate

            combined = f"{title_text} {desc_text}".strip()
            return combined if combined else None

    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None

    return None


def extract_text_from_url(url: str) -> str:
    """Extracts alphanumeric tokens from a URL string."""
    clean = url.lower()
    clean = re.sub(r"^https?://", "", clean)
    clean = re.sub(r"^www\.", "", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    return " ".join(clean.split())


if __name__ == "__main__":
    test_urls = [
        "https://www.youtube.com/watch?v=1L420xXpDTg",
        "https://www.github.com",
    ]
    for u in test_urls:
        print(f"URL: {u} -> Meta: {extract_meta_data(u)}")
