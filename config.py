# ─────────────────────────────────────────────
#  PeopleStrong Timesheet Bot — Configuration
# ─────────────────────────────────────────────
# Fill in your details below before running.

# Your company's PeopleStrong login page URL
# Example: "https://acme.peoplestrong.com"
PEOPLESTRONG_URL = "Work url ^ "


# Punch timings  (24-hour format: "HH:MM")
PUNCH_IN_TIME  = "09:36"
PUNCH_OUT_TIME = "20:06"

# Keep False — Flutter Web needs a visible browser to build its semantic tree reliably.
HEADLESS = False

# How many seconds to wait for page elements before giving up
PAGE_TIMEOUT = 30

# Log file location (leave as-is or change to a preferred path)
LOG_FILE = "/tmp/peoplestrong_bot.log"
