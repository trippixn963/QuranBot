#!/usr/bin/env python3
"""
QuranBot FFmpeg Checker and Updater
Handles checking FFmpeg status and updating FFmpeg installation.
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import tempfile
import shutil
import argparse
from pathlib import Path
from src.monitoring.logging.tree_log import tree_log
import traceback

def check_ffmpeg():
    """Check if FFmpeg is installed and get its version."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return True, version_line
        else:
            return False, None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, None
    except Exception as e:
        tree_log('error', 'Error checking ffmpeg', {'error': str(e), 'traceback': traceback.format_exc()})
        return False, None

def get_ffmpeg_path():
    """Get the path where FFmpeg is installed."""
    try:
        result = subprocess.run(['where', 'ffmpeg'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
        else:
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

def download_ffmpeg():
    """Download and install FFmpeg."""
    print("🔄 Downloading FFmpeg...")
    
    # FFmpeg download URL
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    try:
        # Create temp directory
        temp_dir = Path(tempfile.gettempdir()) / "ffmpeg_install"
        temp_dir.mkdir(exist_ok=True)
        
        # Download FFmpeg
        zip_path = temp_dir / "ffmpeg-latest.zip"
        print(f"📥 Downloading from: {ffmpeg_url}")
        
        with urllib.request.urlopen(ffmpeg_url) as response:
            with open(zip_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        
        print("📦 Extracting FFmpeg...")
        
        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find the extracted directory
        ffmpeg_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and 'ffmpeg' in d.name.lower()]
        if not ffmpeg_dirs:
            print("❌ Failed to extract FFmpeg properly")
            return False
        
        ffmpeg_dir = ffmpeg_dirs[0]
        bin_path = ffmpeg_dir / "bin"
        
        if not bin_path.exists():
            print("❌ FFmpeg bin directory not found")
            return False
        
        # Copy FFmpeg to a permanent location
        install_dir = Path.home() / "ffmpeg"
        install_dir.mkdir(exist_ok=True)
        
        # Copy bin directory
        install_bin = install_dir / "bin"
        if install_bin.exists():
            shutil.rmtree(install_bin)
        shutil.copytree(bin_path, install_bin)
        
        print(f"✅ FFmpeg installed to: {install_bin}")
        print("📝 Add the following to your system PATH:")
        print(f"   {install_bin}")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        tree_log('error', 'Error downloading/installing FFmpeg', {'error': str(e), 'traceback': traceback.format_exc()})
        return False

def check_system_path():
    """Check system PATH for FFmpeg entries."""
    path_entries = os.environ.get('PATH', '').split(os.pathsep)
    ffmpeg_paths = [p for p in path_entries if 'ffmpeg' in p.lower()]
    return ffmpeg_paths

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='FFmpeg Checker and Updater')
    parser.add_argument('--status', action='store_true', help='Check FFmpeg status')
    parser.add_argument('--update', action='store_true', help='Update FFmpeg')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("        QuranBot FFmpeg Checker")
    print("=" * 50)
    print()
    
    # Check FFmpeg status
    is_installed, version = check_ffmpeg()
    ffmpeg_path = get_ffmpeg_path()
    
    print("🔍 FFmpeg Status Check:")
    print("-" * 30)
    
    if is_installed:
        print("✅ FFmpeg is installed!")
        print(f"📍 Location: {ffmpeg_path}")
        print(f"📋 Version: {version}")
    else:
        print("❌ FFmpeg is NOT installed or not in PATH")
    
    # Check system PATH
    print("\n🔍 System PATH entries:")
    print("-" * 30)
    ffmpeg_paths = check_system_path()
    if ffmpeg_paths:
        for path in ffmpeg_paths:
            print(f"📍 {path}")
    else:
        print("❌ No FFmpeg entries found in PATH")
    
    # Handle commands
    if args.status:
        # Status check only
        pass
    elif args.update:
        print("\n🔄 FFmpeg Update:")
        print("-" * 30)
        
        if is_installed:
            response = input("FFmpeg is already installed. Update anyway? (y/n): ")
            if response.lower() != 'y':
                print("Update cancelled.")
                return
        
        success = download_ffmpeg()
        if success:
            print("\n✅ FFmpeg update completed!")
            print("🔄 Please restart your terminal/command prompt for PATH changes to take effect.")
        else:
            print("\n❌ FFmpeg update failed!")
            sys.exit(1)
    else:
        # Interactive mode
        print("\nOptions:")
        print("1. Check status only")
        print("2. Update FFmpeg")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "2":
            print("\n🔄 FFmpeg Update:")
            print("-" * 30)
            
            if is_installed:
                response = input("FFmpeg is already installed. Update anyway? (y/n): ")
                if response.lower() != 'y':
                    print("Update cancelled.")
                    return
            
            success = download_ffmpeg()
            if success:
                print("\n✅ FFmpeg update completed!")
                print("🔄 Please restart your terminal/command prompt for PATH changes to take effect.")
            else:
                print("\n❌ FFmpeg update failed!")
                sys.exit(1)
        elif choice == "3":
            print("Goodbye!")
            return

if __name__ == "__main__":
    main() 