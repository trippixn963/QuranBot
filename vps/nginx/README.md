# 🌐 Nginx Reverse Proxy Setup for Multiple Bot Dashboards

## Overview

Set up dedicated URLs for your bot dashboards using Nginx reverse proxy. This allows you to:

- **Custom Domains**: `quranbot.yourdomain.com`, `musicbot.yourdomain.com`
- **Multiple Bots**: Run multiple bot dashboards on same VPS
- **SSL/HTTPS**: Secure connections with Let's Encrypt
- **Professional URLs**: No more `:8080` port numbers
- **Load Balancing**: Distribute traffic across multiple instances

## Quick Setup

### 1. Install Nginx
```bash
# Update system
sudo apt update

# Install Nginx
sudo apt install nginx -y

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

### 2. Configure Firewall
```bash
# Allow Nginx through firewall
sudo ufw allow 'Nginx Full'
sudo ufw allow 'Nginx HTTP'
sudo ufw allow 'Nginx HTTPS'

# Check firewall status
sudo ufw status
```

### 3. Basic Configuration Test
```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check if working
curl http://your-vps-ip
```

## Dashboard Configuration

### Single Bot Dashboard
```nginx
# /etc/nginx/sites-available/quranbot
server {
    listen 80;
    server_name quranbot.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for real-time updates)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Multiple Bot Dashboards
```nginx
# /etc/nginx/sites-available/multi-bots
server {
    listen 80;
    server_name bots.yourdomain.com;

    # QuranBot Dashboard
    location /quranbot/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Remove /quranbot from the path when forwarding
        rewrite ^/quranbot/(.*)$ /$1 break;
    }

    # MusicBot Dashboard (example)
    location /musicbot/ {
        proxy_pass http://localhost:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        rewrite ^/musicbot/(.*)$ /$1 break;
    }

    # GameBot Dashboard (example)
    location /gamebot/ {
        proxy_pass http://localhost:8082/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        rewrite ^/gamebot/(.*)$ /$1 break;
    }

    # Main dashboard index
    location = / {
        return 200 '
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bot Dashboards</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .bot-link { display: block; padding: 20px; margin: 10px 0; 
                           background: #f0f0f0; text-decoration: none; color: #333; 
                           border-radius: 5px; }
                .bot-link:hover { background: #e0e0e0; }
            </style>
        </head>
        <body>
            <h1>Bot Dashboards</h1>
            <a href="/quranbot/" class="bot-link">🕌 QuranBot Dashboard</a>
            <a href="/musicbot/" class="bot-link">🎵 MusicBot Dashboard</a>
            <a href="/gamebot/" class="bot-link">🎮 GameBot Dashboard</a>
        </body>
        </html>';
        add_header Content-Type text/html;
    }
}
```

## SSL/HTTPS Setup

### Install Certbot
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d quranbot.yourdomain.com

# Or for multiple domains
sudo certbot --nginx -d bots.yourdomain.com
```

### Auto-renewal
```bash
# Test auto-renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

## Complete Setup Scripts

### QuranBot Nginx Configuration
```bash
#!/bin/bash
# setup-quranbot-nginx.sh

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/quranbot > /dev/null <<EOF
server {
    listen 80;
    server_name quranbot.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/quranbot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

echo "✅ QuranBot Nginx configuration created!"
echo "📝 Next steps:"
echo "1. Point your domain to this VPS IP"
echo "2. Run: sudo certbot --nginx -d quranbot.yourdomain.com"
echo "3. Access your dashboard at: https://quranbot.yourdomain.com"
```

### Multi-Bot Nginx Configuration
```bash
#!/bin/bash
# setup-multi-bot-nginx.sh

# Create multi-bot configuration
sudo tee /etc/nginx/sites-available/multi-bots > /dev/null <<'EOF'
server {
    listen 80;
    server_name bots.yourdomain.com;

    # QuranBot Dashboard
    location /quranbot/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        rewrite ^/quranbot/(.*)$ /$1 break;
    }

    # Add more bots here...
    # location /musicbot/ {
    #     proxy_pass http://localhost:8081/;
    #     # ... same headers ...
    #     rewrite ^/musicbot/(.*)$ /$1 break;
    # }

    # Main dashboard index
    location = / {
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>Bot Dashboards</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .bot-link { display: block; padding: 20px; margin: 15px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   text-decoration: none; color: white; border-radius: 8px; transition: transform 0.2s; }
        .bot-link:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .bot-name { font-size: 18px; font-weight: bold; }
        .bot-desc { font-size: 14px; opacity: 0.9; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Bot Dashboards</h1>
        <a href="/quranbot/" class="bot-link">
            <div class="bot-name">🕌 QuranBot Dashboard</div>
            <div class="bot-desc">Monitor and control your Quran audio bot</div>
        </a>
        <!-- Add more bots here -->
    </div>
</body>
</html>';
        add_header Content-Type text/html;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/multi-bots /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t && sudo systemctl reload nginx

echo "✅ Multi-bot Nginx configuration created!"
echo "📝 Access your dashboards at:"
echo "   - Main: https://bots.yourdomain.com"
echo "   - QuranBot: https://bots.yourdomain.com/quranbot/"
```

## Port Management

### Dashboard Port Configuration
```bash
# QuranBot Dashboard: Port 8080 (current)
# MusicBot Dashboard: Port 8081
# GameBot Dashboard: Port 8082
# etc...

# Update your dashboard services to use different ports
# In your systemd service files, you can set environment variables:
Environment="DASHBOARD_PORT=8080"
```

### Dashboard Port Environment Variable
Update your dashboard to use configurable port:

```python
# In vps/web_dashboard/app.py
import os

if __name__ == '__main__':
    port = int(os.environ.get('DASHBOARD_PORT', 8080))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
```

## Domain Setup Examples

### Option 1: Subdomains
```
quranbot.yourdomain.com  → Port 8080
musicbot.yourdomain.com  → Port 8081
gamebot.yourdomain.com   → Port 8082
```

### Option 2: Path-based
```
bots.yourdomain.com/quranbot/  → Port 8080
bots.yourdomain.com/musicbot/  → Port 8081
bots.yourdomain.com/gamebot/   → Port 8082
```

### Option 3: Combined
```
dashboard.yourdomain.com       → Main dashboard index
dashboard.yourdomain.com/quranbot/
dashboard.yourdomain.com/musicbot/
```

## Security Enhancements

### Basic Authentication
```nginx
# Add to your server block
auth_basic "Bot Dashboard";
auth_basic_user_file /etc/nginx/.htpasswd;

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### IP Restrictions
```nginx
# Allow only specific IPs
location / {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    
    proxy_pass http://localhost:8080;
    # ... other proxy settings
}
```

### Rate Limiting
```nginx
# Add to http block in /etc/nginx/nginx.conf
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=10r/m;

# Add to location block
limit_req zone=dashboard burst=5 nodelay;
```

## Monitoring and Logs

### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log

# Dashboard-specific logs
sudo tail -f /var/log/nginx/quranbot_access.log
```

### Custom Logging
```nginx
# Add to server block
access_log /var/log/nginx/quranbot_access.log;
error_log /var/log/nginx/quranbot_error.log;
```

## Troubleshooting

### Common Issues
```bash
# Check Nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# Check if ports are open
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8080

# Check firewall
sudo ufw status

# Test proxy connection
curl -H "Host: quranbot.yourdomain.com" http://localhost
```

### Restart Services
```bash
# Restart Nginx
sudo systemctl restart nginx

# Restart dashboard
sudo systemctl restart quranbot-dashboard

# Check both services
sudo systemctl status nginx quranbot-dashboard
```

## Benefits

✅ **Professional URLs**: No more port numbers  
✅ **SSL/HTTPS**: Secure connections  
✅ **Multiple Bots**: Scale to many dashboards  
✅ **Load Balancing**: Distribute traffic  
✅ **Security**: Authentication and IP restrictions  
✅ **Monitoring**: Detailed access logs  
✅ **SEO Friendly**: Custom domains  
✅ **Mobile Friendly**: Works great on all devices  

This setup gives you enterprise-grade dashboard hosting with professional URLs! 