# PeopleStrong Timesheet Bot 🤖

Automatically punches in/out on PeopleStrong HRMS at scheduled times on macOS.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | **Your settings** — URL and punch timings |
| `timesheet_bot.py` | Playwright automation script |
| `install.sh` | One-time dependency installer |
| `setup_cron.sh` | Installs cron jobs from your config |
| `remove_cron.sh` | Removes the cron jobs |

---

## Setup (do this once)

### 1. Install dependencies
```bash
bash install.sh
```

### 2. Edit config.py
Open `config.py` and fill in:
```python
PEOPLESTRONG_URL = "https://yourcompany.peoplestrong.com"
PUNCH_IN_TIME    = "09:00"   # 24-hr format
PUNCH_OUT_TIME   = "18:00"
HEADLESS         = False     # set True once tested
```

### 3. Save your session (do this once)
```bash
python3 timesheet_bot.py save_session
```
A browser window will open. Log in manually (including any OTP/MFA). Press Enter in the terminal when done — your session is saved to `ps_profile/` and reused for all future runs.

### 4. Test punch in
```bash
python3 timesheet_bot.py punch_in
```
Watch it navigate and click the Punch In button. If the button isn't found, see **Troubleshooting** below.

### 5. Schedule with cron
```bash
bash setup_cron.sh
```

### 6. Grant cron Full Disk Access (macOS requirement)
1. **System Settings → Privacy & Security → Full Disk Access**
2. Click **+** and add `/usr/sbin/cron`
3. If `/usr/sbin/cron` isn't visible, press **Cmd+Shift+G** and type that path

---

## Manual usage

```bash
python3 timesheet_bot.py save_session   # once — saves your login to ps_profile/
python3 timesheet_bot.py punch_in
python3 timesheet_bot.py punch_out
python3 timesheet_bot.py test_login    # verify saved session is still valid
```

---

## Viewing logs

```bash
tail -f /tmp/peoplestrong_bot.log
```

---

## Troubleshooting

### Button not found
PeopleStrong's UI labels differ by company config. To find the right selector:

1. Set `HEADLESS = False` in config.py
2. Run `python3 timesheet_bot.py test_login` — browser stays open
3. Navigate to Attendance manually
4. Right-click the Punch In button → **Inspect**
5. Note the button text, `id`, or `data-*` attribute
6. Open `timesheet_bot.py`, find `_click_punch_button()`, and add your selector to the `candidates` list

### Two-factor authentication (OTP)
OTP/MFA is handled during `save_session` — the browser opens and waits for you to complete login including any OTP before saving the session. Subsequent `punch_in`/`punch_out` runs use the saved session and don't require OTP.

### cron not running
- Check logs: `cat /tmp/peoplestrong_bot.log`
- Verify cron entries: `crontab -l`
- Ensure Full Disk Access is granted (step 6 above)
- Ensure your Mac is awake at punch times (disable sleep or use a caffeinate wrapper)

### Keep Mac awake
Add this to crontab (already handled by setup_cron.sh — shown for reference):
```
# Prevent sleep 5 min before punch in
55 8 * * 1-5 caffeinate -t 600 &
```

---

## Remove the bot
```bash
bash remove_cron.sh
```
