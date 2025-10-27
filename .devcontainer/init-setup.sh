#!/bin/bash
# GitWiki DevContainer Initialization Script
# Runs on first container creation

set -e

echo "========================================="
echo "GitWiki DevContainer Initialization"
echo "========================================="
echo ""

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -U gitwiki; do
    echo "  PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✓ PostgreSQL is ready"
echo ""

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli -h redis ping > /dev/null 2>&1; do
    echo "  Redis is unavailable - sleeping"
    sleep 2
done
echo "✓ Redis is ready"
echo ""

# Initialize wiki repository if it doesn't exist
if [ ! -d "/app/wiki-repo/.git" ]; then
    echo "Initializing wiki content repository..."
    cd /app/wiki-repo
    git init
    git config user.name "GitWiki System"
    git config user.email "system@gitwiki.local"

    # Create initial README
    cat > README.md << 'EOF'
# GitWiki

Welcome to your GitWiki!

This is your main wiki page. You can edit this and create new pages through the web interface.

## Getting Started

1. Visit http://localhost:8015 to view your wiki
2. Click "Edit" to modify any page
3. Use the admin interface at http://localhost:8015/admin (create a superuser first)

## Features

- Web-based markdown editor
- Git-backed version control
- Image upload support (clipboard paste!)
- Conflict resolution
- Full-text search

Happy wiki-ing!
EOF

    git add README.md
    git commit -m "Initial commit: GitWiki setup"
    echo "✓ Wiki repository initialized"
    cd /workspace
else
    echo "✓ Wiki repository already exists"
fi
echo ""

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --no-input
echo "✓ Migrations complete"
echo ""

# Initialize GitWiki configuration
echo "Initializing GitWiki configuration..."
python manage.py init_config 2>/dev/null || echo "  Configuration already exists"
echo "✓ Configuration initialized"
echo ""

# Create logs directory
echo "Setting up logs directory..."
mkdir -p /workspace/logs
echo "✓ Logs directory ready"
echo ""

# Install git hooks
echo "Installing git hooks..."
if [ -f "/workspace/scripts/install-hooks.sh" ]; then
    bash /workspace/scripts/install-hooks.sh || echo "  (hooks already installed or not needed)"
else
    echo "  (hook installation script not found, skipping)"
fi
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Create a superuser (optional):"
echo "   python manage.py createsuperuser"
echo ""
echo "2. Start the development server:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "3. Access your wiki:"
echo "   http://localhost:8015"
echo ""
echo "4. Access admin interface:"
echo "   http://localhost:8015/admin"
echo ""
echo "Background services (Celery) are already running!"
echo "========================================="
