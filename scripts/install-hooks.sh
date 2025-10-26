#!/bin/bash
#
# GitWiki Git Hooks Installation Script
#
# This script installs pre-commit hooks for GitWiki repository.
# Run this after cloning the repository to enable branch validation.
#
# Usage:
#   ./scripts/install-hooks.sh
#

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}GitWiki Git Hooks Installer${NC}"
echo "=============================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Verify we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ ERROR: Not in a Git repository${NC}"
    echo "Please run this script from the GitWiki project directory."
    exit 1
fi

echo "Project root: $PROJECT_ROOT"
echo ""

# Install pre-commit hook
PRE_COMMIT_SOURCE="$PROJECT_ROOT/.githooks/pre-commit"
PRE_COMMIT_DEST="$PROJECT_ROOT/.git/hooks/pre-commit"

if [ ! -f "$PRE_COMMIT_SOURCE" ]; then
    echo -e "${RED}❌ ERROR: Pre-commit hook not found at $PRE_COMMIT_SOURCE${NC}"
    exit 1
fi

echo "Installing pre-commit hook..."
cp "$PRE_COMMIT_SOURCE" "$PRE_COMMIT_DEST"
chmod +x "$PRE_COMMIT_DEST"
echo -e "${GREEN}✅ Pre-commit hook installed${NC}"
echo ""

# Show what the hook does
echo -e "${BLUE}What does the pre-commit hook do?${NC}"
echo "- Validates draft branch naming (draft-{user_id}-{uuid})"
echo "- Prevents direct commits to 'main' branch"
echo "- Enforces GitWiki's draft/publish workflow"
echo ""

# Test the hook
echo "Testing hook installation..."
if [ -x "$PRE_COMMIT_DEST" ]; then
    echo -e "${GREEN}✅ Hook is executable and ready${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: Hook may not be executable${NC}"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "The hooks will now run automatically before each commit."
echo ""
echo "To bypass hooks (not recommended): git commit --no-verify"
echo ""
