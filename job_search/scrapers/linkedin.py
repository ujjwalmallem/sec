import time
import logging
import requests
from bs4 import BeautifulSoup

from job_search import db

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://www.linkedin.com/jobs/search/"


def scrape(keywords: str, location: str, max_pages: int = 3) -> int:
    session = requests.Session()
    session.headers.update(HEADERS)
    added = 0
    for page in range(max_pages):
        start = page * 25
        url = f"{BASE_URL}?keywords={requests.utils.quote(keywords)}&location={requests.utils.quote(location)}&start={start}&f_TPR=r86400"
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            log.warning("LinkedIn page %d fetch failed: %s", page, e)
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.base-card") or soup.select("li.jobs-search__results-list > div")

        if not cards:
            log.info("LinkedIn: no cards found on page %d (may be blocked)", page)
            break

        for card in cards:
            try:
                title_el = card.select_one("h3.base-search-card__title") or card.select_one("h3")
                company_el = card.select_one("h4.base-search-card__subtitle") or card.select_one("h4")
                location_el = card.select_one("span.job-search-card__location")
                link_el = card.select_one("a.base-card__full-link") or card.select_one("a")

                if not title_el or not link_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                loc = location_el.get_text(strip=True) if location_el else location
                href = link_el.get("href", "").split("?")[0]
                if not href.startswith("http"):
                    continue
                description = f"{title} at {company} — {loc}"

                job_id = db.upsert_job(title, company, loc, href, "linkedin", description)
                if job_id:
                    added += 1
            except Exception as e:
                log.debug("LinkedIn card parse error: %s", e)

        log.info("LinkedIn page %d: %d new jobs (total added: %d)", page + 1, len(cards), added)
        time.sleep(2)

    log.info("LinkedIn scrape done. Added %d jobs.", added)
    return added
