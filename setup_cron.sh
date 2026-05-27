#!/bin/bash
# ─────────────────────────────────────────────────────
#  setup_cron.sh — Install cron jobs for PeopleStrong
# ─────────────────────────────────────────────────────
# Run this ONCE after configuring config.py.
# Usage: bash setup_cron.sh

set -e

# ── Resolve paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_SCRIPT="$SCRIPT_DIR/timesheet_bot.py"
PYTHON_BIN="$(which python3)"

# Read punch times from config.py
PUNCH_IN_TIME=$(python3 -c "from config import PUNCH_IN_TIME; print(PUNCH_IN_TIME)" 2>/dev/null || echo "09:00")
PUNCH_OUT_TIME=$(python3 -c "from config import PUNCH_OUT_TIME; print(PUNCH_OUT_TIME)" 2>/dev/null || echo "18:00")

# Parse into cron fields (HH:MM → M H)
IN_HOUR=$(echo "$PUNCH_IN_TIME"  | cut -d: -f1 | sed 's/^0//')
IN_MIN=$( echo "$PUNCH_IN_TIME"  | cut -d: -f2 | sed 's/^0//')
OUT_HOUR=$(echo "$PUNCH_OUT_TIME" | cut -d: -f1 | sed 's/^0//')
OUT_MIN=$( echo "$PUNCH_OUT_TIME" | cut -d: -f2 | sed 's/^0//')

# Default to 0 if empty (e.g. "09:00" → hour=9, min=0)
IN_MIN=${IN_MIN:-0}
OUT_MIN=${OUT_MIN:-0}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PeopleStrong Bot — Cron Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Python  : $PYTHON_BIN"
echo "  Script  : $BOT_SCRIPT"
echo "  Punch In : $PUNCH_IN_TIME  (cron: $IN_MIN $IN_HOUR * * 1-5)"
echo "  Punch Out: $PUNCH_OUT_TIME (cron: $OUT_MIN $OUT_HOUR * * 1-5)"
echo ""

# ── Build cron entries ─────────────────────────────────────────────────────────
# Runs Monday–Friday (1-5) only
CRON_IN="$IN_MIN $IN_HOUR * * 1-5 cd '$SCRIPT_DIR' && $PYTHON_BIN '$BOT_SCRIPT' punch_in >> /tmp/peoplestrong_bot.log 2>&1"
CRON_OUT="$OUT_MIN $OUT_HOUR * * 1-5 cd '$SCRIPT_DIR' && $PYTHON_BIN '$BOT_SCRIPT' punch_out >> /tmp/peoplestrong_bot.log 2>&1"

# ── Install into crontab ───────────────────────────────────────────────────────
MARKER="# peoplestrong-bot"

# Remove old entries if any
(crontab -l 2>/dev/null | grep -v "$MARKER") | crontab - || true

# Add new entries
(crontab -l 2>/dev/null
  echo "$MARKER"
  echo "$CRON_IN"
  echo "$CRON_OUT"
) | crontab -

echo "✅ Cron jobs installed:"
crontab -l | grep -A3 "$MARKER"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⚠️  macOS cron needs Full Disk Access"
echo "  Go to: System Settings → Privacy & Security"
echo "        → Full Disk Access → add 'cron'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To remove these cron jobs later, run:"
echo "  bash remove_cron.sh"
