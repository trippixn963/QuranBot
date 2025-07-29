# =============================================================================
# QuranBot - Modern SQLite-Based Quiz Service
# =============================================================================
# Modern quiz service that integrates with Discord.py and uses SQLite for
# all data storage. Replaces the old JSON-based quiz manager.
# =============================================================================

import asyncio
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sqlite3

from ..core.structured_logger import StructuredLogger
from ..services.sqlite_state_service import SQLiteStateService


class QuizQuestion:
    """Represents a quiz question with all metadata"""
    
    def __init__(self, question_id: int, question: str, option_a: str, option_b: str,
                 option_c: str, option_d: str, correct_answer: str, category: str = "general",
                 difficulty: str = "medium", explanation: str = "", surah_reference: str = "",
                 verse_reference: str = "", source: str = "imported", times_used: int = 0,
                 times_correct: int = 0):
        self.id = question_id
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.correct_answer = correct_answer.upper()
        self.category = category
        self.difficulty = difficulty
        self.explanation = explanation
        self.surah_reference = surah_reference
        self.verse_reference = verse_reference
        self.source = source
        self.times_used = times_used
        self.times_correct = times_correct
    
    @property
    def options(self) -> Dict[str, str]:
        """Get options as a dictionary"""
        return {
            "A": self.option_a,
            "B": self.option_b, 
            "C": self.option_c,
            "D": self.option_d
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.times_used == 0:
            return 0.0
        return (self.times_correct / self.times_used) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "category": self.category,
            "difficulty": self.difficulty,
            "explanation": self.explanation,
            "surah_reference": self.surah_reference,
            "verse_reference": self.verse_reference,
            "source": self.source,
            "times_used": self.times_used,
            "times_correct": self.times_correct,
            "success_rate": round(self.success_rate, 1)
        }


class ModernQuizService:
    """
    Modern SQLite-based quiz service for Discord bot integration.
    
    Features:
    - SQLite storage for questions, stats, and configuration
    - Intelligent question selection based on difficulty and usage
    - User statistics and leaderboard tracking
    - Configurable quiz intervals and settings
    - Anti-duplicate question tracking
    - Performance analytics and reporting
    """
    
    def __init__(self, logger: StructuredLogger, db_path: Path = None):
        """Initialize the modern quiz service"""
        self.logger = logger
        self.db_path = db_path or Path("data/quranbot.db")
        self.sqlite_service = SQLiteStateService(logger=logger, db_path=self.db_path)
        self._initialized = False
        
        # Quiz configuration (loaded from SQLite)
        self.config = {
            "send_interval_hours": 3.0,
            "questions_per_quiz": 1,
            "default_difficulty": "medium",
            "enable_explanations": True,
            "enable_leaderboard": True,
            "max_recent_questions": 20,
            "auto_adjust_difficulty": True
        }
        
        # Recent questions tracking
        self.recent_questions = []
        
    async def initialize(self) -> bool:
        """Initialize the quiz service"""
        try:
            await self.sqlite_service.initialize()
            
            # Load configuration
            config = await self.sqlite_service.load_quiz_config()
            self.config.update(config)
            
            # Load recent questions
            await self._load_recent_questions()
            
            self._initialized = True
            await self.logger.info("Modern quiz service initialized", {
                "config": self.config,
                "recent_questions_count": len(self.recent_questions)
            })
            return True
            
        except Exception as e:
            await self.logger.error("Failed to initialize quiz service", {"error": str(e)})
            return False
    
    async def _load_recent_questions(self) -> None:
        """Load recently used questions from database"""
        try:
            # Get recent quiz activities from system events
            query = """
                SELECT event_data FROM system_events 
                WHERE event_type = 'quiz_question_sent' 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(query, (self.config["max_recent_questions"],))
                results = cursor.fetchall()
                
                self.recent_questions = []
                for row in results:
                    try:
                        import json
                        event_data = json.loads(row[0])
                        question_id = event_data.get("question_id")
                        if question_id:
                            self.recent_questions.append(question_id)
                    except (json.JSONDecodeError, KeyError):
                        continue
                        
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.warning("Could not load recent questions", {"error": str(e)})
            self.recent_questions = []
    
    async def get_next_question(self, difficulty: str = None, category: str = None,
                               user_id: str = None) -> Optional[QuizQuestion]:
        """
        Get the next quiz question with intelligent selection.
        
        Args:
            difficulty: Preferred difficulty level
            category: Preferred category
            user_id: User ID for personalized selection
            
        Returns:
            QuizQuestion object or None if no questions available
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Build query based on criteria
            query_parts = ["SELECT * FROM quiz_questions WHERE is_active = 1"]
            params = []
            
            # Filter by difficulty
            if difficulty:
                query_parts.append("AND difficulty = ?")
                params.append(difficulty)
            
            # Filter by category
            if category:
                query_parts.append("AND category = ?")
                params.append(category)
            
            # Exclude recent questions
            if self.recent_questions:
                placeholders = ",".join("?" * len(self.recent_questions))
                query_parts.append(f"AND id NOT IN ({placeholders})")
                params.extend(self.recent_questions)
            
            # Order by usage (prefer less used questions) and randomize
            query_parts.append("ORDER BY times_used ASC, RANDOM() LIMIT 5")
            
            query = " ".join(query_parts)
            
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                if not rows:
                    # No questions found, try without recent question filter
                    await self.logger.warning("No quiz questions found with criteria", {
                        "difficulty": difficulty,
                        "category": category,
                        "recent_count": len(self.recent_questions)
                    })
                    return None
                
                # Pick random question from top 5 least used
                row = random.choice(rows)
                
                question = QuizQuestion(
                    question_id=row[0],
                    question=row[1],
                    option_a=row[2],
                    option_b=row[3],
                    option_c=row[4],
                    option_d=row[5],
                    correct_answer=row[6],
                    category=row[7],
                    difficulty=row[8],
                    explanation=row[11],
                    surah_reference=row[12],
                    verse_reference=row[13],
                    source=row[14],
                    times_used=row[15],
                    times_correct=row[16]
                )
                
                # Log the question selection
                await self._log_question_sent(question, user_id)
                
                return question
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to get next question", {"error": str(e)})
            return None
    
    async def _log_question_sent(self, question: QuizQuestion, user_id: str = None) -> None:
        """Log that a question was sent"""
        try:
            # Add to recent questions
            self.recent_questions.insert(0, question.id)
            if len(self.recent_questions) > self.config["max_recent_questions"]:
                self.recent_questions = self.recent_questions[:self.config["max_recent_questions"]]
            
            # Update question usage count
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "UPDATE quiz_questions SET times_used = times_used + 1 WHERE id = ?",
                    (question.id,)
                )
                conn.commit()
            finally:
                conn.close()
            
            # Log system event
            import json
            event_data = {
                "question_id": question.id,
                "category": question.category,
                "difficulty": question.difficulty,
                "user_id": user_id
            }
            
            await self.sqlite_service.log_system_event(
                "quiz_question_sent",
                event_data,
                "info"
            )
            
        except Exception as e:
            await self.logger.warning("Failed to log question sent", {"error": str(e)})
    
    async def record_answer(self, question_id: int, user_id: str, answer: str, 
                           is_correct: bool, response_time_ms: int = None) -> bool:
        """
        Record a user's answer to a quiz question.
        
        Args:
            question_id: ID of the question answered
            user_id: Discord user ID
            answer: User's answer (A, B, C, or D)
            is_correct: Whether the answer was correct
            response_time_ms: Time taken to answer in milliseconds
            
        Returns:
            True if recorded successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                # Update question statistics
                if is_correct:
                    conn.execute(
                        "UPDATE quiz_questions SET times_correct = times_correct + 1 WHERE id = ?",
                        (question_id,)
                    )
                
                # Update user statistics
                conn.execute("""
                    INSERT OR REPLACE INTO user_quiz_stats 
                    (user_id, total_questions, correct_answers, last_answered, best_streak)
                    VALUES (
                        ?, 
                        COALESCE((SELECT total_questions FROM user_quiz_stats WHERE user_id = ?), 0) + 1,
                        COALESCE((SELECT correct_answers FROM user_quiz_stats WHERE user_id = ?), 0) + ?,
                        ?,
                        COALESCE((SELECT best_streak FROM user_quiz_stats WHERE user_id = ?), 0)
                    )
                """, (user_id, user_id, user_id, 1 if is_correct else 0, 
                      datetime.now(timezone.utc).isoformat(), user_id))
                
                conn.commit()
                
                # Log the answer
                import json
                event_data = {
                    "question_id": question_id,
                    "user_id": user_id,
                    "answer": answer.upper(),
                    "is_correct": is_correct,
                    "response_time_ms": response_time_ms
                }
                
                await self.sqlite_service.log_system_event(
                    "quiz_answer_recorded",
                    event_data,
                    "info"
                )
                
                await self.logger.info("Quiz answer recorded", {
                    "question_id": question_id,
                    "user_id": user_id,
                    "correct": is_correct
                })
                
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to record quiz answer", {"error": str(e)})
            return False
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user quiz statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    "SELECT * FROM user_quiz_stats WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return {
                        "user_id": user_id,
                        "total_questions": 0,
                        "correct_answers": 0,
                        "accuracy_percentage": 0.0,
                        "best_streak": 0,
                        "rank": None,
                        "total_points": 0
                    }
                
                total_questions = row[1]
                correct_answers = row[2]
                accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0.0
                
                # Get user rank
                rank_cursor = conn.execute("""
                    SELECT COUNT(*) + 1 FROM user_quiz_stats 
                    WHERE total_points > (SELECT total_points FROM user_quiz_stats WHERE user_id = ?)
                """, (user_id,))
                rank = rank_cursor.fetchone()[0]
                
                return {
                    "user_id": user_id,
                    "total_questions": total_questions,
                    "correct_answers": correct_answers,
                    "accuracy_percentage": round(accuracy, 1),
                    "best_streak": row[4] or 0,
                    "rank": rank,
                    "total_points": row[5] or 0,
                    "last_answered": row[3]
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to get user stats", {"error": str(e)})
            return {"error": str(e)}
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the quiz leaderboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    SELECT user_id, total_questions, correct_answers, best_streak, total_points
                    FROM user_quiz_stats 
                    WHERE total_questions > 0
                    ORDER BY total_points DESC, correct_answers DESC, total_questions ASC
                    LIMIT ?
                """, (limit,))
                
                leaderboard = []
                for i, row in enumerate(cursor.fetchall(), 1):
                    user_id, total_qs, correct_ans, best_streak, total_points = row
                    accuracy = (correct_ans / total_qs * 100) if total_qs > 0 else 0.0
                    
                    leaderboard.append({
                        "rank": i,
                        "user_id": user_id,
                        "total_questions": total_qs,
                        "correct_answers": correct_ans,
                        "accuracy_percentage": round(accuracy, 1),
                        "best_streak": best_streak or 0,
                        "total_points": total_points or 0
                    })
                
                return leaderboard
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to get leaderboard", {"error": str(e)})
            return []
    
    async def should_send_question(self) -> bool:
        """Check if it's time to send a question based on interval configuration"""
        try:
            # Load latest config
            config = await self.sqlite_service.load_quiz_config()
            interval_hours = config.get("send_interval_hours", self.config["send_interval_hours"])
            
            # Check last question sent time
            query = """
                SELECT MAX(created_at) FROM system_events 
                WHERE event_type = 'quiz_question_sent'
            """
            
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(query)
                last_sent = cursor.fetchone()[0]
                
                if not last_sent:
                    return True  # No questions sent yet
                
                # Parse last sent time
                last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                time_since = datetime.now(timezone.utc) - last_sent_dt
                hours_since = time_since.total_seconds() / 3600
                
                return hours_since >= interval_hours
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to check question timing", {"error": str(e)})
            return False
    
    async def update_config(self, **config_updates) -> bool:
        """Update quiz configuration"""
        try:
            # Update local config
            self.config.update(config_updates)
            
            # Save to database
            success = await self.sqlite_service.save_quiz_config(self.config)
            
            if success:
                await self.logger.info("Quiz config updated", {"updates": config_updates})
            
            return success
            
        except Exception as e:
            await self.logger.error("Failed to update quiz config", {"error": str(e)})
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive quiz system statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                # Question statistics
                cursor = conn.execute("SELECT COUNT(*) FROM quiz_questions WHERE is_active = 1")
                total_questions = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT category) FROM quiz_questions WHERE is_active = 1")
                total_categories = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT AVG(times_used) FROM quiz_questions WHERE is_active = 1")
                avg_usage = cursor.fetchone()[0] or 0
                
                # User statistics
                cursor = conn.execute("SELECT COUNT(*) FROM user_quiz_stats WHERE total_questions > 0")
                active_users = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(total_questions) FROM user_quiz_stats")
                total_answers = cursor.fetchone()[0] or 0
                
                cursor = conn.execute("SELECT SUM(correct_answers) FROM user_quiz_stats")
                total_correct = cursor.fetchone()[0] or 0
                
                overall_accuracy = (total_correct / total_answers * 100) if total_answers > 0 else 0.0
                
                return {
                    "total_questions": total_questions,
                    "total_categories": total_categories,
                    "average_question_usage": round(avg_usage, 1),
                    "active_users": active_users,
                    "total_answers_given": total_answers,
                    "total_correct_answers": total_correct,
                    "overall_accuracy": round(overall_accuracy, 1),
                    "recent_questions_tracked": len(self.recent_questions),
                    "config": self.config
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            await self.logger.error("Failed to get quiz statistics", {"error": str(e)})
            return {"error": str(e)} 