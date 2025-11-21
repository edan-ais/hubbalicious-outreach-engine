import csv
import json
import random
import smtplib
import ssl
import time
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from openai import OpenAI
from dotenv import load_dotenv

# ================================
# LOAD API KEY
# ================================
load_dotenv()
client = OpenAI()

# ============================================================
# MODE SWITCH — EDIT THIS LINE ONLY
# Options: "development" or "production"
# ============================================================

MODE = "development"   # ← change to "production" when ready
TEST_EMAIL = "support@hubbalicious.com"

print(f"\n========== RUNNING IN {MODE.upper()} MODE ==========\n")


# ============================================================
# FILE PATHS
# ============================================================

CSV_PATH = "school_scraper/fundraiser_outreach.csv"
LOG_PATH = "sent_log.csv"
SENDERS_PATH = "senders.json"


# ============================================================
# LOAD SENDER ACCOUNTS
# ============================================================

with open(SENDERS_PATH, "r") as f:
    SENDER_ACCOUNTS = json.load(f)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# ============================================================
# SETTINGS
# ============================================================

MIN_DELAY = 8
MAX_DELAY = 25
MAX_PER_ACCOUNT_PER_RUN = 200
SUBJECT_LINE = "Quick question about your PTO"


# ============================================================
# LOGGING
# ============================================================

def init_log_file():
    """Create log file if missing."""
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
    """Append a row to the log file."""
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
    print(f"LOG: {status.upper()} | {recipient} | via {sender_email}")


# ============================================================
# AI PERSONALIZED EMAIL GENERATION
# ============================================================

def build_email_body(admin_name, school, county, entity_type, website):
    """
    Generates a unique, warm, human, non-commercial email asking 
    for the PTO contact, personalized to the school and admin.
    """

    prompt = f"""
You are generating a friendly, non-commercial outreach email.

PURPOSE:
Ask for the PTO contact. Do NOT pitch or describe a service.

TONE:
Friendly, natural, warm, conversational, human. 
It must sound individually typed.

PERSONALIZATION DETAILS:
- Administrator Name: {admin_name}
- School: {school}
- County: {county}
- Entity Type: {entity_type}
- Website: {website}

REQUIREMENTS:
- 4–6 sentences max.
- No sales language.
- No "we offer", "we provide", or promotional tone.
- Start with “Hi {admin_name},” or “Hi there,” if blank.
- End with: Hubbalicious Outreach Team
- Ask gently for the PTO contact.
- Make it feel personal, not automated.
- DO NOT mention AI or personalization.

OUTPUT:
Return the full email body only, no quotes.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


# ============================================================
# SEND EMAIL
# ============================================================

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


# ============================================================
# OUTREACH ENGINE
# ============================================================

def multi_account_outreach(csv_file):
    init_log_file()

    # Load already-contacted recipients
    already_contacted = set()
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            already_contacted.add(row["recipient_email"])

    # Track sent count per account
    send_index = {acc["email"]: 0 for acc in SENDER_ACCOUNTS}

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:

            # DEVELOPMENT MODE
            if MODE == "development":
                recipient = TEST_EMAIL

            else:
                # PRODUCTION MODE
                recipient = (row.get("Email") or "").strip()
                if not recipient:
                    continue
                if recipient in already_contacted:
                    continue

            admin_name = row.get("Administrator Name", "").strip()
            school = row.get("School", "").strip()
            county = row.get("County", "").strip()
            entity_type = row.get("Entity Type", "").strip()
            website = row.get("Website", "").strip()

            # Determine eligible sending accounts
            eligible = [
                acc for acc in SENDER_ACCOUNTS
                if send_index[acc["email"]] < MAX_PER_ACCOUNT_PER_RUN
            ]

            if not eligible:
                print("All accounts are at their daily sending limit.")
                break

            sender = random.choice(eligible)

            print(f"\nGenerating AI email for {recipient}...")
            body = build_email_body(admin_name, school, county, entity_type, website)

            print(f"Sending from {sender['email']} to {recipient}...")

            try:
                send_email(sender, recipient, SUBJECT_LINE, body)
                send_index[sender["email"]] += 1
                print(" ✔ SENT")

                write_log(sender["email"], recipient, school, admin_name, "success")

            except Exception as e:
                print(f" ✖ ERROR: {e}")
                write_log(sender["email"], recipient, school, admin_name, "error", str(e))

            # Randomized wait to avoid spam filters
            delay = round(random.uniform(MIN_DELAY, MAX_DELAY), 2)
            print(f" ⏳ Waiting {delay} seconds...\n")
            time.sleep(delay)

            # DEV MODE stops after one email per account
            if MODE == "development":
                if all(send_index[a["email"]] >= 1 for a in SENDER_ACCOUNTS):
                    print("\nDEV MODE COMPLETE — one test email per account sent.")
                    break

    print("\n========== BATCH COMPLETE ==========\n")


if __name__ == "__main__":
    multi_account_outreach(CSV_PATH)
