"""Government job notification watcher -> Telegram + WhatsApp.

Run every 10-15 min (GitHub Actions cron or any scheduler).
Config comes from environment variables, see README.md.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SEEN_FILE = Path(os.getenv("SEEN_FILE", "seen.json"))
HEADERS = {"User-Agent": "Mozilla/5.0 (job-alert-bot; personal use)"}
TIMEOUT = 25

# Starting points only: open each URL in a browser and swap in the exact
# "Recruitment / Notifications / What's New" page you want. The "selector"
# narrows which part of the page to scan (leave "a" to scan every link).
SOURCES = [
    {"name": "UPSC",        "url": "https://upsc.gov.in/",                          "selector": "a"},
    {"name": "SSC",         "url": "https://ssc.gov.in/",                           "selector": "a"},
    {"name": "MHA/IB",      "url": "https://www.mha.gov.in/en/notifications/vacancies", "selector": "a"},
    {"name": "Army",        "url": "https://joinindianarmy.nic.in/",                "selector": "a"},
    {"name": "Navy",        "url": "https://www.joinindiannavy.gov.in/",            "selector": "a"},
    {"name": "DRDO",        "url": "https://www.drdo.gov.in/",                      "selector": "a"},
    {"name": "TNPSC",       "url": "https://www.tnpsc.gov.in/",                     "selector": "a"},
    {"name": "Employment News", "url": "https://www.employmentnews.gov.in/",        "selector": "a"},
]

# A link is kept only if its text contains one of these (case-insensitive).
KEYWORDS = [k.strip().lower() for k in os.getenv(
    "KEYWORDS",
    "recruitment,vacancy,vacancies,notification,advertisement,advt,agniveer,"
    "constable,acio,examination,apply online,posts,admit card,result",
).split(",") if k.strip()]


def fetch_items(src):
    r = requests.get(src["url"], headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = {}
    for a in soup.select(src.get("selector", "a")):
        href = a.get("href")
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if not href or href.startswith(("#", "javascript:", "mailto:")) or len(title) < 12:
            continue
        if KEYWORDS and not any(k in title.lower() for k in KEYWORDS):
            continue
        url = urljoin(src["url"], href)
        key = hashlib.sha1(f"{url}|{title}".encode()).hexdigest()
        items[key] = {"source": src["name"], "title": title, "url": url}
    return items


# ---------- notifiers ----------
def send_telegram(text):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text, "disable_web_page_preview": "true"},
        timeout=TIMEOUT,
    )
    if not r.ok:
        print("Telegram failed:", r.text, file=sys.stderr)


def send_whatsapp(text):
    text = text[:1500]
    # Option A: CallMeBot (free, personal use)
    phone, key = os.getenv("CALLMEBOT_PHONE"), os.getenv("CALLMEBOT_APIKEY")
    if phone and key:
        r = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": text, "apikey": key},
            timeout=TIMEOUT,
        )
        if not r.ok:
            print("CallMeBot failed:", r.text, file=sys.stderr)
    # Option B: Twilio WhatsApp
    sid, tok = os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")
    to = os.getenv("TWILIO_WHATSAPP_TO")  # e.g. +91XXXXXXXXXX
    frm = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")  # sandbox number
    if sid and tok and to:
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, tok),
            data={"From": f"whatsapp:{frm}", "To": f"whatsapp:{to}", "Body": text},
            timeout=TIMEOUT,
        )
        if not r.ok:
            print("Twilio failed:", r.text, file=sys.stderr)


def notify(text):
    send_telegram(text)
    send_whatsapp(text)


# ---------- main ----------
def main():
    first_run = not SEEN_FILE.exists()
    seen = set(json.loads(SEEN_FILE.read_text())) if not first_run else set()
    new_items = []

    for src in SOURCES:
        try:
            items = fetch_items(src)
        except Exception as e:  # one broken site must not stop the rest
            print(f"[{src['name']}] error: {e}", file=sys.stderr)
            continue
        for key, item in items.items():
            if key not in seen:
                seen.add(key)
                new_items.append(item)
        print(f"[{src['name']}] {len(items)} matching links")

    SEEN_FILE.write_text(json.dumps(sorted(seen)))

    if first_run:
        notify(f"Job alert bot is live. Indexed {len(new_items)} existing notices; "
               "you'll only get new ones from now on.")
        return
    if not new_items:
        return

    # send in batches so messages stay short
    for i in range(0, len(new_items), 8):
        batch = new_items[i:i + 8]
        lines = [f"New govt notices ({i + 1}-{i + len(batch)} of {len(new_items)})"]
        for it in batch:
            lines.append(f"\n[{it['source']}] {it['title']}\n{it['url']}")
        notify("\n".join(lines))


if __name__ == "__main__":
    main()
