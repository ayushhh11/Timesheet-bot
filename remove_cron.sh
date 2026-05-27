#!/bin/bash
# Remove PeopleStrong bot cron jobs
(crontab -l 2>/dev/null | grep -v "# peoplestrong-bot" | grep -v "timesheet_bot.py") | crontab -
echo "✅ PeopleStrong cron jobs removed."
crontab -l
