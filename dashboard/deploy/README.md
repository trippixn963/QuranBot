# 🚀 Dashboard Deployment Guide

This directory contains all files needed to deploy the QuranBot dashboard as a 24/7 service.

## 📂 Files

- `quranbot-dashboard.service` - Systemd service file for 24/7 operation
- `start_dashboard.sh` - Startup script that handles environment setup
- `nginx.conf` - Nginx configuration for reverse proxy (optional)
- `deploy.sh` - Automated deployment script

## 🔧 Quick Deployment

### 1. Copy Files to Server
```bash
rsync -avz dashboard/ user@your-server:/path/to/quranbot/dashboard/
```

### 2. Install Dependencies
```bash
cd /path/to/quranbot/dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Service
```bash
sudo cp deploy/quranbot-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable quranbot-dashboard
sudo systemctl start quranbot-dashboard
```

### 4. Check Status
```bash
sudo systemctl status quranbot-dashboard
```

## 🔒 Security Notes

1. Change the secret key in production
2. Configure firewall to allow port 5000
3. Use HTTPS with nginx reverse proxy for production
4. Set appropriate CORS origins

## 📊 Monitoring

View logs:
```bash
sudo journalctl -u quranbot-dashboard -f
```

## 🛠️ Troubleshooting

If the service fails to start:
1. Check logs with `journalctl`
2. Ensure all paths in service file are correct
3. Verify Python virtual environment is set up
4. Check firewall rules

---

*May Allah accept this work and make it beneficial for the Ummah* 🕌