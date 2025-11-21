import csv
import json
import random
import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==========================
# LOAD SENDER ACCOUNTS
# ==========================

with open("senders.json", "r") as f:
    SENDER_ACCOUNTS = json.load(f)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ==========================
# OUTREACH SETTINGS
# ==========================

CSV_PATH = "schools.csv"

MIN_DELAY = 8
MAX_DELAY = 25

MAX_PER_ACCOUNT_PER_RUN = 200

SUBJECT_LINE = "Quick question about your PTO"


# ==========================
# PERSONALIZED EMAIL TEMPLATE
# ==========================

def build_email_body(admin_name, school):
    name = admin_name if admin_name else "there"

    return f"""Hi {name},

We’re connecting with local schools to understand how parent and community involvement is organized. I came across {school} and was hoping you might know the best contact for your PTO or parent leadership team.

Any direction would be a big help — thank you!

Best,
Hubbalicious Outreach Team
Helping Unite Businesses, LLC
"""


# ==========================
# SEND EMAIL
# ==========================

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


# ==========================
# MAIN SCRIPT
# ==========================

def multi_account_outreach(csv_file):
    send_index = {acc["email"]: 0 for acc in SENDER_ACCOUNTS}

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            recipient = (row.get("Email") or "").strip()
            if not recipient:
                continue

            school = row.get("School", "").strip()
            admin_name = row.get("Administrator Name", "").strip()

            # Pick sender with available capacity
            eligible = [
                acc for acc in SENDER_ACCOUNTS
                if send_index[acc["email"]] < MAX_PER_ACCOUNT_PER_RUN
            ]

            if not eligible:
                print("All accounts reached limit. Stopping run.")
                break

            sender = random.choice(eligible)

            # Build personalized message
            body = build_email_body(admin_name, school)

            print(f"Sending to {recipient} from {sender['email']}...")

            try:
                send_email(sender, recipient, SUBJECT_LINE, body)
                send_index[sender["email"]] += 1
                print(f"Sent! ({send_index[sender['email']]} from this account)")

            except Exception as e:
                print(f"Failed: {recipient} via {sender['email']} — {e}")

            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"Sleeping {delay:.1f} seconds...\n")
            time.sleep(delay)

    print("BATCH COMPLETE.")


if __name__ == "__main__":
    multi_account_outreach(CSV_PATH)
