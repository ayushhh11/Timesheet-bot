#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  server_install.sh
#  Run this ON THE ORACLE VM after uploading files.
#  Sets up Python, Playwright, and cron.
# ─────────────────────────────────────────────────────────────────
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PeopleStrong Bot — Server Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update system
echo "→ Updating system packages..."
sudo apt-get update -qq

# Install Python + pip
echo "→ Installing Python..."
sudo apt-get install -y -qq python3 python3-pip

# Install Playwright dependencies (headless Chromium on Linux needs these)
echo "→ Installing browser system dependencies..."
sudo apt-get install -y -qq \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libxshmfence1 wget ca-certificates

# Install Playwright Python package
echo "→ Installing Playwright..."
pip3 install playwright --break-system-packages 2>/dev/null || pip3 install playwright

# Install Chromium for Playwright
echo "→ Installing Playwright Chromium..."
python3 -m playwright install chromium
python3 -m playwright install-deps chromium 2>/dev/null || true

echo ""
echo "→ Testing bot can reach PeopleStrong..."
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox'])
    pg = b.new_page()
    pg.goto('https://onenv.peoplestrong.com/oneweb/#/home', wait_until='domcontentloaded', timeout=20000)
    print('  ✅ Can reach PeopleStrong:', pg.url)
    b.close()
"

# ── Set up cron ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3)"

# Read punch times from config.py and convert IST → UTC (subtract 5h 30m)
read IN_HOUR IN_MIN OUT_HOUR OUT_MIN <<< $(python3 - << PYEOF
import sys
sys.path.insert(0, "$SCRIPT_DIR")
from config import PUNCH_IN_TIME, PUNCH_OUT_TIME

def ist_to_utc(t):
    h, m = map(int, t.split(":"))
    total = h * 60 + m - 330  # subtract 5h30m
    total = total % (24 * 60)  # wrap around midnight
    return total // 60, total % 60

ih, im = ist_to_utc(PUNCH_IN_TIME)
oh, om = ist_to_utc(PUNCH_OUT_TIME)
print(ih, im, oh, om)
PYEOF
)

echo ""
echo "→ Installing cron jobs..."
echo "  Punch in : $PUNCH_IN_TIME  (cron: $IN_MIN $IN_HOUR * * 1-5)"
echo "  Punch out: $PUNCH_OUT_TIME (cron: $OUT_MIN $OUT_HOUR * * 1-5)"

CRON_IN="$IN_MIN $IN_HOUR * * 1-5 cd '$SCRIPT_DIR' && $PYTHON_BIN timesheet_bot.py punch_in  >> /tmp/peoplestrong_bot.log 2>&1"
CRON_OUT="$OUT_MIN $OUT_HOUR * * 1-5 cd '$SCRIPT_DIR' && $PYTHON_BIN timesheet_bot.py punch_out >> /tmp/peoplestrong_bot.log 2>&1"

MARKER="# peoplestrong-bot"
(crontab -l 2>/dev/null | grep -v "$MARKER") | crontab - || true
(crontab -l 2>/dev/null
  echo "$MARKER"
  echo "$CRON_IN"
  echo "$CRON_OUT"
) | crontab -

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup complete!"
echo ""
echo "  Test punch_in now:"
echo "    cd $SCRIPT_DIR && python3 timesheet_bot.py punch_in"
echo ""
echo "  Watch logs:"
echo "    tail -f /tmp/peoplestrong_bot.log"
echo ""
echo "  The VM will punch in/out automatically Mon–Fri"
echo "  even when your laptop is off."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
