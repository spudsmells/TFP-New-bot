#!/bin/bash
# SQLite backup script — run via cron for regular backups
set -e

cd "$(dirname "$0")/.."

DB_FILE="bot.db"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ ! -f "$DB_FILE" ]; then
    echo "Database file not found: $DB_FILE"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# Use SQLite's backup command for safe copy
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/bot_${TIMESTAMP}.db'"

echo "Backup created: $BACKUP_DIR/bot_${TIMESTAMP}.db"

# Keep only the last 7 backups
ls -t "$BACKUP_DIR"/bot_*.db | tail -n +8 | xargs -r rm --
echo "Old backups cleaned up."
