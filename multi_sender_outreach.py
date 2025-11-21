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

# Safe throttling for Gmail
MIN_DELAY = 8
MAX_DELAY = 25

# Gmail safe warm-up limit
MAX_PER_ACCOUNT_PER_RUN = 200

SUBJECT_LINE = "Quick question about your PTO"


# ==========================
# PERSONALIZED EMAIL TEMPLATE
# ==========================

def build_email_body(contact_name, school_name):
    name = contact_name if contact_name else "there"

    return f"""Hi {name},

We’re connecting with local schools to understand how parent and community involvement is organized. I came across {school_name} and was hoping you might know the best contact for your PTO or parent leadership team.

Any direction would be a big help — thank you!

Best,
Hubbalicious Outreach Team
Helping Unite Businesses, LLC
"""


# ==========================
# SEND EMAIL FUNCTION
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
# MAIN LOGIC
# ==========================

def multi_account_outreach(csv_file):
    # Track sends per account
    send_index = {acc["email"]: 0 for acc in SENDER_ACCOUNTS}

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            recipient = (row.get("email") or "").strip()
            if not recipient:
                continue

            school_name = row.get("school_name", "").strip()
            contact_name = row.get("contact_name", "").strip()

            # Choose an account with available sending capacity
            eligible_accounts = [
                acc for acc in SENDER_ACCOUNTS
                if send_index[acc["email"]] < MAX_PER_ACCOUNT_PER_RUN
            ]

            if not eligible_accounts:
                print("All accounts reached daily limit. Ending run.")
                break

            sender = random.choice(eligible_accounts)

            # Build email
            body = build_email_body(contact_name, school_name)

            print(f"Sending to {recipient} from {sender['email']}...")

            try:
                send_email(sender, recipient, SUBJECT_LINE, body)
                send_index[sender["email"]] += 1
                print(f"Sent! Total from this account: {send_index[sender['email']]}")

            except Exception as e:
                print(f"Failed to send to {recipient} from {sender['email']}: {e}")

            # Human-like delay
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"Waiting {delay:.1f} seconds...\n")
            time.sleep(delay)

    print("BATCH COMPLETE.")


if __name__ == "__main__":
    multi_account_outreach(CSV_PATH)
