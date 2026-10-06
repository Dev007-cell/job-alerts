# Govt Job Alerts -> Telegram + WhatsApp

## 1. Telegram (2 min)
1. In Telegram, message **@BotFather** -> `/newbot` -> copy the **bot token**.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id` -> **chat id**.

## 2. WhatsApp (pick one)
**CallMeBot (free, own number):** follow the setup on callmebot.com (you send a
one-time activation message to their WhatsApp number and get an API key).
Set `CALLMEBOT_PHONE` (e.g. +91XXXXXXXXXX) and `CALLMEBOT_APIKEY`.

**Twilio:** create an account, join the WhatsApp sandbox, then set
`TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_TO`. Check Twilio's current
pricing and session rules first.

## 3. Run it
Local test:
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
    python main.py            # first run indexes existing notices silently

Automatic (free): push this folder to a GitHub repo, add the values above under
Settings -> Secrets and variables -> Actions, then enable Actions. It runs
every 15 minutes and commits `seen.json` to remember what it already sent.

## 4. Tune it
- Edit `SOURCES` in `main.py`: point each URL at the exact recruitment page and
  narrow `selector` (e.g. `"table a"`) to cut noise. I could not test these live
  sites, so expect to adjust a few.
- Set `KEYWORDS` env var (comma-separated) to filter, e.g. `agniveer,constable,acio`.
- Always confirm a notice on the official site before applying.
