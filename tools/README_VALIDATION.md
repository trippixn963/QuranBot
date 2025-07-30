# QuranBot Validation System

This directory contains comprehensive validation tools to catch startup issues before the bot runs.

## Files

### `validate_bot_startup.py`
Main validation script that checks:
- ✅ Configuration field consistency (catches uppercase/lowercase mismatches)
- ✅ Import statement validity
- ✅ Data file integrity and structure
- ✅ Environment file (.env) validation
- ✅ File permissions for critical files
- ✅ Code structure issues (empty except blocks, etc.)

### `pre_commit_validation.py`
Pre-commit hook that runs validation before git commits.

### `validate_and_start.py`
Script that validates before starting the bot.

## Usage

### Manual Validation
```bash
# Run full validation
python tools/validate_bot_startup.py

# Run validation before starting bot
python start_bot.py
```

### Pre-Commit Hook
```bash
# Run validation before commit
python tools/pre_commit_validation.py
```

## What It Catches

### Configuration Issues
- ❌ `DAILY_VERSE_CHANNEL_ID` instead of `daily_verse_channel_id`
- ❌ `DEVELOPER_ID` instead of `developer_id`
- ❌ `DISCORD_TOKEN` instead of `discord_token`
- ❌ Missing environment variables
- ❌ Empty environment variable values

### Import Issues
- ❌ Missing modules (`src.core.webhook_utils` not found)
- ❌ Syntax errors in Python files
- ❌ Circular import dependencies

### Data Issues
- ❌ Missing required data files
- ❌ Invalid JSON in data files
- ❌ Empty data files (no verses, no questions)
- ❌ Wrong data structure

### File Issues
- ❌ Missing critical files/directories
- ❌ Permission issues
- ❌ Empty cache files

## Example Output

```
🚀 Starting QuranBot startup validation...
============================================================

🔍 Checking configuration field consistency...
❌ ERROR: Found uppercase config field 'DAILY_VERSE_CHANNEL_ID' instead of 'daily_verse_channel_id'
✅ Configuration field consistency check completed

🔍 Checking import statements...
❌ ERROR: Import error: module 'src.core.webhook_utils' not found
✅ Import validation completed

🔍 Checking data files...
✅ verses.json validated (54 verses)
✅ quiz.json validated (200 questions)
❌ ERROR: Invalid JSON in cache.json
✅ Data file validation completed

============================================================
📊 VALIDATION SUMMARY
============================================================
✅ Successful checks: 8
⚠️  Warnings: 34
❌ Errors: 89

❌ Bot startup validation FAILED with 89 errors!
```

## Benefits

1. **Prevents Runtime Errors**: Catches issues before the bot starts
2. **Configuration Consistency**: Ensures all config fields use correct naming
3. **Data Integrity**: Validates JSON files and data structures
4. **Import Safety**: Checks for missing modules and syntax errors
5. **File System**: Ensures critical files exist with proper permissions

## Integration

The validation system is designed to be integrated into:
- Pre-commit hooks
- CI/CD pipelines
- Manual startup process
- Development workflow

This ensures that issues are caught early and the bot only starts when everything is properly configured. 