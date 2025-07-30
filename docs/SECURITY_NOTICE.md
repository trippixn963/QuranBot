# 🔒 SECURITY NOTICE - Protecting Your Credentials

## ⚠️ CRITICAL SECURITY WARNING

**NEVER commit real credentials to version control!**

This repository contains example configuration files with placeholder values.
You MUST replace these placeholders with your actual credentials locally.

## 🚨 What NOT to Commit

### ❌ Never commit these to Git:
- Discord bot tokens
- OpenAI API keys
- Webhook URLs
- Database passwords
- Any secret keys or tokens

### ✅ Safe to commit:
- Configuration templates with placeholders
- Documentation and examples
- Code without embedded secrets

## 🛡️ How to Handle Secrets Safely

### 1. Use Environment Variables
```bash
# Set in your shell or .env file (not committed)
export DISCORD_TOKEN="your_real_token_here"
export OPENAI_API_KEY="sk-your_real_key_here"
```

### 2. Use .env Files (Add to .gitignore)
```bash
# Add to .gitignore
echo "config/.env" >> .gitignore
echo ".env" >> .gitignore
```

### 3. Use Secure Deployment Methods
- Environment variables in production
- Secret management services (AWS Secrets Manager, etc.)
- Encrypted configuration files

## 🔍 Placeholder Format Guide

Our placeholders are designed to be obviously fake:

| Type | Placeholder Format | Real Format |
|------|-------------------|-------------|
| Discord Token | `paste_your_bot_token_here` | 59+ character string |
| Discord IDs | `your_server_id_18_digits` | 17-19 digit number |
| OpenAI Key | `sk-your_openai_api_key_starts_with_sk` | `sk-` + 48 characters |
| Webhook URL | `your_webhook_id/your_webhook_token` | Real Discord webhook |

## 🚨 If You Accidentally Commit Secrets

### Immediate Actions:
1. **Revoke the compromised credentials immediately**
2. **Generate new credentials**
3. **Remove from Git history** (use `git filter-branch` or BFG)
4. **Update all systems** with new credentials
5. **Monitor for unauthorized usage**

### Prevention:
- Use pre-commit hooks to scan for secrets
- Regular security audits
- Team training on security practices

## 📞 Security Contact

If you discover security issues or accidentally committed secrets:
- **Email**: security@quranbot.example.com
- **Create Issue**: Mark as security-sensitive
- **Immediate Action**: Revoke compromised credentials first

---

**Remember: Security is everyone's responsibility!**
