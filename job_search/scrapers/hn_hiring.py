import logging
import re
import requests
from datetime import datetime

from job_search import db

log = logging.getLogger(__name__)

ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
ALGOLIA_ITEM = "https://hn.algolia.com/api/v1/items/{item_id}"


def _find_latest_thread() -> dict | None:
    """Return the most recent 'Ask HN: Who is hiring?' story."""
    now = datetime.utcnow()
    query = f"Ask HN: Who is hiring? ({now.strftime('%B %Y')})"
    try:
        resp = requests.get(
            ALGOLIA_SEARCH,
            params={"query": query, "tags": "story", "hitsPerPage": 5},
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        log.warning("HN Algolia search failed: %s", e)
        return None

    for hit in hits:
        title = hit.get("title", "")
        if "who is hiring" in title.lower() or "who's hiring" in title.lower():
            return hit

    # Fallback: previous month
    if now.month == 1:
        prev = now.replace(year=now.year - 1, month=12)
    else:
        prev = now.replace(month=now.month - 1)
    query = f"Ask HN: Who is hiring? ({prev.strftime('%B %Y')})"
    try:
        resp = requests.get(
            ALGOLIA_SEARCH,
            params={"query": query, "tags": "story", "hitsPerPage": 5},
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        for hit in hits:
            title = hit.get("title", "")
            if "who is hiring" in title.lower() or "who's hiring" in title.lower():
                return hit
    except Exception as e:
        log.warning("HN Algolia fallback search failed: %s", e)

    return None


def _parse_comment(comment: dict) -> dict | None:
    """Extract job fields from an HN comment text."""
    text = comment.get("text") or ""
    if not text or len(text) < 40:
        return None

    # Strip HTML tags roughly
    clean = re.sub(r"<[^>]+>", " ", text).strip()
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"&#x27;", "'", clean)
    clean = re.sub(r"\s+", " ", clean)

    first_line = clean.split("\n")[0].strip()

    # Find a URL in the comment
    urls = re.findall(r"https?://[^\s<>\"']+", clean)
    url = urls[0] if urls else None
    if not url:
        # Use HN item URL as fallback
        obj_id = comment.get("objectID") or comment.get("id") or ""
        url = f"https://news.ycombinator.com/item?id={obj_id}"

    # Try to split "Company | Role | Location" from first line
    parts = [p.strip() for p in first_line.split("|")]
    company = parts[0] if parts else "Unknown"
    title = parts[1] if len(parts) > 1 else "Software Engineer"
    location = parts[2] if len(parts) > 2 else "See listing"

    if len(company) > 100 or not company:
        return None

    return {
        "title": title[:200],
        "company": company[:200],
        "location": location[:200],
        "url": url,
        "description": clean[:4000],
    }


def scrape() -> int:
    thread = _find_latest_thread()
    if not thread:
        log.warning("HN: could not find Who's Hiring thread")
        return 0

    thread_id = thread.get("objectID") or thread.get("story_id")
    log.info("HN: found thread '%s' (id=%s)", thread.get("title"), thread_id)

    try:
        resp = requests.get(ALGOLIA_ITEM.format(item_id=thread_id), timeout=15)
        resp.raise_for_status()
        item = resp.json()
    except Exception as e:
        log.warning("HN: failed to fetch thread comments: %s", e)
        return 0

    comments = item.get("children", [])
    added = 0
    for comment in comments:
        parsed = _parse_comment(comment)
        if not parsed:
            continue
        job_id = db.upsert_job(
            parsed["title"],
            parsed["company"],
            parsed["location"],
            parsed["url"],
            "hn_hiring",
            parsed["description"],
        )
        if job_id:
            added += 1

    log.info("HN scrape done. Added %d jobs.", added)
    return added
