#!/usr/bin/env python3
"""
Audio File Validation Script for QuranBot
Validates all audio files for corruption, format issues, and provides detailed reporting.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.config.config import Config

class AudioValidator:
    def __init__(self, audio_folder: Optional[str] = None):
        self.audio_folder = audio_folder or Config.AUDIO_FOLDER
        self.results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'corrupted_files': 0,
            'empty_files': 0,
            'format_errors': 0,
            'reciters': {},
            'errors': [],
            'warnings': []
        }
        
    def validate_file(self, file_path: str) -> Dict:
        """Validate a single audio file."""
        result = {
            'file': file_path,
            'valid': False,
            'size': 0,
            'duration': None,
            'codec': None,
            'bitrate': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                result['errors'].append("File does not exist")
                return result
                
            # Check file size
            file_size = os.path.getsize(file_path)
            result['size'] = file_size
            
            if file_size == 0:
                result['errors'].append("File is empty")
                return result
                
            # Validate audio format using ffprobe
            try:
                cmd = [
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', file_path
                ]
                result_probe = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result_probe.returncode != 0:
                    result['errors'].append(f"FFprobe failed: {result_probe.stderr}")
                    return result
                    
                probe_data = json.loads(result_probe.stdout)
                
                # Check for audio streams
                audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
                if not audio_streams:
                    result['errors'].append("No audio streams found")
                    return result
                    
                # Get audio stream info
                audio_stream = audio_streams[0]
                result['codec'] = audio_stream.get('codec_name')
                result['bitrate'] = audio_stream.get('bit_rate')
                
                # Get duration
                format_info = probe_data.get('format', {})
                duration = format_info.get('duration')
                if duration:
                    result['duration'] = float(duration)
                    
                # Validate duration is reasonable (between 1 second and 2 hours)
                if result['duration']:
                    if result['duration'] < 1:
                        result['warnings'].append(f"Very short duration: {result['duration']:.2f}s")
                    elif result['duration'] > 7200:  # 2 hours
                        result['warnings'].append(f"Very long duration: {result['duration']:.2f}s")
                        
                # Check for common audio codecs
                if result['codec'] not in ['mp3', 'aac', 'opus', 'flac', 'wav']:
                    result['warnings'].append(f"Unusual codec: {result['codec']}")
                    
                # File is valid if we got here
                result['valid'] = True
                
            except subprocess.TimeoutExpired:
                result['errors'].append("FFprobe timeout")
            except json.JSONDecodeError:
                result['errors'].append("Invalid JSON output from ffprobe")
            except Exception as e:
                result['errors'].append(f"FFprobe error: {str(e)}")
                
        except Exception as e:
            result['errors'].append(f"General error: {str(e)}")
            
        return result
        
    def validate_reciter_folder(self, reciter_path: str) -> Dict:
        """Validate all files in a reciter folder."""
        reciter_name = os.path.basename(reciter_path)
        reciter_results = {
            'reciter': reciter_name,
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'files': []
        }
        
        try:
            # Get all audio files
            audio_extensions = {'.mp3', '.m4a', '.aac', '.opus', '.flac', '.wav'}
            files = [f for f in os.listdir(reciter_path) 
                    if os.path.isfile(os.path.join(reciter_path, f)) and 
                    Path(f).suffix.lower() in audio_extensions]
            
            reciter_results['total_files'] = len(files)
            
            for file_name in files:
                file_path = os.path.join(reciter_path, file_name)
                file_result = self.validate_file(file_path)
                reciter_results['files'].append(file_result)
                
                if file_result['valid']:
                    reciter_results['valid_files'] += 1
                else:
                    reciter_results['invalid_files'] += 1
                    
        except Exception as e:
            reciter_results['error'] = str(e)
            
        return reciter_results
        
    def validate_all(self) -> Dict:
        """Validate all audio files in the audio folder."""
        print(f"🔍 Starting audio validation for: {self.audio_folder}")
        
        if not os.path.exists(self.audio_folder):
            self.results['errors'].append(f"Audio folder not found: {self.audio_folder}")
            return self.results
            
        try:
            # Get all reciter folders
            reciter_folders = [f for f in os.listdir(self.audio_folder) 
                             if os.path.isdir(os.path.join(self.audio_folder, f))]
            
            if not reciter_folders:
                self.results['warnings'].append("No reciter folders found")
                return self.results
                
            print(f"📁 Found {len(reciter_folders)} reciter folders")
            
            for reciter_folder in reciter_folders:
                reciter_path = os.path.join(self.audio_folder, reciter_folder)
                print(f"🎤 Validating reciter: {reciter_folder}")
                
                reciter_results = self.validate_reciter_folder(reciter_path)
                self.results['reciters'][reciter_folder] = reciter_results
                
                # Update totals
                self.results['total_files'] += reciter_results['total_files']
                self.results['valid_files'] += reciter_results['valid_files']
                self.results['invalid_files'] += reciter_results['invalid_files']
                
                # Count specific issues
                for file_result in reciter_results['files']:
                    if not file_result['valid']:
                        if file_result['size'] == 0:
                            self.results['empty_files'] += 1
                        elif 'corrupt' in ' '.join(file_result['errors']).lower():
                            self.results['corrupted_files'] += 1
                        elif 'format' in ' '.join(file_result['errors']).lower():
                            self.results['format_errors'] += 1
                            
        except Exception as e:
            self.results['errors'].append(f"Validation error: {str(e)}")
            
        return self.results
        
    def generate_report(self) -> str:
        """Generate a detailed validation report."""
        report = []
        report.append("=" * 60)
        report.append("🎵 AUDIO FILE VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"📁 Audio Folder: {self.audio_folder}")
        report.append(f"⏰ Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("📊 SUMMARY:")
        report.append(f"   Total Files: {self.results['total_files']}")
        report.append(f"   Valid Files: {self.results['valid_files']} ({self.results['valid_files']/max(self.results['total_files'], 1)*100:.1f}%)")
        report.append(f"   Invalid Files: {self.results['invalid_files']} ({self.results['invalid_files']/max(self.results['total_files'], 1)*100:.1f}%)")
        report.append(f"   Empty Files: {self.results['empty_files']}")
        report.append(f"   Corrupted Files: {self.results['corrupted_files']}")
        report.append(f"   Format Errors: {self.results['format_errors']}")
        report.append("")
        
        # Reciter details
        if self.results['reciters']:
            report.append("🎤 RECITER DETAILS:")
            for reciter_name, reciter_data in self.results['reciters'].items():
                valid_pct = reciter_data['valid_files'] / max(reciter_data['total_files'], 1) * 100
                status = "✅" if valid_pct == 100 else "⚠️" if valid_pct > 80 else "❌"
                report.append(f"   {status} {reciter_name}: {reciter_data['valid_files']}/{reciter_data['total_files']} ({valid_pct:.1f}%)")
            report.append("")
            
        # Invalid files details
        invalid_files = []
        for reciter_name, reciter_data in self.results['reciters'].items():
            for file_result in reciter_data['files']:
                if not file_result['valid']:
                    invalid_files.append((reciter_name, file_result))
                    
        if invalid_files:
            report.append("❌ INVALID FILES:")
            for reciter_name, file_result in invalid_files[:20]:  # Show first 20
                report.append(f"   {reciter_name}/{os.path.basename(file_result['file'])}:")
                for error in file_result['errors']:
                    report.append(f"     - {error}")
            if len(invalid_files) > 20:
                report.append(f"     ... and {len(invalid_files) - 20} more files")
            report.append("")
            
        # Warnings
        if self.results['warnings']:
            report.append("⚠️ WARNINGS:")
            for warning in self.results['warnings']:
                report.append(f"   - {warning}")
            report.append("")
            
        # Errors
        if self.results['errors']:
            report.append("🚨 ERRORS:")
            for error in self.results['errors']:
                report.append(f"   - {error}")
            report.append("")
            
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if self.results['invalid_files'] > 0:
            report.append("   - Fix or replace invalid audio files")
        if self.results['empty_files'] > 0:
            report.append("   - Remove empty audio files")
        if self.results['corrupted_files'] > 0:
            report.append("   - Re-download corrupted audio files")
        if self.results['format_errors'] > 0:
            report.append("   - Convert files to supported formats (MP3 recommended)")
        if self.results['valid_files'] == 0:
            report.append("   - No valid audio files found. Check audio folder path and file formats.")
        else:
            report.append("   - Audio files are ready for use")
            
        report.append("=" * 60)
        
        return "\n".join(report)
        
    def save_report(self, output_file: Optional[str] = None):
        """Save the validation report to a file."""
        if not output_file:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_file = f"audio_validation_report_{timestamp}.txt"
            
        report = self.generate_report()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Report saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")
            
    def get_invalid_files_list(self) -> List[str]:
        """Get a list of all invalid file paths."""
        invalid_files = []
        for reciter_name, reciter_data in self.results['reciters'].items():
            for file_result in reciter_data['files']:
                if not file_result['valid']:
                    invalid_files.append(file_result['file'])
        return invalid_files

def main():
    parser = argparse.ArgumentParser(description='Validate QuranBot audio files')
    parser.add_argument('--audio-folder', help='Path to audio folder (default: from config)')
    parser.add_argument('--output', help='Output file for report (default: auto-generated)')
    parser.add_argument('--list-invalid', action='store_true', help='List invalid files only')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = AudioValidator(args.audio_folder)
    
    # Run validation
    if not args.quiet:
        print("🔍 Starting audio file validation...")
        
    results = validator.validate_all()
    
    if args.list_invalid:
        invalid_files = validator.get_invalid_files_list()
        for file_path in invalid_files:
            print(file_path)
    else:
        # Generate and display report
        report = validator.generate_report()
        print(report)
        
        # Save report
        if args.output:
            validator.save_report(args.output)
        else:
            validator.save_report()

if __name__ == "__main__":
    main() 