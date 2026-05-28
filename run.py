#!/usr/bin/env python3
"""
Job Search CLI

Commands:
  scrape    — scrape all enabled job boards
  score     — score unscored jobs using Claude API
  apply     — auto-apply to qualifying jobs
  pipeline  — scrape + score + apply in sequence
  serve     — start the web dashboard (default: localhost:5000)
  stats     — print quick stats from the database
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def cmd_scrape(cfg: dict) -> None:
    from job_search.scrapers import linkedin, indeed, hn_hiring, ats
    total = 0
    sc = cfg.get("scrapers", {})

    if sc.get("linkedin", {}).get("enabled"):
        lc = sc["linkedin"]
        total += linkedin.scrape(
            keywords=lc.get("keywords", "Software Engineer"),
            location=lc.get("location", "Remote"),
            max_pages=lc.get("max_pages", 3),
        )

    if sc.get("indeed", {}).get("enabled"):
        ic = sc["indeed"]
        total += indeed.scrape(
            query=ic.get("query", "software engineer"),
            location=ic.get("location", "remote"),
            max_pages=ic.get("max_pages", 3),
        )

    if sc.get("hn_hiring", {}).get("enabled"):
        total += hn_hiring.scrape()

    if sc.get("ats", {}).get("enabled"):
        ats_cfg = sc["ats"]
        total += ats.scrape(
            greenhouse=ats_cfg.get("greenhouse", []),
            lever=ats_cfg.get("lever", []),
            ashby=ats_cfg.get("ashby", []),
        )

    print(f"\nScrape complete. {total} new jobs added to database.")


def cmd_score() -> None:
    from job_search import scorer
    n = scorer.score_all()
    print(f"\nScoring complete. {n} jobs scored.")


def cmd_apply() -> None:
    from job_search import applicator
    n = applicator.apply_all()
    print(f"\nAuto-apply complete. Applied to {n} jobs.")


def cmd_pipeline(cfg: dict) -> None:
    cmd_scrape(cfg)
    cmd_score()
    cmd_apply()


def cmd_serve(cfg: dict) -> None:
    from job_search.web.app import app
    web_cfg = cfg.get("web", {})
    port = web_cfg.get("port", 5000)
    debug = web_cfg.get("debug", False)
    print(f"Starting dashboard at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)


def cmd_stats() -> None:
    from job_search import db
    s = db.stats()
    print(f"\nTotal jobs:  {s['total']}")
    print(f"Avg score:   {s['avg_score']}")
    print("By status:")
    for status, cnt in sorted(s["by_status"].items()):
        print(f"  {status:<12} {cnt}")


def main():
    from job_search import config, db

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]
    db.init()

    if command == "scrape":
        cfg = config.load()
        cmd_scrape(cfg)
    elif command == "score":
        config.load()
        cmd_score()
    elif command == "apply":
        cfg = config.load()
        cmd_apply()
    elif command == "pipeline":
        cfg = config.load()
        cmd_pipeline(cfg)
    elif command == "serve":
        cfg = config.load()
        cmd_serve(cfg)
    elif command == "stats":
        config.load()
        cmd_stats()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
