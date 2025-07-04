# 🔒 Security Setup Guide

## ⚠️ IMPORTANT: Secure Configuration

This repository is designed to be secure by default. Follow these steps to set up your bot securely:

## 1. Environment Variables (.env file)

Create a `.env` file in the root directory with your sensitive configuration:

```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DEVELOPER_ID=your_discord_user_id_here

# Channel Configuration
AUDIO_CHANNEL_ID=your_voice_channel_id_here
PANEL_CHANNEL_ID=your_control_panel_channel_id_here

# FFmpeg Configuration (Optional - auto-detects if not specified)
# FFMPEG_PATH=C:\ffmpeg\bin    # Windows
# FFMPEG_PATH=/usr/bin/ffmpeg  # Linux/VPS
```

## 2. VPS Configuration (Optional)

If you're using VPS deployment, copy the template and customize it:

```bash
cp scripts/vps/vps_config.json.template scripts/vps/vps_config.json
```

Then edit `scripts/vps/vps_config.json` with your VPS details:
- Replace `YOUR_VPS_IP_ADDRESS` with your VPS IP
- Replace `YOUR_VPS_USERNAME` with your VPS username
- Replace `YOUR_SSH_KEY_FILENAME` with your SSH key filename
- Replace paths with your actual paths

## 3. SSH Key Security

**NEVER commit SSH keys to git!**

- Keep your SSH keys in a secure location
- Use strong passphrases for your SSH keys
- Regularly rotate your SSH keys
- Use SSH key authentication instead of passwords

## 4. Files That Should NEVER Be Committed

The following files are automatically ignored by `.gitignore`:

- `.env` (contains your bot token)
- `quranbot_key*` (SSH keys)
- `scripts/vps/vps_config.json` (VPS configuration)
- `bot_state.json` (runtime data)
- `data/user_vc_sessions.json` (user data)
- `data/daily_verses_*.json` (runtime state)
- `logs/` (log files)
- `audio/` (audio files)

## 5. Before Pushing to GitHub

Always check what you're about to commit:

```bash
git status
git diff --cached
```

If you see any sensitive files, remove them from git:

```bash
git rm --cached SENSITIVE_FILE
```

## 6. If You Accidentally Commit Sensitive Data

1. Remove the file from git tracking:
   ```bash
   git rm --cached SENSITIVE_FILE
   ```

2. Add it to `.gitignore`

3. Commit the changes:
   ```bash
   git add .gitignore
   git commit -m "Remove sensitive file from tracking"
   ```

4. **Change all exposed credentials immediately!**

## 7. Deployment Security

- Use environment variables for secrets
- Enable firewall on your VPS
- Use non-root user for running the bot
- Keep your system updated
- Use strong SSH keys and disable password authentication

## 8. Discord Bot Security

- Keep your bot token secret
- Use appropriate Discord permissions (least privilege)
- Regularly review bot permissions
- Monitor bot activity logs

---

**Remember**: Security is an ongoing process. Regularly review and update your security practices. 