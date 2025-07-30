# =============================================================================
# QuranBot Dashboard Configuration
# =============================================================================
# Configuration settings for the QuranBot web dashboard
# =============================================================================

import os
from pathlib import Path

# =============================================================================
# Base Configuration
# =============================================================================

class Config:
    """Base configuration class"""
    
    # Flask Settings
    SECRET_KEY = os.getenv('DASHBOARD_SECRET_KEY', 'quranbot-dashboard-dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Dashboard Settings
    DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 5000))
    
    # Data Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATABASE_PATH = DATA_DIR / "quranbot.db"
    METRICS_FILE = DATA_DIR / "discord_api_monitor.json"
    
    # Update Intervals (seconds)
    REFRESH_INTERVAL = int(os.getenv('DASHBOARD_REFRESH_INTERVAL', 5))
    API_TIMEOUT = int(os.getenv('DASHBOARD_API_TIMEOUT', 30))
    
    # Chart Settings
    MAX_HISTORY_POINTS = int(os.getenv('DASHBOARD_MAX_HISTORY', 100))
    CHART_UPDATE_INTERVAL = int(os.getenv('CHART_UPDATE_INTERVAL', 15))
    
    # WebSocket Settings
    SOCKET_IO_ASYNC_MODE = 'threading'
    SOCKET_IO_CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Islamic Features
    SHOW_ARABIC_TEXT = os.getenv('SHOW_ARABIC_TEXT', 'True').lower() == 'true'
    SHOW_HIJRI_DATE = os.getenv('SHOW_HIJRI_DATE', 'True').lower() == 'true'
    
    # Security Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'False').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '100 per hour')

# =============================================================================
# Environment-Specific Configurations
# =============================================================================

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DASHBOARD_HOST = '127.0.0.1'
    REFRESH_INTERVAL = 2  # Faster updates in development

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.getenv('DASHBOARD_SECRET_KEY')  # Must be set in production
    RATE_LIMIT_ENABLED = True
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:;"
    }

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_PATH = ":memory:"  # In-memory database for testing

# =============================================================================
# Configuration Factory
# =============================================================================

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])

# =============================================================================
# Dashboard Themes
# =============================================================================

DASHBOARD_THEMES = {
    'default': {
        'name': 'Default Islamic',
        'primary_color': '#1ABC9C',
        'secondary_color': '#16A085',
        'accent_color': '#E74C3C',
        'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
    },
    'ramadan': {
        'name': 'Ramadan Night',
        'primary_color': '#8E44AD',
        'secondary_color': '#9B59B6',
        'accent_color': '#F39C12',
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    'hajj': {
        'name': 'Hajj Gold',
        'primary_color': '#F39C12',
        'secondary_color': '#E67E22',
        'accent_color': '#27AE60',
        'background': 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)'
    }
}

# =============================================================================
# Islamic Configuration
# =============================================================================

ISLAMIC_CONFIG = {
    # Arabic font settings
    'arabic_font': 'Amiri, Traditional Arabic, serif',
    'arabic_font_size': '1.2em',
    
    # Islamic greetings
    'greetings': [
        {'arabic': 'السَّلاَمُ عَلَيْكُمْ', 'english': 'Peace be upon you'},
        {'arabic': 'بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيْمِ', 'english': 'In the name of Allah, the Most Gracious, the Most Merciful'},
        {'arabic': 'الْحَمْدُ لِلّهِ رَبِّ الْعَالَمِينَ', 'english': 'All praise is for Allah, Lord of all the worlds'}
    ],
    
    # Prayer times API (if needed)
    'prayer_times_api': os.getenv('PRAYER_TIMES_API', 'http://api.aladhan.com/v1/timings'),
    'default_city': os.getenv('DEFAULT_CITY', 'Mecca'),
    'default_country': os.getenv('DEFAULT_COUNTRY', 'Saudi Arabia'),
    
    # Hijri calendar
    'hijri_adjustment': int(os.getenv('HIJRI_ADJUSTMENT', 0)),  # Days to adjust
    
    # Islamic content validation
    'require_arabic_content': os.getenv('REQUIRE_ARABIC_CONTENT', 'True').lower() == 'true',
    'validate_quran_references': os.getenv('VALIDATE_QURAN_REFERENCES', 'True').lower() == 'true',
}

# =============================================================================
# Monitoring Configuration
# =============================================================================

MONITORING_CONFIG = {
    # Performance thresholds
    'response_time_warning': float(os.getenv('RESPONSE_TIME_WARNING', 500)),  # ms
    'response_time_critical': float(os.getenv('RESPONSE_TIME_CRITICAL', 1000)),  # ms
    'error_rate_warning': float(os.getenv('ERROR_RATE_WARNING', 5)),  # percentage
    'error_rate_critical': float(os.getenv('ERROR_RATE_CRITICAL', 10)),  # percentage
    
    # Data retention
    'metrics_retention_days': int(os.getenv('METRICS_RETENTION_DAYS', 30)),
    'activity_retention_days': int(os.getenv('ACTIVITY_RETENTION_DAYS', 7)),
    
    # Alert settings
    'enable_alerts': os.getenv('ENABLE_ALERTS', 'False').lower() == 'true',
    'alert_webhook_url': os.getenv('ALERT_WEBHOOK_URL', ''),
    'alert_cooldown_minutes': int(os.getenv('ALERT_COOLDOWN_MINUTES', 15)),
}

# =============================================================================
# Feature Flags
# =============================================================================

FEATURE_FLAGS = {
    'show_performance_charts': os.getenv('SHOW_PERFORMANCE_CHARTS', 'True').lower() == 'true',
    'show_leaderboard': os.getenv('SHOW_LEADERBOARD', 'True').lower() == 'true',
    'show_activity_feed': os.getenv('SHOW_ACTIVITY_FEED', 'True').lower() == 'true',
    'enable_real_time_updates': os.getenv('ENABLE_REAL_TIME_UPDATES', 'True').lower() == 'true',
    'enable_islamic_features': os.getenv('ENABLE_ISLAMIC_FEATURES', 'True').lower() == 'true',
    'enable_advanced_analytics': os.getenv('ENABLE_ADVANCED_ANALYTICS', 'False').lower() == 'true',
    'enable_user_management': os.getenv('ENABLE_USER_MANAGEMENT', 'False').lower() == 'true',
}