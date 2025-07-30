#!/bin/bash
# =============================================================================
# QuranBot Dashboard Startup Script
# =============================================================================
# This script ensures the dashboard starts properly in production mode
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASHBOARD_DIR="$(dirname "$SCRIPT_DIR")"

# Change to dashboard directory
cd "$DASHBOARD_DIR"

# Activate virtual environment
source venv/bin/activate

# Set production environment variables if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating production .env file..."
    cat > .env << EOF
FLASK_ENV=production
DASHBOARD_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
FLASK_DEBUG=False
DASHBOARD_REFRESH_INTERVAL=10
SHOW_ARABIC_TEXT=True
SHOW_HIJRI_DATE=True
EOF
fi

# Export environment variables
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Start the dashboard
echo "🕌 Starting QuranBot Dashboard in production mode..."
exec python run_dashboard.py --no-checks --env production --host 0.0.0.0 --port 5000