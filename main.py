#!/usr/bin/env python3
"""
Safe F-1 Visa Slot Monitor (read-only)

- DOES NOT log in to any account.
- Polls public appointment pages for change in availability.
- Sends email notifications via Mailjet when availability status changes.
- Persists last-known status to a small JSON file to avoid duplicate alerts.
- Use --test to send a single test email and exit.
"""

import os
import time
import json
import argparse
from datetime import datetime
import requests
from mailjet_rest import Client

# --------- Configuration (via environment variables) ----------
# Required Mailjet env vars:
#   MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE, MJ_SENDER_EMAIL, MJ_RECEIVER_EMAIL
MJ_PUBLIC = os.getenv("MJ_APIKEY_PUBLIC")
MJ_PRIVATE = os.getenv("MJ_APIKEY_PRIVATE")
MJ_SENDER_EMAIL = os.getenv("MJ_SENDER_EMAIL")  # verified sender in Mailjet
MJ_RECEIVER_EMAIL = os.getenv("MJ_RECEIVER_EMAIL")  # your email

# Monitoring settings
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
CONSULATE_URLS = os.getenv(
    "CONSULATE_URLS",
    "https://ais.usvisa-info.com/en-in/niv/appointments"
).split(",")  # comma-separated list of public pages to check

# Storage for last-known states
STATE_FILE = os.getenv("STATE_FILE", "last_status.json")

# Request settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# Safety notice included in messages
SAFETY_NOTICE = (
    "This is a read-only reminder alert. No login or booking was attempted by this monitor.\n"
    "Please open the link and log in manually if you want to book. Avoid multiple quick logins."
)

# ----------------------------------------------------------------

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

def send_mail(subject: str, text: str) -> bool:
    if not (MJ_PUBLIC and MJ_PRIVATE and MJ_SENDER_EMAIL and MJ_RECEIVER_EMAIL):
        print("Mailjet not fully configured. Skipping email send.")
        return False
    try:
        api = Client(auth=(MJ_PUBLIC, MJ_PRIVATE), version='v3.1')
        data = {
            "Messages": [
                {
                    "From": {"Email": MJ_SENDER_EMAIL, "Name": "Visa Monitor"},
                    "To": [{"Email": MJ_RECEIVER_EMAIL}],
                    "Subject": subject,
                    "TextPart": text
                }
            ]
        }
        res = api.send.create(data=data)
        code = getattr(res, "status_code", None)
        print(f"{datetime.utcnow().isoformat()} - Mailjet send status: {code}")
        return True
    except Exception as e:
        print("Mailjet send error:", e)
        return False

def fetch_page(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        r = requests.get(url.strip(), headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def interpret_availability(html_text: str) -> str:
    """
    Return one of: "no_slots", "possible_slots", "unknown"
    Basic heuristics:
     - If the page contains common 'no appointments' phrases -> no_slots
     - If page loaded fine but doesn't include 'no appointments' -> possible_slots
    """
    if not html_text:
        return "unknown"
    low = html_text.lower()
    # Common negative markers
    negatives = [
        "no appointments are available",
        "no appointment available",
        "there are no appointments available",
        "no appointment times available",
        "currently no appointments available"
    ]
    for n in negatives:
        if n in low:
            return "no_slots"
    # If page loaded (200) and doesn't include negatives -> possible_slots
    return "possible_slots"

def check_all(consulate_urls, last_state):
    results = {}
    for url in consulate_urls:
        url = url.strip()
        if not url:
            continue
        print(f"{datetime.utcnow().isoformat()} - Checking: {url}")
        text = fetch_page(url)
        status = interpret_availability(text)
        results[url] = status
    return results

def build_message(changes):
    lines = [
        "F-1 Visa Availability Change Detected",
        "",
        SAFETY_NOTICE,
        "",
        "Changes:",
    ]
    for url, (old, new) in changes.items():
        lines.append(f"- {url}")
        lines.append(f"  previous: {old}")
        lines.append(f"  now:      {new}")
        lines.append("")
    lines.append(f"Checked at: {datetime.utcnow().isoformat()} UTC")
    return "\n".join(lines)

def run_loop(interval_minutes=30):
    state = load_state()
    while True:
        try:
            new = check_all(CONSULATE_URLS, state)
            changes = {}
            for url, new_status in new.items():
                old_status = state.get(url)
                if old_status != new_status:
                    # Only alert when state flips to possible_slots OR changes in any way
                    changes[url] = (old_status or "unknown", new_status)
                state[url] = new_status
            if changes:
                msg = build_message(changes)
                subject = "F-1 Visa Slot Monitor: availability change"
                sent = send_mail(subject, msg)
                if sent:
                    print("Alert sent.")
                else:
                    print("Alert NOT sent (Mailjet issue).")
                save_state(state)
            else:
                print(f"{datetime.utcnow().isoformat()} - No changes. Sleeping {interval_minutes} minutes.")
            # Sleep with small jitter +/-10%
            base = interval_minutes * 60
            jitter = int(base * 0.1)
            wait = base + (0 if jitter == 0 else __import__("random").randint(-jitter, jitter))
            time.sleep(wait)
        except KeyboardInterrupt:
            print("Interrupted by user. Exiting.")
            break
        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(60)

def send_test():
    subject = "Test: F-1 Slot Monitor (Mailjet test)"
    body = "This is a test email from your safe F-1 Visa Slot Monitor.\n\n" + build_message({CONSULATE_URLS[0]: ("unknown", "possible_slots")})
    ok = send_mail(subject, body)
    print("Test send:", ok)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Send test email and exit")
    args = parser.parse_args()
    if args.test:
        send_test()
    else:
        print("Starting safe F-1 monitor. Interval minutes:", CHECK_INTERVAL_MINUTES)
        run_loop(CHECK_INTERVAL_MINUTES)
