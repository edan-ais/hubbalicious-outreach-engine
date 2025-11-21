import csv
import json
import random
import smtplib
import ssl
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# ================================
# LOAD SENDER ACCOUNTS
# ================================

with open("senders.json", "r") as f:
    SENDER_ACCOUNTS = json.load(f)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ================================
# SETTINGS
# ================================

CSV_PATH = "Fundraiser Outreach - Fundraiser Outreach.csv"
LOG_PATH = "sent_log.csv"

MIN_DELAY = 8
MAX_DELAY = 25
MAX_PER_ACCOUNT_PER_RUN = 200

SUBJECT_LINE = "Quick question about your PTO"

# ========================================================
# LOGGING
# ========================================================

def init_log_file():
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "sender_email",
                "recipient_email",
                "school",
                "admin_name",
                "status",
                "error"
            ])

def write_log(sender_email, recipient, school, admin_name, status, error=""):
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sender_email,
            recipient,
            school,
            admin_name,
            status,
            error
        ])


# ================================
# EMAIL TEMPLATE
# ================================

def build_email_body(admin_name, school):
    name = admin_name if admin_name else "there"

    return f"""Hi {name},

We’re connecting with local schools to understand how parent and community involvement is organized. I came across {school} and was hoping you might know the best contact for your PTO or parent leadership team.

Any direction would be a big help — thank you!

Best,
Hubbalicious Outreach Team
"""


# ================================
# SEND EMAIL
# ================================

def send_email(sender, to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender["email"], sender["password"])
        server.send_message(msg)


# ================================
# MAIN JOB
# ================================

def multi_account_outreach(csv_file):
    init_log_file()

    send_index = {acc["email"]: 0 for acc in SENDER_ACCOUNTS}

    already_contacted = set()
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        log_reader = csv.DictReader(f)
        for row in log_reader:
            already_contacted.add(row["recipient_email"])

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            recipient = (row.get("Email") or "").strip()
            if not recipient:
                continue

            # Skip if already contacted
            if recipient in already_contacted:
                continue

            school = row.get("School", "").strip()
            admin_name = row.get("Administrator Name", "").strip()

            eligible = [
                acc for acc in SENDER_ACCOUNTS
                if send_index[acc["email"]] < MAX_PER_ACCOUNT_PER_RUN
            ]

            if not eligible:
                print("All accounts hit limit.")
                break

            sender = random.choice(eligible)
            body = build_email_body(admin_name, school)

            print(f"Sending to {recipient} from {sender['email']}...")

            try:
                send_email(sender, recipient, SUBJECT_LINE, body)
                send_index[sender["email"]] += 1
                print("Sent!")

                write_log(sender["email"], recipient, school, admin_name, "success")

            except Exception as e:
                print(f"Error sending to {recipient}: {e}")
                write_log(sender["email"], recipient, school, admin_name, "error", str(e))

            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"Sleeping {delay:.1f} seconds\n")
            time.sleep(delay)

    print("Batch complete.")


if __name__ == "__main__":
    multi_account_outreach(CSV_PATH)
