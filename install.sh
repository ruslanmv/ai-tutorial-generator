#!/usr/bin/env bash
set -euo pipefail

# colors
BLUE="\033[1;34m"; GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; NC="\033[0m"

echo -e "${BLUE}🔄  Updating apt cache…${NC}"
sudo apt-get update -y

echo -e "${BLUE}📥  Adding deadsnakes PPA for Python 3.11…${NC}"
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update -y

echo -e "${BLUE}🐍  Installing Python 3.11 and venv support…${NC}"
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    curl \
    poppler-utils \
    ghostscript

echo -e "${GREEN}✅  Python check:${NC}"
printf "   • python3.11 → %s\n" "$(python3.11 --version)"
printf "   • pip3.11    → %s\n" "$(python3.11 -m pip --version || echo 'pip not yet installed')"

echo -e "${BLUE}🧹  Cleaning up…${NC}"
sudo apt-get autoremove -y

# Create & activate a Python 3.11 venv
if [ -d ".venv" ]; then
  echo -e "${YELLOW}⚠️   .venv exists; recreating with Python3.11...${NC}"
  rm -rf .venv
fi

echo -e "${BLUE}🐍  Creating virtual environment (.venv) with Python 3.11…${NC}"
python3.11 -m venv .venv

echo -e "${BLUE}🔐  Activating .venv…${NC}"
# shellcheck disable=SC1091
source .venv/bin/activate

echo -e "${BLUE}⬆️   Upgrading pip in the venv…${NC}"
pip install --upgrade pip

# Install project dependencies
if [ -f "requirements.txt" ]; then
  echo -e "${BLUE}📦  Installing Python dependencies…${NC}"
  pip install -r requirements.txt
else
  echo -e "${YELLOW}📄  No requirements.txt found; skipping.${NC}"
fi

echo -e "${GREEN}🎉  Setup complete!${NC}"
echo -e "   • Inside venv: python → $(python --version), pip → $(pip --version)"
