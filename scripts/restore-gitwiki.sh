#!/bin/bash
#
# GitWiki Restore Script
# Restores GitWiki from a backup directory
#
# Usage: ./restore-gitwiki.sh /backup/gitwiki/20251026_020000
#
# WARNING: This will overwrite existing data!
# Always stop GitWiki services before restoring.
#

set -e  # Exit on error

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_directory>"
    echo "Example: $0 /backup/gitwiki/20251026_020000"
    exit 1
fi

BACKUP_DIR="$1"

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Load environment if available
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Paths
REPO_PATH="${WIKI_REPO_PATH:-$PROJECT_ROOT/wiki_repo}"
STATIC_PATH="${WIKI_STATIC_PATH:-$PROJECT_ROOT/wiki_static}"

# Database settings
if [ ! -z "$DATABASE_URL" ]; then
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

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Confirmation
echo ""
log_warn "================================================"
log_warn "WARNING: This will restore GitWiki from backup"
log_warn "Backup Directory: $BACKUP_DIR"
log_warn "Current data will be OVERWRITTEN!"
log_warn "================================================"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled"
    exit 0
fi

# Check if services are running
log_info "Checking if GitWiki services are running..."
if systemctl is-active --quiet gitwiki 2>/dev/null; then
    log_warn "GitWiki service is running. Please stop it first:"
    echo "  sudo systemctl stop gitwiki celery-worker celery-beat"
    exit 1
fi

# Start restore
log_info "Starting restore from: $BACKUP_DIR"

# Restore 1: Git Repository
if [ -f "$BACKUP_DIR/repo.tar.gz" ]; then
    log_info "Restoring Git repository..."

    # Backup existing repo
    if [ -d "$REPO_PATH" ]; then
        log_info "Backing up existing repository to ${REPO_PATH}.old"
        mv "$REPO_PATH" "${REPO_PATH}.old"
    fi

    # Extract backup
    mkdir -p "$(dirname "$REPO_PATH")"
    tar -xzf "$BACKUP_DIR/repo.tar.gz" -C "$(dirname "$REPO_PATH")"
    log_info "Git repository restored"
else
    log_warn "No repository backup found in $BACKUP_DIR"
fi

# Restore 2: Database
if [ -f "$BACKUP_DIR/database.sql.gz" ]; then
    log_info "Restoring database..."

    # Drop and recreate database
    log_warn "Dropping existing database: $DB_NAME"
    PGPASSWORD="${DB_PASSWORD}" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true

    log_info "Creating fresh database: $DB_NAME"
    PGPASSWORD="${DB_PASSWORD}" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

    log_info "Restoring database dump..."
    gunzip < "$BACKUP_DIR/database.sql.gz" | PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    log_info "Database restored"
else
    log_warn "No database backup found in $BACKUP_DIR"
fi

# Restore 3: Configuration
if [ -f "$BACKUP_DIR/env.backup" ]; then
    log_info "Configuration backup found"
    log_warn "Configuration NOT automatically restored (security)"
    log_info "To restore configuration, manually copy:"
    echo "  cp $BACKUP_DIR/env.backup $ENV_FILE"
else
    log_warn "No configuration backup found"
fi

# Restore 4: Static Files
if [ -f "$BACKUP_DIR/static.tar.gz" ]; then
    log_info "Restoring static files..."

    # Backup existing static
    if [ -d "$STATIC_PATH" ]; then
        log_info "Backing up existing static files to ${STATIC_PATH}.old"
        mv "$STATIC_PATH" "${STATIC_PATH}.old"
    fi

    # Extract backup
    mkdir -p "$(dirname "$STATIC_PATH")"
    tar -xzf "$BACKUP_DIR/static.tar.gz" -C "$(dirname "$STATIC_PATH")"
    log_info "Static files restored"
else
    log_info "No static files backup found (can be regenerated)"
fi

# Post-restore tasks
echo ""
log_info "================================================"
log_info "Restore Complete!"
log_info "================================================"
echo ""
log_info "Next steps:"
echo "  1. Review configuration file if needed"
echo "  2. Regenerate static files (optional):"
echo "     python manage.py full_static_rebuild"
echo "  3. Start GitWiki services:"
echo "     sudo systemctl start gitwiki celery-worker celery-beat"
echo "  4. Verify restoration:"
echo "     curl http://localhost:8000/health/"
echo ""

exit 0
