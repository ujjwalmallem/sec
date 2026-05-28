import logging
import re
import requests
from datetime import datetime, timezone

from job_search import config, db

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "JobSearchBot/1.0"}


def _apply_greenhouse(job: dict, cfg: dict) -> bool:
    """
    Greenhouse public apply endpoint.
    NOTE: Full application requires resume upload + form fields that vary per job.
    This submits a minimal application (name + email) only if the job has a simple form.
    """
    url = job["url"]
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if not m:
        return False
    company, job_id = m.group(1), m.group(2)
    apply_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"

    try:
        resp = requests.get(apply_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        job_data = resp.json()
    except Exception as e:
        log.warning("Could not fetch Greenhouse job detail for apply: %s", e)
        return False

    questions = job_data.get("questions", [])
    required_fields = [q for q in questions if q.get("required")]
    non_basic = [
        q for q in required_fields
        if q.get("fields", [{}])[0].get("name") not in ("first_name", "last_name", "email", "resume")
    ]
    if non_basic:
        log.info(
            "Greenhouse %s job %s has %d required non-basic fields — skipping auto-apply",
            company, job_id, len(non_basic)
        )
        return False

    criteria = cfg.get("criteria", {})
    resume_text = cfg.get("resume", "")
    contact = cfg.get("contact", {})
    first = contact.get("first_name", "")
    last = contact.get("last_name", "")
    email = contact.get("email", "")

    if not first or not last or not email:
        log.info("No contact info in config — cannot auto-apply to Greenhouse")
        return False

    post_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}/applications"
    payload = {
        "first_name": first,
        "last_name": last,
        "email": email,
        "resume_text": resume_text[:5000],
        "source_id": None,
    }
    try:
        resp = requests.post(post_url, json=payload, headers=HEADERS, timeout=15)
        if resp.status_code in (200, 201):
            log.info("Applied to Greenhouse %s job %s", company, job_id)
            return True
        else:
            log.warning("Greenhouse apply failed: %s %s", resp.status_code, resp.text[:200])
            return False
    except Exception as e:
        log.warning("Greenhouse apply request failed: %s", e)
        return False


def apply_all() -> int:
    cfg = config.get()
    threshold = cfg.get("scoring", {}).get("auto_apply_threshold", 70)
    applied = 0

    jobs = db.list_jobs(status="new", min_score=threshold)
    log.info("Auto-apply: %d jobs meet score threshold (%d)", len(jobs), threshold)

    for job in jobs:
        board = job["board"]
        if board == "greenhouse":
            success = _apply_greenhouse(dict(job), cfg)
        else:
            log.info(
                "Board '%s' does not support auto-apply — open manually: %s",
                board, job["url"]
            )
            success = False

        if success:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            db.update_status(job["id"], "applied", applied_at=now)
            applied += 1

    log.info("Auto-apply done. Applied to %d jobs.", applied)
    return applied
