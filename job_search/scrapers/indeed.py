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
    "Referer": "https://www.indeed.com/",
}

BASE_URL = "https://www.indeed.com/jobs"


def scrape(query: str, location: str, max_pages: int = 3) -> int:
    session = requests.Session()
    session.headers.update(HEADERS)
    added = 0

    for page in range(max_pages):
        start = page * 10
        params = {"q": query, "l": location, "start": start, "fromage": "1"}
        try:
            resp = session.get(BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            log.warning("Indeed page %d fetch failed: %s", page, e)
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.job_seen_beacon") or soup.select("div.tapItem")

        if not cards:
            log.info("Indeed: no cards on page %d (may be blocked or end of results)", page)
            break

        for card in cards:
            try:
                title_el = card.select_one("h2.jobTitle span[title]") or card.select_one("h2.jobTitle")
                company_el = card.select_one("span.companyName") or card.select_one("[data-testid='company-name']")
                location_el = card.select_one("div.companyLocation") or card.select_one("[data-testid='text-location']")
                link_el = card.select_one("a[data-jk]") or card.select_one("h2.jobTitle a")

                if not title_el or not link_el:
                    continue

                title = title_el.get("title") or title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                loc = location_el.get_text(strip=True) if location_el else location
                jk = link_el.get("data-jk") or ""
                href = f"https://www.indeed.com/viewjob?jk={jk}" if jk else ""
                if not href:
                    href = "https://www.indeed.com" + link_el.get("href", "")
                if not href.startswith("http"):
                    continue

                description = f"{title} at {company} — {loc}"
                job_id = db.upsert_job(title, company, loc, href, "indeed", description)
                if job_id:
                    added += 1
            except Exception as e:
                log.debug("Indeed card parse error: %s", e)

        log.info("Indeed page %d: found %d cards (total added: %d)", page + 1, len(cards), added)
        time.sleep(2)

    log.info("Indeed scrape done. Added %d jobs.", added)
    return added
