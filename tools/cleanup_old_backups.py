#!/usr/bin/env python3
# =============================================================================
# QuranBot - Cleanup Old Backups
# =============================================================================
# Script to clean up frequent backup files from the old system
# Prepares for the new lightweight DataBackupService
# =============================================================================

import argparse
from datetime import datetime
from pathlib import Path


def cleanup_old_backups(backup_dir: Path, dry_run: bool = True):
    """Clean up old backup files"""
    
    print(f"🧹 Cleaning up old backup files in: {backup_dir}")
    
    if not backup_dir.exists():
        print("❓ Backup directory does not exist")
        return
    
    # Find old backup files
    patterns = [
        "backup_*.json.gz",  # StateService backups
        "backup_*.zip",      # BackupManager ZIP files
        "*hourly*.zip",      # Hourly backups
        "*daily*.zip",       # Daily backups
    ]
    
    files_to_remove = []
    total_size = 0
    
    for pattern in patterns:
        for file in backup_dir.glob(pattern):
            if file.is_file():
                files_to_remove.append(file)
                total_size += file.stat().st_size
    
    if not files_to_remove:
        print("✅ No old backup files found")
        return
    
    print(f"\n📋 Found {len(files_to_remove)} old backup files:")
    print(f"💾 Total size: {total_size / 1024 / 1024:.2f} MB")
    
    for file in sorted(files_to_remove):
        size_mb = file.stat().st_size / 1024 / 1024
        print(f"   📄 {file.name} ({size_mb:.2f} MB)")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - No files were actually deleted")
        print(f"   Run with --delete to actually remove files")
    else:
        print(f"\n🗑️  Deleting files...")
        removed_count = 0
        removed_size = 0
        
        for file in files_to_remove:
            try:
                size = file.stat().st_size
                file.unlink()
                removed_count += 1
                removed_size += size
                print(f"   ✅ Deleted: {file.name}")
            except Exception as e:
                print(f"   ❌ Failed to delete {file.name}: {e}")
        
        print(f"\n🎉 Cleanup complete!")
        print(f"   📁 Files removed: {removed_count}")
        print(f"   💾 Space freed: {removed_size / 1024 / 1024:.2f} MB")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Clean up old frequent backup files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/cleanup_old_backups.py                 # Dry run (preview only)
  python tools/cleanup_old_backups.py --delete        # Actually delete files
  python tools/cleanup_old_backups.py --backup-dir /path/to/backup  # Custom backup directory
        """
    )
    
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backup"),
        help="Backup directory path (default: backup)"
    )
    
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files (default is dry run)"
    )
    
    args = parser.parse_args()
    
    print("🛠️  QuranBot - Old Backup Cleanup")
    print("=" * 50)
    print(f"📁 Backup directory: {args.backup_dir}")
    print(f"🔥 Delete mode: {'ON' if args.delete else 'OFF (dry run)'}")
    print()
    
    try:
        cleanup_old_backups(args.backup_dir, dry_run=not args.delete)
        
    except KeyboardInterrupt:
        print("\n🛑 Cleanup interrupted by user")
    except Exception as e:
        print(f"\n💥 Cleanup failed: {e}")


if __name__ == "__main__":
    main() 