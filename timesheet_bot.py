#!/usr/bin/env python3
"""
PeopleStrong Timesheet Bot
--------------------------
PeopleStrong uses Flutter Web (CanvasKit) — the UI is drawn on canvas,
not HTML. We enable Flutter's accessibility/semantic layer first, which
exposes real interactive elements Playwright can click.

Usage:
    python timesheet_bot.py save_session   ← do ONCE to save login
    python timesheet_bot.py punch_in       ← Mon-Fri only (via cron)
    python timesheet_bot.py punch_out      ← Mon-Fri only (via cron)
    python timesheet_bot.py keep_warm      ← every 2 hrs, 7 days (via cron)

Cron setup on server:
    12 4  * * 1-5  cd /home/ubuntu/peoplestrong-bot && xvfb-run python3 timesheet_bot.py punch_in  >> /tmp/peoplestrong_bot.log 2>&1
    33 14 * * 1-5  cd /home/ubuntu/peoplestrong-bot && xvfb-run python3 timesheet_bot.py punch_out >> /tmp/peoplestrong_bot.log 2>&1
    0  */2 * * *   cd /home/ubuntu/peoplestrong-bot && xvfb-run python3 timesheet_bot.py keep_warm >> /tmp/peoplestrong_bot.log 2>&1
"""

import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from config import PEOPLESTRONG_URL, PAGE_TIMEOUT, LOG_FILE, HEADLESS

# ── Constants ─────────────────────────────────────────────────────────────────
PROFILE_DIR    = str(Path(__file__).parent / "ps_profile")
PUNCH_LOG_FILE = "/var/www/html/punch_log.json"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# ── Notifications ─────────────────────────────────────────────────────────────
def telegram(message: str):
    """Send a Telegram message synchronously — guaranteed to fire before process exits."""
    try:
        script = Path(__file__).parent / "telegram_notify.py"
        subprocess.run(
            [sys.executable, str(script), message],
            timeout=20,
            stdout=open(LOG_FILE, "a"),
            stderr=open(LOG_FILE, "a"),
        )
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")


def notify(title: str, message: str):
    """Send desktop notification (Mac only) + Telegram."""
    # macOS desktop notification — skipped silently on Linux
    try:
        if subprocess.run(["which", "osascript"], capture_output=True).returncode == 0:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}" sound name "Basso"'
            ], check=False)
    except Exception:
        pass
    # Telegram — works everywhere
    telegram(f"{title}\n{message}")


# ── Punch log (nginx dashboard) ───────────────────────────────────────────────
def write_punch_log(action: str, status: str):
    """Append punch event to JSON file served by nginx dashboard."""
    try:
        try:
            with open(PUNCH_LOG_FILE, "r") as f:
                entries = json.load(f)
        except Exception:
            entries = []
        entries.append({
            "action": action,
            "status": status,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        entries = entries[-200:]  # keep last 200
        with open(PUNCH_LOG_FILE, "w") as f:
            json.dump(entries, f)
        log.info(f"Punch log updated: {action} / {status}")
    except Exception as e:
        log.warning(f"Could not write punch log: {e}")


# ── Browser context ───────────────────────────────────────────────────────────
def get_context(playwright, headless=True):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )


# ── Flutter accessibility ─────────────────────────────────────────────────────
def enable_flutter_accessibility(page):
    """
    Flutter CanvasKit renders entirely on canvas — no HTML elements.
    Triggering the accessibility placeholder forces Flutter to build
    a semantic DOM tree we can interact with.
    """
    for attempt in range(10):
        page.evaluate("""() => {
            const el = document.querySelector('flt-semantics-placeholder');
            if (el) ['pointerdown','pointerup','click'].forEach(type =>
                el.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true}))
            );
        }""")
        log.info(f"Flutter accessibility trigger attempt {attempt + 1}")
        page.wait_for_timeout(5000)

        found = page.evaluate("""() => {
            const groups = document.querySelectorAll('flt-semantics[role="group"]');
            return [...groups].some(g =>
                (g.getAttribute('aria-label') || '').includes('Today') ||
                (g.getAttribute('aria-label') || '').includes('Punch')
            );
        }""")
        count = page.evaluate("""() => document.querySelectorAll('flt-semantics[role="group"]').length""")
        log.info(f"Groups found: {count}, attendance card present: {found}")
        if found:
            log.info("✅ Attendance card ready.")
            return

    log.warning("Attendance card not found after 10 attempts — proceeding anyway.")


# ── Save session (one time) ───────────────────────────────────────────────────
def save_session():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("  SAVE SESSION — only needed once")
    print("  A browser will open. Log in + complete MFA.")
    print("  Once on the home page, press Enter here.")
    print("=" * 60 + "\n")

    with sync_playwright() as p:
        context = get_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(PEOPLESTRONG_URL + "/oneweb/#/home", wait_until="domcontentloaded")
        input("  Press Enter once you are fully logged in: ")
        context.close()

    print(f"\n  ✅ Session saved to: {PROFILE_DIR}/")
    log.info(f"Session saved to {PROFILE_DIR}")


# ── Keep warm (runs every 2 hrs, 7 days a week) ───────────────────────────────
def keep_warm(page):
    """
    Visit PeopleStrong pages to keep the session alive.
    Sends Telegram alert immediately if session has expired.
    """
    log.info("=== Keep warm started ===")

    page.goto(PEOPLESTRONG_URL + "/oneweb/#/home", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    # Check if redirected to login
    if "login" in page.url.lower() or "auth" in page.url.lower():
        log.error("❌ Session expired during keep_warm.")
        telegram(
            "🔐 PeopleStrong Session Expired\n"
            "Bot cannot punch in/out.\n"
            "Fix: Run save_session on Mac and re-upload ps_profile."
        )
        sys.exit(1)

    # Visit attendance page — triggers real API calls on the server side
    page.goto(PEOPLESTRONG_URL + "/oneweb/#/attendance", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # Check again after navigation
    if "login" in page.url.lower() or "auth" in page.url.lower():
        log.error("❌ Session expired on attendance page.")
        telegram(
            "🔐 PeopleStrong Session Expired\n"
            "Redirected to login on attendance page.\n"
            "Fix: Run save_session on Mac and re-upload ps_profile."
        )
        sys.exit(1)

    # Go back home to complete the activity cycle
    page.goto(PEOPLESTRONG_URL + "/oneweb/#/home", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)

    log.info("✅ Session is alive and warm.")


# ── Navigate to attendance ────────────────────────────────────────────────────
def go_to_attendance(page):
    url = PEOPLESTRONG_URL.rstrip("/") + "/oneweb/#/attendance"
    log.info(f"Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(15000)

    if "login" in page.url.lower() or "auth" in page.url.lower():
        telegram(
            "🔐 PeopleStrong Session Expired\n"
            "Punch failed — redirected to login.\n"
            "Fix: Run save_session on Mac and re-upload ps_profile."
        )
        raise RuntimeError("Redirected to login — session expired.")

    enable_flutter_accessibility(page)
    log.info("Attendance page ready.")


# ── Punch ─────────────────────────────────────────────────────────────────────
def punch(page, direction: str):
    """Find and click Punch In / Punch Out button using Flutter semantic tree."""
    log.info(f"Looking for punch {direction} button...")

    result = page.evaluate("""() => {
        const groups = [...document.querySelectorAll('flt-semantics[role="group"]')];
        const card = groups.find(g => (g.getAttribute('aria-label') || '').includes('Today'));
        if (!card) return {error: "attendance card not found"};

        const cr = card.getBoundingClientRect();
        const buttons = [...document.querySelectorAll('flt-semantics[role="button"]')];
        const inner = buttons.filter(b => {
            const br = b.getBoundingClientRect();
            return br.x >= cr.x && br.right <= cr.right &&
                   br.y >= cr.y && br.bottom <= cr.bottom &&
                   br.width > 10 && br.height > 10;
        });
        if (inner.length === 0) return {error: "no buttons inside attendance card"};

        const btn = inner[0];
        const br = btn.getBoundingClientRect();
        return {
            x: br.x + br.width / 2,
            y: br.y + br.height / 2,
            label: btn.getAttribute('aria-label') || '(no label)',
            total: inner.length,
        };
    }""")

    if isinstance(result, dict) and result.get("error"):
        page.screenshot(path="/tmp/ps_punch_fail.png")
        raise RuntimeError(f"Could not locate punch button: {result['error']}")

    x, y = result["x"], result["y"]
    log.info(f"Clicking punch {direction} at ({x:.0f}, {y:.0f})")
    page.mouse.click(x, y)
    page.wait_for_timeout(2000)
    confirm_dialog(page)


def confirm_dialog(page):
    """Dismiss any confirmation popup after punching."""
    page.wait_for_timeout(1500)
    result = page.evaluate("""() => {
        const els = document.querySelectorAll('flt-semantics[role="button"]');
        for (const el of els) {
            const lbl = (el.getAttribute('aria-label') || '').toLowerCase();
            if (['confirm','ok','yes','submit','done'].some(k => lbl.includes(k))) {
                const r = el.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2, lbl};
            }
        }
        return null;
    }""")
    if result:
        page.mouse.click(result["x"], result["y"])
        log.info(f"Dismissed confirmation: '{result['lbl']}'")


# ── Main runner ───────────────────────────────────────────────────────────────
def run(action: str):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    if not Path(PROFILE_DIR).exists():
        log.error("No saved session. Run: python3 timesheet_bot.py save_session")
        sys.exit(1)

    log.info(f"=== Starting: {action} ===")

    with sync_playwright() as p:
        context = get_context(p, headless=HEADLESS)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT * 1000)

        try:
            if action == "keep_warm":
                keep_warm(page)

            elif action in ("punch_in", "punch_out"):
                go_to_attendance(page)
                direction = "in" if action == "punch_in" else "out"
                punch(page, direction)

                from datetime import timezone, timedelta
                IST = timezone(timedelta(hours=5, minutes=30))
                ts = datetime.now(IST).strftime("%H:%M")
                label = "Punched In 🟢" if action == "punch_in" else "Punched Out 🔴"
                notify(f"PeopleStrong — {label}", f"Timesheet marked at {ts} IST")
                log.info(f"✅ {action} done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                write_punch_log(action, "success")

        except SystemExit:
            raise  # already sent Telegram, just exit

        except PWTimeout as e:
            page.screenshot(path="/tmp/ps_error.png")
            log.error(f"Timeout: {e}")
            notify("⏰ PeopleStrong Bot Failed", f"Timeout during {action}")
            write_punch_log(action, "failure")
            sys.exit(1)

        except Exception as e:
            page.screenshot(path="/tmp/ps_error.png")
            log.error(f"Error: {e}")
            notify("❌ PeopleStrong Bot Failed", f"{action} failed: {str(e)[:80]}")
            write_punch_log(action, "failure")
            raise

        finally:
            context.close()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    valid = ("save_session", "punch_in", "punch_out", "keep_warm")
    if len(sys.argv) != 2 or sys.argv[1] not in valid:
        print("Usage: python3 timesheet_bot.py [save_session | punch_in | punch_out | keep_warm]")
        sys.exit(1)

    if sys.argv[1] == "save_session":
        save_session()
    else:
        run(sys.argv[1])