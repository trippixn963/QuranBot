#!/usr/bin/env python3
# =============================================================================
# Conversation Memory Service - Smart Context & User Preferences
# =============================================================================
# This service tracks user conversations, preferences, and learning patterns
# to provide more personalized and contextually aware AI responses.
# =============================================================================

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import aiofiles

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class ConversationMemoryService:
    """Manages conversation history and user learning preferences."""

    def __init__(self):
        self.memory_file = Path("data/conversation_memory.json")
        self.memory = {"users": {}, "preferences": {}, "topic_frequency": {}}

        # Load existing memory
        # Note: _load_memory is now async, should be called with await during initialization

    async def _load_memory(self):
        """Load conversation memory from file."""
        try:
            if self.memory_file.exists():
                async with aiofiles.open(self.memory_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)

                # Load data with proper structure
                self.memory["users"] = data.get("users", {})
                self.memory["preferences"] = data.get("preferences", {})
                self.memory["topic_frequency"] = data.get("topic_frequency", {})

                # Convert old format if needed
                if "conversations" in data:
                    self.memory["users"] = data.get("conversations", {})

                log_perfect_tree_section(
                    "Conversation Memory - Loaded",
                    [
                        ("users_tracked", str(len(self.memory["users"]))),
                        (
                            "total_conversations",
                            str(
                                sum(
                                    len(user.get("conversation_history", []))
                                    for user in self.memory["users"].values()
                                )
                            ),
                        ),
                        ("preferences_stored", str(len(self.memory["preferences"]))),
                    ],
                    "💾",
                )
            else:
                log_perfect_tree_section(
                    "Conversation Memory - New File",
                    [("status", "Creating new memory file")],
                    "🆕",
                )

        except Exception as e:
            log_error_with_traceback("Error loading conversation memory", e)

    async def _save_memory(self):
        """Save conversation memory to file."""
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(self.memory_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.memory, indent=2, ensure_ascii=False))

        except Exception as e:
            log_error_with_traceback("Error saving conversation memory", e)

    async def add_conversation(
        self, user_id: int, question: str, response: str, topics: list[str]
    ) -> None:
        """Add a new conversation to memory with enhanced analysis."""
        try:
            user_str = str(user_id)
            current_time = datetime.now().isoformat()

            # Initialize user if not exists
            if user_str not in self.memory["users"]:
                self.memory["users"][user_str] = {
                    "total_conversations": 0,
                    "first_interaction": current_time,
                    "last_interaction": current_time,
                    "conversation_history": [],
                    "topic_frequency": {},
                    "favorite_topics": [],
                    "conversation_style": "new",
                    "learning_focus": None,
                    "cultural_indicators": [],
                    "knowledge_level": "beginner",
                    "emotional_patterns": [],
                    "question_complexity_trend": [],
                    "preferred_response_length": "medium",
                    "religious_practice_level": "unknown",
                }

            user_data = self.memory["users"][user_str]

            # Add conversation to history
            conversation_entry = {
                "timestamp": current_time,
                "question": question,
                "response": response,
                "topics": topics,
                "question_length": len(question),
                "response_length": len(response),
            }

            user_data["conversation_history"].append(conversation_entry)
            user_data["total_conversations"] += 1
            user_data["last_interaction"] = current_time

            # Analyze and update cultural indicators
            cultural_indicators = self._extract_cultural_indicators(question)
            if cultural_indicators:
                for indicator in cultural_indicators:
                    if indicator not in user_data["cultural_indicators"]:
                        user_data["cultural_indicators"].append(indicator)

            # Analyze knowledge level based on question complexity
            question_complexity = self._analyze_question_complexity(question)
            user_data["question_complexity_trend"].append(question_complexity)
            user_data["knowledge_level"] = self._determine_knowledge_level(
                user_data["question_complexity_trend"]
            )

            # Track emotional patterns
            emotional_indicators = self._extract_emotional_indicators(question)
            if emotional_indicators:
                user_data["emotional_patterns"].extend(emotional_indicators)
                # Keep only recent emotional patterns (last 20)
                user_data["emotional_patterns"] = user_data["emotional_patterns"][-20:]

            # Analyze religious practice level
            practice_indicators = self._extract_practice_indicators(question)
            if practice_indicators:
                user_data["religious_practice_level"] = practice_indicators

            # Update topic frequency
            for topic in topics:
                user_data["topic_frequency"][topic] = (
                    user_data["topic_frequency"].get(topic, 0) + 1
                )

            # Update favorite topics (top 5)
            sorted_topics = sorted(
                user_data["topic_frequency"].items(), key=lambda x: x[1], reverse=True
            )
            user_data["favorite_topics"] = [topic for topic, count in sorted_topics[:5]]

            # Update conversation style based on interaction patterns
            user_data["conversation_style"] = self._determine_conversation_style(
                user_data
            )

            # Determine learning focus
            if user_data["favorite_topics"]:
                user_data["learning_focus"] = user_data["favorite_topics"][0]

            # Determine preferred response length
            recent_responses = user_data["conversation_history"][
                -5:
            ]  # Last 5 conversations
            avg_response_length = sum(
                conv["response_length"] for conv in recent_responses
            ) / len(recent_responses)
            if avg_response_length > 800:
                user_data["preferred_response_length"] = "detailed"
            elif avg_response_length < 400:
                user_data["preferred_response_length"] = "concise"
            else:
                user_data["preferred_response_length"] = "medium"

            # Keep conversation history manageable (last 50 conversations)
            if len(user_data["conversation_history"]) > 50:
                user_data["conversation_history"] = user_data["conversation_history"][
                    -50:
                ]

            await self._save_memory()

        except Exception as e:
            print(f"Error adding conversation to memory: {e}")

    def _extract_cultural_indicators(self, question: str) -> list[str]:
        """Extract cultural indicators from the question."""
        question_lower = question.lower()
        cultural_indicators = []

        # Cultural patterns - Syrian first since this is a Syrian server
        cultural_patterns = {
            "syrian": [
                "syria",
                "syrian",
                "damascus",
                "aleppo",
                "levantine",
                "sham",
                "bilad al-sham",
                "levant",
                "homs",
                "latakia",
                "daraa",
                "tartus",
            ],
            "south_asian": [
                "urdu",
                "pakistan",
                "india",
                "bangladesh",
                "desi",
                "subcontinental",
                "hanafi",
            ],
            "arab": [
                "arabic",
                "saudi",
                "egypt",
                "lebanon",
                "jordan",
                "gulf",
                "makkah",
                "madinah",
            ],
            "southeast_asian": [
                "indonesia",
                "malaysia",
                "brunei",
                "singapore",
                "shafi",
            ],
            "african": [
                "nigeria",
                "senegal",
                "morocco",
                "tunisia",
                "algeria",
                "mali",
                "maliki",
            ],
            "western": [
                "america",
                "europe",
                "canada",
                "australia",
                "workplace",
                "minority",
            ],
            "convert": [
                "new muslim",
                "convert",
                "revert",
                "recently accepted",
                "just became muslim",
                "first time",
            ],
        }

        for culture, indicators in cultural_patterns.items():
            if any(indicator in question_lower for indicator in indicators):
                cultural_indicators.append(culture)

        # If no specific indicators found, default to Syrian since this is a Syrian server
        if not cultural_indicators:
            cultural_indicators.append("syrian")

        return cultural_indicators

    def _analyze_question_complexity(self, question: str) -> str:
        """Analyze the complexity level of a question."""
        question_lower = question.lower()

        # Basic indicators
        basic_indicators = [
            "what is",
            "who is",
            "when is",
            "where is",
            "how many",
            "simple",
            "basic",
        ]
        intermediate_indicators = [
            "how do",
            "why do",
            "what does",
            "explain",
            "difference between",
            "compare",
        ]
        advanced_indicators = [
            "jurisprudence",
            "fiqh",
            "madhab",
            "scholarly opinion",
            "detailed",
            "in depth",
            "comprehensive",
        ]

        # Check complexity
        if any(indicator in question_lower for indicator in advanced_indicators):
            return "advanced"
        elif any(indicator in question_lower for indicator in intermediate_indicators):
            return "intermediate"
        elif any(indicator in question_lower for indicator in basic_indicators):
            return "basic"

        # Default based on length and question words
        if len(question.split()) > 15:
            return "intermediate"
        elif len(question.split()) < 5:
            return "basic"
        else:
            return "intermediate"

    def _determine_knowledge_level(self, complexity_trend: list[str]) -> str:
        """Determine overall knowledge level from question complexity trend."""
        if not complexity_trend:
            return "beginner"

        recent_trend = complexity_trend[-10:]  # Last 10 questions

        advanced_count = recent_trend.count("advanced")
        intermediate_count = recent_trend.count("intermediate")
        basic_count = recent_trend.count("basic")

        if advanced_count >= 3:
            return "advanced"
        elif intermediate_count >= 5:
            return "intermediate"
        elif basic_count >= 7:
            return "beginner"
        else:
            return "intermediate"  # Default

    def _extract_emotional_indicators(self, question: str) -> list[str]:
        """Extract emotional indicators from the question."""
        question_lower = question.lower()
        emotional_indicators = []

        emotional_patterns = {
            "struggling": [
                "struggling",
                "difficult",
                "hard time",
                "can't",
                "impossible",
            ],
            "doubting": ["doubt", "questioning", "not sure", "confused about faith"],
            "sad": ["sad", "depressed", "hopeless", "grief", "mourning"],
            "anxious": ["worried", "anxious", "scared", "afraid", "nervous"],
            "guilty": ["guilty", "shame", "regret", "sinned", "wrong"],
            "seeking_motivation": [
                "motivation",
                "inspiration",
                "encourage",
                "strength",
            ],
            "grateful": ["thank", "grateful", "appreciate", "blessed", "alhamdulillah"],
            "curious": ["interested", "want to learn", "tell me more", "explain"],
        }

        for emotion, indicators in emotional_patterns.items():
            if any(indicator in question_lower for indicator in indicators):
                emotional_indicators.append(emotion)

        return emotional_indicators

    def _extract_practice_indicators(self, question: str) -> str:
        """Extract religious practice level indicators."""
        question_lower = question.lower()

        # Practice level indicators
        beginner_indicators = [
            "new to islam",
            "just started",
            "basic",
            "how to start",
            "first time",
        ]
        practicing_indicators = [
            "regular prayer",
            "daily dhikr",
            "follow sunnah",
            "practice regularly",
        ]
        advanced_indicators = [
            "seeking perfection",
            "detailed fiqh",
            "scholarly level",
            "deep understanding",
        ]

        if any(indicator in question_lower for indicator in advanced_indicators):
            return "advanced_practicing"
        elif any(indicator in question_lower for indicator in practicing_indicators):
            return "regular_practicing"
        elif any(indicator in question_lower for indicator in beginner_indicators):
            return "new_practicing"

        return "unknown"  # Don't change if no clear indicators

    def _determine_conversation_style(self, user_data: dict) -> str:
        """Determine user's conversation style based on interaction patterns."""
        total_conversations = user_data["total_conversations"]

        if total_conversations >= 20:
            return "experienced"
        elif total_conversations >= 10:
            return "regular"
        elif total_conversations >= 3:
            return "returning"
        else:
            return "new"

    def get_user_context(self, user_id: int) -> dict:
        """Get comprehensive user context for personalized responses."""
        user_str = str(user_id)

        if user_str not in self.memory["users"]:
            return {
                "is_new_user": True,
                "total_conversations": 0,
                "conversation_style": "new",
                "learning_focus": None,
                "favorite_topics": [],
                "cultural_indicators": [],
                "knowledge_level": "beginner",
                "emotional_patterns": [],
                "religious_practice_level": "unknown",
                "preferred_response_length": "medium",
            }

        user_data = self.memory["users"][user_str]

        # Analyze recent emotional state
        recent_emotions = user_data.get("emotional_patterns", [])[
            -5:
        ]  # Last 5 emotional indicators
        dominant_emotion = (
            max(set(recent_emotions), key=recent_emotions.count)
            if recent_emotions
            else "neutral"
        )

        # Determine if user needs encouragement
        needs_encouragement = any(
            emotion in recent_emotions
            for emotion in ["struggling", "doubting", "sad", "guilty"]
        )

        return {
            "is_new_user": user_data.get("total_conversations", 0) == 0,
            "total_conversations": user_data.get("total_conversations", 0),
            "conversation_style": user_data.get("conversation_style", "new"),
            "learning_focus": user_data.get("learning_focus"),
            "favorite_topics": user_data.get("favorite_topics", []),
            "cultural_indicators": user_data.get("cultural_indicators", []),
            "knowledge_level": user_data.get("knowledge_level", "beginner"),
            "emotional_patterns": recent_emotions,
            "dominant_emotion": dominant_emotion,
            "needs_encouragement": needs_encouragement,
            "religious_practice_level": user_data.get(
                "religious_practice_level", "unknown"
            ),
            "preferred_response_length": user_data.get(
                "preferred_response_length", "medium"
            ),
            "conversation_history": user_data.get("conversation_history", [])[
                -10:
            ],  # Last 10 conversations for contradiction detection
        }

    async def update_user_preference(
        self, user_id: int, preference_key: str, preference_value: Any
    ):
        """Update user preference."""
        try:
            if user_id not in self.memory["preferences"]:
                self.memory["preferences"][user_id] = {}

            self.memory["preferences"][user_id][preference_key] = preference_value
            self.memory["preferences"][user_id]["last_updated"] = (
                datetime.now().isoformat()
            )

            await self._save_memory()

        except Exception as e:
            log_error_with_traceback("Error updating user preference", e)

    def get_user_preferences(self, user_id: int) -> dict[str, Any]:
        """Get user preferences."""
        return self.memory["preferences"].get(user_id, {})

    def classify_question_topics(self, question: str) -> list[str]:
        """Classify question into Islamic topics for tracking."""
        question_lower = question.lower()

        topics = []

        # Topic mapping
        topic_keywords = {
            "prayer": [
                "prayer",
                "salah",
                "namaz",
                "wudu",
                "ablution",
                "qibla",
                "mosque",
            ],
            "fasting": ["fasting", "sawm", "ramadan", "iftar", "suhur"],
            "hajj": ["hajj", "pilgrimage", "umrah", "mecca", "kaaba", "tawaf"],
            "zakat": ["zakat", "charity", "giving", "sadaqah", "alms"],
            "quran": ["quran", "verse", "surah", "ayah", "recitation"],
            "hadith": ["hadith", "prophet", "sunnah", "narrated", "reported"],
            "faith": ["faith", "belief", "iman", "allah", "god", "islam"],
            "family": ["family", "parents", "children", "marriage", "spouse"],
            "knowledge": ["knowledge", "learning", "education", "study", "scholar"],
            "dua": ["dua", "supplication", "prayer", "dhikr", "remembrance"],
            "forgiveness": ["forgiveness", "repentance", "mercy", "sin", "tawbah"],
            "patience": ["patience", "sabr", "trial", "difficulty", "hardship"],
            "practical": ["time", "direction", "calculate", "location", "calendar"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                topics.append(topic)

        return topics if topics else ["general"]

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        try:
            total_users = len(self.memory["users"])
            total_conversations = sum(
                len(user.get("conversation_history", []))
                for user in self.memory["users"].values()
            )
            total_preferences = len(self.memory["preferences"])

            # Most popular topics across all users
            all_topics = {}
            for user_topics in self.memory["topic_frequency"].values():
                for topic, count in user_topics.items():
                    all_topics[topic] = all_topics.get(topic, 0) + count

            popular_topics = sorted(
                all_topics.items(), key=lambda x: x[1], reverse=True
            )[:5]

            return {
                "total_users": total_users,
                "total_conversations": total_conversations,
                "total_preferences": total_preferences,
                "popular_topics": popular_topics,
            }

        except Exception as e:
            log_error_with_traceback("Error getting memory stats", e)
            return {}


# Global instance
conversation_memory_service: ConversationMemoryService | None = None


def get_conversation_memory_service() -> ConversationMemoryService:
    """Get singleton instance of conversation memory service."""
    global conversation_memory_service

    if conversation_memory_service is None:
        conversation_memory_service = ConversationMemoryService()

    return conversation_memory_service
