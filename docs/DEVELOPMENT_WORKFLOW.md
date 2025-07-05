# QuranBot Development Workflow

## 🎯 Overview

This workflow ensures **nothing broken ever reaches your VPS production environment**. [[memory:2298754]] The QuranBot is designed for single guild use and requires bulletproof deployment safety.

## 🏗️ Environment Setup

### Development Environment (Local Mac)

- **Purpose**: Code development, testing, and validation
- **Safety**: Can break without affecting production
- **Testing**: Comprehensive test suite before any VPS deployment

### Production Environment (VPS)

- **Purpose**: Live bot serving Discord guild
- **Safety**: **NEVER deploy untested code**
- **Stability**: Zero tolerance for breaking changes

## 🔄 Development Workflow

### 1. Daily Development Cycle

```bash
# Start development session
cd /path/to/QuranBot

# Pull latest changes (if working with team)
git pull origin master

# Install/update dependencies
pip install -r requirements.txt

# Format code before starting
python format_code.py

# Start coding...
# [Make your changes]

# Test everything before committing
python test_bot.py

# Format code after changes
python format_code.py

# Commit changes
git add .
git commit -m "Descriptive commit message"
git push origin master
```

### 2. Pre-Deployment Safety Check

**NEVER deploy to VPS without running this:**

```bash
# Run comprehensive deployment safety check
python deploy_to_vps.py
```

This script will:

- ✅ Format all code
- ✅ Run comprehensive tests
- ✅ Validate git repository state
- ✅ Generate deployment guide
- ✅ Create safety checklist

### 3. VPS Deployment Process

**Only after `deploy_to_vps.py` gives the green light:**

1. **Review the generated guide**: `VPS_DEPLOYMENT_GUIDE.md`
2. **SSH to your VPS**
3. **Execute commands manually** (never automated)
4. **Test on VPS before starting**

```bash
# On VPS - execute these commands one by one
cd /path/to/QuranBot
python bot_manager.py stop
git pull origin master
pip install -r requirements.txt
python test_bot.py  # CRITICAL: Must pass on VPS
python bot_manager.py start
python bot_manager.py status
```

## 🧪 Testing Strategy

### Development Testing (`test_bot.py`)

- **Environment setup validation**
- **Python syntax checking**
- **Import resolution testing**
- **Configuration validation**
- **Logging system testing**
- **Bot manager functionality**

### VPS Testing (Before Starting Bot)

- **Same test suite on production environment**
- **Environment-specific validation**
- **Dependency verification**
- **Configuration verification**

## 🛡️ Safety Measures

### Code Quality Gates

1. **Black formatting** - Consistent code style
2. **Syntax validation** - No Python errors
3. **Import testing** - All dependencies available
4. **Configuration testing** - Environment variables set
5. **Logging testing** - Error tracking works

### Deployment Gates

1. **All tests pass locally**
2. **Code is properly formatted**
3. **Git repository is clean**
4. **Deployment guide generated**
5. **Manual VPS testing required**

## 📁 File Organization

```
QuranBot/
├── 🔧 Development Tools
│   ├── test_bot.py              # Comprehensive testing
│   ├── deploy_to_vps.py         # Deployment safety
│   ├── format_code.py           # Code formatting
│   └── bot_manager.py           # Process management
├── 📚 Documentation
│   ├── STYLE_GUIDE.md           # Coding standards
│   ├── DEVELOPMENT_WORKFLOW.md  # This file
│   └── VPS_DEPLOYMENT_GUIDE.md  # Generated deployment guide
├── ⚙️ Configuration
│   ├── pyproject.toml           # Black/isort config
│   ├── requirements.txt         # Dependencies
│   └── .vscode/settings.json    # Editor config
└── 🤖 Bot Code
    ├── main.py                  # Entry point
    └── src/                     # Source code
```

## 🚀 Quick Commands

### Daily Development

```bash
# Test everything
python test_bot.py

# Format code
python format_code.py

# Check deployment readiness
python deploy_to_vps.py
```

### Bot Management (Local)

```bash
# Start bot locally
python main.py

# Or use manager
python bot_manager.py start
python bot_manager.py status
python bot_manager.py stop
python bot_manager.py restart
```

### VPS Management (Production)

```bash
# Check bot status
python bot_manager.py status

# Restart bot
python bot_manager.py restart

# View logs
tail -f logs/$(date +%Y-%m-%d)/$(date +%Y-%m-%d).log
```

## ⚠️ Critical Rules

### NEVER Do This:

- ❌ Deploy untested code to VPS
- ❌ Skip the deployment safety check
- ❌ Push breaking changes without testing
- ❌ Modify VPS code directly
- ❌ Override VPS data folders
- ❌ Run multiple bot instances

### ALWAYS Do This:

- ✅ Test thoroughly in development first
- ✅ Run `deploy_to_vps.py` before VPS deployment
- ✅ Execute VPS commands manually, one by one
- ✅ Test on VPS before starting the bot
- ✅ Monitor logs after deployment
- ✅ Keep backups of working versions

## 🔄 Rollback Strategy

If something goes wrong on VPS:

```bash
# Immediate rollback
python bot_manager.py stop
git checkout HEAD~1  # Go back to previous commit
python test_bot.py   # Test the previous version
python bot_manager.py start
```

## 📊 Monitoring

### Log Files (Both Environments)

- `logs/YYYY-MM-DD/YYYY-MM-DD.log` - Human-readable logs
- `logs/YYYY-MM-DD/YYYY-MM-DD.json` - Structured logs
- `logs/YYYY-MM-DD/YYYY-MM-DD-errors.log` - Error-only logs

### Health Checks

```bash
# Check bot status
python bot_manager.py status

# View recent logs
tail -n 50 logs/$(date +%Y-%m-%d)/$(date +%Y-%m-%d).log

# Check for errors
tail -n 20 logs/$(date +%Y-%m-%d)/$(date +%Y-%m-%d)-errors.log
```

## 🎉 Benefits of This Workflow

- **Zero production downtime** from broken deployments
- **Comprehensive testing** catches issues early
- **Consistent code quality** across all files
- **Safe deployment process** with multiple validation gates
- **Easy rollback** if issues occur
- **Beautiful logging** for easy debugging
- **Professional development** practices

---

**Remember**: This workflow protects your production VPS from broken code. Follow it religiously! [[memory:2298754]]
