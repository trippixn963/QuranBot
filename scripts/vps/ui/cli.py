"""
Command-line interface for QuranBot VPS Management
"""

import sys
import argparse
from typing import List
from ..core import VPSManager, LogManager, BackupManager

def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="QuranBot VPS Management CLI")
    
    # Create subparsers for different command groups
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Bot control commands
    bot_parser = subparsers.add_parser('bot', help='Bot control commands')
    bot_subparsers = bot_parser.add_subparsers(dest='subcommand')
    
    bot_subparsers.add_parser('start', help='Start the bot')
    bot_subparsers.add_parser('stop', help='Stop the bot')
    bot_subparsers.add_parser('restart', help='Restart the bot')
    bot_subparsers.add_parser('status', help='Show bot status')
    
    # Log commands
    log_parser = subparsers.add_parser('logs', help='Log management commands')
    log_subparsers = log_parser.add_subparsers(dest='subcommand')
    
    view_parser = log_subparsers.add_parser('view', help='View logs')
    view_parser.add_argument('--lines', type=int, default=50, help='Number of lines to show')
    
    download_parser = log_subparsers.add_parser('download', help='Download logs')
    download_parser.add_argument('--date', help='Date in YYYY-MM-DD format')
    
    analyze_parser = log_subparsers.add_parser('analyze', help='Analyze logs')
    analyze_parser.add_argument('--date', help='Date in YYYY-MM-DD format')
    analyze_parser.add_argument('--lines', type=int, default=1000, help='Number of lines to analyze')
    
    cleanup_parser = log_subparsers.add_parser('cleanup', help='Clean up old logs')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete logs older than days')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Backup management commands')
    backup_subparsers = backup_parser.add_subparsers(dest='subcommand')
    
    create_parser = backup_subparsers.add_parser('create', help='Create backup')
    create_parser.add_argument('--name', help='Backup name')
    create_parser.add_argument('--include-logs', action='store_true', help='Include log files')
    
    backup_subparsers.add_parser('list', help='List backups')
    
    restore_parser = backup_subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('name', help='Backup name to restore')
    
    download_backup_parser = backup_subparsers.add_parser('download', help='Download backup')
    download_backup_parser.add_argument('name', help='Backup name to download')
    
    cleanup_backup_parser = backup_subparsers.add_parser('cleanup', help='Clean up old backups')
    cleanup_backup_parser.add_argument('--days', type=int, default=30, help='Delete backups older than days')
    
    return parser.parse_args(args)

def main():
    """Main entry point"""
    args = parse_args(sys.argv[1:])
    
    # Initialize managers
    vps = VPSManager()
    log_mgr = LogManager(vps)
    backup_mgr = BackupManager(vps)
    
    if args.command == 'bot':
        if args.subcommand == 'start':
            vps.start_bot()
        elif args.subcommand == 'stop':
            vps.stop_bot()
        elif args.subcommand == 'restart':
            vps.restart_bot()
        elif args.subcommand == 'status':
            status = vps.get_status()
            print("\n📊 Bot Status:")
            print(f"Running: {'✅' if status['running'] else '❌'}")
            if status['running']:
                print(f"CPU Usage: {status.get('cpu_usage', 'N/A')}%")
                print(f"Memory Usage: {status.get('memory_usage', 'N/A')}%")
                if status.get('errors'):
                    print("\nRecent Errors:")
                    for error in status['errors'][-3:]:
                        print(f"  ❌ {error}")
    
    elif args.command == 'logs':
        if args.subcommand == 'view':
            vps.stream_logs(args.lines)
        elif args.subcommand == 'download':
            log_mgr.download_logs(args.date)
        elif args.subcommand == 'analyze':
            analysis = log_mgr.analyze_logs(args.date, args.lines)
            report_file = log_mgr.generate_report(analysis)
            print(f"\n📋 Analysis report saved to: {report_file}")
        elif args.subcommand == 'cleanup':
            log_mgr.cleanup_old_logs(args.days)
    
    elif args.command == 'backup':
        if args.subcommand == 'create':
            backup_mgr.create_backup(args.name, args.include_logs)
        elif args.subcommand == 'list':
            backup_mgr.list_backups()
        elif args.subcommand == 'restore':
            backup_mgr.restore_backup(args.name)
        elif args.subcommand == 'download':
            backup_mgr.download_backup(args.name)
        elif args.subcommand == 'cleanup':
            backup_mgr.cleanup_old_backups(args.days)
    
    else:
        print("❌ No command specified. Use --help to see available commands.")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1) 