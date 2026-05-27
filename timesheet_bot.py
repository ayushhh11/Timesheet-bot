#!/usr/bin/env python3
"""
PeopleStrong Timesheet Bot
--------------------------
PeopleStrong uses Flutter Web (CanvasKit) — the UI is drawn on canvas,
not HTML. We enable Flutter's accessibility/semantic layer first, which
exposes real interactive elements Playwright can click.

Usage:
    python timesheet_bot.py save_session   ← do ONCE to save login
    python timesheet_bot.py punch_in
    python timesheet_bot.py punch_out
    python timesheet_bot.py test_login
"""

import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from config import PEOPLESTRONG_URL, PAGE_TIMEOUT, LOG_FILE, HEADLESS


def notify(title: str, message: str):
    """Send a macOS desktop notification + WhatsApp message."""
    # Desktop notification
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "Basso"'
        ], check=False)
    except Exception:
        pass

    # WhatsApp notification via subprocess (avoids Playwright conflict)
    try:
        script = Path(__file__).parent / "whatsapp_notify.py"
        msg = f"{title}\n{message}"
        # Use sys.executable for full Python path — works correctly under cron
        subprocess.Popen(
            [sys.executable, str(script), msg],
            stdout=open(LOG_FILE, "a"),
            stderr=open(LOG_FILE, "a"),
            cwd=str(Path(__file__).parent),
            env={**__import__("os").environ, "PATH": "/usr/local/bin:/usr/bin:/bin"}
        )
    except Exception as e:
        log.warning(f"WhatsApp notify failed: {e}")

PROFILE_DIR = str(Path(__file__).parent / "ps_profile")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


def get_context(playwright, headless=True):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=headless,
        args=["--no-sandbox"],
    )


def enable_flutter_accessibility(page):
    """
    Flutter CanvasKit hides everything in canvas by default.
    Trigger accessibility layer via JS events, then wait for semantic tree.
    """
    for attempt in range(3):
        result = page.evaluate("""() => {
            const el = document.querySelector('flt-semantics-placeholder');
            if (!el) return 'not_found';
            ['pointerdown','pointerup','click'].forEach(type => {
                el.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true}));
            });
            return 'triggered';
        }""")
        log.info(f"Flutter accessibility trigger attempt {attempt+1}: {result}")
        page.wait_for_timeout(3000)

        # Check if semantic tree built — look for any flt-semantics group
        count = page.evaluate("""() => document.querySelectorAll('flt-semantics[role="group"]').length""")
        log.info(f"flt-semantics groups found: {count}")
        if count > 0:
            log.info("Semantic tree ready.")
            return

    log.warning("Semantic tree may not be fully built — proceeding anyway.")


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
    print("  punch_in and punch_out will now run automatically.\n")
    log.info(f"Session saved to {PROFILE_DIR}")


def run(action: str):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    if not Path(PROFILE_DIR).exists():
        log.error("No saved session. Run: python3 timesheet_bot.py save_session")
        sys.exit(1)

    log.info(f"Starting: {action}")

    with sync_playwright() as p:
        context = get_context(p, headless=HEADLESS)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT * 1000)

        try:
            if action == "test_login":
                _test_login(page)
                return

            _go_to_attendance(page)

            if action == "punch_in":
                _punch(page, "in")
            elif action == "punch_out":
                _punch(page, "out")

            ts = datetime.now().strftime('%H:%M')
            label = "Punched In 🟢" if action == "punch_in" else "Punched Out 🔴"
            notify(f"PeopleStrong — {label}", f"Timesheet marked at {ts}")
            log.info(f"✅ {action} done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except PWTimeout as e:
            page.screenshot(path="/tmp/ps_error.png")
            log.error(f"Timeout: {e} — screenshot → /tmp/ps_error.png")
            notify("⏰ PeopleStrong Bot Failed", f"Timeout during {action} — check log")
            sys.exit(1)
        except Exception as e:
            page.screenshot(path="/tmp/ps_error.png")
            log.error(f"Error: {e} — screenshot → /tmp/ps_error.png")
            notify("❌ PeopleStrong Bot Failed", f"{action} failed: {str(e)[:60]}")
            raise
        finally:
            context.close()


def _test_login(page):
    page.goto(PEOPLESTRONG_URL + "/oneweb/#/home", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    if "login" in page.url.lower() or "auth" in page.url.lower():
        log.error("❌ Session expired — run save_session again.")
        sys.exit(1)
    log.info("✅ Session valid.")


def _go_to_attendance(page):
    url = PEOPLESTRONG_URL.rstrip("/") + "/oneweb/#/attendance"
    log.info(f"Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(8000)  # Flutter needs extra time in headless mode

    if "login" in page.url.lower() or "auth" in page.url.lower():
        notify("🔐 PeopleStrong Session Expired", "Open Terminal: run save_session to re-login")
        raise RuntimeError("Redirected to login — run: python3 timesheet_bot.py save_session")

    # Enable Flutter's semantic/accessibility layer so elements become clickable
    enable_flutter_accessibility(page)
    log.info("Attendance page ready.")


def _punch(page, direction: str):
    """
    Click Punch in / Punch out.
    The button has no aria-label (Flutter CanvasKit), so we find it by
    locating the attendance card group and clicking the button inside it.
    """
    log.info(f"Looking for punch {direction} button inside attendance card...")

    result = page.evaluate("""() => {
        // Find the attendance card — the group whose label mentions Today's Shift
        const groups = [...document.querySelectorAll('flt-semantics[role="group"]')];
        const card = groups.find(g =>
            (g.getAttribute('aria-label') || '').includes("Today")
        );
        if (!card) return {error: "attendance card group not found"};

        const cr = card.getBoundingClientRect();

        // Find all role=button elements that sit inside the card's bounds
        const buttons = [...document.querySelectorAll('flt-semantics[role="button"]')];
        const inner = buttons.filter(b => {
            const br = b.getBoundingClientRect();
            return br.x >= cr.x && br.right <= cr.right &&
                   br.y >= cr.y && br.bottom <= cr.bottom &&
                   br.width > 10 && br.height > 10;
        });

        if (inner.length === 0) return {error: "no buttons inside attendance card"};

        // There is one button: the Punch in (or Punch out after punching in)
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
        raise RuntimeError(
            f"Could not locate punch button: {result['error']}\n"
            "Screenshot → /tmp/ps_punch_fail.png"
        )

    x, y = result["x"], result["y"]
    log.info(f"Found punch button at ({x:.0f}, {y:.0f}), label={result['label']!r}, "
             f"total buttons in card={result['total']}")

    # Use mouse click on canvas coordinates — more reliable than .click() for Flutter
    page.mouse.click(x, y)
    log.info(f"Clicked punch {direction} at ({x:.0f}, {y:.0f})")
    page.wait_for_timeout(2000)
    _confirm_dialog(page)


def _confirm_dialog(page):
    """Dismiss any confirmation popup that appears after punching."""
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
        log.info(f"Dismissed confirmation dialog: {result['lbl']!r}")


if __name__ == "__main__":
    valid = ("save_session", "punch_in", "punch_out", "test_login")
    if len(sys.argv) != 2 or sys.argv[1] not in valid:
        print("Usage: python3 timesheet_bot.py [save_session | punch_in | punch_out | test_login]")
        sys.exit(1)

    if sys.argv[1] == "save_session":
        save_session()
    else:
        run(sys.argv[1])
