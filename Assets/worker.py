import os
import datetime
from celery import Celery
from celery.schedules import crontab
# Ensure the import points to Assets if db.py is in the Assets folder
from db import SessionLocal, MatchRecord, User 

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("notification_worker", broker=REDIS_URL, backend=REDIS_URL)

app.conf.beat_schedule = {
    "send-daily-digest-every-midnight": {
        "task": "worker.send_daily_digest_task",
        "schedule": crontab(hour=0, minute=0), 
    },
    "send-weekly-digest-every-sunday": {
        "task": "worker.send_weekly_digest_task",
        "schedule": crontab(day_of_week=0, hour=8, minute=0),
    },
}
app.conf.timezone = "UTC"

@app.task
def send_daily_digest_task():
    db = SessionLocal()
    try:
        unsent_matches = db.query(MatchRecord).filter(MatchRecord.sent_in_daily == False).all()
        user_groups = {}
        for match in unsent_matches:
            user_groups.setdefault(match.user_id, []).append(match)
            
        for user_id, matches in user_groups.items():
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.notification_preference in ["Daily", "ON", "Immediate"]:
                job_list = "".join([f"<li>{m.job_title} at {m.company}</li>" for m in matches])
                print(f"[Email Provider] Sending Daily Digest to {user.email}")
                for match in matches:
                    match.sent_in_daily = True
        db.commit()
    except Exception as e:
        print(f"[Worker Error] Daily digest failed: {e}")
    finally:
        db.close()

@app.task
def send_weekly_digest_task():
    db = SessionLocal()
    try:
        one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        weekly_matches = db.query(MatchRecord).filter(
            MatchRecord.created_at >= one_week_ago,
            MatchRecord.sent_in_weekly == False
        ).all()
        
        user_groups = {}
        for match in weekly_matches:
            user_groups.setdefault(match.user_id, []).append(match)
            
        for user_id, matches in user_groups.items():
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.notification_preference in ["Weekly", "ON"]:
                for match in matches:
                    match.sent_in_weekly = True
        db.commit()
    except Exception as e:
        print(f"[Worker Error] Weekly digest failed: {e}")
    finally:
        db.close()
