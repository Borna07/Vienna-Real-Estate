#!/bin/bash
# Unix/Linux cron script for Vienna Apartment Price Tracker
# Add to crontab to run every 3 days:
# 0 6 */3 * * /path/to/project/scripts/schedule_unix.sh >> /path/to/project/logs/cron.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment
source myenv/bin/activate

# Run scraper
python -m scripts.scrape

exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "Scrape failed with error code $exit_code"
    exit $exit_code
fi

echo "Scrape completed successfully"
