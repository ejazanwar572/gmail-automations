#!/bin/zsh
export PATH="/Users/ejazanwar/.pyenv/shims:/Users/ejazanwar/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONUNBUFFERED=1

cd "/Users/ejazanwar/Documents/Gmail Automations" || exit 1

mkdir -p "Instamart_Alerts/logs"
LOG_FILE="Instamart_Alerts/logs/instamart_scraper_run.log"

echo "==================================================" >> "$LOG_FILE"
echo "Starting Instamart Scraper run at $(date)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

/Users/ejazanwar/.pyenv/shims/python3 "Instamart_Alerts/instamart_scraper.py" >> "$LOG_FILE" 2>&1

echo "Run finished at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
