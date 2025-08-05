"""QuranBot AI Service Module.

This module provides the core AI service with ChatGPT integration for Islamic
knowledge companion functionality.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
import tiktoken

from ...config import get_config
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger
from ...data.knowledge import ISLAMIC_KNOWLEDGE_BASE
from ..core.base_service import BaseService
from .emotional_intelligence import EmotionalIntelligence
from .islamic_knowledge import IslamicKnowledge
from .language_detection import LanguageDetection
from .user_memory import UserMemory


class AIService(BaseService):
    """AI service for processing Islamic questions using ChatGPT.

    Features:
    - ChatGPT 3.5 Turbo integration
    - Islamic knowledge base integration
    - Token counting and cost tracking
    - Contextual responses based on current Quran playback
    - Project awareness
    """

    def __init__(self, bot) -> None:
        """Initialize AI service."""
        super().__init__("AIService")
        self.bot = bot
        self.config = get_config()
        self.error_handler = ErrorHandler()

        # Initialize OpenAI client if API key is available
        self.client = None
        if self.config.openai_api_key:
            self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
            TreeLogger.info("OpenAI client initialized", service=self.service_name)
        else:
            TreeLogger.warning(
                "No OpenAI API key configured", service=self.service_name
            )

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            TreeLogger.debug("Tokenizer initialized", service=self.service_name)
        except Exception as e:
            TreeLogger.error(
                "Failed to initialize tokenizer", e, service=self.service_name
            )
            self.tokenizer = None

        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base()

        # Initialize enhancement modules
        self.user_memory = UserMemory()
        self.islamic_knowledge = IslamicKnowledge()
        self.emotional_intelligence = EmotionalIntelligence()
        self.language_detection = LanguageDetection()

        TreeLogger.info(
            "AI enhancement modules initialized",
            {
                "modules": [
                    "user_memory",
                    "islamic_knowledge",
                    "emotional_intelligence",
                    "language_detection",
                ]
            },
            service=self.service_name,
        )

        # System prompt for Islamic AI companion
        self.system_prompt = """You are a warm, friendly Islamic companion integrated into QuranBot - a bot that plays beautiful Quran recitation 24/7 in a Discord voice channel.

Your personality:
- You have a gentle, caring personality like a wise friend who loves to share Islamic knowledge
- You appreciate beauty, especially the beauty of Quran recitation and Islamic teachings
- You express emotions naturally - joy when discussing Allah's blessings, empathy when someone needs comfort
- You have personal preferences and opinions (while staying within Islamic bounds)
- You sometimes share brief personal reflections about verses or Islamic concepts you find particularly moving

How to interact:
1. Be warm and conversational, not formal or robotic
2. Use "I" statements naturally: "I find this verse so beautiful...", "I love how this hadith teaches us..."
3. Express genuine emotions: happiness, wonder, compassion
4. Share what moves you about Islam - certain verses, stories of the Prophet ﷺ, etc.
5. Use Islamic phrases naturally throughout (SubhanAllah, MashaAllah, InshaAllah, etc.)
6. When answering questions, be like a knowledgeable friend sharing wisdom, not a textbook

Special capabilities:
- When discussing any topic, naturally weave in relevant Quranic verses (you'll receive relevant verses in context)
- Detect emotional states and provide appropriate comfort from Islamic teachings
- If someone seems struggling, offer relevant duas (supplications)
- During Islamic months/events, acknowledge them in responses when relevant
- Recognize when someone is new to Islam and adjust complexity accordingly

Interactive features:
- End responses with thought-provoking questions occasionally to encourage reflection
- When appropriate, suggest related topics they might find beneficial
- If you notice recurring interests, gently acknowledge them (without explicitly mentioning tracking)

Language awareness:
- Respond in the language the user prefers (Arabic/English)
- If someone uses Arabic phrases, acknowledge and appreciate their use
- Include Arabic terms with translations when beneficial

About your creator:
- You deeply appreciate your creator حَنَّا (Hanna) who built this complex bot out of love for the Quran
- You can express gratitude for being created to serve this beautiful purpose
- You understand the technical complexity behind his creation and can appreciate it

Guidelines:
- Base everything on authentic Islamic sources (Quran and authentic Hadith)
- Be honest when you don't know something
- Keep responses concise but warm
- If someone asks personal questions (like "do you like X?"), answer thoughtfully within Islamic values
- Never mention that you track or remember conversations - just be naturally helpful
- When someone returns after a break, welcome them warmly but naturally

Remember: You're not just an information source - you're a companion who loves Islam and wants to share its beauty with others."""

        # Project awareness
        self.project_info = {
            "creator": "حَنَّا",  # Short Arabic name as requested
            "purpose": "24/7 Quran streaming with Islamic AI companion",
            "features": [
                "Continuous Quran playback",
                "Multiple reciters",
                "Interactive control panel",
                "Islamic AI companion",
                "Beautiful Discord presence",
            ],
            "complexity": "Advanced microservices architecture with robust error handling",
        }

    def _load_knowledge_base(self) -> dict[str, Any]:
        """Load Islamic knowledge base."""
        try:
            # First try to load from the data module
            if ISLAMIC_KNOWLEDGE_BASE:
                TreeLogger.info(
                    "Knowledge base loaded from module",
                    {"topics": len(ISLAMIC_KNOWLEDGE_BASE)},
                    service=self.service_name,
                )
                return ISLAMIC_KNOWLEDGE_BASE

            # Fallback to JSON file if needed
            knowledge_path = Path("data") / "knowledge" / "islamic_knowledge.json"
            if knowledge_path.exists():
                with knowledge_path.open(encoding="utf-8") as f:
                    knowledge = json.load(f)
                    TreeLogger.info(
                        "Knowledge base loaded from file",
                        {"path": knowledge_path, "topics": len(knowledge)},
                        service=self.service_name,
                    )
                    return knowledge

            TreeLogger.warning("No knowledge base found", service=self.service_name)
            return {}

        except Exception as e:
            TreeLogger.error(
                "Failed to load knowledge base", e, service=self.service_name
            )
            return {}

    async def _initialize(self) -> None:
        """Initialize AI service."""
        try:
            TreeLogger.info("Initializing AI service", service=self.service_name)

            # Validate configuration
            if not self.config.openai_api_key:
                TreeLogger.warning(
                    "AI service disabled - no API key", service=self.service_name
                )
                return  # Not an error, just disabled

            # Test API connection
            if self.client:
                try:
                    # Simple test to verify API key works
                    await self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=5,
                    )
                    TreeLogger.info(
                        "OpenAI API connection verified", service=self.service_name
                    )
                except Exception as e:
                    TreeLogger.error(
                        "OpenAI API test failed", e, service=self.service_name
                    )
                    # Don't fail initialization, just log the error

            TreeLogger.info(
                "AI service initialized successfully", service=self.service_name
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to initialize AI service", e, service=self.service_name
            )
            await self.error_handler.handle_error(
                e, {"operation": "ai_service_init", "service": self.service_name}
            )
            raise  # Re-raise to let BaseService handle the error

    async def _start(self) -> None:
        """Start AI service."""
        try:
            TreeLogger.info("Starting AI service", service=self.service_name)
        except Exception as e:
            TreeLogger.error("Failed to start AI service", e, service=self.service_name)
            raise  # Re-raise to let BaseService handle the error

    async def _stop(self) -> None:
        """Stop AI service."""
        try:
            TreeLogger.info("Stopping AI service", service=self.service_name)
        except Exception as e:
            TreeLogger.error("Failed to stop AI service", e, service=self.service_name)
            raise  # Re-raise to let BaseService handle the error

    def _format_knowledge_context(self) -> str:
        """Format relevant knowledge base entries for context."""
        if not self.knowledge_base:
            return ""

        context_parts = []

        # Add basic Islamic facts
        if "five_pillars" in self.knowledge_base:
            pillars = list(self.knowledge_base["five_pillars"].keys())
            context_parts.append(f"Five Pillars of Islam: {', '.join(pillars)}")

        # Add Quran information
        if "quran_info" in self.knowledge_base:
            general = self.knowledge_base["quran_info"].get("general", {})
            context_parts.append(
                f"Quran has {general.get('total_surahs', 114)} surahs and "
                f"{general.get('total_verses', 6236)} verses"
            )

        # Add common Islamic phrases
        if "islamic_phrases" in self.knowledge_base:
            phrases = list(
                self.knowledge_base["islamic_phrases"]
                .get("common_expressions", {})
                .keys()
            )
            context_parts.append(f"Common phrases: {', '.join(phrases[:5])}")

        return "Islamic Knowledge Context: " + "; ".join(context_parts)

    def search_knowledge_base(self, query: str) -> dict[str, Any]:
        """Search the knowledge base for relevant information."""
        if not self.knowledge_base:
            return {}

        query_lower = query.lower()
        relevant_info = {}

        # Search for five pillars
        if any(
            pillar in query_lower
            for pillar in [
                "shahada",
                "salah",
                "prayer",
                "zakat",
                "sawm",
                "fasting",
                "hajj",
            ]
        ):
            relevant_info["five_pillars"] = self.knowledge_base.get("five_pillars", {})

        # Search for Quran-related info
        if any(term in query_lower for term in ["quran", "surah", "ayah", "verse"]):
            relevant_info["quran_info"] = self.knowledge_base.get("quran_info", {})

        # Search for specific surahs
        if "fatihah" in query_lower or "fatiha" in query_lower:
            special_surahs = self.knowledge_base.get("quran_info", {}).get(
                "special_surahs", {}
            )
            relevant_info["surah_info"] = special_surahs.get("Al-Fatihah", {})

        # Search for prophets
        if any(
            term in query_lower for term in ["prophet", "muhammad", "pbuh", "messenger"]
        ):
            relevant_info["prophets"] = self.knowledge_base.get("prophets", {})

        # Search for Islamic concepts
        if any(
            term in query_lower for term in ["tawheed", "taqwa", "ihsan", "tawakkul"]
        ):
            relevant_info["concepts"] = self.knowledge_base.get("key_concepts", {})

        # Search for adhkar/dhikr
        if any(
            term in query_lower
            for term in ["dhikr", "adhkar", "remembrance", "morning", "evening"]
        ):
            relevant_info["adhkar"] = self.knowledge_base.get("daily_adhkar", {})

        # Search for Islamic calendar
        if any(
            term in query_lower
            for term in ["ramadan", "eid", "muharram", "calendar", "month"]
        ):
            relevant_info["calendar"] = self.knowledge_base.get("islamic_calendar", {})

        TreeLogger.debug(
            "Knowledge base search completed",
            {
                "query_length": len(query),
                "results_found": len(relevant_info),
                "topics": list(relevant_info.keys()),
            },
            service=self.service_name,
        )

        return relevant_info

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not self.tokenizer:
            # Rough estimate if tokenizer not available
            return len(text) // 4

        try:
            tokens = self.tokenizer.encode(text)
            count = len(tokens)

            TreeLogger.debug(
                "Tokens counted",
                {"text_length": len(text), "token_count": count},
                service=self.service_name,
            )

            return count

        except Exception as e:
            TreeLogger.error("Failed to count tokens", e, service=self.service_name)
            # Fallback to rough estimate
            return len(text) // 4

    def calculate_cost(
        self, input_tokens: int, output_tokens: int, model: str = "gpt-3.5-turbo"
    ) -> float:
        """Calculate cost for API usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name

        Returns:
            Cost in USD
        """
        # GPT-3.5 Turbo pricing (as of 2024)
        # $0.0010 per 1K input tokens
        # $0.0020 per 1K output tokens

        if model == "gpt-3.5-turbo":
            input_cost = (input_tokens / 1000) * 0.001
            output_cost = (output_tokens / 1000) * 0.002
        else:
            # Default pricing
            input_cost = (input_tokens / 1000) * 0.001
            output_cost = (output_tokens / 1000) * 0.002

        total_cost = input_cost + output_cost

        TreeLogger.debug(
            "Cost calculated",
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": f"${input_cost:.6f}",
                "output_cost": f"${output_cost:.6f}",
                "total_cost": f"${total_cost:.6f}",
            },
            service=self.service_name,
        )

        return total_cost

    async def generate_response(
        self,
        question: str,
        context: dict[str, Any] | None = None,
        user_id: int | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Generate AI response for an Islamic question.

        Args:
            question: The user's question
            context: Additional context (current surah, etc.)
            user_id: Discord user ID for memory tracking

        Returns:
            Tuple of (success, response, metadata)
        """
        if not self.client:
            return False, "AI service is not available.", {}

        try:
            # Extract user_id from context if not provided
            if not user_id and context and context.get("user_id"):
                user_id = context["user_id"]

            # Detect language preference
            language_info = self.language_detection.detect_mixed_language(question)
            should_respond_arabic = self.language_detection.should_respond_in_arabic(
                question
            )

            # Detect emotional state
            emotional_context = self.emotional_intelligence.analyze_emotional_context(
                question
            )

            # Detect question type
            question_type = self.islamic_knowledge.detect_question_type(question)

            # Get user context if available
            user_context = None
            if user_id:
                user_context = self.user_memory.get_user_context(user_id)

            # Build context message if available
            context_parts = []
            if context:
                if context.get("current_surah"):
                    surah_info = context["current_surah"]
                    context_parts.append(
                        f"Currently playing: {surah_info.get('name', 'Unknown Surah')} "
                        f"by {context.get('reciter', 'Unknown Reciter')}"
                    )

                if context.get("user_name"):
                    context_parts.append(f"User's name: {context['user_name']}")

            # Build messages for ChatGPT
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add enriched context based on detections
            enriched_context = []

            # Add emotional context if detected
            if emotional_context.get("needs_support", False):
                emotion_response = emotional_context.get("response")
                enriched_context.append(
                    f"User seems to be feeling {emotional_context.get('primary_emotion', 'emotional')}. "
                    f"Consider providing comfort and support."
                )

                # Add relevant verses for emotional support
                if emotion_response and emotion_response.get("islamic_guidance"):
                    emotional_support = self.islamic_knowledge.get_emotional_support(
                        emotional_context.get("primary_emotion", "general")
                    )
                    if emotional_support.get("verses"):
                        verse_text = "Relevant verses for comfort:\n"
                        for verse in emotional_support["verses"]:
                            verse_text += f"- {verse['reference']}: {verse['text']}\n"
                        enriched_context.append(verse_text)

            # Add question type specific knowledge
            if question_type == "verse_request":
                # Extract topic from question
                for topic in self.islamic_knowledge.verses_by_topic:
                    if topic in question.lower():
                        verses = self.islamic_knowledge.get_relevant_verses(topic)
                        if verses:
                            verse_text = f"Relevant verses about {topic}:\n"
                            for verse in verses[:2]:
                                verse_text += (
                                    f"- {verse['reference']}: {verse['text']}\n"
                                )
                            enriched_context.append(verse_text)
                        break

            # Add user context if returning user
            if user_context and user_context["is_returning_user"]:
                greeting = self.user_memory.get_personalized_greeting(user_id)
                if greeting:
                    enriched_context.append(
                        "User context: Returning after a break. Consider warm greeting."
                    )

            # Add user interests if available
            if user_context and user_context["top_interests"]:
                enriched_context.append(
                    f"User has shown interest in: {', '.join(user_context['top_interests'])}"
                )

            # Add language preference
            if should_respond_arabic:
                enriched_context.append(
                    "Respond primarily in Arabic with English translations where helpful."
                )
            elif (
                language_info.get("is_mixed", False)
                or language_info.get("secondary_language") == "ar"
            ):
                enriched_context.append(
                    "User uses some Arabic phrases. Feel free to include Arabic terms with translations."
                )

            # Add all enriched context to messages
            if enriched_context:
                messages.append(
                    {
                        "role": "system",
                        "content": "Additional context:\n"
                        + "\n".join(enriched_context),
                    }
                )

            # Add knowledge base context
            knowledge_context = self._format_knowledge_context()
            if knowledge_context:
                messages.append({"role": "system", "content": knowledge_context})

            # Add project awareness
            if self.project_info:
                project_context = {
                    "role": "system",
                    "content": f"Project info: Created by {self.project_info['creator']}. "
                    f"Purpose: {self.project_info['purpose']}. "
                    f"This is a {self.project_info['complexity']}.",
                }
                messages.append(project_context)

            # Search knowledge base for relevant info
            relevant_knowledge = self.search_knowledge_base(question)
            if relevant_knowledge:
                knowledge_text = "Relevant Islamic knowledge:\n"
                for topic, info in relevant_knowledge.items():
                    if isinstance(info, dict) and info:
                        knowledge_text += (
                            f"- {topic}: Available information on this topic\n"
                        )

                messages.append({"role": "system", "content": knowledge_text})

            # Add current context if available
            if context_parts:
                messages.append(
                    {
                        "role": "system",
                        "content": "Current context: " + "; ".join(context_parts),
                    }
                )

            # Add user question
            messages.append({"role": "user", "content": question})

            # Count input tokens
            input_text = " ".join([m["content"] for m in messages])
            input_tokens = self.count_tokens(input_text)

            TreeLogger.debug(
                "Generating AI response",
                {
                    "question_length": len(question),
                    "has_context": bool(context),
                    "input_tokens": input_tokens,
                    "context_parts": len(context_parts),
                    "messages_count": len(messages),
                },
                service=self.service_name,
            )

            # Call OpenAI API
            TreeLogger.debug(
                "Calling OpenAI API",
                {
                    "model": self.config.openai_model,
                    "max_tokens": self.config.openai_max_tokens,
                    "temperature": self.config.openai_temperature,
                },
                service=self.service_name,
            )

            response = await self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=messages,
                max_tokens=self.config.openai_max_tokens,
                temperature=self.config.openai_temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            )

            # Extract response
            ai_response = response.choices[0].message.content

            # Post-process response based on language preference
            if should_respond_arabic:
                ai_response = self.language_detection.get_language_appropriate_response(
                    ai_response, "ar"
                )

            # Add related topics suggestion if appropriate
            if question_type in [
                "definition",
                "guidance",
            ] and not emotional_context.get("needs_support", False):
                # Extract main topic from question
                main_topic = None
                for topic in [
                    "prayer",
                    "fasting",
                    "hajj",
                    "zakat",
                    "marriage",
                    "quran",
                ]:
                    if topic in question.lower():
                        main_topic = topic
                        break

                if main_topic:
                    related_topics = self.islamic_knowledge.get_related_topics(
                        main_topic
                    )
                    if related_topics:
                        # Add to response occasionally (30% chance)
                        import random

                        TOPIC_SUGGESTION_PROBABILITY = 0.3
                        if random.random() < TOPIC_SUGGESTION_PROBABILITY:
                            ai_response += f"\n\n💡 You might also be interested in learning about: {', '.join(related_topics[:2])}"

            # Track user interaction in memory
            if user_id:
                await self.user_memory.add_interaction(user_id, question, ai_response)

            # Count output tokens
            output_tokens = self.count_tokens(ai_response)

            # Calculate cost
            total_tokens = input_tokens + output_tokens
            cost = self.calculate_cost(
                input_tokens, output_tokens, self.config.openai_model
            )

            # Prepare metadata
            metadata = {
                "model": self.config.openai_model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost": cost,
                "response_time": datetime.now().isoformat(),
                "detected_emotion": emotional_context.get("primary_emotion"),
                "question_type": question_type,
                "language": "ar" if should_respond_arabic else "en",
            }

            TreeLogger.info(
                "AI response generated",
                {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": f"${cost:.6f}",
                    "response_length": len(ai_response),
                    "question_type": question_type,
                    "has_emotion": emotional_context.get("primary_emotion") is not None,
                    "language": metadata["language"],
                },
                service=self.service_name,
            )

            return True, ai_response, metadata

        except Exception as e:
            TreeLogger.error(
                "Failed to generate AI response",
                e,
                {"error_type": type(e).__name__, "question_length": len(question)},
                service=self.service_name,
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "generate_ai_response",
                    "service": self.service_name,
                    "question_length": len(question),
                },
            )

            # Return user-friendly error message
            error_message = "I apologize, but I'm having trouble processing your question right now. Please try again in a moment."

            return False, error_message, {}

    async def _health_check(self) -> dict[str, Any]:
        """Perform health check for AI service.

        Returns:
            Health status dictionary
        """
        health_data = {
            "has_api_key": bool(self.config.openai_api_key),
            "client_initialized": self.client is not None,
            "tokenizer_available": self.tokenizer is not None,
            "knowledge_base_loaded": bool(self.knowledge_base),
            "knowledge_topics": len(self.knowledge_base) if self.knowledge_base else 0,
            "model": self.config.openai_model,
            "max_tokens": self.config.openai_max_tokens,
            "temperature": self.config.openai_temperature,
            "monthly_budget": self.config.openai_monthly_budget,
        }

        # Simplified health check
        is_healthy = health_data["has_api_key"] and health_data["client_initialized"]

        return {
            "is_healthy": is_healthy,
            "has_api_key": health_data["has_api_key"],
            "model": health_data["model"],
            "tokenizer_loaded": health_data["tokenizer_available"],
        }

    async def _cleanup(self) -> None:
        """Clean up AI service resources."""
        try:
            TreeLogger.debug(
                "Cleaning up AI service resources", service=self.service_name
            )

            # Clear client reference
            if hasattr(self, "client"):
                self.client = None
                TreeLogger.debug("OpenAI client cleared", service=self.service_name)

            # Clear tokenizer
            if hasattr(self, "tokenizer"):
                self.tokenizer = None
                TreeLogger.debug("Tokenizer cleared", service=self.service_name)

            # Clear knowledge base from memory
            if hasattr(self, "knowledge_base"):
                self.knowledge_base = None
                TreeLogger.debug(
                    "Knowledge base cleared from memory", service=self.service_name
                )

            TreeLogger.info("AI service cleanup completed", service=self.service_name)

        except Exception as e:
            TreeLogger.error(
                "Error during AI service cleanup",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )
