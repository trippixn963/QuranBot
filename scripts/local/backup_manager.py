#!/usr/bin/env python3
"""
QuranBot Data Backup Manager
Handles backing up the data folder to a zip file with timestamp.
"""

import os
import sys
import zipfile
import shutil
from datetime import datetime
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent

def create_backup():
    """Create a backup of the data folder."""
    project_root = get_project_root()
    data_path = project_root / "data"
    backup_path = project_root / "backups"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"data_backup_{timestamp}.zip"
    
    print("🔄 Creating data backup...")
    
    # Create backups directory if it doesn't exist
    backup_path.mkdir(exist_ok=True)
    
    # Check if data directory exists
    if not data_path.exists():
        print("❌ Data directory not found!")
        return False
    
    try:
        # Create zip file
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in data_path.rglob('*'):
                if file_path.is_file():
                    # Add file to zip with relative path
                    arcname = file_path.relative_to(data_path)
                    zipf.write(file_path, arcname)
                    print(f"📦 Added: {arcname}")
        
        # Write timestamp to log
        log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Data folder backup completed: {backup_file.name}"
        log_file = project_root / "logs" / "backup.log"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
        
        print(f"✅ Backup completed successfully!")
        print(f"📁 Backup file: {backup_file}")
        print(f"📊 Size: {backup_file.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def main():
    """Main function."""
    print("=" * 50)
    print("           QuranBot Backup Manager")
    print("=" * 50)
    print()
    
    success = create_backup()
    
    if success:
        print("\n✅ Backup operation completed successfully!")
    else:
        print("\n❌ Backup operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 