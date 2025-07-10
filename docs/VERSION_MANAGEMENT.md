# QuranBot Version & Author Management

## Overview

QuranBot uses a **centralized version and author management system** to ensure consistency across all files and prevent maintenance issues. Both version numbers and author information are managed from a single source of truth.

## Architecture

### Single Source of Truth: `src/version.py`

All version and author information is centralized in `src/version.py`:

```python
__version__ = "3.5.0"
__author__ = "John (Discord: Trippixn)"
BOT_NAME = "QuranBot"
```

### Import-Based System

All files import version and author information instead of hardcoding:

```python
# ✅ Correct - Import from centralized source
from src.version import BOT_VERSION, __author__

# ❌ Wrong - Hardcoded values
BOT_VERSION = "2.0.0"
__author__ = "John"
```

## Automated Management

### Update Tool: `tools/update_version.py`

The update tool provides comprehensive management:

```bash
# Update version only
python tools/update_version.py 3.6.0

# Update author only
python tools/update_version.py --author "John (Discord: Trippixn)"

# Update both version and author
python tools/update_version.py 3.6.0 --author "John Smith"

# Verify consistency
python tools/update_version.py --verify-only
```

### What the Tool Updates

1. **`src/version.py`** - Main version and author file
2. **`src/utils/__init__.py`** - Fallback version and author for different import contexts
3. **Verification** - Ensures all imports work correctly

## Step-by-Step Update Process

### Version Updates

1. **Update Version:**

   ```bash
   python tools/update_version.py 3.6.0
   ```

2. **Verify Changes:**

   ```bash
   python tools/update_version.py --verify-only
   ```

3. **Test Locally:**

   ```bash
   python tools/test_bot.py
   ```

4. **Commit and Deploy:**
   ```bash
   git add .
   git commit -m "Bump version to 3.6.0"
   git push origin master
   ```

### Author Updates

1. **Update Author:**

   ```bash
   python tools/update_version.py --author "John (Discord: Trippixn)"
   ```

2. **Verify Changes:**

   ```bash
   python tools/update_version.py --verify-only
   ```

3. **Test and Deploy** (same as version updates)

## File Structure

```
src/
├── version.py              # 🎯 Single source of truth
├── __init__.py            # Imports from version.py
├── bot/main.py            # Imports BOT_VERSION, __author__
├── commands/credits.py    # Imports BOT_VERSION, __author__
└── utils/__init__.py      # Fallback version and author

tools/
├── update_version.py      # 🔧 Update automation
├── test_bot.py           # Imports BOT_VERSION
└── deploy_to_vps.py      # Imports BOT_VERSION

main.py                   # Imports BOT_VERSION, BOT_NAME
```

## Version and Author Information Available

### From `src/version.py`:

- `__version__` - Main version string
- `__author__` - Author information
- `BOT_NAME` - Bot name
- `BOT_VERSION` - Alias for version
- `BOT_AUTHOR` - Alias for author
- `VERSION_MAJOR`, `VERSION_MINOR`, `VERSION_PATCH` - Version components
- `get_version_info()` - Comprehensive version data

### Usage Examples:

```python
from src.version import __version__, __author__, BOT_NAME

print(f"{BOT_NAME} v{__version__} by {__author__}")
# Output: QuranBot v3.5.0 by John (Discord: Trippixn)
```

## Benefits

### ✅ Advantages

- **Single Update Point** - Change version/author in one place
- **Guaranteed Consistency** - Import system prevents mismatches
- **Automated Verification** - Tool ensures all imports work
- **Professional Maintenance** - No more manual file-by-file updates
- **Error Prevention** - Impossible to have inconsistent versions/authors

### ❌ Previous Problems (Solved)

- ~~Hardcoded versions scattered across files~~
- ~~Manual updates required for each file~~
- ~~Version inconsistencies between modules~~
- ~~Author information duplicated everywhere~~
- ~~Maintenance nightmare for releases~~

## Troubleshooting

### Import Errors

If you encounter import errors:

1. **Check File Structure:**

   ```bash
   ls -la src/version.py
   ```

2. **Verify Imports:**

   ```bash
   python tools/update_version.py --verify-only
   ```

3. **Test Individual Import:**
   ```python
   from src.version import __version__, __author__
   print(f"Version: {__version__}, Author: {__author__}")
   ```

### Consistency Issues

If versions or authors are inconsistent:

1. **Run Verification:**

   ```bash
   python tools/update_version.py --verify-only
   ```

2. **Force Update:**
   ```bash
   python tools/update_version.py 3.5.0 --author "John (Discord: Trippixn)"
   ```

## Migration Notes

### From Old System (Completed)

- ✅ Removed hardcoded `BOT_VERSION = "1.3.0"` from `tools/test_bot.py`
- ✅ Removed hardcoded `BOT_VERSION = "1.3.0"` from `tools/deploy_to_vps.py`
- ✅ Removed hardcoded `__version__ = "1.5.0"` from `src/__init__.py`
- ✅ Removed hardcoded author strings from `src/commands/credits.py`
- ✅ Added centralized `src/version.py` with single source of truth
- ✅ Updated all files to import from centralized source
- ✅ Created automated update tool with verification

### Current State

- 🎯 All version and author information centralized in `src/version.py`
- 🔧 Automated update tool handles all changes
- ✅ Comprehensive verification ensures consistency
- 📦 Professional version management system active
- 🚀 Current version: v3.5.0 with admin answer key system

## Best Practices

1. **Never hardcode versions or author info** - Always import from `src/version.py`
2. **Use the update tool** - Don't manually edit version files
3. **Verify after updates** - Run `--verify-only` to ensure consistency
4. **Test before deployment** - Run `tools/test_bot.py` after version changes
5. **Follow semantic versioning** - Use MAJOR.MINOR.PATCH format
6. **Keep author format consistent** - Use "Name (Discord: Username)" format

---

_This centralized system ensures QuranBot maintains professional version and author management with zero maintenance overhead._
