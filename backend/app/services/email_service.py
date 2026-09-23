import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_parent_request_email(student_email: str, relationship: str, token: str):
    """
    Send an email to the student with a verification link for the parent request.
    In mock mode or if SMTP is not fully configured, it simulates the email.
    """
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print(f"[MOCK EMAIL] Sending to: {student_email}")
        print(f"[MOCK EMAIL] Relationship: {relationship}")
        print(f"[MOCK EMAIL] Verification Link: {settings.FRONTEND_BASE_URL}/parent-request/verify?token={token}")
        return True

    msg = MIMEMultipart()
    msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg['To'] = student_email
    msg['Subject'] = "SMARTBUS Parent/Guardian Connection Request"

    verification_link = f"{settings.FRONTEND_BASE_URL}/parent-request/verify?token={token}"

    body = f"""Hello,

A Parent/Guardian has requested to connect with your SMARTBUS account.

Relationship: {relationship}

If you approve this request, the Parent will be allowed to complete their SMARTBUS Parent account registration.

HOW TO APPROVE:
1. Open the SMARTBUS mobile app on your phone.
2. Log in with your student account.
3. Go to the 'Profile' tab (bottom right).
4. Tap 'PARENT REQUESTS' and tap 'Accept'.

Once you have accepted the request in the app, the Parent must enter this Registration Token in the app to complete their setup:

Registration Token: {token}

This request expires after {settings.PARENT_REQUEST_TOKEN_EXPIRY_MINUTES} minutes.
If you did not expect this request, you can simply ignore it.

Regards,
SMARTBUS System"""
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
