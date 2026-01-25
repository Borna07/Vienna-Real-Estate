#!/bin/bash
set -e

PROJECT="/home/dev/vienna/Vienna-Real-Estate"
BRANCH="main"
SESSION="vienna"

cd "$PROJECT"

# Fetch & check if remote changed
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "$(date): No changes."

  # If app is not running, start it anyway
  if ! pgrep -f "uvicorn src.app:app --host 0.0.0.0 --port 8080" >/dev/null; then
    echo "$(date): App not running. Starting..."
    tmux send-keys -t "$SESSION" "cd $PROJECT" C-m
    tmux send-keys -t "$SESSION" "source venv/bin/activate" C-m
    tmux send-keys -t "$SESSION" "uvicorn src.app:app --host 0.0.0.0 --port 8080" C-m
  fi

  exit 0
fi


echo "$(date): Changes detected. Updating..."

# Overwrite local with remote (you said you want overwrite everything)
git reset --hard "origin/$BRANCH"
git clean -fd

# Restart app inside tmux
# Sends commands to the tmux session: stop current process, start again
tmux send-keys -t "$SESSION" C-c
sleep 1
tmux send-keys -t "$SESSION" "cd $PROJECT" C-m
tmux send-keys -t "$SESSION" "source venv/bin/activate" C-m
tmux send-keys -t "$SESSION" "uvicorn src.app:app --host 0.0.0.0 --port 8080" C-m

echo "$(date): Updated and restarted."
