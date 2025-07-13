#!/bin/bash
# =============================================================================
# QuranBot Professional Web Dashboard - Deployment Script
# =============================================================================
# This script deploys the new web dashboard to the VPS
# =============================================================================

set -e  # Exit on any error

# Configuration
VPS_HOST="root@159.89.90.90"
VPS_PATH="/opt/QuranBot"
LOCAL_WEB_DIR="$(pwd)"
SERVICE_NAME="quranbot-dashboard"
VENV_PATH="$VPS_PATH/web/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the web directory
if [ ! -f "app.py" ]; then
    log_error "Please run this script from the web/ directory"
    exit 1
fi

log_info "🕌 Starting QuranBot Dashboard Deployment..."

# Step 1: Test local Flask app
log_info "Testing local Flask application..."
python3 -c "
import sys
sys.path.append('.')
try:
    from app import app
    print('✅ Flask app imports successfully')
except Exception as e:
    print(f'❌ Flask app import failed: {e}')
    sys.exit(1)
"

# Step 2: Copy files to VPS
log_info "📁 Copying web dashboard to VPS..."
ssh $VPS_HOST "mkdir -p $VPS_PATH/web"
rsync -avz --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' --exclude='venv' \
    ./ $VPS_HOST:$VPS_PATH/web/

log_success "Files copied to VPS"

# Step 3: Create virtual environment and install dependencies on VPS
log_info "📦 Setting up virtual environment and installing dependencies on VPS..."
ssh $VPS_HOST "
    cd $VPS_PATH/web
    
    # Remove existing venv if it exists
    rm -rf venv
    
    # Create new virtual environment
    python3 -m venv venv
    
    # Activate venv and install dependencies
    source venv/bin/activate
    pip install flask pytz
    echo '✅ Virtual environment created and dependencies installed'
"

# Step 4: Test Flask app on VPS
log_info "🧪 Testing Flask app on VPS..."
ssh $VPS_HOST "
    cd $VPS_PATH/web
    source venv/bin/activate
    python3 -c 'from app import app; print(\"✅ Flask app works on VPS\")'
"

# Step 5: Create systemd service
log_info "⚙️ Creating systemd service..."
ssh $VPS_HOST "
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=QuranBot Professional Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$VPS_PATH/web
ExecStart=$VPS_PATH/web/venv/bin/python3 app.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=$VPS_PATH

[Install]
WantedBy=multi-user.target
EOF
"

# Step 6: Enable and start service
log_info "🚀 Starting dashboard service..."
ssh $VPS_HOST "
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME.service
    systemctl restart $SERVICE_NAME.service
    sleep 3
    systemctl status $SERVICE_NAME.service --no-pager
"

# Step 7: Test web access
log_info "🌐 Testing web access..."
sleep 5
if curl -s -o /dev/null -w "%{http_code}" http://159.89.90.90:8080 | grep -q "200"; then
    log_success "Dashboard is accessible at http://159.89.90.90:8080"
else
    log_warning "Dashboard might not be fully ready yet. Please check manually."
fi

# Step 8: Create management aliases
log_info "🔧 Creating management aliases..."
ssh $VPS_HOST "
cat >> ~/.bashrc << 'EOF'

# QuranBot Dashboard Management
alias qb-dashboard-status='systemctl status quranbot-dashboard.service'
alias qb-dashboard-restart='systemctl restart quranbot-dashboard.service'
alias qb-dashboard-stop='systemctl stop quranbot-dashboard.service'
alias qb-dashboard-start='systemctl start quranbot-dashboard.service'
alias qb-dashboard-logs='journalctl -u quranbot-dashboard.service -f'
alias qb-dashboard-update='cd /opt/QuranBot && git pull && systemctl restart quranbot-dashboard.service'
alias qb-dashboard-shell='cd /opt/QuranBot/web && source venv/bin/activate'
EOF

source ~/.bashrc 2>/dev/null || true
"

# Step 9: Display final information
log_success "🎉 Deployment completed successfully!"
echo ""
echo "📊 Dashboard Information:"
echo "   URL: http://159.89.90.90:8080"
echo "   Service: $SERVICE_NAME.service"
echo "   Path: $VPS_PATH/web"
echo "   Virtual Environment: $VENV_PATH"
echo ""
echo "🛠️ Management Commands:"
echo "   Status:  ssh $VPS_HOST 'qb-dashboard-status'"
echo "   Restart: ssh $VPS_HOST 'qb-dashboard-restart'"
echo "   Logs:    ssh $VPS_HOST 'qb-dashboard-logs'"
echo "   Update:  ssh $VPS_HOST 'qb-dashboard-update'"
echo "   Shell:   ssh $VPS_HOST 'qb-dashboard-shell'"
echo ""
echo "🔧 Manual Commands:"
echo "   systemctl status $SERVICE_NAME.service"
echo "   systemctl restart $SERVICE_NAME.service"
echo "   journalctl -u $SERVICE_NAME.service -f"
echo "   cd $VPS_PATH/web && source venv/bin/activate"
echo ""
echo "🕌 May Allah bless this work and make it beneficial for the Muslim community."
echo ""
echo "🌟 Features:"
echo "   ✅ Real-time bot monitoring"
echo "   ✅ Interactive bot controls"
echo "   ✅ System resource monitoring"
echo "   ✅ Audio controls and status"
echo "   ✅ Discord API health monitoring"
echo "   ✅ Advanced log viewing"
echo "   ✅ Professional responsive design"
echo "   ✅ Islamic-inspired styling"
echo "   ✅ 24/7 VPS service with auto-restart"
echo ""
echo "🔄 Service Status:"
ssh $VPS_HOST "systemctl is-active $SERVICE_NAME.service && echo '✅ Service is running' || echo '❌ Service is not running'"
echo ""
log_info "Visit http://159.89.90.90:8080 to access your new dashboard!" 