# =============================================================================
# QuranBot - User Memory System
# =============================================================================
# Tracks user interactions for personalized AI responses
# =============================================================================

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import traceback

from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger


class UserMemory:
    """
    Manages user interaction history for context-aware responses.
    Silently tracks user questions and interests without revealing this to users.
    """

    def __init__(self, max_history_per_user: int = 10, history_timeout_hours: int = 24):
        """
        Initialize user memory system.

        Args:
            max_history_per_user: Maximum interactions to remember per user
            history_timeout_hours: Hours before old interactions are forgotten
        """
        self.service_name = "UserMemory"
        self.error_handler = ErrorHandler()

        try:
            self.max_history = max_history_per_user
            self.timeout_hours = history_timeout_hours

            # user_id -> deque of (question, response, timestamp)
            self.user_histories: dict[int, deque] = defaultdict(
                lambda: deque(maxlen=self.max_history)
            )

            # user_id -> {topic: count}
            self.user_interests: dict[int, dict[str, int]] = defaultdict(
                lambda: defaultdict(int)
            )

            # user_id -> last_seen timestamp
            self.last_seen: dict[int, datetime] = {}

            # Lock for thread-safe operations
            self._lock = asyncio.Lock()

            # Topic keywords for interest tracking
            self.topic_keywords = {
                "prayer": [
                    "salah",
                    "pray",
                    "prayer",
                    "salat",
                    "namaz",
                    "wudu",
                    "ablution",
                    "قيام",
                    "صلاة",
                ],
                "fasting": [
                    "fast",
                    "fasting",
                    "sawm",
                    "siyam",
                    "ramadan",
                    "iftar",
                    "suhoor",
                    "صيام",
                    "رمضان",
                ],
                "zakat": [
                    "zakat",
                    "charity",
                    "sadaqah",
                    "giving",
                    "zakah",
                    "زكاة",
                    "صدقة",
                ],
                "hajj": ["hajj", "umrah", "pilgrimage", "mecca", "kaaba", "حج", "عمرة"],
                "quran": [
                    "quran",
                    "verse",
                    "ayah",
                    "surah",
                    "recite",
                    "recitation",
                    "قرآن",
                    "آية",
                    "سورة",
                ],
                "prophet": [
                    "prophet",
                    "muhammad",
                    "pbuh",
                    "messenger",
                    "sunnah",
                    "نبي",
                    "محمد",
                    "رسول",
                ],
                "faith": [
                    "iman",
                    "faith",
                    "belief",
                    "believe",
                    "tawheed",
                    "إيمان",
                    "عقيدة",
                ],
                "dua": ["dua", "supplication", "prayer", "pray for", "دعاء"],
                "halal": [
                    "halal",
                    "haram",
                    "permissible",
                    "allowed",
                    "forbidden",
                    "حلال",
                    "حرام",
                ],
                "marriage": [
                    "marriage",
                    "nikah",
                    "spouse",
                    "husband",
                    "wife",
                    "marry",
                    "نكاح",
                    "زواج",
                ],
                "death": [
                    "death",
                    "janazah",
                    "grave",
                    "afterlife",
                    "akhirah",
                    "موت",
                    "آخرة",
                ],
                "repentance": [
                    "repent",
                    "tawbah",
                    "forgive",
                    "sin",
                    "mistake",
                    "توبة",
                    "استغفار",
                ],
            }

            TreeLogger.info(
                "User memory system initialized",
                {
                    "max_history": self.max_history,
                    "timeout_hours": self.timeout_hours,
                    "topic_count": len(self.topic_keywords),
                },
                service=self.service_name,
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to initialize user memory system",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )
            raise

    async def add_interaction(self, user_id: int, question: str, response: str) -> None:
        """
        Add a new interaction to user's history.

        Args:
            user_id: Discord user ID
            question: User's question
            response: Bot's response
        """
        async with self._lock:
            try:
                timestamp = datetime.now()

                TreeLogger.debug(
                    "Adding interaction to memory",
                    {
                        "user_id": user_id,
                        "question_length": len(question),
                        "response_length": len(response),
                        "timestamp": timestamp.isoformat(),
                    },
                    service=self.service_name,
                )

                # Validate inputs
                if not user_id or not isinstance(user_id, int):
                    TreeLogger.warning(
                        "Invalid user_id provided",
                        {"user_id": user_id, "type": type(user_id).__name__},
                        service=self.service_name,
                    )
                    return

                if not question or not response:
                    TreeLogger.warning(
                        "Empty question or response",
                        {
                            "user_id": user_id,
                            "has_question": bool(question),
                            "has_response": bool(response),
                        },
                        service=self.service_name,
                    )
                    return

                # Add to history
                self.user_histories[user_id].append((question, response, timestamp))

                # Update last seen
                self.last_seen[user_id] = timestamp

                # Track interests
                self._track_interests(user_id, question)

                # Clean old data periodically
                if len(self.user_histories) % 50 == 0:
                    TreeLogger.debug(
                        "Triggering periodic cleanup",
                        {"user_count": len(self.user_histories)},
                        service=self.service_name,
                    )
                    await self._cleanup_old_data()

                TreeLogger.info(
                    "User interaction added to memory",
                    {
                        "user_id": user_id,
                        "history_length": len(self.user_histories[user_id]),
                        "interests": dict(self.user_interests[user_id]),
                        "top_interest": (
                            max(
                                self.user_interests[user_id].items(), key=lambda x: x[1]
                            )[0]
                            if self.user_interests[user_id]
                            else None
                        ),
                    },
                    service=self.service_name,
                )

            except Exception as e:
                TreeLogger.error(
                    "Failed to add interaction to memory",
                    e,
                    {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                    },
                    service=self.service_name,
                )

                await self.error_handler.handle_error(
                    e,
                    {
                        "operation": "add_interaction",
                        "service": self.service_name,
                        "user_id": user_id,
                    },
                )

    def get_user_context(self, user_id: int) -> dict[str, any]:
        """
        Get context for a user including recent history and interests.

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary with user context
        """
        try:
            TreeLogger.debug(
                "Retrieving user context",
                {"user_id": user_id},
                service=self.service_name,
            )

            # Validate user_id
            if not user_id or not isinstance(user_id, int):
                TreeLogger.warning(
                    "Invalid user_id for context retrieval",
                    {"user_id": user_id, "type": type(user_id).__name__},
                    service=self.service_name,
                )
                return self._get_default_context()

            context = {
                "has_history": user_id in self.user_histories,
                "interaction_count": len(self.user_histories.get(user_id, [])),
                "recent_questions": [],
                "top_interests": [],
                "last_seen": self.last_seen.get(user_id),
                "is_returning_user": False,
                "time_since_last_seen": None,
            }

            # Get recent questions (last 3)
            if user_id in self.user_histories:
                try:
                    recent = list(self.user_histories[user_id])[-3:]
                    context["recent_questions"] = [q[0] for q in recent]

                    # Check if returning user (more than 1 hour gap)
                    if context["last_seen"]:
                        time_gap = datetime.now() - context["last_seen"]
                        context["is_returning_user"] = time_gap > timedelta(hours=1)
                        context["time_since_last_seen"] = str(time_gap)
                except Exception as e:
                    TreeLogger.warning(
                        "Error processing user history",
                        e,
                        {"user_id": user_id, "error_type": type(e).__name__},
                        service=self.service_name,
                    )

            # Get top interests
            if user_id in self.user_interests:
                try:
                    interests = self.user_interests[user_id]
                    if interests:
                        sorted_interests = sorted(
                            interests.items(), key=lambda x: x[1], reverse=True
                        )
                        context["top_interests"] = [
                            topic for topic, _ in sorted_interests[:3]
                        ]
                except Exception as e:
                    TreeLogger.warning(
                        "Error processing user interests",
                        e,
                        {"user_id": user_id, "error_type": type(e).__name__},
                        service=self.service_name,
                    )

            TreeLogger.debug(
                "User context retrieved",
                {
                    "user_id": user_id,
                    "has_history": context["has_history"],
                    "interaction_count": context["interaction_count"],
                    "is_returning": context["is_returning_user"],
                    "top_interests": context["top_interests"],
                },
                service=self.service_name,
            )

            return context

        except Exception as e:
            TreeLogger.error(
                "Failed to get user context",
                e,
                {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            return self._get_default_context()

    def _get_default_context(self) -> dict[str, any]:
        """Get default context when user data is unavailable."""
        return {
            "has_history": False,
            "interaction_count": 0,
            "recent_questions": [],
            "top_interests": [],
            "last_seen": None,
            "is_returning_user": False,
            "time_since_last_seen": None,
        }

    def _track_interests(self, user_id: int, question: str) -> None:
        """
        Track user interests based on question content.

        Args:
            user_id: Discord user ID
            question: User's question
        """
        try:
            if not question:
                return

            question_lower = question.lower()
            topics_found = []

            for topic, keywords in self.topic_keywords.items():
                for keyword in keywords:
                    if keyword in question_lower:
                        self.user_interests[user_id][topic] += 1
                        topics_found.append(topic)
                        break

            if topics_found:
                TreeLogger.debug(
                    "Topics detected in question",
                    {
                        "user_id": user_id,
                        "topics": topics_found,
                        "question_length": len(question),
                    },
                    service=self.service_name,
                )

        except Exception as e:
            TreeLogger.warning(
                "Error tracking user interests",
                e,
                {"user_id": user_id, "error_type": type(e).__name__},
                service=self.service_name,
            )

    async def _cleanup_old_data(self) -> None:
        """Clean up old interaction data beyond timeout period."""
        async with self._lock:
            try:
                TreeLogger.debug(
                    "Starting cleanup of old data",
                    {
                        "timeout_hours": self.timeout_hours,
                        "current_users": len(self.user_histories),
                    },
                    service=self.service_name,
                )

                current_time = datetime.now()
                timeout_delta = timedelta(hours=self.timeout_hours)
                cleaned_users = 0
                removed_entries = 0

                # Clean up old histories
                for user_id in list(self.user_histories.keys()):
                    try:
                        # Remove old entries from deque
                        history = self.user_histories[user_id]
                        initial_length = len(history)

                        while (
                            history and (current_time - history[0][2]) > timeout_delta
                        ):
                            history.popleft()
                            removed_entries += 1

                        # Remove empty histories
                        if not history:
                            del self.user_histories[user_id]
                            if user_id in self.user_interests:
                                del self.user_interests[user_id]
                            if user_id in self.last_seen:
                                del self.last_seen[user_id]
                            cleaned_users += 1

                            TreeLogger.debug(
                                "Removed user from memory",
                                {"user_id": user_id, "entries_removed": initial_length},
                                service=self.service_name,
                            )

                    except Exception as e:
                        TreeLogger.warning(
                            "Error cleaning user data",
                            e,
                            {"user_id": user_id, "error_type": type(e).__name__},
                            service=self.service_name,
                        )

                TreeLogger.info(
                    "Cleanup completed",
                    {
                        "cleaned_users": cleaned_users,
                        "removed_entries": removed_entries,
                        "remaining_users": len(self.user_histories),
                        "total_entries": sum(
                            len(h) for h in self.user_histories.values()
                        ),
                    },
                    service=self.service_name,
                )

            except Exception as e:
                TreeLogger.error(
                    "Failed to clean up old data",
                    e,
                    {
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                    },
                    service=self.service_name,
                )

                await self.error_handler.handle_error(
                    e, {"operation": "_cleanup_old_data", "service": self.service_name}
                )

    def get_personalized_greeting(self, user_id: int) -> str | None:
        """
        Get a personalized greeting based on user history.

        Args:
            user_id: Discord user ID

        Returns:
            Personalized greeting or None
        """
        try:
            TreeLogger.debug(
                "Generating personalized greeting",
                {"user_id": user_id},
                service=self.service_name,
            )

            context = self.get_user_context(user_id)

            if context["is_returning_user"]:
                # Returning after a break
                greetings = [
                    "Welcome back! It's good to see you again.",
                    "Assalamu alaikum! Nice to have you back.",
                    "MashaAllah, you've returned! How can I help you today?",
                ]

                # Add interest-based continuation
                if context["top_interests"]:
                    top_interest = context["top_interests"][0]
                    TreeLogger.debug(
                        "Customizing greeting based on interest",
                        {"user_id": user_id, "top_interest": top_interest},
                        service=self.service_name,
                    )

                    if top_interest == "prayer":
                        greetings.append(
                            "Welcome back! Still seeking knowledge about Salah?"
                        )
                    elif top_interest == "quran":
                        greetings.append(
                            "Good to see you again! Ready to explore more of the Quran?"
                        )
                    elif top_interest == "fasting":
                        greetings.append(
                            "Assalamu alaikum! Back to learn more about fasting?"
                        )
                    elif top_interest == "hajj":
                        greetings.append(
                            "Welcome back! Continuing your journey learning about Hajj?"
                        )

                import random

                greeting = random.choice(greetings)

                TreeLogger.info(
                    "Personalized greeting generated",
                    {
                        "user_id": user_id,
                        "is_returning": True,
                        "has_interests": bool(context["top_interests"]),
                    },
                    service=self.service_name,
                )

                return greeting

            return None

        except Exception as e:
            TreeLogger.error(
                "Failed to generate personalized greeting",
                e,
                {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            return None
