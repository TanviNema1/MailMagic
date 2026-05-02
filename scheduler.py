from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

# WHY APScheduler: The LightGBM model says "send at 9am".
# APScheduler holds the email job and fires it at exactly that time —
# so emails land in the inbox at peak engagement hours, not whenever
# the user clicks the button.

scheduler = BackgroundScheduler(job_defaults={
    'misfire_grace_time': 300  # 5 minutes grace time
})
scheduler.start()

def schedule_email(customer_id: int, predicted_hour: int,
                   email_payload: dict, send_fn):
    """
    Schedules send_fn to fire today at predicted_hour.
    If that hour has already passed today, schedules for tomorrow.
    """
    now = datetime.now()
    run_time = now.replace(hour=predicted_hour, minute=0,
                           second=0, microsecond=0)

    if run_time <= now:
        run_time += timedelta(days=1)

    job_id = f"email_{customer_id}_{predicted_hour}"

    scheduler.add_job(
        func=send_fn,
        trigger="date",
        run_date=run_time,
        args=[email_payload],       # ✅ fixed — passes payload as positional arg
        id=job_id,
        replace_existing=True
    )

    return {
        "scheduled_for": run_time.isoformat(),
        "job_id":        job_id
    }