# =============================================================================
# QuranBot - Tree Style Logging Module
# =============================================================================
# Provides tree-style logging with symbols for clean, structured output
# Includes timestamp formatting with EST timezone
# =============================================================================

from datetime import datetime
import pytz
import os
import json
from pathlib import Path
import secrets

def get_timestamp():
    """Get current timestamp in EST timezone with custom format"""
    try:
        # Create EST timezone
        est = pytz.timezone('US/Eastern')
        # Get current time in EST
        now_est = datetime.now(est)
        # Format as MM/DD HH:MM AM/PM EST
        formatted_time = now_est.strftime('%m/%d %I:%M %p EST')
        return f"[{formatted_time}]"
    except ImportError:
        # Fallback if pytz is not available
        now = datetime.now()
        formatted_time = now.strftime('%m/%d %I:%M %p')
        return f"[{formatted_time}]"
    except Exception:
        # Fallback if timezone handling fails
        now = datetime.now()
        formatted_time = now.strftime('%m/%d %I:%M %p')
        return f"[{formatted_time}]"

def get_log_date():
    """Get current date for log file naming (YYYY-MM-DD format)"""
    try:
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        return now_est.strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

def generate_run_id():
    """Generate a unique run ID for each bot instance"""
    return secrets.token_hex(4).upper()

def setup_log_directories():
    """Create log directory structure for today"""
    try:
        log_date = get_log_date()
        log_dir = Path(f"logs/{log_date}")
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception as e:
        print(f"Warning: Could not create log directory: {e}")
        return None

def get_current_datetime_iso():
    """Get current datetime in ISO format for JSON logs"""
    try:
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        return now_est.isoformat()
    except:
        return datetime.now().isoformat()

def write_to_log_files(message, level="INFO", log_type="general"):
    """Write log message to appropriate files"""
    try:
        log_dir = setup_log_directories()
        if not log_dir:
            return
        
        log_date = get_log_date()
        timestamp_iso = get_current_datetime_iso()
        
        # Prepare log entry
        log_entry = {
            "timestamp": timestamp_iso,
            "level": level,
            "type": log_type,
            "message": message
        }
        
        # Write to main log file (.log)
        try:
            main_log_file = log_dir / f"{log_date}.log"
            with open(main_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{get_timestamp()} {message}\n")
        except Exception as e:
            print(f"Warning: Could not write to main log file: {e}")
        
        # Write to JSON log file (.json)
        try:
            json_log_file = log_dir / f"{log_date}.json"
            with open(json_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Warning: Could not write to JSON log file: {e}")
        
        # Write to error log if it's an error
        if level.upper() in ['ERROR', 'CRITICAL', 'EXCEPTION', 'WARNING']:
            try:
                error_log_file = log_dir / f"{log_date}-errors.log"
                with open(error_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{get_timestamp()} {message}\n")
            except Exception as e:
                print(f"Warning: Could not write to error log file: {e}")
                
    except Exception as e:
        # Don't let logging errors crash the application
        print(f"Warning: Could not write to log files: {e}")

def log_run_separator():
    """Create a visual separator for new runs"""
    separator_line = "=" * 80
    timestamp = get_timestamp()
    
    # Print separator to console
    print(f"\n{separator_line}")
    print(f"{timestamp} 🚀 NEW BOT RUN STARTED")
    print(f"{separator_line}")
    
    # Write separator to log files
    write_to_log_files("", "INFO", "run_separator")
    write_to_log_files(separator_line, "INFO", "run_separator")
    write_to_log_files("🚀 NEW BOT RUN STARTED", "INFO", "run_separator")
    write_to_log_files(separator_line, "INFO", "run_separator")

def log_run_header(bot_name, version, run_id=None):
    """Log run header with bot info and unique run ID"""
    if run_id is None:
        run_id = generate_run_id()
    
    timestamp = get_timestamp()
    
    # Create run header
    header_info = [
        f"🎯 {bot_name} v{version} - Run ID: {run_id}",
        f"├─ started_at: {timestamp}",
        f"├─ version: {version}",
        f"├─ run_id: {run_id}",
        f"└─ log_session: {get_log_date()}"
    ]
    
    # Print to console
    for line in header_info:
        print(f"{timestamp} {line}")
    
    # Write to log files
    for line in header_info:
        write_to_log_files(line, "INFO", "run_header")
    
    return run_id

def log_run_end(run_id, reason="Normal shutdown"):
    """Log run end with run ID and reason"""
    timestamp = get_timestamp()
    
    end_info = [
        f"🏁 Bot Run Ended - Run ID: {run_id}",
        f"├─ ended_at: {timestamp}",
        f"├─ run_id: {run_id}",
        f"└─ reason: {reason}"
    ]
    
    # Print to console
    for line in end_info:
        print(f"{timestamp} {line}")
    
    # Write to log files
    for line in end_info:
        write_to_log_files(line, "INFO", "run_end")
    
    # Add spacing after run end
    print()
    write_to_log_files("", "INFO", "run_end")

def log_tree(message, level="INFO"):
    """Tree-style logging with symbols"""
    timestamp = get_timestamp()
    formatted_message = f"├─ {level}: {message}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, level, "tree")

def log_tree_end(message, level="INFO"):
    """Tree-style logging with end symbol"""
    timestamp = get_timestamp()
    formatted_message = f"└─ {level}: {message}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, level, "tree_end")

def log_tree_branch(key, value):
    """Tree-style logging for key-value pairs"""
    timestamp = get_timestamp()
    formatted_message = f"├─ {key}: {value}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, "INFO", "tree_branch")

def log_tree_final(key, value):
    """Tree-style logging for final key-value pair"""
    timestamp = get_timestamp()
    formatted_message = f"└─ {key}: {value}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, "INFO", "tree_final")

def log_section_start(title, emoji="🎯"):
    """Start a new section with emoji and title"""
    timestamp = get_timestamp()
    formatted_message = f"{emoji} {title}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, "INFO", "section_start")

def log_progress(current, total, emoji="🎶"):
    """Log progress with current/total format"""
    timestamp = get_timestamp()
    formatted_message = f"{emoji} Progress ({current}/{total})"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, "INFO", "progress")

def log_status(message, status="INFO", emoji="📍"):
    """Log status with emoji and message"""
    timestamp = get_timestamp()
    formatted_message = f"{emoji} {message}"
    print(f"{timestamp} {formatted_message}")
    write_to_log_files(formatted_message, status, "status")
    if status != "INFO":
        log_tree_end(f"Status: {status}", status)

def log_version_info(bot_name, version, additional_info=None):
    """Log version information in a structured format"""
    log_section_start(f"{bot_name} Version Information", "📋")
    log_tree_branch("name", bot_name)
    log_tree_branch("version", version)
    log_tree_branch("changelog", "See CHANGELOG.md for details")
    if additional_info:
        for key, value in additional_info.items():
            log_tree_branch(key, value)
    log_tree_end("Version info complete", "SUCCESS") 