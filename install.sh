#!/bin/bash
# ─────────────────────────────────────────
#  install.sh — One-time setup
# ─────────────────────────────────────────
set -e

echo "📦 Installing Python dependencies..."
pip3 install playwright

echo "🌐 Installing Chromium browser for Playwright..."
playwright install chromium

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit config.py with your URL, username, password & timings"
echo "  2. Test:  python3 timesheet_bot.py test_login"
echo "  3. Trial: python3 timesheet_bot.py punch_in"
echo "  4. Schedule: bash setup_cron.sh"
