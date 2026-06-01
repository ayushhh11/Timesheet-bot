#!/usr/bin/env python3
"""
telegram_notify.py — sends a Telegram message via Bot API.
No browser session needed — works from any server.

Usage:
    python3 telegram_notify.py "your message here"
"""

import sys
import logging
import urllib.request
import urllib.parse

# ── Config ────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = ""   # ← paste your token
TELEGRAM_CHAT_ID = ""           # ← your chat ID
LOG_FILE = ""
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


def send(message: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.info("✅ Telegram message sent.")
                return True
            else:
                log.error(f"Telegram API error: {resp.status}")
                return False
    except Exception as e:
        log.error(f"Telegram send failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 telegram_notify.py "your message"')
        sys.exit(1)
    success = send(sys.argv[1])
    sys.exit(0 if success else 1)
