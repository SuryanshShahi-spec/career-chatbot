import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()
#1. Setup Gmail configurations
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "15"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")


def send_job_alert(recipient_email: str, job_title: str, location: str, jobs_list: list):
    """
    Sends a job alert email with the provided list of jobs.
    """
    if not recipient_email or not job_title or not location:
        print("Error: recipient email, job title, and location are required.")
        return False

    if not SENDER_EMAIL or not APP_PASSWORD:
        print("Error: SMTP credentials not found in environment.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"New Job Alerts for {job_title} in {location}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    
    if not jobs_list:
        content = f"There are currently no new jobs for {job_title} in {location}. We will keep looking!"
    else:
        content = f"Here are the latest jobs for {job_title} in {location}:\n\n"
        for i, job in enumerate(jobs_list, 1):
            content += f"{i}. {job.get('title', 'Unknown Title')} at {job.get('company', 'Unknown Company')}\n"
            content += f"   Link: {job.get('url', 'No link provided')}\n\n"
            
    msg.set_content(content)

    try:
        # 3. Connect and send
        with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        print(f"Email sent successfully to {recipient_email}!")
        return True

    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
        return False

if __name__ == "__main__":
    if os.getenv("RUN_EMAIL_TEST") == "1":
        recipient = os.getenv("TEST_RECIPIENT")
        if not recipient:
            raise SystemExit("Set TEST_RECIPIENT when RUN_EMAIL_TEST=1.")

        success = send_job_alert(
            recipient,
            "Python Developer",
            "Remote",
            [{"title": "Senior Python Dev", "company": "Tech Corp", "url": "http://example.com"}],
        )
        raise SystemExit(0 if success else 1)

    print("emailand.py loaded successfully. Set RUN_EMAIL_TEST=1 and TEST_RECIPIENT to send a test email.")