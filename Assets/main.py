from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from worker import send_email_notification, send_sms_notification

app = FastAPI(title="Notification System")

# Request schema
class MatchPayload(BaseModel):
  user_id: int
  email: EmailStr
  phone: str
  match_details: str

@app.post("/trigger-match")
def trigger_match(payload: MatchPayload):
  """
  Simulates a database matching event.
  Saves state to PostgreSQL (logic omitted for brevity) and queues notifications.
  """
  # 1. Save the match data into your PostgreSQL here
  print(f"[API] Match found for User {payload.user_id}. Storing in PostgreSQL...")

  # 2. Hand off the notifications to the Redis Queue
  notification_msg = f"Match found: {payload.match_details}"

  # .delay() pushes the task to Redis immediately
  send_email_notification.delay(payload.email, notification_msg)
  send_sms_notification.delay(payload.phone, notification_msg)

  return {
    "status": "success",
    "message": "Match processed. Notifications queued asynchronously."
  }


