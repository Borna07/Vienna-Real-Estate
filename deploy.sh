#!/bin/bash
set -e

PROJECT="/home/dev/vienna/Vienna-Real-Estate"
BRANCH="main"
SERVICE="vienna-real-estate"

cd "$PROJECT"

# Fetch & check if remote changed
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "$(date): No changes."

  # If app is not running, start it anyway
  if ! systemctl is-active --quiet "$SERVICE"; then
    echo "$(date): App not running. Starting..."
    sudo -n systemctl start "$SERVICE"
  fi

  exit 0
fi


echo "$(date): Changes detected. Updating..."

# Overwrite local with remote (you said you want overwrite everything)
git reset --hard "origin/$BRANCH"
git clean -fd

# Restart the systemd service (see deploy/vienna-real-estate.service)
sudo -n systemctl restart "$SERVICE"

echo "$(date): Updated and restarted."
