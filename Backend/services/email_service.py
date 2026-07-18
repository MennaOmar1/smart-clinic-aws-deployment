import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))


def send_email(
    to_email: str,
    subject: str,
    body: str
):

    try:

        msg = MIMEMultipart()

        msg["From"] = f"Clinify Support <{EMAIL_ADDRESS}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        ) as server:

            server.starttls()

            server.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            server.sendmail(
                EMAIL_ADDRESS,
                to_email,
                msg.as_string()
            )

        print(f"✅ Email sent to {to_email}")

    except Exception as e:

        print(f"❌ Email failed: {e}")