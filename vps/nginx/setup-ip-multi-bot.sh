#!/bin/bash
# =============================================================================
# IP-Based Multi-Bot Nginx Setup Script
# =============================================================================
# Sets up Nginx reverse proxy for multiple bot dashboards using IP address
# Usage: ./setup-ip-multi-bot.sh
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

log_info "Setting up IP-based multi-bot dashboard system..."

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
ufw allow 80/tcp > /dev/null 2>&1 || true
ufw allow 8080/tcp > /dev/null 2>&1 || true

# Create Nginx configuration for IP-based access
log_info "Creating Nginx configuration for IP-based multi-bot access..."

cat > /etc/nginx/sites-available/multi-bots-ip << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    # Accept all hostnames (IP addresses)
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # QuranBot Dashboard (Port 8080)
    location /quranbot/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Remove /quranbot from the path when forwarding
        rewrite ^/quranbot/(.*)$ /$1 break;
        
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

    # MusicBot Dashboard (Port 8081) - Future use
    location /musicbot/ {
        proxy_pass http://localhost:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        rewrite ^/musicbot/(.*)$ /$1 break;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # GameBot Dashboard (Port 8082) - Future use
    location /gamebot/ {
        proxy_pass http://localhost:8082/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        rewrite ^/gamebot/(.*)$ /$1 break;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API endpoints for all bots
    location ~ ^/([^/]+)/api/(.*)$ {
        set $bot_name $1;
        set $api_path $2;
        
        # Route to appropriate port based on bot name
        if ($bot_name = "quranbot") {
            proxy_pass http://localhost:8080/api/$api_path;
        }
        if ($bot_name = "musicbot") {
            proxy_pass http://localhost:8081/api/$api_path;
        }
        if ($bot_name = "gamebot") {
            proxy_pass http://localhost:8082/api/$api_path;
        }
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Main dashboard index page
    location = / {
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Management Dashboard</title>
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
            max-width: 1000px; 
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
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 300;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        .bots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
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
            position: relative;
        }
        .bot-card:hover { 
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            text-decoration: none;
            color: #333;
        }
        .bot-card.disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .bot-card.disabled:hover {
            transform: none;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
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
            margin-bottom: 15px;
        }
        .bot-status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            margin-top: 10px;
        }
        .status-online { background: #e8f5e8; color: #2e7d32; }
        .status-offline { background: #ffebee; color: #c62828; }
        .status-checking { background: #fff3e0; color: #f57c00; }
        .status-not-configured { background: #f5f5f5; color: #666; }
        .bot-path {
            font-size: 12px;
            color: #999;
            margin-top: 8px;
            font-family: monospace;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }
        .server-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .server-info h3 {
            color: #333;
            margin-bottom: 10px;
        }
        .server-info p {
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
        <h1>🤖 Discord Bot Dashboard</h1>
        <p class="subtitle">Centralized management for all your Discord bots</p>
        
        <div class="server-info">
            <h3>📍 Server Information</h3>
            <p>VPS Location: /opt/DiscordBots/ | Nginx Reverse Proxy | Real-time Monitoring</p>
        </div>
        
        <div class="bots-grid">
            <a href="/quranbot/" class="bot-card" id="quranbot-card">
                <div class="bot-icon">🕌</div>
                <div class="bot-name">QuranBot</div>
                <div class="bot-desc">Monitor and control your Quran audio bot with real-time statistics, user activity tracking, and system monitoring.</div>
                <div class="bot-path">/opt/DiscordBots/QuranBot</div>
                <div class="bot-status status-checking" id="quranbot-status">Checking...</div>
            </a>
            
            <div class="bot-card disabled">
                <div class="bot-icon">🎵</div>
                <div class="bot-name">MusicBot</div>
                <div class="bot-desc">Manage your music bot with playlist controls, queue management, and audio quality monitoring.</div>
                <div class="bot-path">/opt/DiscordBots/MusicBot</div>
                <div class="bot-status status-not-configured">Not Configured</div>
            </div>
            
            <div class="bot-card disabled">
                <div class="bot-icon">🎮</div>
                <div class="bot-name">GameBot</div>
                <div class="bot-desc">Control your gaming bot with user statistics, leaderboards, and game session management.</div>
                <div class="bot-path">/opt/DiscordBots/GameBot</div>
                <div class="bot-status status-not-configured">Not Configured</div>
            </div>
        </div>
        
        <div class="footer">
            <p>🔧 Powered by Nginx Reverse Proxy | 🖥️ VPS Management | 📱 Mobile Responsive</p>
            <p>Add new bots by creating folders in /opt/DiscordBots/ and configuring additional ports</p>
        </div>
    </div>
    
    <script>
        // Check QuranBot status
        function checkBotStatus() {
            fetch("/quranbot/api/status")
                .then(response => response.json())
                .then(data => {
                    const statusEl = document.getElementById("quranbot-status");
                    const cardEl = document.getElementById("quranbot-card");
                    
                    if (data.status === "running") {
                        statusEl.textContent = "Online";
                        statusEl.className = "bot-status status-online";
                        cardEl.classList.remove("disabled");
                    } else {
                        statusEl.textContent = "Offline";
                        statusEl.className = "bot-status status-offline";
                        cardEl.classList.add("disabled");
                    }
                })
                .catch(() => {
                    const statusEl = document.getElementById("quranbot-status");
                    const cardEl = document.getElementById("quranbot-card");
                    statusEl.textContent = "Offline";
                    statusEl.className = "bot-status status-offline";
                    cardEl.classList.add("disabled");
                });
        }
        
        // Check status on load and every 30 seconds
        checkBotStatus();
        setInterval(checkBotStatus, 30000);
    </script>
</body>
</html>';
        add_header Content-Type text/html;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Custom error pages
    error_page 502 503 504 /50x.html;
    location = /50x.html {
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>Bot Dashboard - Service Unavailable</title>
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
ln -sf /etc/nginx/sites-available/multi-bots-ip /etc/nginx/sites-enabled/

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

# Get server IP
SERVER_IP=$(curl -s http://ipv4.icanhazip.com 2>/dev/null || echo "YOUR_VPS_IP")

# Final summary
log_info "IP-based Multi-Bot Dashboard Setup Complete!"
echo ""
echo "🌐 Access your dashboards at:"
echo "   Main Dashboard: http://$SERVER_IP/"
echo "   QuranBot: http://$SERVER_IP/quranbot/"
echo "   Future bots: http://$SERVER_IP/musicbot/, http://$SERVER_IP/gamebot/"
echo ""
echo "📁 Bot Directory Structure:"
echo "   /opt/DiscordBots/QuranBot/"
echo "   /opt/DiscordBots/MusicBot/ (future)"
echo "   /opt/DiscordBots/GameBot/ (future)"
echo ""
echo "🔧 Management:"
echo "   Nginx config: /etc/nginx/sites-available/multi-bots-ip"
echo "   Logs: /var/log/nginx/multi_bots_*.log"
echo "   Health check: http://$SERVER_IP/health"
echo ""
echo "✅ Setup completed successfully!"

log_success "Multi-bot dashboard system is ready!" 