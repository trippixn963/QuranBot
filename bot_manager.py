# =============================================================================
# QuranBot - Bot Manager Utility
# =============================================================================
# Easy management of bot instances with start, stop, restart, and status commands
# =============================================================================

import sys
import os
import psutil
import subprocess
import time
import signal

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import logging utilities
from utils.tree_log import log_section_start, log_tree_branch, log_tree_final

BOT_NAME = "QuranBot"
MAIN_SCRIPT = "main.py"

def find_bot_processes():
    """Find all running bot processes."""
    current_pid = os.getpid()
    bot_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                
                # Check if it's a Python process (including virtual environments)
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        # Check if it's running main.py and verify it's in QuranBot directory
                        if 'main.py' in cmdline_str:
                            # Additional verification: check working directory
                            try:
                                proc_cwd = proc.cwd()
                                if 'QuranBot' in proc_cwd:
                                    # Extra verification for virtual environments
                                    # Check if it's running from the same project directory
                                    current_cwd = os.getcwd()
                                    if os.path.normpath(proc_cwd) == os.path.normpath(current_cwd):
                                        bot_processes.append(proc)
                                    elif 'QuranBot' in proc_cwd:
                                        # Regular QuranBot process
                                        bot_processes.append(proc)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # If we can't get cwd, skip this process for safety
                                pass
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        log_tree_branch("error", f"Failed to scan processes: {e}")
        
    return bot_processes

def format_uptime(seconds):
    """Format uptime in a human-readable way."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def status_command():
    """Check the status of bot instances."""
    log_section_start("Bot Status Check", "📊")
    
    bot_processes = find_bot_processes()
    
    if not bot_processes:
        log_tree_branch("status", "No bot instances running")
        log_tree_final("result", "✅ Bot is offline")
        return False
    
    log_tree_branch("instances_found", f"{len(bot_processes)} instance(s)")
    
    for i, proc in enumerate(bot_processes, 1):
        try:
            # Get process information
            create_time = proc.create_time()
            uptime = time.time() - create_time
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            log_tree_branch(f"instance_{i}", f"PID {proc.pid}")
            log_tree_branch(f"  uptime", format_uptime(uptime))
            log_tree_branch(f"  memory", f"{memory_mb:.1f} MB")
            log_tree_branch(f"  command", ' '.join(proc.cmdline()))
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log_tree_branch(f"instance_{i}", f"PID {proc.pid} - Error: {e}")
    
    log_tree_final("result", "🟢 Bot is online")
    return True

def start_command():
    """Start the bot."""
    log_section_start("Starting Bot", "🚀")
    
    # Check if already running
    if find_bot_processes():
        log_tree_branch("error", "Bot is already running")
        log_tree_final("status", "❌ Use 'restart' to restart or 'stop' to stop first")
        return False
    
    log_tree_branch("command", f"python {MAIN_SCRIPT}")
    log_tree_branch("mode", "Background process")
    
    try:
        # Start the bot in the background
        if os.name == 'nt':  # Windows
            subprocess.Popen([sys.executable, MAIN_SCRIPT], 
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:  # Unix-like
            subprocess.Popen([sys.executable, MAIN_SCRIPT], 
                           start_new_session=True)
        
        # Wait a moment and check if it started
        time.sleep(3)
        
        if find_bot_processes():
            log_tree_final("status", "✅ Bot started successfully")
            return True
        else:
            log_tree_final("status", "❌ Bot failed to start")
            return False
            
    except Exception as e:
        log_tree_branch("error", str(e))
        log_tree_final("status", "❌ Failed to start bot")
        return False

def stop_command():
    """Stop all bot instances."""
    log_section_start("Stopping Bot", "🛑")
    
    bot_processes = find_bot_processes()
    
    if not bot_processes:
        log_tree_branch("status", "No bot instances running")
        log_tree_final("result", "✅ Bot is already offline")
        return True
    
    log_tree_branch("instances_found", f"{len(bot_processes)} instance(s)")
    
    stopped_count = 0
    failed_count = 0
    
    for proc in bot_processes:
        try:
            log_tree_branch("stopping", f"PID {proc.pid}")
            
            # First try graceful termination
            proc.terminate()
            
            # Wait up to 5 seconds for graceful shutdown
            try:
                proc.wait(timeout=5)
                log_tree_branch("result", f"PID {proc.pid} - Gracefully stopped")
                stopped_count += 1
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                log_tree_branch("forcing", f"PID {proc.pid} - Force killing")
                proc.kill()
                proc.wait(timeout=3)
                log_tree_branch("result", f"PID {proc.pid} - Force killed")
                stopped_count += 1
                
        except psutil.NoSuchProcess:
            log_tree_branch("result", f"PID {proc.pid} - Already stopped")
            stopped_count += 1
        except psutil.AccessDenied:
            log_tree_branch("result", f"PID {proc.pid} - Access denied")
            failed_count += 1
        except Exception as e:
            log_tree_branch("result", f"PID {proc.pid} - Error: {e}")
            failed_count += 1
    
    if failed_count == 0:
        log_tree_final("status", f"✅ All {stopped_count} instances stopped")
        return True
    else:
        log_tree_final("status", f"⚠️ {stopped_count} stopped, {failed_count} failed")
        return False

def restart_command():
    """Restart the bot."""
    log_section_start("Restarting Bot", "🔄")
    
    log_tree_branch("step_1", "Stopping existing instances")
    stop_success = stop_command()
    
    if stop_success:
        log_tree_branch("step_2", "Starting new instance")
        time.sleep(2)  # Wait a moment between stop and start
        start_success = start_command()
        
        if start_success:
            log_tree_final("status", "✅ Bot restarted successfully")
            return True
        else:
            log_tree_final("status", "❌ Failed to start after stop")
            return False
    else:
        log_tree_final("status", "❌ Failed to stop existing instances")
        return False

def show_help():
    """Show help information."""
    print(f"""
# =============================================================================
# {BOT_NAME} - Bot Manager
# =============================================================================

Usage: python bot_manager.py <command>

Commands:
  start     Start the bot in the background
  stop      Stop all bot instances
  restart   Restart the bot (stop + start)
  status    Check bot status and uptime
  help      Show this help message

Examples:
  python bot_manager.py start
  python bot_manager.py status
  python bot_manager.py restart
  python bot_manager.py stop

# =============================================================================
""")

def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) != 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        start_command()
    elif command == 'stop':
        stop_command()
    elif command == 'restart':
        restart_command()
    elif command == 'status':
        status_command()
    elif command == 'help':
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main() 