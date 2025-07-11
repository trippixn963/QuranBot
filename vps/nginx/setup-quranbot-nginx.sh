#!/bin/bash
# =============================================================================
# QuranBot Nginx Setup Script
# =============================================================================
# Automatically sets up Nginx reverse proxy for QuranBot dashboard
# Usage: ./setup-quranbot-nginx.sh yourdomain.com
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check if domain is provided
if [ -z "$1" ]; then
    log_error "Domain name is required!"
    echo "Usage: $0 yourdomain.com"
    echo "Example: $0 example.com"
    echo "This will create: quranbot.example.com"
    exit 1
fi

DOMAIN="$1"
SUBDOMAIN="quranbot.$DOMAIN"

log_info "Setting up Nginx reverse proxy for QuranBot dashboard"
log_info "Domain: $SUBDOMAIN"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

# Install Nginx if not installed
if ! command -v nginx &> /dev/null; then
    log_info "Installing Nginx..."
    apt update
    apt install nginx -y
    systemctl start nginx
    systemctl enable nginx
    log_success "Nginx installed and started"
else
    log_info "Nginx is already installed"
fi

# Configure firewall
log_info "Configuring firewall..."
ufw allow 'Nginx Full' > /dev/null 2>&1 || true
ufw allow 'Nginx HTTP' > /dev/null 2>&1 || true
ufw allow 'Nginx HTTPS' > /dev/null 2>&1 || true

# Create Nginx configuration
log_info "Creating Nginx configuration for $SUBDOMAIN..."

cat > /etc/nginx/sites-available/quranbot << EOF
server {
    listen 80;
    server_name $SUBDOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Proxy configuration
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # API endpoints (for direct API access)
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # API-specific settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Static files (if any)
    location /static/ {
        proxy_pass http://localhost:8080/static/;
        proxy_set_header Host \$host;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }

    # Custom error pages
    error_page 502 503 504 /50x.html;
    location = /50x.html {
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>QuranBot Dashboard - Temporarily Unavailable</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #e74c3c; }
        p { color: #666; line-height: 1.6; }
        .emoji { font-size: 48px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🔧</div>
        <h1>Dashboard Temporarily Unavailable</h1>
        <p>The QuranBot dashboard is currently offline for maintenance or the bot service is starting up.</p>
        <p>Please try again in a few moments.</p>
        <p><small>If this problem persists, please contact the administrator.</small></p>
    </div>
</body>
</html>';
        add_header Content-Type text/html;
    }

    # Logging
    access_log /var/log/nginx/quranbot_access.log;
    error_log /var/log/nginx/quranbot_error.log;
}
EOF

# Enable the site
log_info "Enabling Nginx site..."
ln -sf /etc/nginx/sites-available/quranbot /etc/nginx/sites-enabled/

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
    log_info "Removed default Nginx site"
fi

# Test Nginx configuration
log_info "Testing Nginx configuration..."
if nginx -t; then
    log_success "Nginx configuration is valid"
else
    log_error "Nginx configuration test failed!"
    exit 1
fi

# Reload Nginx
log_info "Reloading Nginx..."
systemctl reload nginx

# Check if QuranBot dashboard is running
log_info "Checking if QuranBot dashboard is running..."
if curl -s http://localhost:8080/api/status > /dev/null 2>&1; then
    log_success "QuranBot dashboard is running on port 8080"
else
    log_warning "QuranBot dashboard is not running on port 8080"
    log_warning "Make sure to start the dashboard service:"
    log_warning "  systemctl start quranbot-dashboard"
fi

# Install Certbot for SSL
log_info "Installing Certbot for SSL certificates..."
if ! command -v certbot &> /dev/null; then
    apt install certbot python3-certbot-nginx -y
    log_success "Certbot installed"
else
    log_info "Certbot is already installed"
fi

# Final instructions
echo
log_success "✅ Nginx reverse proxy setup completed!"
echo
echo "📝 Next steps:"
echo "1. Point your domain '$SUBDOMAIN' to this VPS IP address"
echo "2. Wait for DNS propagation (usually 5-60 minutes)"
echo "3. Test the domain: curl -H 'Host: $SUBDOMAIN' http://localhost"
echo "4. Get SSL certificate: sudo certbot --nginx -d $SUBDOMAIN"
echo "5. Access your dashboard at: https://$SUBDOMAIN"
echo
echo "🔧 Management commands:"
echo "  - Check Nginx status: systemctl status nginx"
echo "  - Check dashboard: systemctl status quranbot-dashboard"
echo "  - View access logs: tail -f /var/log/nginx/quranbot_access.log"
echo "  - View error logs: tail -f /var/log/nginx/quranbot_error.log"
echo
echo "🌐 Your QuranBot dashboard will be available at:"
echo "   HTTP:  http://$SUBDOMAIN"
echo "   HTTPS: https://$SUBDOMAIN (after SSL setup)"
echo
log_success "Setup complete! 🎉" 