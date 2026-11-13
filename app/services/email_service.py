import json
import urllib.request
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from flask import current_app

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_async_email(app_config, recipient_email, recipient_name):
        brevo_api_key = app_config.get("BREVO_API_KEY")
        resend_api_key = app_config.get("RESEND_API_KEY")
        server = app_config.get("MAIL_SERVER")
        port = app_config.get("MAIL_PORT", 587)
        use_tls = app_config.get("MAIL_USE_TLS", True)
        username = app_config.get("MAIL_USERNAME")
        password = app_config.get("MAIL_PASSWORD")
        sender = app_config.get("MAIL_DEFAULT_SENDER", "akaswin145@gmail.com")

        subject = "Welcome to Trip Planner! 🎒✈️"
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f7f9f8; padding: 20px; color: #111827;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 30px; border: 1px solid #e5e7eb;">
              <h2 style="color: #0D6B58; margin-bottom: 8px;">Trip Planner</h2>
              <p style="font-size: 14px; color: #6b7280; margin-top: 0;">Plan together. Split fairly.</p>
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
              <h3>Welcome, {recipient_name}! 👋</h3>
              <p>Thank you for joining <strong>Trip Planner</strong>. You're all set to organize seamless trips with your friends and family.</p>
              <div style="background-color: #f0fdf4; border-left: 4px solid #0D6B58; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; color: #0D6B58; font-weight: bold;">Here is what you can do:</p>
                <ul style="margin: 8px 0 0; padding-left: 20px; color: #374151;">
                  <li>Create <strong>Packaged Trips</strong> with fixed budgets</li>
                  <li>Create <strong>Unpackaged Trips</strong> with pay-as-you-go tracking</li>
                  <li>Split expenses equally with zero confusion</li>
                </ul>
              </div>
              <p style="color: #6b7280; font-size: 13px;">Happy travels,<br>The Trip Planner Team</p>
            </div>
          </body>
        </html>
        """

        # Priority 1: Brevo HTTPS REST API (Port 443 - sends to ANY recipient email!)
        if brevo_api_key:
            try:
                payload = {
                    "sender": {"name": "Trip Planner", "email": sender if "@" in sender else "akaswin145@gmail.com"},
                    "to": [{"email": recipient_email, "name": recipient_name}],
                    "subject": subject,
                    "htmlContent": html_content
                }
                req = urllib.request.Request(
                    "https://api.brevo.com/v3/smtp/email",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "api-key": brevo_api_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "TripPlannerApp/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode("utf-8")
                    print(f"✅ [Brevo API] Welcome email successfully sent to {recipient_email}: {resp_body}")
                    logger.info(f"Welcome email sent via Brevo API to {recipient_email}")
                    return
            except Exception as e:
                err_msg = str(e)
                if hasattr(e, "read"):
                    try:
                        err_msg = e.read().decode("utf-8")
                    except Exception:
                        pass
                print(f"❌ [Brevo API] Failed to send welcome email to {recipient_email}: {err_msg}")
                logger.error(f"Brevo API error: {err_msg}")

        # Priority 2: Resend HTTPS API (Port 443)
        if resend_api_key:
            try:
                payload = {
                    "from": "Trip Planner <onboarding@resend.dev>",
                    "to": [recipient_email],
                    "subject": subject,
                    "html": html_content
                }
                req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {resend_api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "TripPlannerApp/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode("utf-8")
                    print(f"✅ [Resend API] Welcome email successfully sent to {recipient_email}: {resp_body}")
                    logger.info(f"Welcome email sent via Resend API to {recipient_email}")
                    return
            except Exception as e:
                err_msg = str(e)
                if hasattr(e, "read"):
                    try:
                        err_msg = e.read().decode("utf-8")
                    except Exception:
                        pass
                print(f"❌ [Resend API] Failed to send welcome email to {recipient_email}: {err_msg}")
                logger.error(f"Resend API error: {err_msg}")

        # Priority 3: SMTP (Gmail / Custom SMTP)
        if username and password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = sender
                msg["To"] = recipient_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(server, port, timeout=10) as s:
                    if use_tls:
                        s.starttls()
                    s.login(username, password)
                    s.send_message(msg)
                    print(f"✅ [SMTP] Welcome email successfully sent to {recipient_email}")
                    logger.info(f"Welcome email successfully sent to {recipient_email}")
                    return
            except Exception as e:
                print(f"❌ [SMTP] Failed to send welcome email to {recipient_email}: {str(e)}")
                logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")

        # Dev mode / unconfigured fallback: log email to console
        print(f"\n=======================================================")
        print(f"📧 [DEV EMAIL SIMULATOR] Welcome Email Sent!")
        print(f"To: {recipient_name} <{recipient_email}>")
        print(f"Subject: {subject}")
        print(f"=======================================================\n")

    @classmethod
    def send_welcome_email(cls, recipient_email: str, recipient_name: str):
        app_config = {
            "BREVO_API_KEY": current_app.config.get("BREVO_API_KEY"),
            "RESEND_API_KEY": current_app.config.get("RESEND_API_KEY"),
            "MAIL_SERVER": current_app.config.get("MAIL_SERVER"),
            "MAIL_PORT": current_app.config.get("MAIL_PORT"),
            "MAIL_USE_TLS": current_app.config.get("MAIL_USE_TLS"),
            "MAIL_USERNAME": current_app.config.get("MAIL_USERNAME"),
            "MAIL_PASSWORD": current_app.config.get("MAIL_PASSWORD"),
            "MAIL_DEFAULT_SENDER": current_app.config.get("MAIL_DEFAULT_SENDER"),
        }
        # Fire and forget in a separate background thread so registration is instantaneous
        thread = Thread(target=cls._send_async_email, args=(app_config, recipient_email, recipient_name))
        thread.daemon = True
        thread.start()
