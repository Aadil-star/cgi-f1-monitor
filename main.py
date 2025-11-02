import os
import time
import requests
from bs4 import BeautifulSoup
from mailjet_rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MJ_APIKEY_PUBLIC = os.getenv("MJ_APIKEY_PUBLIC")
MJ_APIKEY_PRIVATE = os.getenv("MJ_APIKEY_PRIVATE")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
CONSULATE = os.getenv("CONSULATE", "All")
VISA_TYPE = os.getenv("VISA_TYPE", "F1")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

mailjet = Client(auth=(MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE), version='v3.1')

def send_email_alert(subject, message):
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "aadilkhan1424@gmail.com",
                    "Name": "Visa Slot Notifier"
                },
                "To": [
                    {
                        "Email": RECEIVER_EMAIL
                    }
                ],
                "Subject": subject,
                "TextPart": message
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(f"📧 Email sent: {result.status_code}")

def check_slots():
    url = "https://www.ustraveldocs.com/in/en"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Placeholder logic (you can expand this)
    if "F1" in soup.text:
        print("✅ Slot info found (mock check)")
        send_email_alert(
            "✅ F1 Visa Slot Monitor — Slot Detected",
            f"Visa slots detected for {CONSULATE}!"
        )
    else:
        print("No F1 slots yet.")

def main():
    print(f"✅ Monitoring started for {VISA_TYPE} visa slots at CGI Federal ({CONSULATE})")
    print(f"⏰ Checking every {CHECK_INTERVAL_MINUTES} minutes...")

    while True:
        try:
            check_slots()
        except Exception as e:
            print(f"⚠️ Error: {e}")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
