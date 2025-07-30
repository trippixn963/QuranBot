#!/usr/bin/env python3
# =============================================================================
# QuranBot - Bot Startup Validation Tool
# =============================================================================
# This script validates the bot configuration and codebase before startup
# to catch common issues that would cause runtime errors.
#
# Checks performed:
# - Configuration field consistency
# - Import statement validity
# - File existence and permissions
# - Data file integrity
# - Code syntax and structure
# =============================================================================

import os
import sys
import json
import importlib
import ast
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class BotStartupValidator:
    """Comprehensive validation tool for bot startup issues."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        
    def log_error(self, message: str, file: str = None, line: int = None):
        """Log an error with optional file and line information."""
        error_msg = f"❌ ERROR: {message}"
        if file:
            error_msg += f" (in {file}"
            if line:
                error_msg += f":{line}"
            error_msg += ")"
        self.errors.append(error_msg)
        print(error_msg)
    
    def log_warning(self, message: str, file: str = None):
        """Log a warning with optional file information."""
        warning_msg = f"⚠️  WARNING: {message}"
        if file:
            warning_msg += f" (in {file})"
        self.warnings.append(warning_msg)
        print(warning_msg)
    
    def log_success(self, message: str):
        """Log a successful check."""
        self.success_count += 1
        print(f"✅ {message}")
    
    def validate_configuration_consistency(self) -> None:
        """Check for configuration field name inconsistencies."""
        print("\n🔍 Checking configuration field consistency...")
        
        # Define expected field mappings (lowercase -> possible uppercase variants)
        field_mappings = {
            'daily_verse_channel_id': ['DAILY_VERSE_CHANNEL_ID'],
            'developer_id': ['DEVELOPER_ID'],
            'discord_webhook_url': ['DISCORD_WEBHOOK_URL'],
            'discord_token': ['DISCORD_TOKEN'],
            'guild_id': ['GUILD_ID'],
            'voice_channel_id': ['VOICE_CHANNEL_ID'],
        }
        
        # Search for uppercase variants in Python files (excluding venv and some test files)
        python_files = list(project_root.rglob("*.py"))
        
        for field_lower, field_variants in field_mappings.items():
            for variant in field_variants:
                for file_path in python_files:
                    # Skip venv files and some test files
                    if any(skip in str(file_path) for skip in [".venv", "venv", "site-packages", "test_webhook_footer.py"]):
                        continue
                        
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if variant in content:
                                self.log_error(
                                    f"Found uppercase config field '{variant}' instead of '{field_lower}'",
                                    str(file_path.relative_to(project_root))
                                )
                    except Exception as e:
                        self.log_error(f"Could not read {file_path}: {e}")
        
        self.log_success("Configuration field consistency check completed")
    
    def validate_imports(self) -> None:
        """Check for import errors in all Python files."""
        print("\n🔍 Checking import statements...")
        
        python_files = list(project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip venv files and some test files
            if any(skip in str(file_path) for skip in [".venv", "venv", "site-packages", "test_webhook_footer.py"]):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file to check for syntax errors
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    self.log_error(f"Syntax error: {e}", str(file_path.relative_to(project_root)), e.lineno)
                    continue
                
                # Check for import statements
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.ImportFrom):
                            module = node.module
                            if module and module.startswith('src.'):
                                # Check if the module exists
                                module_path = module.replace('.', '/')
                                potential_paths = [
                                    project_root / f"{module_path}.py",
                                    project_root / f"{module_path}/__init__.py"
                                ]
                                
                                if not any(p.exists() for p in potential_paths):
                                    self.log_error(
                                        f"Import error: module '{module}' not found",
                                        str(file_path.relative_to(project_root))
                                    )
                
            except Exception as e:
                self.log_error(f"Could not parse {file_path}: {e}")
        
        self.log_success("Import validation completed")
    
    def validate_data_files(self) -> None:
        """Check data files for integrity and required structure."""
        print("\n🔍 Checking data files...")
        
        data_dir = project_root / "data"
        if not data_dir.exists():
            self.log_error("Data directory does not exist")
            return
        
        # Check required data files
        required_files = [
            "verses.json",
            "quiz.json", 
            "state.json",
            "cache.json"
        ]
        
        for filename in required_files:
            file_path = data_dir / filename
            if not file_path.exists():
                self.log_error(f"Required data file missing: {filename}")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate specific file structures
                if filename == "verses.json":
                    if "verses" not in data:
                        self.log_error("verses.json missing 'verses' key")
                    elif not isinstance(data["verses"], list):
                        self.log_error("verses.json 'verses' should be a list")
                    elif len(data["verses"]) == 0:
                        self.log_warning("verses.json has no verses")
                    else:
                        self.log_success(f"verses.json validated ({len(data['verses'])} verses)")
                
                elif filename == "quiz.json":
                    if "questions" not in data:
                        self.log_error("quiz.json missing 'questions' key")
                    elif not isinstance(data["questions"], list):
                        self.log_error("quiz.json 'questions' should be a list")
                    elif len(data["questions"]) == 0:
                        self.log_warning("quiz.json has no questions")
                    else:
                        self.log_success(f"quiz.json validated ({len(data['questions'])} questions)")
                
            except json.JSONDecodeError as e:
                self.log_error(f"Invalid JSON in {filename}: {e}")
            except Exception as e:
                self.log_error(f"Error reading {filename}: {e}")
        
        self.log_success("Data file validation completed")
    
    def validate_environment_file(self) -> None:
        """Check .env file for required variables."""
        print("\n🔍 Checking environment configuration...")
        
        env_file = project_root / ".env"
        if not env_file.exists():
            self.log_error(".env file not found")
            return
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required environment variables
            required_vars = [
                "DISCORD_TOKEN",
                "GUILD_ID", 
                "VOICE_CHANNEL_ID",
                "DAILY_VERSE_CHANNEL_ID"
            ]
            
            for var in required_vars:
                if var not in content:
                    self.log_error(f"Missing required environment variable: {var}")
                else:
                    # Check if it has a value
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith(f"{var}="):
                            value = line.split('=', 1)[1].strip()
                            if not value:
                                self.log_error(f"Environment variable {var} has no value")
                            break
                    else:
                        self.log_error(f"Environment variable {var} not properly set")
            
            self.log_success("Environment file validation completed")
            
        except Exception as e:
            self.log_error(f"Error reading .env file: {e}")
    
    def validate_file_permissions(self) -> None:
        """Check file permissions for critical files."""
        print("\n🔍 Checking file permissions...")
        
        critical_files = [
            "main.py",
            ".env",
            "data/",
            "src/"
        ]
        
        for file_path in critical_files:
            full_path = project_root / file_path
            if full_path.exists():
                if not os.access(full_path, os.R_OK):
                    self.log_error(f"No read permission for {file_path}")
                if full_path.is_file() and not os.access(full_path, os.W_OK):
                    self.log_warning(f"No write permission for {file_path}")
            else:
                self.log_error(f"Critical file/directory missing: {file_path}")
        
        self.log_success("File permissions validation completed")
    
    def validate_code_structure(self) -> None:
        """Check for common code structure issues."""
        print("\n🔍 Checking code structure...")
        
        # Check for empty except blocks
        python_files = list(project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip venv files and some test files
            if any(skip in str(file_path) for skip in [".venv", "venv", "site-packages", "test_webhook_footer.py"]):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('except:') or stripped.startswith('except Exception:'):
                        # Check if the next line is just pass
                        if i < len(lines) and lines[i].strip() == 'pass':
                            self.log_warning(f"Empty except block found", str(file_path.relative_to(project_root)))
                
            except Exception as e:
                self.log_error(f"Error checking {file_path}: {e}")
        
        self.log_success("Code structure validation completed")
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print("🚀 Starting QuranBot startup validation...")
        print("=" * 60)
        
        self.validate_configuration_consistency()
        self.validate_imports()
        self.validate_data_files()
        self.validate_environment_file()
        self.validate_file_permissions()
        self.validate_code_structure()
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"✅ Successful checks: {self.success_count}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
            print(f"\n❌ Bot startup validation FAILED with {len(self.errors)} errors!")
            return False
        else:
            print(f"\n✅ Bot startup validation PASSED! All checks successful.")
            return True

def main():
    """Main validation function."""
    validator = BotStartupValidator()
    success = validator.run_all_validations()
    
    if not success:
        sys.exit(1)
    else:
        print("\n🎉 Bot is ready to start!")
        sys.exit(0)

if __name__ == "__main__":
    main() 