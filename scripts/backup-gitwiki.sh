#!/bin/bash
#
# GitWiki Backup Script
# Performs comprehensive backup of all GitWiki data
#
# Usage: ./backup-gitwiki.sh [backup_dir]
#
# Creates timestamped backups of:
# - Git repository (wiki content)
# - PostgreSQL database
# - Configuration files
# - Static files (optional)
#
# Schedule with cron for automated backups:
# 0 2 * * * /path/to/backup-gitwiki.sh /backup/gitwiki >> /var/log/gitwiki-backup.log 2>&1

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default backup directory (can be overridden)
BACKUP_ROOT="${1:-/backup/gitwiki}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE"

# Paths (adjust these for your installation)
REPO_PATH="${WIKI_REPO_PATH:-$PROJECT_ROOT/wiki_repo}"
STATIC_PATH="${WIKI_STATIC_PATH:-$PROJECT_ROOT/wiki_static}"
ENV_FILE="$PROJECT_ROOT/.env"

# Database settings (loaded from .env if available)
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Parse DATABASE_URL if present
if [ ! -z "$DATABASE_URL" ]; then
    # Extract database name from DATABASE_URL
    # Format: postgresql://user:password@host:port/dbname
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
else
    DB_NAME="${DB_NAME:-gitwiki}"
    DB_USER="${DB_USER:-gitwiki}"
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
fi

# Retention settings
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"  # Keep backups for 30 days

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create backup directory
log_info "Starting GitWiki backup to: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup 1: Git Repository
log_info "Backing up Git repository..."
if [ -d "$REPO_PATH/.git" ]; then
    tar -czf "$BACKUP_DIR/repo.tar.gz" -C "$(dirname "$REPO_PATH")" "$(basename "$REPO_PATH")" 2>/dev/null
    REPO_SIZE=$(du -sh "$BACKUP_DIR/repo.tar.gz" | cut -f1)
    log_info "Git repository backup complete (Size: $REPO_SIZE)"
else
    log_warn "Git repository not found at: $REPO_PATH"
fi

# Backup 2: PostgreSQL Database
log_info "Backing up PostgreSQL database..."
if command -v pg_dump &> /dev/null; then
    PGPASSWORD="${DB_PASSWORD}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/database.sql.gz" 2>/dev/null
    if [ $? -eq 0 ]; then
        DB_SIZE=$(du -sh "$BACKUP_DIR/database.sql.gz" | cut -f1)
        log_info "Database backup complete (Size: $DB_SIZE)"
    else
        log_error "Database backup failed"
    fi
else
    log_warn "pg_dump not found, skipping database backup"
fi

# Backup 3: Configuration Files
log_info "Backing up configuration files..."
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$BACKUP_DIR/env.backup"
    log_info "Configuration backup complete"
else
    log_warn ".env file not found at: $ENV_FILE"
fi

# Backup 4: Static Files (optional, can be regenerated)
if [ "${BACKUP_STATIC:-false}" = "true" ]; then
    log_info "Backing up static files..."
    if [ -d "$STATIC_PATH" ]; then
        tar -czf "$BACKUP_DIR/static.tar.gz" -C "$(dirname "$STATIC_PATH")" "$(basename "$STATIC_PATH")" 2>/dev/null
        STATIC_SIZE=$(du -sh "$BACKUP_DIR/static.tar.gz" | cut -f1)
        log_info "Static files backup complete (Size: $STATIC_SIZE)"
    else
        log_warn "Static files directory not found at: $STATIC_PATH"
    fi
else
    log_info "Skipping static files (set BACKUP_STATIC=true to enable)"
fi

# Create backup manifest
cat > "$BACKUP_DIR/manifest.txt" <<EOF
GitWiki Backup Manifest
=======================
Backup Date: $(date)
Backup Directory: $BACKUP_DIR

Repository Path: $REPO_PATH
Database Name: $DB_NAME
Static Path: $STATIC_PATH

Files in this backup:
EOF

ls -lh "$BACKUP_DIR" >> "$BACKUP_DIR/manifest.txt"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_info "Total backup size: $TOTAL_SIZE"

# Cleanup old backups
log_info "Cleaning up backups older than $KEEP_DAYS days..."
find "$BACKUP_ROOT" -maxdepth 1 -type d -name "20*" -mtime +$KEEP_DAYS -exec rm -rf {} \; 2>/dev/null || true
REMAINING=$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name "20*" | wc -l)
log_info "Remaining backups: $REMAINING"

# Create "latest" symlink
ln -sfn "$BACKUP_DIR" "$BACKUP_ROOT/latest"

# Final summary
echo ""
log_info "================================================"
log_info "Backup Complete!"
log_info "Backup Location: $BACKUP_DIR"
log_info "Total Size: $TOTAL_SIZE"
log_info "================================================"

# Exit successfully
exit 0
