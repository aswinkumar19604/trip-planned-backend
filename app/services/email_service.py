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
        server = app_config.get("MAIL_SERVER")
        port = app_config.get("MAIL_PORT", 587)
        use_tls = app_config.get("MAIL_USE_TLS", True)
        username = app_config.get("MAIL_USERNAME")
        password = app_config.get("MAIL_PASSWORD")
        sender = app_config.get("MAIL_DEFAULT_SENDER", "welcome@tripplanner.com")

        # Dev mode / unconfigured fallback: log email to console
        if not username or not password:
            print(f"\n=======================================================")
            print(f"📧 [DEV EMAIL SIMULATOR] Welcome Email Sent!")
            print(f"To: {recipient_name} <{recipient_email}>")
            print(f"Subject: Welcome to Trip Planner - Plan Together, Split Fairly!")
            print(f"Body: Hello {recipient_name}! Welcome to Trip Planner. Start creating packaged or unpackaged trips now!")
            print(f"=======================================================\n")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Welcome to Trip Planner! 🎒✈️"
            msg["From"] = sender
            msg["To"] = recipient_email

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
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(server, port, timeout=10) as s:
                if use_tls:
                    s.starttls()
                s.login(username, password)
                s.send_message(msg)
                logger.info(f"Welcome email successfully sent to {recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")

    @classmethod
    def send_welcome_email(cls, recipient_email: str, recipient_name: str):
        app_config = {
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

