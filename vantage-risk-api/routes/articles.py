"""
routes/articles.py — Full article content extraction endpoint.
Uses newspaper3k + BeautifulSoup to extract article text from external URLs.
Falls back gracefully when extraction fails (paywalls, JS-only content, etc.).
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleExtractionRequest(BaseModel):
    url: str


class ArticleContent(BaseModel):
    title: str
    author: Optional[str] = None
    publish_date: Optional[str] = None
    top_image: Optional[str] = None
    text: str
    source_domain: str
    word_count: int = 0
    success: bool = True


def _extract_with_newspaper(url: str) -> ArticleContent:
    """Extract article using newspaper3k library."""
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        domain = urlparse(url).netloc.replace("www.", "")
        text = article.text.strip()

        # If extracted text is too short, it probably failed
        if len(text) < 100:
            raise ValueError("Extracted text too short, likely extraction failure")

        pub_date = None
        if article.publish_date:
            pub_date = article.publish_date.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(article.publish_date, 'strftime') else str(article.publish_date)

        return ArticleContent(
            title=article.title or "Untitled",
            author=", ".join(article.authors) if article.authors else None,
            publish_date=pub_date,
            top_image=article.top_image or None,
            text=text,
            source_domain=domain,
            word_count=len(text.split()),
            success=True,
        )
    except Exception as e:
        log.warning(f"newspaper3k extraction failed for {url}: {e}")
        raise


def _extract_with_requests(url: str) -> ArticleContent:
    """Fallback extraction using requests + BeautifulSoup."""
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove scripts, styles, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    # Try to find the article body
    article_body = soup.find("article") or soup.find("div", class_=re.compile(r"article|content|post|story|body"))
    if article_body:
        paragraphs = article_body.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Get the open graph image
    og_image = soup.find("meta", property="og:image")
    top_image = og_image["content"] if og_image and og_image.get("content") else None

    domain = urlparse(url).netloc.replace("www.", "")

    if len(text) < 50:
        raise ValueError("BeautifulSoup extraction returned insufficient content")

    return ArticleContent(
        title=title,
        author=None,
        publish_date=None,
        top_image=top_image,
        text=text,
        source_domain=domain,
        word_count=len(text.split()),
        success=True,
    )


@router.post("/extract", response_model=ArticleContent)
def extract_article(req: ArticleExtractionRequest):
    """
    Extract full article content from a URL.
    Tries newspaper3k first, falls back to requests+BeautifulSoup.
    Returns partial content with success=False if all methods fail.
    """
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    domain = urlparse(url).netloc.replace("www.", "")

    # Try newspaper3k first
    try:
        return _extract_with_newspaper(url)
    except Exception:
        pass

    # Fallback to requests + BeautifulSoup
    try:
        return _extract_with_requests(url)
    except Exception as e:
        log.error(f"All extraction methods failed for {url}: {e}")

    # Ultimate fallback — return a stub indicating failure
    return ArticleContent(
        title="Article Unavailable",
        text="This article could not be extracted automatically. The source may require a subscription or uses JavaScript-only rendering. Please visit the original source to read the full article.",
        source_domain=domain,
        word_count=0,
        success=False,
    )
