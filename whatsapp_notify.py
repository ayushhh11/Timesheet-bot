#!/usr/bin/env python3
"""
whatsapp_notify.py — sends a WhatsApp message to yourself via WhatsApp Web.
Uses a saved browser session so no API or login needed each time.

Usage:
    python3 whatsapp_notify.py save_session        ← do once
    python3 whatsapp_notify.py "your message here" ← send a message
"""

import sys
import logging
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────
# Your WhatsApp number with country code, no + or spaces
# India example: 919876543210  (91 = India code, then your 10-digit number)
MY_PHONE = "91XXXXXXXXXX"   # ← replace with your number

WA_PROFILE_DIR = str(Path(__file__).parent / "wa_profile")
LOG_FILE = "/tmp/peoplestrong_bot.log"
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


def get_context(playwright, headless=False):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=WA_PROFILE_DIR,
        headless=headless,
        args=["--no-sandbox"],
    )


def save_session():
    """Open WhatsApp Web — scan QR once — session saved forever."""
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 55)
    print("  WHATSAPP SAVE SESSION")
    print("  A browser will open WhatsApp Web.")
    print("  Scan the QR code with your phone.")
    print("  Once your chats are visible, press Enter here.")
    print("=" * 55 + "\n")

    with sync_playwright() as p:
        context = get_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        input("  Press Enter once WhatsApp Web is fully loaded: ")
        context.close()

    print(f"\n  ✅ WhatsApp session saved to: {WA_PROFILE_DIR}/")
    print("  Messages will now be sent automatically.\n")


def send(message: str):
    """Send a WhatsApp message to MY_PHONE."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    if not Path(WA_PROFILE_DIR).exists():
        log.error("No WhatsApp session. Run: python3 whatsapp_notify.py save_session")
        return False

    log.info("=== WhatsApp notify started ===")
    log.info(f"Sending WhatsApp: {message[:60]}")

    with sync_playwright() as p:
        context = get_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60000)

        try:
            # Direct URL to open/start chat with your number
            url = f"https://web.whatsapp.com/send?phone={MY_PHONE}&text={message}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)  # WhatsApp Web takes time to load

            # Wait longer for WhatsApp Web to fully load the chat
            page.wait_for_timeout(8000)

            # Try multiple selectors for the message input box
            input_box = None
            selectors = [
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][data-tab="1"]',
                'footer div[contenteditable="true"]',
                'div[role="textbox"]',
                'div[contenteditable="true"][spellcheck="true"]',
            ]
            for sel in selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=4000):
                        input_box = loc
                        log.info(f"Found input box via: {sel}")
                        break
                except Exception:
                    continue

            if not input_box:
                raise RuntimeError("Could not find WhatsApp message input box")

            input_box.click()
            page.wait_for_timeout(1000)

            # Clear pre-filled text from URL and type fresh
            input_box.press("Control+a")
            input_box.type(message, delay=50)
            page.wait_for_timeout(500)

            # Send
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)

            log.info("✅ WhatsApp message sent.")
            return True

        except PWTimeout:
            log.error("WhatsApp send timed out — session may have expired.")
            log.error("Run: python3 whatsapp_notify.py save_session")
            return False
        except Exception as e:
            log.error(f"WhatsApp send failed: {e}")
            return False
        finally:
            context.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 whatsapp_notify.py save_session")
        print('  python3 whatsapp_notify.py "your message"')
        sys.exit(1)

    if sys.argv[1] == "save_session":
        save_session()
    else:
        success = send(sys.argv[1])
        sys.exit(0 if success else 1)
