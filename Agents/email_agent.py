
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

# Setup logger
logger = logging.getLogger("HealthValidator")

class EmailVerificationAgent:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        
        # Load SMTP configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_username)
        
        # Check if real email sending is possible
        self.is_configured = all([self.smtp_username, self.smtp_password, self.sender_email])
        if not self.is_configured:
            logger.warning("⚠️ SMTP credentials not fully configured. Email agent running in SIMULATION mode.")

    def generate_verification_token(self) -> str:
        """Generates a secure, URL-safe token."""
        return secrets.token_urlsafe(32)

    def create_verification_link(self, token: str) -> str:
        """Creates the full verification URL."""
        return f"{self.base_url}/verify?token={token}"

    def send_verification_email(self, recipient_email: str, recipient_name: str, verification_link: str) -> bool:
        """
        Sends a verification email using configured SMTP server.
        Falls back to simulation (logging) if credentials are missing.
        """
        subject = f"ACTION REQUIRED: Verify Provider Details for {recipient_name}"
        
        body_text = f"""
        Dear Dr. {recipient_name},

        We require verification of your professional details for our Health Data Validation system.
        Please click the secure link below to review and update your information:

        {verification_link}

        This link will expire in 48 hours.

        Thank you,
        Health Validation Team
        """

        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #2563eb;">Health Data Validation Request</h2>
                <p>Dear <strong>Dr. {recipient_name}</strong>,</p>
                <p>We require verification of your professional details for our Health Data Validation system to ensure our provider directory is accurate.</p>
                <p>Please click the button below to review and update your information:</p>
                <p>
                    <a href="{verification_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Verify Information
                    </a>
                </p>
                <p style="font-size: 0.9em; color: #666;">If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{verification_link}">{verification_link}</a></p>
                <p style="margin-top: 30px; font-size: 0.8em; color: #888;">This link will expire in 48 hours.</p>
                <p>Thank you,<br>Health Validation Team</p>
            </body>
        </html>
        """

        # 1. Simulation Mode (Log only)
        if not self.is_configured or "your_email" in str(self.smtp_username):
            logger.info(f"📧 [SIMULATION] To: {recipient_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Link: {verification_link}")
            return True

        # 2. Real Sending Mode (SMTP)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient_email

            part1 = MIMEText(body_text, "plain")
            part2 = MIMEText(body_html, "html")
            msg.attach(part1)
            msg.attach(part2)

            logger.info(f"🚀 Connecting to SMTP server {self.smtp_server}:{self.smtp_port}...")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls() # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
            
            logger.info(f"✅ Email successfully sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email via SMTP: {e}")
            # Fallback to logging the link so usage isn't blocked
            logger.info(f"Fallback Debug Link: {verification_link}")
            return False
