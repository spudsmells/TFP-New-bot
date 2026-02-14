#!/bin/bash
# PebbleHost startup script for The Gayborhood Bot
set -e

cd "$(dirname "$0")/.."

# Install/update dependencies
pip install -r requirements.txt --quiet

# Run the bot
python bot.py
