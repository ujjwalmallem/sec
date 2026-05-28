import json
import logging
import re
import anthropic

from job_search import config, db

log = logging.getLogger(__name__)


def _build_system_prompt(cfg: dict) -> str:
    resume = cfg.get("resume", "").strip()
    criteria = cfg.get("criteria", {})
    titles = ", ".join(criteria.get("titles", []))
    skills_req = ", ".join(criteria.get("skills_required", []))
    skills_nice = ", ".join(criteria.get("skills_nice_to_have", []))
    avoid = ", ".join(criteria.get("avoid_companies", []))
    avoid_kw = ", ".join(criteria.get("avoid_keywords", []))
    salary = criteria.get("salary_min", 0)
    remote = criteria.get("remote_ok", True)

    return f"""You are a job fit evaluator. Score job listings on a 0-100 scale for this candidate.

CANDIDATE RESUME:
{resume}

JOB CRITERIA:
- Target titles: {titles}
- Required skills: {skills_req}
- Nice-to-have skills: {skills_nice}
- Remote OK: {remote}
- Salary minimum: ${salary:,}
- Avoid these companies: {avoid}
- Avoid if listing contains: {avoid_kw}

Respond ONLY with a JSON object:
{{"score": <integer 0-100>, "reasoning": "<2 sentences explaining the fit score>"}}

Score 0 if: company is on avoid list, avoid keywords present, or clearly wrong field.
Score 90-100 only for near-perfect matches on title, skills, and location/remote."""


def _parse_response(text: str) -> tuple[int, str]:
    """Extract score and reasoning from model response with fallback regex."""
    try:
        data = json.loads(text.strip())
        return int(data["score"]), str(data["reasoning"])
    except Exception:
        pass
    m = re.search(r'\{[^{}]*"score"\s*:\s*(\d+)[^{}]*"reasoning"\s*:\s*"([^"]+)"[^{}]*\}', text, re.DOTALL)
    if m:
        return int(m.group(1)), m.group(2)
    m = re.search(r'"score"\s*:\s*(\d+)', text)
    score = int(m.group(1)) if m else 50
    m2 = re.search(r'"reasoning"\s*:\s*"([^"]+)"', text)
    reasoning = m2.group(1) if m2 else "Could not parse reasoning."
    return score, reasoning


def score_all() -> int:
    cfg = config.get()
    jobs = db.get_unscored_jobs()
    if not jobs:
        log.info("No unscored jobs.")
        return 0

    client = anthropic.Anthropic(api_key=config.api_key())
    system_prompt = _build_system_prompt(cfg)
    scored = 0

    log.info("Scoring %d jobs with Claude...", len(jobs))
    for job in jobs:
        job_text = f"""Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Board: {job['board']}

Description:
{(job['description'] or '')[:2000]}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": job_text}],
            )
            raw = response.content[0].text
            score, reasoning = _parse_response(raw)
            score = max(0, min(100, score))
            db.update_score(job["id"], score, reasoning)
            scored += 1
            log.debug("Job %d '%s': score=%d", job["id"], job["title"], score)
        except Exception as e:
            log.warning("Failed to score job %d: %s", job["id"], e)

    log.info("Scored %d jobs.", scored)
    return scored
