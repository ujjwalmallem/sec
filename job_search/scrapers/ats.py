import re
import time
import logging
import requests

from job_search import db

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "JobSearchBot/1.0 (automated job aggregator)"}

# Public JSON APIs — no auth required
GREENHOUSE_JOBS = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
LEVER_JOBS      = "https://api.lever.co/v0/postings/{company}?mode=json&limit=50"
ASHBY_JOBS      = "https://api.ashbyhq.com/posting-public/job-board/{company}"


def _scrape_greenhouse(company: str) -> int:
    url = GREENHOUSE_JOBS.format(company=company)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("Greenhouse %s: %s", company, e)
        return 0

    added = 0
    for job in data.get("jobs", []):
        title = job.get("title", "")
        location = job.get("location", {}).get("name", "")
        apply_url = job.get("absolute_url", "")
        description = job.get("content", "") or f"{title} at {company}"
        if not apply_url:
            continue
        job_id = db.upsert_job(title, company.title(), location, apply_url, "greenhouse", description[:4000])
        if job_id:
            added += 1
    log.info("Greenhouse %s: %d new jobs", company, added)
    return added


def _scrape_lever(company: str) -> int:
    url = LEVER_JOBS.format(company=company)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        jobs = resp.json()
    except Exception as e:
        log.warning("Lever %s: %s", company, e)
        return 0

    added = 0
    for job in jobs if isinstance(jobs, list) else []:
        title = job.get("text", "")
        location = (job.get("categories") or {}).get("location", "")
        apply_url = job.get("hostedUrl", "")
        description_parts = [job.get("description", ""), job.get("additional", "")]
        description = "\n".join(p for p in description_parts if p)[:4000]
        if not apply_url:
            continue
        job_id = db.upsert_job(title, company.title(), location, apply_url, "lever", description)
        if job_id:
            added += 1
    log.info("Lever %s: %d new jobs", company, added)
    return added


def _scrape_ashby(company: str) -> int:
    url = ASHBY_JOBS.format(company=company)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("Ashby %s: %s", company, e)
        return 0

    added = 0
    for job in data.get("jobPostings", []):
        title = job.get("title", "")
        location = job.get("locationName", "") or job.get("secondaryLocations", [""])[0]
        job_url = f"https://jobs.ashbyhq.com/{company}/{job.get('id', '')}"
        description = job.get("descriptionHtml", "") or f"{title} at {company}"
        description = re.sub(r"<[^>]+>", " ", description)[:4000]
        if not job.get("id"):
            continue
        job_id = db.upsert_job(title, company.title(), location, job_url, "ashby", description)
        if job_id:
            added += 1
    log.info("Ashby %s: %d new jobs", company, added)
    return added


def scrape(greenhouse: list[str], lever: list[str], ashby: list[str]) -> int:
    total = 0
    for company in greenhouse or []:
        total += _scrape_greenhouse(company)
        time.sleep(1)
    for company in lever or []:
        total += _scrape_lever(company)
        time.sleep(1)
    for company in ashby or []:
        total += _scrape_ashby(company)
        time.sleep(1)
    log.info("ATS scrape done. Added %d jobs total.", total)
    return total
