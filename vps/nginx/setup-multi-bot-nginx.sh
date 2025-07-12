#!/bin/bash
# =============================================================================
# Multi-Bot Nginx Setup Script
# =============================================================================
# Sets up Nginx reverse proxy for multiple bot dashboards
# Usage: ./setup-multi-bot-nginx.sh yourdomain.com
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
    echo "This will create: bots.example.com"
    exit 1
fi

DOMAIN="$1"
SUBDOMAIN="bots.$DOMAIN"

log_info "Setting up Nginx reverse proxy for multiple bot dashboards"
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

cat > /etc/nginx/sites-available/multi-bots << EOF
server {
    listen 80;
    server_name $SUBDOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # QuranBot Dashboard (Port 8080)
    location /quranbot/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Remove /quranbot from the path when forwarding
        rewrite ^/quranbot/(.*)$ /\$1 break;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # MusicBot Dashboard (Port 8081) - Example
    location /musicbot/ {
        proxy_pass http://localhost:8081/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        rewrite ^/musicbot/(.*)$ /\$1 break;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # GameBot Dashboard (Port 8082) - Example
    location /gamebot/ {
        proxy_pass http://localhost:8082/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        rewrite ^/gamebot/(.*)$ /\$1 break;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API endpoints for all bots
    location ~ ^/([^/]+)/api/(.*)$ {
        set \$bot_name \$1;
        set \$api_path \$2;
        
        # Route to appropriate port based on bot name
        if (\$bot_name = "quranbot") {
            proxy_pass http://localhost:8080/api/\$api_path;
        }
        if (\$bot_name = "musicbot") {
            proxy_pass http://localhost:8081/api/\$api_path;
        }
        if (\$bot_name = "gamebot") {
            proxy_pass http://localhost:8082/api/\$api_path;
        }
        
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Main dashboard index
    location = / {
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>Bot Dashboards</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container { 
            max-width: 900px; 
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        h1 { 
            color: #333;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            font-weight: 300;
        }
        .bots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .bot-card { 
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-decoration: none;
            color: #333;
            transition: all 0.3s ease;
            border: 1px solid #e0e0e0;
        }
        .bot-card:hover { 
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            text-decoration: none;
            color: #333;
        }
        .bot-icon { 
            font-size: 48px;
            margin-bottom: 15px;
            display: block;
        }
        .bot-name { 
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .bot-desc { 
            font-size: 16px;
            color: #666;
            line-height: 1.5;
        }
        .bot-status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            margin-top: 10px;
        }
        .status-online { background: #e8f5e8; color: #2e7d32; }
        .status-offline { background: #ffebee; color: #c62828; }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }
        @media (max-width: 768px) {
            .container { padding: 20px; }
            h1 { font-size: 2em; }
            .bots-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Bot Dashboards</h1>
        <div class="bots-grid">
            <a href="/quranbot/" class="bot-card">
                <div class="bot-icon">🕌</div>
                <div class="bot-name">QuranBot</div>
                <div class="bot-desc">Monitor and control your Quran audio bot with real-time statistics and system monitoring.</div>
                <div class="bot-status status-online" id="quranbot-status">Checking...</div>
            </a>
            <a href="/musicbot/" class="bot-card" style="opacity: 0.6;">
                <div class="bot-icon">🎵</div>
                <div class="bot-name">MusicBot</div>
                <div class="bot-desc">Manage your music bot with playlist controls and audio quality monitoring.</div>
                <div class="bot-status status-offline">Not Configured</div>
            </a>
            <a href="/gamebot/" class="bot-card" style="opacity: 0.6;">
                <div class="bot-icon">🎮</div>
                <div class="bot-name">GameBot</div>
                <div class="bot-desc">Control your gaming bot with user statistics and game session management.</div>
                <div class="bot-status status-offline">Not Configured</div>
            </a>
        </div>
        <div class="footer">
            <p>🔧 Powered by Nginx Reverse Proxy | 🔒 Secure HTTPS | 📱 Mobile Responsive</p>
        </div>
    </div>
    
    <script>
        // Check QuranBot status
        fetch("/quranbot/api/status")
            .then(response => response.json())
            .then(data => {
                const statusEl = document.getElementById("quranbot-status");
                if (data.status === "running") {
                    statusEl.textContent = "Online";
                    statusEl.className = "bot-status status-online";
                } else {
                    statusEl.textContent = "Offline";
                    statusEl.className = "bot-status status-offline";
                }
            })
            .catch(() => {
                const statusEl = document.getElementById("quranbot-status");
                statusEl.textContent = "Offline";
                statusEl.className = "bot-status status-offline";
            });
    </script>
</body>
</html>';
        add_header Content-Type text/html;
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
    <title>Bot Dashboards - Service Unavailable</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #e74c3c; }
        p { color: #666; line-height: 1.6; }
        .emoji { font-size: 48px; margin: 20px 0; }
        .back-link { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🔧</div>
        <h1>Service Temporarily Unavailable</h1>
        <p>The requested bot dashboard is currently offline for maintenance or the service is starting up.</p>
        <p>Please try again in a few moments.</p>
        <a href="/" class="back-link">← Back to Dashboard List</a>
    </div>
</body>
</html>';
        add_header Content-Type text/html;
    }

    # Logging
    access_log /var/log/nginx/multi_bots_access.log;
    error_log /var/log/nginx/multi_bots_error.log;
}
EOF

# Enable the site
log_info "Enabling Nginx site..."
ln -sf /etc/nginx/sites-available/multi-bots /etc/nginx/sites-enabled/

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

# Check bot services
log_info "Checking bot services..."
SERVICES_RUNNING=0

if curl -s http://localhost:8080/api/status > /dev/null 2>&1; then
    log_success "QuranBot dashboard is running on port 8080"
    SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
else
    log_warning "QuranBot dashboard is not running on port 8080"
fi

if curl -s http://localhost:8081 > /dev/null 2>&1; then
    log_success "MusicBot dashboard is running on port 8081"
    SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
else
    log_info "MusicBot dashboard is not configured (port 8081)"
fi

if curl -s http://localhost:8082 > /dev/null 2>&1; then
    log_success "GameBot dashboard is running on port 8082"
    SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
else
    log_info "GameBot dashboard is not configured (port 8082)"
fi

# Install Certbot for SSL
log_info "Installing Certbot for SSL certificates..."
if ! command -v certbot &> /dev/null; then
    apt install certbot python3-certbot-nginx -y
    log_success "Certbot installed"
else
    log_info "Certbot is already installed"
fi

# Create management script
log_info "Creating management script..."
cat > /usr/local/bin/manage-bot-dashboards << 'EOF'
#!/bin/bash
# Bot Dashboard Management Script

case "$1" in
    "status")
        echo "=== Bot Dashboard Status ==="
        echo "QuranBot (8080):"
        curl -s http://localhost:8080/api/status | jq -r '.status' 2>/dev/null || echo "Offline"
        echo "MusicBot (8081):"
        curl -s http://localhost:8081/api/status | jq -r '.status' 2>/dev/null || echo "Not configured"
        echo "GameBot (8082):"
        curl -s http://localhost:8082/api/status | jq -r '.status' 2>/dev/null || echo "Not configured"
        ;;
    "logs")
        echo "=== Recent Access Logs ==="
        tail -20 /var/log/nginx/multi_bots_access.log
        ;;
    "errors")
        echo "=== Recent Error Logs ==="
        tail -20 /var/log/nginx/multi_bots_error.log
        ;;
    *)
        echo "Usage: $0 {status|logs|errors}"
        ;;
esac
EOF

chmod +x /usr/local/bin/manage-bot-dashboards

# Final instructions
echo
log_success "✅ Multi-bot Nginx reverse proxy setup completed!"
echo
echo "📝 Next steps:"
echo "1. Point your domain '$SUBDOMAIN' to this VPS IP address"
echo "2. Wait for DNS propagation (usually 5-60 minutes)"
echo "3. Test the domain: curl -H 'Host: $SUBDOMAIN' http://localhost"
echo "4. Get SSL certificate: sudo certbot --nginx -d $SUBDOMAIN"
echo "5. Access your dashboards at: https://$SUBDOMAIN"
echo
echo "🤖 Bot Dashboard URLs:"
echo "  - Main Dashboard: https://$SUBDOMAIN"
echo "  - QuranBot: https://$SUBDOMAIN/quranbot/"
echo "  - MusicBot: https://$SUBDOMAIN/musicbot/ (configure port 8081)"
echo "  - GameBot: https://$SUBDOMAIN/gamebot/ (configure port 8082)"
echo
echo "🔧 Management commands:"
echo "  - Check all bots: manage-bot-dashboards status"
echo "  - View access logs: manage-bot-dashboards logs"
echo "  - View error logs: manage-bot-dashboards errors"
echo "  - Check Nginx: systemctl status nginx"
echo
echo "📊 Currently running: $SERVICES_RUNNING/3 bot services"
echo
log_success "Setup complete! 🎉" 