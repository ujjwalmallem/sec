from flask import Flask, render_template, request, redirect, url_for, jsonify

from job_search import db

app = Flask(__name__)


@app.route("/")
def index():
    status_filter = request.args.get("status", "")
    board_filter = request.args.get("board", "")
    min_score_str = request.args.get("min_score", "")
    order_by = request.args.get("order", "fit_score DESC")

    min_score = int(min_score_str) if min_score_str.isdigit() else None

    jobs = db.list_jobs(
        status=status_filter or None,
        min_score=min_score,
        board=board_filter or None,
        order_by=order_by,
    )
    s = db.stats()

    return render_template(
        "index.html",
        jobs=jobs,
        stats=s,
        status_filter=status_filter,
        board_filter=board_filter,
        min_score=min_score_str,
        order_by=order_by,
        valid_statuses=db.VALID_STATUSES,
    )


@app.route("/job/<int:job_id>")
def job_detail(job_id: int):
    job = db.get_job(job_id)
    if not job:
        return "Job not found", 404
    return render_template("job.html", job=job, valid_statuses=db.VALID_STATUSES)


@app.route("/job/<int:job_id>/status", methods=["POST"])
def update_status(job_id: int):
    status = request.form.get("status", "")
    if status not in db.VALID_STATUSES:
        return "Invalid status", 400
    from datetime import datetime, timezone
    applied_at = None
    if status == "applied":
        applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.update_status(job_id, status, applied_at=applied_at)
    return redirect(request.referrer or url_for("index"))


@app.route("/api/stats")
def api_stats():
    return jsonify(db.stats())


@app.route("/api/jobs")
def api_jobs():
    jobs = db.list_jobs()
    return jsonify([dict(j) for j in jobs])
