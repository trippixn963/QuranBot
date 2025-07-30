#!/usr/bin/env python3
# =============================================================================
# QuranBot Dashboard Launcher
# =============================================================================
# Production-ready launcher for the QuranBot web dashboard
# =============================================================================

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.app import app, socketio
from dashboard.config import get_config

def setup_logging():
    """Setup logging for the dashboard"""
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Setup file handler
    file_handler = RotatingFileHandler(
        log_dir / "dashboard.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure werkzeug logger
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask',
        'flask_socketio',
        'flask_cors',
        'eventlet'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    print("✅ All dependencies are installed")

def check_data_directory():
    """Check if data directory exists and is accessible"""
    config = get_config()
    data_dir = config.DATA_DIR
    
    if not data_dir.exists():
        print(f"⚠️  Data directory not found: {data_dir}")
        print("Creating data directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check database file
    if not config.DATABASE_PATH.exists():
        print(f"⚠️  Database not found: {config.DATABASE_PATH}")
        print("The dashboard will show limited data until the bot creates the database.")
    
    print(f"📂 Data directory: {data_dir}")
    print(f"🗄️  Database: {config.DATABASE_PATH}")

def print_startup_banner():
    """Print beautiful startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                    🕌 QuranBot Dashboard                      ║
    ║                                                              ║
    ║              بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيْمِ                ║
    ║          In the name of Allah, Most Gracious, Most Merciful  ║
    ║                                                              ║
    ║              Serving the Islamic Community with              ║
    ║                 Beautiful Web Dashboard                      ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_dashboard_info(config):
    """Print dashboard information"""
    print(f"🌐 Dashboard URL: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    print(f"🔄 Update Interval: {config.REFRESH_INTERVAL} seconds")
    print(f"📊 Environment: {'Development' if config.DEBUG else 'Production'}")
    print(f"🔒 CORS Origins: {', '.join(config.CORS_ORIGINS) if hasattr(config, 'CORS_ORIGINS') else '*'}")
    print(f"🕌 Islamic Features: {'Enabled' if hasattr(config, 'SHOW_ARABIC_TEXT') and config.SHOW_ARABIC_TEXT else 'Disabled'}")

def main():
    """Main dashboard launcher"""
    parser = argparse.ArgumentParser(description='QuranBot Dashboard Launcher')
    parser.add_argument('--host', default=None, help='Host to bind to')
    parser.add_argument('--port', type=int, default=None, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--env', choices=['development', 'production', 'testing'], 
                       default=None, help='Environment configuration')
    parser.add_argument('--no-checks', action='store_true', help='Skip dependency and data checks')
    
    args = parser.parse_args()
    
    # Set environment
    if args.env:
        os.environ['FLASK_ENV'] = args.env
    
    # Get configuration
    config_class = get_config(args.env)
    config = config_class()
    
    # Override with command line arguments
    if args.host:
        config.DASHBOARD_HOST = args.host
    if args.port:
        config.DASHBOARD_PORT = args.port
    if args.debug:
        config.DEBUG = True
    
    # Print startup banner
    print_startup_banner()
    
    # Setup logging
    setup_logging()
    
    # Run checks unless disabled
    if not args.no_checks:
        print("🔍 Running pre-flight checks...")
        check_dependencies()
        check_data_directory()
        print("✅ Pre-flight checks completed\n")
    
    # Print dashboard info
    print_dashboard_info(config)
    print()
    
    # Configure Flask app
    app.config.from_object(config)
    
    # Add security headers for production
    if not config.DEBUG and hasattr(config, 'SECURITY_HEADERS'):
        @app.after_request
        def add_security_headers(response):
            for header, value in config.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response
    
    try:
        print("🚀 Starting QuranBot Dashboard...")
        print("Press Ctrl+C to stop the dashboard\n")
        
        # Run the dashboard
        socketio.run(
            app,
            host=config.DASHBOARD_HOST,
            port=config.DASHBOARD_PORT,
            debug=config.DEBUG,
            use_reloader=config.DEBUG,
            log_output=True,
            allow_unsafe_werkzeug=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard shutdown requested by user")
    except Exception as e:
        print(f"\n❌ Dashboard startup failed: {e}")
        sys.exit(1)
    finally:
        print("🕌 May Allah accept this work. Dashboard stopped.")

if __name__ == '__main__':
    main()