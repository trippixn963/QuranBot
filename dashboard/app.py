# =============================================================================
# QuranBot - Web Dashboard Application
# =============================================================================
# Beautiful, responsive web dashboard for QuranBot monitoring and management
# Features real-time metrics, Islamic design, and comprehensive bot control
# =============================================================================

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sqlite3

# =============================================================================
# Flask Application Setup
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('DASHBOARD_SECRET_KEY', 'quranbot-dashboard-dev-key')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "quranbot.db"
METRICS_FILE = DATA_DIR / "discord_api_monitor.json"

# Dashboard settings
REFRESH_INTERVAL = 5  # seconds
MAX_HISTORY_POINTS = 100

# =============================================================================
# Database Helper Functions
# =============================================================================

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_actual_bot_status():
    """Get actual bot status with multiple verification methods"""
    try:
        status_indicators = {
            'metrics_file_exists': False,
            'metrics_file_recent': False,
            'gateway_connected': False,
            'recent_database_activity': False,
            'last_activity_time': None
        }
        
        # 1. Check metrics file existence and freshness
        if METRICS_FILE.exists():
            status_indicators['metrics_file_exists'] = True
            file_time = datetime.fromtimestamp(METRICS_FILE.stat().st_mtime, tz=UTC)
            time_diff = datetime.now(UTC) - file_time
            status_indicators['last_activity_time'] = file_time.isoformat()
            
            # If metrics file is newer than 2 minutes, consider it recent
            if time_diff.total_seconds() <= 120:
                status_indicators['metrics_file_recent'] = True
                
                # Check gateway connection in metrics file
                try:
                    with open(METRICS_FILE, 'r') as f:
                        metrics_data = json.load(f)
                    
                    recent_health = metrics_data.get('health_history', [])
                    if recent_health:
                        latest_health = recent_health[-1]
                        status_indicators['gateway_connected'] = latest_health.get('gateway_connected', False)
                except:
                    pass
        
        # 2. Check database for recent activity
        try:
            with get_db_connection() as conn:
                # Check for recent system events (within last 5 minutes)
                recent_events = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM system_events 
                    WHERE timestamp > datetime('now', '-5 minutes')
                """).fetchone()
                
                if recent_events and recent_events['count'] > 0:
                    status_indicators['recent_database_activity'] = True
                
                # Check bot statistics last update
                bot_stats = conn.execute("SELECT last_startup FROM bot_statistics WHERE id = 1").fetchone()
                if bot_stats and bot_stats['last_startup']:
                    startup_time = datetime.fromisoformat(bot_stats['last_startup'].replace('Z', '+00:00'))
                    if (datetime.now(UTC) - startup_time).total_seconds() < 300:  # Started within 5 minutes
                        status_indicators['recent_database_activity'] = True
        except Exception as e:
            print(f"Error checking database activity: {e}")
        
        # 3. Determine final status based on multiple indicators
        if (status_indicators['metrics_file_recent'] and 
            status_indicators['gateway_connected']):
            return 'online', status_indicators
        elif status_indicators['recent_database_activity']:
            return 'starting', status_indicators  # Bot is starting up
        else:
            return 'offline', status_indicators
            
    except Exception as e:
        print(f"Error checking bot status: {e}")
        return 'offline', {}

def get_accurate_bot_statistics():
    """Get comprehensive and accurate bot statistics from database"""
    try:
        with get_db_connection() as conn:
            # Get actual bot statistics
            bot_stats = conn.execute("SELECT * FROM bot_statistics WHERE id = 1").fetchone()
            
            # Get actual quiz statistics  
            quiz_stats = conn.execute("SELECT * FROM quiz_statistics WHERE id = 1").fetchone()
            
            # Get user count from quiz participants
            user_count = conn.execute("SELECT COUNT(*) as count FROM user_quiz_stats").fetchone()
            
            # Get recent system events for activity
            recent_events = conn.execute("""
                SELECT event_type, event_data, severity, timestamp 
                FROM system_events 
                ORDER BY timestamp DESC 
                LIMIT 10
            """).fetchall()
            
            # Get leaderboard data
            leaderboard = conn.execute("""
                SELECT display_name, username, points, correct_answers, total_attempts, best_streak
                FROM user_quiz_stats 
                ORDER BY points DESC 
                LIMIT 10
            """).fetchall()
            
            # Calculate accuracy rates
            total_attempts = quiz_stats['total_attempts'] if quiz_stats else 0
            correct_answers = quiz_stats['correct_answers'] if quiz_stats else 0
            accuracy = (correct_answers / total_attempts * 100) if total_attempts > 0 else 0
            
            return {
                'bot_stats': {
                    'total_runtime_hours': bot_stats['total_runtime_hours'] if bot_stats else 0,
                    'total_sessions': bot_stats['total_sessions'] if bot_stats else 0,
                    'total_completed_sessions': bot_stats['total_completed_sessions'] if bot_stats else 0,
                    'last_startup': bot_stats['last_startup'] if bot_stats else None,
                    'last_shutdown': bot_stats['last_shutdown'] if bot_stats else None,
                    'favorite_reciter': bot_stats['favorite_reciter'] if bot_stats else 'Unknown'
                },
                'quiz_stats': {
                    'questions_sent': quiz_stats['questions_sent'] if quiz_stats else 0,
                    'total_attempts': total_attempts,
                    'correct_answers': correct_answers,
                    'unique_participants': quiz_stats['unique_participants'] if quiz_stats else 0,
                    'accuracy_percentage': round(accuracy, 1),
                    'last_reset': quiz_stats['last_reset'] if quiz_stats else None
                },
                'user_count': user_count['count'] if user_count else 0,
                'recent_events': [
                    {
                        'event_type': event['event_type'],
                        'event_data': event['event_data'],
                        'severity': event['severity'],
                        'timestamp': event['timestamp']
                    } for event in recent_events
                ] if recent_events else [],
                'leaderboard': [
                    {
                        'display_name': user['display_name'] or user['username'] or 'Unknown',
                        'points': user['points'],
                        'correct_answers': user['correct_answers'],
                        'total_attempts': user['total_attempts'],
                        'best_streak': user['best_streak'],
                        'accuracy': round((user['correct_answers'] / user['total_attempts'] * 100) if user['total_attempts'] > 0 else 0, 1)
                    } for user in leaderboard
                ] if leaderboard else []
            }
            
    except Exception as e:
        print(f"Error fetching bot statistics: {e}")
        import traceback
        traceback.print_exc()
        return {
            'bot_stats': {},
            'quiz_stats': {},
            'user_count': 0,
            'recent_events': [],
            'leaderboard': []
        }

def get_bot_statistics():
    """Get comprehensive bot statistics"""
    try:
        with get_db_connection() as conn:
            # Check if tables exist first
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [table[0] for table in tables]
            
            bot_stats = {}
            quiz_stats = {}
            user_count = 0
            top_users = []
            recent_events = []
            
            # Bot runtime stats
            if 'bot_statistics' in table_names:
                bot_stats_row = conn.execute(
                    "SELECT * FROM bot_statistics WHERE id = 1"
                ).fetchone()
                if bot_stats_row:
                    bot_stats = dict(bot_stats_row)
            
            # Quiz statistics
            if 'quiz_statistics' in table_names:
                quiz_stats_row = conn.execute(
                    "SELECT * FROM quiz_statistics WHERE id = 1"
                ).fetchone()
                if quiz_stats_row:
                    quiz_stats = dict(quiz_stats_row)
            
            # User quiz stats count
            if 'user_quiz_stats' in table_names:
                user_count_row = conn.execute(
                    "SELECT COUNT(*) as count FROM user_quiz_stats"
                ).fetchone()
                if user_count_row:
                    user_count = user_count_row['count']
                
                # Top users
                top_users_rows = conn.execute(
                    """
                    SELECT username, display_name, points, best_streak, total_attempts, correct_answers
                    FROM user_quiz_stats 
                    ORDER BY points DESC, best_streak DESC
                    LIMIT 10
                    """
                ).fetchall()
                top_users = [dict(user) for user in top_users_rows]
            
            # Recent system events
            if 'system_events' in table_names:
                recent_events_rows = conn.execute(
                    """
                    SELECT event_type, event_data, severity, timestamp
                    FROM system_events 
                    ORDER BY timestamp DESC
                    LIMIT 20
                    """
                ).fetchall()
                recent_events = [dict(event) for event in recent_events_rows]
            
            return {
                'bot_stats': bot_stats,
                'quiz_stats': quiz_stats,
                'user_count': user_count,
                'top_users': top_users,
                'recent_events': recent_events
            }
    except Exception as e:
        print(f"Error getting bot statistics: {e}")
        return {
            'bot_stats': {},
            'quiz_stats': {},
            'user_count': 0,
            'top_users': [],
            'recent_events': []
        }

def get_islamic_content_stats():
    """Get Islamic content statistics"""
    try:
        # Load quiz data
        quiz_file = DATA_DIR / "quiz.json"
        verses_file = DATA_DIR / "verses.json"
        
        quiz_data = {}
        verses_data = {}
        
        if quiz_file.exists():
            with open(quiz_file, 'r', encoding='utf-8') as f:
                quiz_data = json.load(f)
        
        if verses_file.exists():
            with open(verses_file, 'r', encoding='utf-8') as f:
                verses_data = json.load(f)
        
        # Analyze quiz categories
        quiz_categories = {}
        if 'questions' in quiz_data:
            for question in quiz_data['questions']:
                category = question.get('category', 'Unknown')
                quiz_categories[category] = quiz_categories.get(category, 0) + 1
        
        # Analyze verse categories
        verse_categories = {}
        if 'verses' in verses_data:
            for verse in verses_data['verses']:
                category = verse.get('category', 'Unknown')
                verse_categories[category] = verse_categories.get(category, 0) + 1
        
        return {
            'quiz_total': len(quiz_data.get('questions', [])),
            'quiz_categories': quiz_categories,
            'verses_total': len(verses_data.get('verses', [])),
            'verse_categories': verse_categories,
            'quiz_metadata': quiz_data.get('metadata', {}),
            'verses_metadata': verses_data.get('metadata', {})
        }
    except Exception as e:
        print(f"Error getting Islamic content stats: {e}")
        return {
            'quiz_total': 0,
            'quiz_categories': {},
            'verses_total': 0,
            'verse_categories': {},
            'quiz_metadata': {},
            'verses_metadata': {}
        }

def get_performance_metrics():
    """Get performance and API metrics"""
    try:
        if METRICS_FILE.exists():
            with open(METRICS_FILE, 'r') as f:
                metrics_data = json.load(f)
            
            # Get recent API metrics
            api_metrics = metrics_data.get('api_metrics', [])
            recent_metrics = [m for m in api_metrics if 
                            datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > 
                            datetime.now(UTC) - timedelta(hours=1)]
            
            # Calculate averages
            if recent_metrics:
                avg_response_time = sum(m['response_time'] for m in recent_metrics) / len(recent_metrics)
                error_rate = len([m for m in recent_metrics if m['status_code'] >= 400]) / len(recent_metrics)
            else:
                avg_response_time = 0
                error_rate = 0
            
            health_history = metrics_data.get('health_history', [])
            latest_health = health_history[-1] if health_history else {}
            
            return {
                'avg_response_time': round(avg_response_time * 1000, 2),  # Convert to ms
                'error_rate': round(error_rate * 100, 2),  # Convert to percentage
                'total_api_calls': len(api_metrics),
                'recent_calls': len(recent_metrics),
                'health_status': latest_health.get('status', 'unknown'),
                'gateway_connected': latest_health.get('gateway_connected', False),
                'gateway_latency': round(latest_health.get('gateway_latency', 0) * 1000, 2) if latest_health.get('gateway_latency') else 0
            }
    except Exception as e:
        print(f"Error getting performance metrics: {e}")
        return {
            'avg_response_time': 0,
            'error_rate': 0,
            'total_api_calls': 0,
            'recent_calls': 0,
            'health_status': 'unknown',
            'gateway_connected': False,
            'gateway_latency': 0
        }

# =============================================================================
# Dashboard Routes
# =============================================================================

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/overview')
def api_overview():
    """Get accurate dashboard overview data with real-time statistics"""
    try:
        print("Getting accurate bot statistics...")
        
        # Get actual bot status with detailed indicators
        bot_status, status_indicators = get_actual_bot_status()
        print(f"Bot status: {bot_status}, indicators: {status_indicators}")
        
        # Get accurate database statistics
        accurate_stats = get_accurate_bot_statistics()
        print(f"Accurate stats: {accurate_stats}")
        
        # Get Islamic content stats
        content_stats = get_islamic_content_stats()
        print(f"Content stats: {content_stats}")
        
        # Get performance metrics
        performance = get_performance_metrics()
        print(f"Performance: {performance}")
        
        # Calculate accuracy percentage for community stats
        total_attempts = accurate_stats['quiz_stats'].get('total_attempts', 0)
        correct_answers = accurate_stats['quiz_stats'].get('correct_answers', 0)
        accuracy_pct = (correct_answers / total_attempts * 100) if total_attempts > 0 else 0
        
        overview_data = {
            'timestamp': datetime.now(UTC).isoformat(),
            'bot_info': {
                'status': bot_status,
                'status_details': status_indicators,
                'uptime_hours': accurate_stats['bot_stats'].get('total_runtime_hours', 0),
                'total_sessions': accurate_stats['bot_stats'].get('total_sessions', 0),
                'total_completed_sessions': accurate_stats['bot_stats'].get('total_completed_sessions', 0),
                'last_startup': accurate_stats['bot_stats'].get('last_startup'),
                'last_shutdown': accurate_stats['bot_stats'].get('last_shutdown'),
                'favorite_reciter': accurate_stats['bot_stats'].get('favorite_reciter', 'Unknown')
            },
            'islamic_content': {
                'total_quizzes': content_stats.get('quiz_total', 0),
                'total_verses': content_stats.get('verses_total', 0),
                'quiz_categories': len(content_stats.get('quiz_categories', {})),
                'verse_categories': len(content_stats.get('verse_categories', {})),
                'quiz_metadata': content_stats.get('quiz_metadata', {}),
                'verses_metadata': content_stats.get('verses_metadata', {})
            },
            'community': {
                'total_users': accurate_stats.get('user_count', 0),
                'quiz_questions_sent': accurate_stats['quiz_stats'].get('questions_sent', 0),
                'total_quiz_attempts': total_attempts,
                'correct_answers': correct_answers,
                'accuracy_percentage': round(accuracy_pct, 1),
                'unique_participants': accurate_stats['quiz_stats'].get('unique_participants', 0)
            },
            'performance': performance,
            'recent_activity': accurate_stats.get('recent_events', [])[:5],
            'leaderboard_preview': accurate_stats.get('leaderboard', [])[:5]
        }
        
        print(f"Final overview data: {overview_data}")
        return jsonify(overview_data)
        
    except Exception as e:
        print(f"Error in api_overview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat(),
            'bot_info': {'status': 'error'},
            'islamic_content': {},
            'community': {},
            'performance': {},
            'recent_activity': []
        }), 500

@app.route('/api/leaderboard')
def api_leaderboard():
    """Get accurate leaderboard data from database"""
    try:
        accurate_stats = get_accurate_bot_statistics()
        return jsonify({
            'top_users': accurate_stats.get('leaderboard', []),
            'total_users': accurate_stats.get('user_count', 0),
            'quiz_stats': accurate_stats.get('quiz_stats', {}),
            'timestamp': datetime.now(UTC).isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/content')
def api_content():
    """Get Islamic content statistics"""
    try:
        content_stats = get_islamic_content_stats()
        return jsonify({
            'quiz_data': {
                'total': content_stats.get('quiz_total', 0),
                'categories': content_stats.get('quiz_categories', {}),
                'metadata': content_stats.get('quiz_metadata', {})
            },
            'verses_data': {
                'total': content_stats.get('verses_total', 0),
                'categories': content_stats.get('verse_categories', {}),
                'metadata': content_stats.get('verses_metadata', {})
            },
            'timestamp': datetime.now(UTC).isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """Get detailed performance metrics"""
    try:
        performance = get_performance_metrics()
        
        # Add system health indicators
        performance.update({
            'system_health': 'excellent' if performance['error_rate'] < 1 else 
                           'good' if performance['error_rate'] < 5 else 
                           'warning' if performance['error_rate'] < 10 else 'critical',
            'response_health': 'excellent' if performance['avg_response_time'] < 100 else
                             'good' if performance['avg_response_time'] < 500 else
                             'warning' if performance['avg_response_time'] < 1000 else 'critical'
        })
        
        return jsonify(performance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# WebSocket Events for Real-time Updates
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {'message': 'Connected to QuranBot Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('request_update')
def handle_update_request():
    """Handle real-time update request"""
    try:
        with app.app_context():
            overview_data = api_overview().get_json()
            emit('dashboard_update', overview_data)
    except Exception as e:
        emit('error', {'message': str(e)})

# =============================================================================
# Background Task for Real-time Updates
# =============================================================================

def background_updates():
    """Send periodic updates to connected clients"""
    while True:
        try:
            socketio.sleep(REFRESH_INTERVAL)
            with app.app_context():
                overview_data = api_overview().get_json()
                socketio.emit('dashboard_update', overview_data, broadcast=True)
        except Exception as e:
            print(f"Error in background updates: {e}")
            socketio.sleep(10)  # Wait longer on error

# Start background task
socketio.start_background_task(background_updates)

# =============================================================================
# Main Application Entry Point
# =============================================================================

if __name__ == '__main__':
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Run the dashboard
    print("🕌 Starting QuranBot Dashboard...")
    print(f"📊 Data directory: {DATA_DIR}")
    print(f"🗄️ Database: {DATABASE_PATH}")
    print("🌐 Dashboard will be available at http://localhost:5000")
    
    socketio.run(app, 
                host='0.0.0.0', 
                port=5000, 
                debug=True,
                allow_unsafe_werkzeug=True)