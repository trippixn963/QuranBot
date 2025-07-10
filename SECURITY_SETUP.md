# 🔒 Security Setup Guide

## ⚠️ CRITICAL: Remove Exposed Tokens

**IMMEDIATE ACTION REQUIRED** - Your Discord bot tokens are exposed in the repository!

### 1. Remove Exposed Files

```bash
# Remove exposed token files
rm -f config/.env src/config/.env

# Verify they're gone
ls -la config/ src/config/
```

### 2. Create Secure Environment File

```bash
# Create your private .env file (NOT tracked by git)
cp config/.env.example config/.env

# Edit with your actual values
nano config/.env
```

### 3. Required Environment Variables

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_actual_bot_token_here

# Channel IDs (get from Discord with Developer Mode enabled)
TARGET_CHANNEL_ID=1234567890123456789
PANEL_CHANNEL_ID=1234567890123456789
DAILY_VERSE_CHANNEL_ID=1234567890123456789

# Server and User IDs
GUILD_ID=1234567890123456789
DEVELOPER_ID=1234567890123456789

# Audio Settings
DEFAULT_RECITER=Saad Al Ghamdi
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg
```

## 🛡️ Security Best Practices

### Token Security

- **Never commit** `.env` files to version control
- **Regenerate tokens** if accidentally exposed
- **Use environment variables** for all sensitive data
- **Restrict bot permissions** to minimum required

### File Permissions

```bash
# Secure your environment file
chmod 600 config/.env

# Secure your data directory
chmod 700 data/
```

### VPS Security

```bash
# Use SSH keys instead of passwords
ssh-keygen -t rsa -b 4096

# Disable password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80   # if using web dashboard
```

### Discord Bot Permissions

Only grant these required permissions:

- ✅ View Channels
- ✅ Send Messages
- ✅ Embed Links
- ✅ Use Slash Commands
- ✅ Connect to Voice
- ✅ Speak in Voice
- ❌ Administrator (NOT required)

## 🔧 Getting Discord IDs

### Enable Developer Mode

1. Discord → Settings → Advanced → Developer Mode ✅

### Get Channel IDs

1. Right-click channel → Copy ID

### Get Server ID

1. Right-click server name → Copy ID

### Get User ID

1. Right-click your username → Copy ID

## 🚨 Emergency Response

### If Tokens Are Compromised

1. **Immediately regenerate** Discord bot token
2. **Update** all deployment environments
3. **Check logs** for unauthorized usage
4. **Review** bot permissions

### If Repository Is Compromised

1. **Remove** from git history:
   ```bash
   git filter-branch --force --index-filter \
   'git rm --cached --ignore-unmatch config/.env' \
   --prune-empty --tag-name-filter cat -- --all
   ```
2. **Force push** cleaned history
3. **Regenerate** all exposed tokens

## ✅ Security Checklist

- [ ] Removed exposed `.env` files from repository
- [ ] Created secure `config/.env` with actual values
- [ ] Set proper file permissions (600 for .env)
- [ ] Verified `.env` is in `.gitignore`
- [ ] Regenerated Discord bot token if previously exposed
- [ ] Configured minimal bot permissions
- [ ] Secured VPS with SSH keys
- [ ] Enabled firewall on VPS
- [ ] Tested bot functionality with new secure setup

---

**Remember: Security is not optional. Take these steps seriously to protect your bot and users.**
