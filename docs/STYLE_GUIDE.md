# QuranBot Style Guide

## 🎯 Overview

This document defines the coding standards and formatting requirements for the QuranBot project. **All files must follow these standards exactly** to maintain consistency across the codebase.

## 🔧 Code Formatting

### Primary Formatter: Black

- **Line length**: 88 characters
- **Target Python versions**: 3.8+
- **String quotes**: Double quotes preferred
- **Trailing commas**: Required for multi-line structures

### Import Organization: isort

- **Profile**: black-compatible
- **Multi-line output**: Mode 3 (Vertical Hanging Indent)
- **Order**: Standard library → Third party → Local imports

## 📝 File Structure Standards

### 1. File Header (Required)

```python
# =============================================================================
# QuranBot - [Module Description]
# =============================================================================
# [Brief description of what this module does]
# [Additional context if needed]
# =============================================================================
```

### 2. Import Organization

```python
# Standard library imports
import os
import sys
import traceback

# Third-party imports
import discord
from discord.ext import commands

# Local imports
from utils.tree_log import (
    log_section_start, log_tree_branch, log_tree_final,
    log_error_with_traceback, log_critical_error
)
```

### 3. Section Headers (Required)

```python
# =============================================================================
# [Section Name]
# =============================================================================
```

### 4. Function Documentation

```python
def function_name(param1, param2):
    """Brief description of what the function does"""
    try:
        # Implementation
        pass
    except Exception as e:
        log_error_with_traceback("Description of error", e)
```

## 🛡️ Error Handling Standards (Mandatory)

### Required Imports

```python
import traceback
from utils.tree_log import (
    log_error_with_traceback, log_critical_error,
    log_async_error, log_discord_error
)
```

### Error Handling Patterns

#### 1. General Exceptions

```python
try:
    # Code that might fail
    pass
except Exception as e:
    log_error_with_traceback("Description of what failed", e)
```

#### 2. Critical Errors (Application Breaking)

```python
try:
    # Critical operation
    pass
except Exception as e:
    log_critical_error("Critical failure description", e)
    return False  # or sys.exit(1)
```

#### 3. Async Function Errors

```python
async def async_function():
    try:
        # Async operation
        pass
    except Exception as e:
        log_async_error("async_function", e, "Additional context")
```

#### 4. Discord-Specific Errors

```python
@bot.event
async def on_some_event():
    try:
        # Discord operation
        pass
    except Exception as e:
        log_discord_error("on_some_event", e, guild_id, channel_id)
```

## 📁 Directory Structure

```
QuranBot/
├── main.py                 # Main entry point
├── bot_manager.py          # Bot management utility
├── format_code.py          # Code formatting utility
├── requirements.txt        # Dependencies
├── pyproject.toml         # Black/isort configuration
├── STYLE_GUIDE.md         # This file
├── src/                   # Source code directory
│   ├── __init__.py
│   ├── bot/               # Discord bot modules
│   │   ├── __init__.py
│   │   └── main.py        # Bot implementation
│   ├── config/            # Configuration modules
│   │   └── __init__.py
│   └── utils/             # Utility modules
│       ├── __init__.py
│       └── tree_log.py    # Logging system
└── .vscode/
    └── settings.json      # VSCode configuration
```

## 🎨 Naming Conventions

### Variables and Functions

- **snake_case** for variables and functions
- **Descriptive names** that explain purpose
- **No single-letter variables** except for loops

### Constants

- **UPPER_SNAKE_CASE** for constants
- **Module-level constants** at the top after imports

### Classes

- **PascalCase** for class names
- **Descriptive names** that explain the class purpose

## 📊 Logging Standards

### Required Logging Structure

```python
# At function start
log_section_start("Function Description", "🎯")

# For progress/status
log_tree_branch("key", "value")
log_tree_final("final_key", "final_value")

# For errors (with traceback)
log_error_with_traceback("Error description", exception)

# For warnings (with context)
log_warning_with_context("Warning message", "Additional context")
```

### Logging Categories

- **General operations**: `log_tree_branch()`, `log_tree_final()`
- **Errors with traceback**: `log_error_with_traceback()`
- **Critical errors**: `log_critical_error()`
- **Async errors**: `log_async_error()`
- **Discord errors**: `log_discord_error()`

## 🔄 Development Workflow

### 1. Before Coding

```bash
# Install formatters
pip install black isort

# Format existing code
python format_code.py
```

### 2. During Development

- **Use VSCode** with the provided settings for auto-formatting
- **Follow error handling patterns** for all new code
- **Add proper documentation** for all functions
- **Use tree logging** for all operations

### 3. Before Committing

```bash
# Format all code
python format_code.py

# Verify no errors
python -m py_compile main.py
python -m py_compile src/bot/main.py
```

## ✅ Checklist for New Files

- [ ] File header with box-style comments
- [ ] Proper import organization (standard → third-party → local)
- [ ] Section headers for logical code blocks
- [ ] Traceback import for error handling
- [ ] Enhanced tree_log imports
- [ ] Comprehensive error handling with try/catch
- [ ] Proper function documentation
- [ ] Consistent naming conventions
- [ ] Tree-structured logging throughout
- [ ] Black formatting applied
- [ ] isort import organization applied

## 🚫 What NOT to Do

- ❌ Don't use generic `except:` without specific exception handling
- ❌ Don't skip error logging for any exceptions
- ❌ Don't use inconsistent comment styles
- ❌ Don't skip function documentation
- ❌ Don't use single-letter variable names
- ❌ Don't skip the traceback import
- ❌ Don't use print() instead of tree logging
- ❌ Don't skip section headers for logical blocks

## 🎉 Benefits of Following This Guide

- **Consistent codebase** that's easy to read and maintain
- **Comprehensive error tracking** with full stack traces
- **Professional logging** with beautiful tree structure
- **Easy debugging** with detailed error context
- **Scalable architecture** that supports growth
- **Team-friendly code** that anyone can understand

---

**Remember**: Every file must follow these standards exactly. Consistency is key to maintaining a professional, scalable codebase! [[memory:2298601]]
