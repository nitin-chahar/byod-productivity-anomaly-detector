"""
Web scraping and URL parsing utilities for BYOD Productivity Logger.
Extracts HTML meta-tags (title, description) or extracts normalized lexical tokens
from raw URLs to prepare inputs for NLP classification.
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


def extract_meta_data(url: str) -> Optional[str]:
    """
    Attempts to fetch the target URL and extract its meta description or title.
    Returns the extracted text, or None if the request fails or content is absent.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Attempt to extract Meta Description
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                content = meta_tag["content"].strip()
                if content:
                    return content

            # 2. Fall back to OpenGraph Description
            og_meta = soup.find("meta", attrs={"property": "og:description"})
            if og_meta and og_meta.get("content"):
                content = og_meta["content"].strip()
                if content:
                    return content

            # 3. Fall back to Page Title
            title_tag = soup.find("title")
            if title_tag and title_tag.text:
                content = title_tag.text.strip()
                if content:
                    return content

    except requests.exceptions.RequestException:
        # Failed to fetch or connection timed out, fallback to URL lexical tokens
        return None
    except Exception:
        return None

    return None


def extract_text_from_url(url: str) -> str:
    """
    Extracts meaningful words from a raw URL string by stripping protocol,
    www subdomain, top-level domain patterns, and punctuation.
    """
    clean = url.lower()
    clean = re.sub(r"^https?://", "", clean)
    clean = re.sub(r"^www\.", "", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    return " ".join(clean.split())


if __name__ == "__main__":
    test_urls = [
        "https://www.github.com",
        "https://www.youtube.com/wwe",
        "https://en.wikipedia.org/wiki/Machine_learning"
    ]
    for u in test_urls:
        print(f"\nURL: {u}")
        print(f"Meta Extracted: {extract_meta_data(u)}")
        print(f"Token Extracted: {extract_text_from_url(u)}")
