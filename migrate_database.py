#!/usr/bin/env python3
# =============================================================================
# Database Migration Script for Enhanced Dashboard
# =============================================================================
# Creates new tables for historical charts, user profiles, and live audio
# =============================================================================

import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Add new tables to existing database"""
    print("🔄 Migrating database for enhanced dashboard features...")
    
    data_dir = Path("data")
    db_path = data_dir / "quranbot.db"
    
    if not db_path.exists():
        print("❌ Database file not found. Please run the bot first to create initial database.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Historical bot statistics for charts
        print("📊 Creating bot_stats_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_stats_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_runtime_hours REAL NOT NULL DEFAULT 0.0,
                active_sessions INTEGER NOT NULL DEFAULT 0,
                total_commands INTEGER NOT NULL DEFAULT 0,
                total_messages INTEGER NOT NULL DEFAULT 0,
                memory_usage_mb REAL DEFAULT 0.0,
                cpu_percent REAL DEFAULT 0.0,
                gateway_latency REAL DEFAULT 0.0,
                guild_count INTEGER DEFAULT 0
            )
        """)
        
        # Historical quiz statistics for trends
        print("📈 Creating quiz_history table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                questions_sent_today INTEGER NOT NULL DEFAULT 0,
                attempts_today INTEGER NOT NULL DEFAULT 0,
                correct_today INTEGER NOT NULL DEFAULT 0,
                active_users INTEGER NOT NULL DEFAULT 0,
                accuracy_rate REAL DEFAULT 0.0
            )
        """)
        
        # User activity tracking for profiles
        print("👥 Creating user_activity table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                activity_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                channel_id TEXT,
                guild_id TEXT
            )
        """)
        
        # User achievements system
        print("🏆 Creating user_achievements table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT,
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                points_awarded INTEGER DEFAULT 0
            )
        """)
        
        # Live audio tracking
        print("🎵 Creating audio_status table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_surah INTEGER NOT NULL DEFAULT 1,
                current_verse INTEGER NOT NULL DEFAULT 1,
                reciter TEXT NOT NULL DEFAULT 'Saad Al Ghamdi',
                is_playing BOOLEAN NOT NULL DEFAULT 0,
                current_position_seconds REAL DEFAULT 0.0,
                total_duration_seconds REAL DEFAULT 0.0,
                listeners_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        print("⚡ Creating performance indexes...")
        
        # Historical data indexes for charts
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bot_stats_history_timestamp
            ON bot_stats_history(timestamp)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_quiz_history_timestamp
            ON quiz_history(timestamp)
        """)
        
        # User activity indexes for profiles
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_user_timestamp
            ON user_activity(user_id, timestamp DESC)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_type
            ON user_activity(activity_type)
        """)
        
        # User achievements indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_achievements_user
            ON user_achievements(user_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_achievements_type
            ON user_achievements(achievement_type)
        """)
        
        # Initialize default audio status
        print("🎛️ Initializing default audio status...")
        conn.execute("""
            INSERT OR IGNORE INTO audio_status (id, current_surah, current_verse, reciter, is_playing)
            VALUES (1, 1, 1, 'Saad Al Ghamdi', 0)
        """)
        
        # Add some sample historical data for demonstration
        print("📝 Adding sample data for demonstration...")
        import datetime
        from datetime import UTC
        
        # Add sample bot stats history
        for i in range(7):
            timestamp = datetime.datetime.now(UTC) - datetime.timedelta(days=i)
            conn.execute("""
                INSERT INTO bot_stats_history 
                (timestamp, total_runtime_hours, memory_usage_mb, cpu_percent, gateway_latency)
                VALUES (?, ?, ?, ?, ?)
            """, (
                timestamp.isoformat(),
                i * 0.5,  # Runtime increases over time
                25.0 + (i * 2),  # Memory usage varies
                5.0 + (i * 0.5),  # CPU usage
                0.045 + (i * 0.001)  # Latency
            ))
        
        # Add sample quiz history
        for i in range(7):
            timestamp = datetime.datetime.now(UTC) - datetime.timedelta(days=i)
            questions = max(1, 7 - i)
            attempts = questions * 2
            correct = int(attempts * 0.7)  # 70% accuracy
            accuracy = (correct / attempts * 100) if attempts > 0 else 0
            
            conn.execute("""
                INSERT INTO quiz_history 
                (timestamp, questions_sent_today, attempts_today, correct_today, active_users, accuracy_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp.isoformat(),
                questions,
                attempts,
                correct,
                max(1, questions),  # Active users = questions sent
                accuracy
            ))
        
        conn.commit()
        conn.close()
        
        print("✅ Database migration completed successfully!")
        print("🚀 Enhanced dashboard features are now available:")
        print("   📊 Historical charts with 7 days of sample data")
        print("   👤 User profiles and achievements system")
        print("   🎵 Live audio status tracking")
        print("   📋 Enhanced activity monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    migrate_database()