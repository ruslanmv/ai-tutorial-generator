#!/usr/bin/env bash
set -euo pipefail

# ANSI color codes
BLUE="\033[1;34m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
  echo -e "${BLUE}🔐 Activating virtual environment…${NC}"
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo -e "${YELLOW}⚠️  No .venv found. Please run ./install.sh first to create it.${NC}"
  exit 1
fi

# Prompt user to open browser
read -rp "🌐  Launch web UI in browser? [Y/n] " OPEN_BROWSER
OPEN_BROWSER=${OPEN_BROWSER:-Y}

# Start the Flask app in the background
echo -e "${BLUE}🚀  Starting AI Tutorial Generator web server…${NC}"
python app.py &

SERVER_PID=$!

# Give the server a moment to start
sleep 1

URL="http://0.0.0.0:8080"

# Optionally open the default browser
if [[ "$OPEN_BROWSER" =~ ^[Yy]$ ]]; then
  echo -e "${BLUE}🌍  Opening ${URL}${NC}"
  # Linux
  if command -v xdg-open &> /dev/null; then
    xdg-open "$URL"
  # macOS
  elif command -v open &> /dev/null; then
    open "$URL"
  else
    echo -e "${YELLOW}⚠️  Could not detect a browser opener command. Please open ${URL} manually.${NC}"
  fi
else
  echo -e "${GREEN}👉  Web UI available at ${URL}${NC}"
fi

# Wait for the server process to end
wait $SERVER_PID
echo -e "${GREEN}✅  Server stopped. Exiting…${NC}"
echo -e "${YELLOW}⚠️  If you want to stop the server, use Ctrl+C.${NC}"