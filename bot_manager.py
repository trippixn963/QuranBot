#!/usr/bin/env python3
"""
QuranBot Manager - Simple utility to manage the bot instance
"""

import os
import sys
import psutil
import argparse
from pathlib import Path

def find_bot_processes():
    """Find all running QuranBot processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if (proc.info['name'] and 'python' in proc.info['name'].lower() and 
                proc.info['cmdline'] and 'run.py' in ' '.join(proc.info['cmdline'])):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes

def status():
    """Check the status of QuranBot instances."""
    processes = find_bot_processes()
    
    if not processes:
        print("🔴 No QuranBot instances running")
        return False
    
    print(f"🟢 Found {len(processes)} QuranBot instance(s):")
    for proc in processes:
        try:
            create_time = proc.create_time()
            import datetime
            start_time = datetime.datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
            memory_mb = proc.memory_info().rss / 1024 / 1024
            cpu_percent = proc.cpu_percent()
            
            print(f"  PID: {proc.pid}")
            print(f"  Started: {start_time}")
            print(f"  Memory: {memory_mb:.1f} MB")
            print(f"  CPU: {cpu_percent:.1f}%")
            print(f"  Command: {' '.join(proc.cmdline())}")
            print()
        except Exception as e:
            print(f"  PID: {proc.pid} (error getting details: {e})")
    
    return True

def start():
    """Start the QuranBot."""
    processes = find_bot_processes()
    
    if processes:
        print(f"⚠️  QuranBot is already running (PID: {processes[0].pid})")
        print("Use 'python bot_manager.py stop' to stop it first, or 'python run.py' to get the choice menu")
        return False
    
    print("🚀 Starting QuranBot...")
    os.system("python run.py")
    return True

def stop():
    """Stop all QuranBot instances."""
    processes = find_bot_processes()
    
    if not processes:
        print("🔴 No QuranBot instances found to stop")
        return True
    
    print(f"🛑 Stopping {len(processes)} QuranBot instance(s)...")
    
    for proc in processes:
        try:
            print(f"  Stopping PID {proc.pid}...")
            proc.terminate()
            proc.wait(timeout=10)
            print(f"  ✅ PID {proc.pid} stopped gracefully")
        except psutil.TimeoutExpired:
            print(f"  ⚠️  PID {proc.pid} didn't stop gracefully, force killing...")
            proc.kill()
            print(f"  ✅ PID {proc.pid} force killed")
        except Exception as e:
            print(f"  ❌ Failed to stop PID {proc.pid}: {e}")
    
    return True

def restart():
    """Restart the QuranBot."""
    print("🔄 Restarting QuranBot...")
    stop()
    import time
    time.sleep(2)  # Give it a moment to fully stop
    start()
    return True

def main():
    parser = argparse.ArgumentParser(description="QuranBot Manager")
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == 'start':
        start()
    elif args.action == 'stop':
        stop()
    elif args.action == 'restart':
        restart()
    elif args.action == 'status':
        status()

if __name__ == "__main__":
    main() 