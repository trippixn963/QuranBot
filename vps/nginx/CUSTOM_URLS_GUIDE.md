# 🌐 Custom URLs for Bot Dashboards - Complete Guide

## Overview

Transform your bot dashboards from `http://vps-ip:8080` to professional custom URLs like `https://quranbot.yourdomain.com`. This guide covers all setup options for single and multiple bot dashboards.

## 🎯 **URL Options Available**

### **Option 1: Single Bot Subdomain**
```
https://quranbot.yourdomain.com  →  QuranBot Dashboard (Port 8080)
https://musicbot.yourdomain.com  →  MusicBot Dashboard (Port 8081)
https://gamebot.yourdomain.com   →  GameBot Dashboard (Port 8082)
```

### **Option 2: Multi-Bot Path-Based**
```
https://bots.yourdomain.com/              →  Main Dashboard Index
https://bots.yourdomain.com/quranbot/     →  QuranBot Dashboard
https://bots.yourdomain.com/musicbot/     →  MusicBot Dashboard
https://bots.yourdomain.com/gamebot/      →  GameBot Dashboard
```

### **Option 3: Combined Approach**
```
https://dashboard.yourdomain.com          →  Main Dashboard Hub
https://dashboard.yourdomain.com/quranbot/
https://dashboard.yourdomain.com/musicbot/
https://quranbot.yourdomain.com           →  Direct QuranBot access
```

## 🚀 **Quick Setup**

### **Single Bot Setup (Recommended for QuranBot)**
```bash
# On your VPS, run as root:
cd /opt/QuranBot
./vps/nginx/setup-quranbot-nginx.sh yourdomain.com

# This creates: quranbot.yourdomain.com
```

### **Multi-Bot Setup (For Multiple Bots)**
```bash
# On your VPS, run as root:
cd /opt/QuranBot
./vps/nginx/setup-multi-bot-nginx.sh yourdomain.com

# This creates: bots.yourdomain.com with /quranbot/, /musicbot/, etc.
```

## 📋 **Step-by-Step Setup**

### **Prerequisites**
1. **Domain Name**: Own a domain (e.g., `yourdomain.com`)
2. **DNS Access**: Ability to create subdomains
3. **VPS Access**: Root access to your VPS
4. **Running Dashboard**: QuranBot dashboard service running

### **Step 1: Choose Your Setup**

**For Single Bot (QuranBot only):**
- Creates: `quranbot.yourdomain.com`
- Best for: Dedicated QuranBot deployment
- SSL: Automatic with Let's Encrypt

**For Multiple Bots:**
- Creates: `bots.yourdomain.com` with subpaths
- Best for: Managing multiple bot dashboards
- Expandable: Easy to add more bots

### **Step 2: Run Setup Script**

**Single Bot Setup:**
```bash
# SSH into your VPS
ssh root@your-vps-ip

# Navigate to QuranBot directory
cd /opt/QuranBot

# Run setup script
./vps/nginx/setup-quranbot-nginx.sh yourdomain.com
```

**Multi-Bot Setup:**
```bash
# SSH into your VPS
ssh root@your-vps-ip

# Navigate to QuranBot directory
cd /opt/QuranBot

# Run setup script
./vps/nginx/setup-multi-bot-nginx.sh yourdomain.com
```

### **Step 3: Configure DNS**

**For Single Bot:**
```
Create A record: quranbot.yourdomain.com → your-vps-ip
```

**For Multi-Bot:**
```
Create A record: bots.yourdomain.com → your-vps-ip
```

**DNS Configuration Examples:**

*Cloudflare:*
```
Type: A
Name: quranbot
Content: 159.89.90.90
Proxy: Optional (Orange cloud)
```

*Namecheap:*
```
Type: A Record
Host: quranbot
Value: 159.89.90.90
TTL: Automatic
```

*Google Domains:*
```
Type: A
Name: quranbot
Data: 159.89.90.90
```

### **Step 4: Test DNS Propagation**
```bash
# Check DNS propagation
nslookup quranbot.yourdomain.com

# Test HTTP connection
curl -H "Host: quranbot.yourdomain.com" http://your-vps-ip
```

### **Step 5: Setup SSL Certificate**
```bash
# Install SSL certificate (automatic with Let's Encrypt)
sudo certbot --nginx -d quranbot.yourdomain.com

# For multi-bot setup
sudo certbot --nginx -d bots.yourdomain.com
```

### **Step 6: Verify Setup**
```bash
# Test HTTPS connection
curl https://quranbot.yourdomain.com/api/status

# Check Nginx status
sudo systemctl status nginx

# View access logs
sudo tail -f /var/log/nginx/quranbot_access.log
```

## 🔧 **Advanced Configuration**

### **Port Management for Multiple Bots**
```bash
# QuranBot Dashboard: Port 8080 (default)
# MusicBot Dashboard: Port 8081
# GameBot Dashboard: Port 8082
# CustomBot Dashboard: Port 8083

# Update systemd service for different ports
sudo systemctl edit quranbot-dashboard
```

Add environment variable:
```ini
[Service]
Environment="DASHBOARD_PORT=8080"
```

### **Custom Error Pages**
The setup includes custom error pages that show when bots are offline:
- Professional design matching your brand
- Helpful error messages
- Automatic retry suggestions

### **Security Features**
- **Security Headers**: XSS protection, content type sniffing prevention
- **Rate Limiting**: Prevents abuse (optional)
- **IP Restrictions**: Limit access to specific IPs (optional)
- **Basic Authentication**: Password protection (optional)

### **SSL/HTTPS Features**
- **Automatic Certificates**: Let's Encrypt integration
- **Auto-Renewal**: Certificates renew automatically
- **HSTS**: HTTP Strict Transport Security
- **Perfect Forward Secrecy**: Enhanced security

## 🎨 **Customization Options**

### **Custom Branding**
```bash
# Edit the main dashboard page
sudo nano /etc/nginx/sites-available/multi-bots

# Customize colors, logos, descriptions
# Add your own CSS styling
# Include custom JavaScript
```

### **Additional Bots**
To add more bots to multi-bot setup:

1. **Add location block** to Nginx config:
```nginx
location /custombot/ {
    proxy_pass http://localhost:8083/;
    # ... same headers as other bots
    rewrite ^/custombot/(.*)$ /$1 break;
}
```

2. **Update main dashboard** HTML to include new bot
3. **Reload Nginx**: `sudo systemctl reload nginx`

### **Monitoring Integration**
```bash
# Add monitoring endpoints
location /monitoring/ {
    proxy_pass http://localhost:9090/;  # Prometheus
    # ... proxy headers
}

location /grafana/ {
    proxy_pass http://localhost:3000/;  # Grafana
    # ... proxy headers
}
```

## 📊 **Management Commands**

### **Single Bot Management**
```bash
# Check Nginx status
sudo systemctl status nginx

# View access logs
sudo tail -f /var/log/nginx/quranbot_access.log

# View error logs
sudo tail -f /var/log/nginx/quranbot_error.log

# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx
```

### **Multi-Bot Management**
```bash
# Check all bot statuses
manage-bot-dashboards status

# View access logs
manage-bot-dashboards logs

# View error logs
manage-bot-dashboards errors

# Check individual bot APIs
curl https://bots.yourdomain.com/quranbot/api/status
curl https://bots.yourdomain.com/musicbot/api/status
```

## 🔍 **Troubleshooting**

### **Common Issues**

**DNS Not Propagating:**
```bash
# Check DNS
dig quranbot.yourdomain.com

# Test with different DNS servers
nslookup quranbot.yourdomain.com 8.8.8.8
```

**SSL Certificate Issues:**
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --dry-run

# Check Nginx SSL config
sudo nginx -t
```

**Dashboard Not Loading:**
```bash
# Check if dashboard service is running
sudo systemctl status quranbot-dashboard

# Check if port is open
sudo netstat -tlnp | grep :8080

# Test direct connection
curl http://localhost:8080/api/status
```

**Nginx Configuration Errors:**
```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Validate specific site
sudo nginx -t -c /etc/nginx/sites-available/quranbot
```

### **Performance Optimization**
```bash
# Enable gzip compression
# Add to Nginx config:
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript;

# Enable caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🌟 **Benefits of Custom URLs**

### **Professional Appearance**
- **No Port Numbers**: Clean URLs without `:8080`
- **Branded Domains**: Use your own domain name
- **SSL/HTTPS**: Secure, trusted connections
- **Custom Certificates**: Professional SSL certificates

### **Scalability**
- **Multiple Bots**: Easy to add more bot dashboards
- **Load Balancing**: Distribute traffic across instances
- **Subdomain Organization**: Logical separation of services
- **Easy Management**: Centralized configuration

### **Security**
- **Reverse Proxy**: Additional security layer
- **SSL Termination**: Encrypted connections
- **Access Control**: IP restrictions and authentication
- **Rate Limiting**: Prevent abuse and attacks

### **User Experience**
- **Memorable URLs**: Easy to remember and share
- **Mobile Friendly**: Works great on all devices
- **Fast Loading**: Optimized proxy configuration
- **Error Handling**: Professional error pages

## 📱 **Mobile Access**

Your custom URLs work perfectly on mobile devices:
- **Responsive Design**: Adapts to phone/tablet screens
- **Touch Friendly**: Optimized for touch interactions
- **Fast Loading**: Optimized for mobile networks
- **Offline Indicators**: Clear status when bot is down

## 🔄 **Backup and Recovery**

### **Nginx Configuration Backup**
```bash
# Backup Nginx configuration
sudo cp /etc/nginx/sites-available/quranbot /opt/QuranBot/backup/

# Backup SSL certificates
sudo cp -r /etc/letsencrypt /opt/QuranBot/backup/

# Create full backup
sudo tar -czf nginx-backup-$(date +%Y%m%d).tar.gz /etc/nginx /etc/letsencrypt
```

### **Recovery Process**
```bash
# Restore Nginx configuration
sudo cp /opt/QuranBot/backup/quranbot /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/quranbot /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## 📋 **Summary**

### **What You Get:**
✅ **Professional URLs**: `https://quranbot.yourdomain.com`  
✅ **SSL/HTTPS**: Automatic secure certificates  
✅ **Multiple Bot Support**: Scale to many dashboards  
✅ **Custom Branding**: Your domain, your style  
✅ **Mobile Optimized**: Works great on all devices  
✅ **Enterprise Security**: Professional security features  
✅ **Easy Management**: Simple commands and monitoring  
✅ **Scalable Architecture**: Add more bots easily  

### **Perfect For:**
- **Professional Deployments**: Business or community use
- **Multiple Bot Management**: Run several bots on one VPS
- **Branded Experience**: Custom domain and styling
- **Mobile Access**: Monitor from anywhere
- **Team Collaboration**: Share professional URLs
- **Long-term Scaling**: Grow your bot infrastructure

Transform your bot dashboards from basic IP:port access to professional, branded, secure URLs that work beautifully on any device! 