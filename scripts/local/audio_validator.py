#!/usr/bin/env python3
"""
QuranBot Audio Validator
Validates MP3 files using FFmpeg to check for corruption.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from src.monitoring.logging.tree_log import tree_log
import traceback

def check_ffmpeg():
    """Check if FFmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def validate_mp3_file(file_path):
    """Validate a single MP3 file using FFmpeg."""
    try:
        result = subprocess.run([
            'ffmpeg', '-v', 'error', '-i', str(file_path), 
            '-f', 'null', '-'
        ], capture_output=True, text=True, timeout=30)
        
        return result.returncode == 0, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Validation timed out"
    except Exception as e:
        tree_log('error', 'Error validating audio file', {'error': str(e), 'traceback': traceback.format_exc()})
        return False, str(e)

def find_mp3_files(audio_dir):
    """Find all MP3 files in the audio directory."""
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        return []
    
    return list(audio_path.rglob("*.mp3"))

def validate_audio_files(audio_dir, output_file=None):
    """Validate all MP3 files in the audio directory."""
    print("🔍 Checking for FFmpeg...")
    
    if not check_ffmpeg():
        print("❌ FFmpeg not found!")
        print("💡 Please run the FFmpeg checker first or install FFmpeg manually.")
        return False
    
    print("✅ FFmpeg found!")
    
    # Find MP3 files
    mp3_files = find_mp3_files(audio_dir)
    if not mp3_files:
        print(f"❌ No MP3 files found in: {audio_dir}")
        return False
    
    print(f"📁 Found {len(mp3_files)} MP3 files to validate")
    print()
    
    # Validate files
    bad_files = []
    checked_count = 0
    
    for file_path in mp3_files:
        checked_count += 1
        print(f"🔍 Checking ({checked_count}/{len(mp3_files)}): {file_path.name}")
        
        is_valid, error_msg = validate_mp3_file(file_path)
        
        if is_valid:
            print(f"✅ OK: {file_path.name}")
        else:
            print(f"❌ Corrupt: {file_path.name}")
            bad_files.append((file_path, error_msg))
    
    # Summary
    print()
    print("=" * 50)
    print("           Validation Summary")
    print("=" * 50)
    print(f"📊 Total files checked: {checked_count}")
    print(f"✅ Valid files: {checked_count - len(bad_files)}")
    print(f"❌ Corrupt files: {len(bad_files)}")
    
    # Write bad files to log
    if bad_files and output_file:
        print(f"\n📝 Writing corrupt files to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Audio Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            for file_path, error_msg in bad_files:
                f.write(f"File: {file_path}\n")
                f.write(f"Error: {error_msg}\n")
                f.write("-" * 30 + "\n")
    
    if bad_files:
        print(f"\n⚠️  Found {len(bad_files)} corrupt files!")
        if output_file:
            print(f"📄 See {output_file} for details.")
        return False
    else:
        print("\n✅ All files are valid!")
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Audio File Validator')
    parser.add_argument('--audio-dir', default='../audio', 
                       help='Audio directory path (default: ../audio)')
    parser.add_argument('--output', default='bad_mp3s.txt',
                       help='Output file for corrupt files (default: bad_mp3s.txt)')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("        QuranBot Audio Validator")
    print("=" * 50)
    print()
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    audio_dir = project_root / args.audio_dir.lstrip('./').lstrip('../')
    
    print(f"📁 Audio directory: {audio_dir}")
    print(f"📄 Output file: {args.output}")
    print()
    
    if not audio_dir.exists():
        print(f"❌ Audio directory not found: {audio_dir}")
        sys.exit(1)
    
    success = validate_audio_files(audio_dir, args.output)
    
    if success:
        print("\n✅ Validation completed successfully!")
    else:
        print("\n❌ Validation found issues!")
        sys.exit(1)

if __name__ == "__main__":
    main() 