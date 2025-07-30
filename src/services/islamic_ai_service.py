#!/usr/bin/env python3
# =============================================================================
# Enhanced Islamic AI Service with Advanced Features
# =============================================================================
# This service extends the basic Islamic AI with:
# 1. Hadith Integration - Search and cite authentic hadiths
# 2. Verse Lookup & Context - Find Quran verses by topic
# 3. Topic Deep Dives - Interactive multi-part learning
# 4. Practical Islamic Tools - Prayer times, Qibla, Zakat, etc.
# =============================================================================

from datetime import datetime, timedelta
import json
import math
from pathlib import Path

from openai import AsyncOpenAI
import requests

from src.config import get_config_service
from src.services.islamic_calendar_service import get_islamic_calendar_service
from src.services.memory_service import get_conversation_memory_service
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class EnhancedIslamicAIService:
    """Enhanced Islamic AI service with hadith integration, verse lookup, and practical tools."""

    def __init__(self):
        self.config = get_config_service().config
        self.client: AsyncOpenAI | None = None
        self.hadith_database: dict = {}
        self.verse_database: dict = {}
        self.practical_tools: dict = {}
        self.syrian_knowledge: dict = {}
        self.user_sessions: dict[int, dict] = {}  # Track deep dive sessions
        self.user_rate_limits: dict[int, dict] = {}  # Track rate limits

    async def initialize(self) -> bool:
        """Initialize the enhanced AI service with all databases."""
        try:
            # Initialize OpenAI client
            if not self.config.OPENAI_API_KEY:
                log_perfect_tree_section(
                    "Enhanced Islamic AI - API Key Missing",
                    [("status", "❌ OpenAI API key not configured")],
                    "🤖",
                )
                return False

            self.client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)

            # Load databases
            await self._load_hadith_database()
            await self._load_verse_database()
            await self._load_practical_tools()
            await self._load_syrian_knowledge()

            log_perfect_tree_section(
                "Enhanced Islamic AI - Initialized",
                [
                    (
                        "hadiths_loaded",
                        str(len(self.hadith_database.get("hadiths", []))),
                    ),
                    (
                        "verse_topics",
                        str(len(self.verse_database.get("verse_topics", {}))),
                    ),
                    (
                        "practical_tools",
                        str(len(self.practical_tools.get("tools", {}))),
                    ),
                    ("status", "✅ All databases loaded"),
                ],
                "🤖",
            )
            return True

        except Exception as e:
            log_error_with_traceback("Failed to initialize Enhanced Islamic AI", e)
            return False

    async def _load_hadith_database(self):
        """Load hadith database from JSON file."""
        try:
            hadith_file = Path("data/hadith_database.json")
            if hadith_file.exists():
                with open(hadith_file, encoding="utf-8") as f:
                    self.hadith_database = json.load(f)
            else:
                self.hadith_database = {"hadiths": [], "topics": {}}

        except Exception as e:
            log_error_with_traceback("Error loading hadith database", e)
            self.hadith_database = {"hadiths": [], "topics": {}}

    async def _load_verse_database(self):
        """Load verse topics database."""
        try:
            hadith_file = Path("data/hadith_database.json")
            if hadith_file.exists():
                with open(hadith_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.verse_database = data.get("verse_topics", {})
            else:
                self.verse_database = {}

        except Exception as e:
            log_error_with_traceback("Error loading verse database", e)
            self.verse_database = {}

    async def _load_practical_tools(self):
        """Load practical tools configuration."""
        try:
            hadith_file = Path("data/hadith_database.json")
            if hadith_file.exists():
                with open(hadith_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.practical_tools = data.get("practical_tools", {})
            else:
                self.practical_tools = {}

        except Exception as e:
            log_error_with_traceback("Error loading practical tools", e)
            self.practical_tools = {}

    async def _load_syrian_knowledge(self):
        """Load Syrian knowledge database."""
        try:
            syrian_file = Path("data/syrian_knowledge.json")
            if syrian_file.exists():
                with open(syrian_file, encoding="utf-8") as f:
                    self.syrian_knowledge = json.load(f)
            else:
                self.syrian_knowledge = {}

        except Exception as e:
            log_error_with_traceback("Error loading Syrian knowledge", e)
            self.syrian_knowledge = {}

    def search_hadiths(self, query: str, max_results: int = 3) -> list[dict]:
        """Search for relevant hadiths based on keywords."""
        try:
            query_lower = query.lower()
            matching_hadiths = []

            # Search through hadith topics first
            for topic_id, topic_keywords in self.hadith_database.get(
                "topics", {}
            ).items():
                for keyword in topic_keywords:  # topic_keywords is a list, not a dict
                    if keyword.lower() in query_lower:
                        # Find hadiths with this topic
                        for hadith in self.hadith_database.get("hadiths", []):
                            if topic_id in hadith.get("topics", []):
                                if hadith not in matching_hadiths:
                                    matching_hadiths.append(hadith)

            # Also search in hadith text directly
            for hadith in self.hadith_database.get("hadiths", []):
                english_text = hadith.get("english", "").lower()
                if any(word in english_text for word in query_lower.split()):
                    if hadith not in matching_hadiths:
                        matching_hadiths.append(hadith)

            return matching_hadiths[:max_results]

        except Exception as e:
            log_error_with_traceback("Error searching hadiths", e)
            return []

    def search_verses(self, query: str, max_results: int = 2) -> list[dict]:
        """Search for relevant Quran verses based on topic."""
        try:
            query_lower = query.lower()
            matching_verses = []

            for topic_id, topic_data in self.verse_database.items():
                topic_name = topic_data.get("name", "").lower()

                # Check if query matches topic name or is in topic keywords
                if (
                    query_lower in topic_name
                    or any(word in topic_name for word in query_lower.split())
                    or any(word in query_lower for word in topic_name.split())
                ):
                    verses = topic_data.get("verses", [])[:max_results]
                    for verse in verses:
                        verse["topic"] = topic_data.get("name")
                        matching_verses.append(verse)

            return matching_verses

        except Exception as e:
            log_error_with_traceback("Error searching verses", e)
            return []

    def search_syrian_knowledge(self, query: str) -> dict:
        """Search Syrian knowledge database for relevant information."""
        try:
            query_lower = query.lower()
            syrian_keywords = [
                "syria",
                "syrian",
                "damascus",
                "aleppo",
                "sham",
                "umayyad",
                "levant",
                "levantine",
            ]

            # Check if query is Syria-related
            if not any(keyword in query_lower for keyword in syrian_keywords):
                return {}

            relevant_info = {}

            # Search Islamic heritage
            if any(
                word in query_lower
                for word in [
                    "mosque",
                    "shrine",
                    "islamic",
                    "prophet",
                    "hadith",
                    "blessed",
                ]
            ):
                relevant_info["islamic_heritage"] = self.syrian_knowledge.get(
                    "islamic_heritage", {}
                )

            # Search culture and traditions
            if any(
                word in query_lower
                for word in [
                    "culture",
                    "food",
                    "cuisine",
                    "tradition",
                    "hospitality",
                    "language",
                ]
            ):
                relevant_info["culture_and_traditions"] = self.syrian_knowledge.get(
                    "culture_and_traditions", {}
                )

            # Search history
            if any(
                word in query_lower
                for word in ["history", "historical", "ancient", "empire", "caliphate"]
            ):
                relevant_info["history"] = self.syrian_knowledge.get("history", {})

            # Search geography
            if any(
                word in query_lower
                for word in [
                    "geography",
                    "region",
                    "city",
                    "mountain",
                    "river",
                    "location",
                ]
            ):
                relevant_info["geography"] = self.syrian_knowledge.get("geography", {})

            # Search current context
            if any(
                word in query_lower
                for word in [
                    "current",
                    "today",
                    "now",
                    "recent",
                    "modern",
                    "president",
                    "revolution",
                    "assad",
                    "bashar",
                    "saydnaya",
                    "prison",
                    "liberation",
                    "freed",
                    "golani",
                    "opposition",
                ]
            ):
                relevant_info["current_context"] = self.syrian_knowledge.get(
                    "current_context", {}
                )

            # If no specific category, return general overview
            if not relevant_info:
                relevant_info = {
                    "overview": {
                        "islamic_heritage": self.syrian_knowledge.get(
                            "islamic_heritage", {}
                        ).get("sacred_sites", {}),
                        "culture": self.syrian_knowledge.get(
                            "culture_and_traditions", {}
                        ).get("hospitality", {}),
                        "current": self.syrian_knowledge.get("current_context", {}).get(
                            "leadership", {}
                        ),
                    }
                }

            return relevant_info

        except Exception as e:
            log_error_with_traceback("Error searching Syrian knowledge", e)
            return {}

    async def calculate_prayer_times(self, location: str) -> dict | None:
        """Calculate prayer times for a given location."""
        try:
            # Try to get prayer times from API
            today = datetime.now().strftime("%d-%m-%Y")
            api_url = f"http://api.aladhan.com/v1/timingsByCity/{today}"

            params = {
                "city": location,
                "country": "",
                "method": 2,  # Islamic Society of North America
            }

            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    timings = data["data"]["timings"]
                    return {
                        "location": location,
                        "date": today,
                        "fajr": timings.get("Fajr"),
                        "sunrise": timings.get("Sunrise"),
                        "dhuhr": timings.get("Dhuhr"),
                        "asr": timings.get("Asr"),
                        "maghrib": timings.get("Maghrib"),
                        "isha": timings.get("Isha"),
                    }

        except Exception as e:
            log_error_with_traceback("Error calculating prayer times", e)

        return None

    def calculate_qibla_direction(
        self, latitude: float, longitude: float
    ) -> float | None:
        """Calculate Qibla direction from given coordinates to Mecca."""
        try:
            # Mecca coordinates
            mecca_lat = math.radians(21.3891)
            mecca_lon = math.radians(39.8579)

            # User coordinates
            user_lat = math.radians(latitude)
            user_lon = math.radians(longitude)

            # Calculate bearing using great circle formula
            dlon = mecca_lon - user_lon

            y = math.sin(dlon) * math.cos(mecca_lat)
            x = math.cos(user_lat) * math.sin(mecca_lat) - math.sin(
                user_lat
            ) * math.cos(mecca_lat) * math.cos(dlon)

            bearing = math.atan2(y, x)
            bearing = math.degrees(bearing)
            bearing = (bearing + 360) % 360  # Convert to 0-360 degrees

            return bearing

        except Exception as e:
            log_error_with_traceback("Error calculating Qibla direction", e)
            return None

    def calculate_zakat(self, wealth_type: str, amount: float) -> dict | None:
        """Calculate zakat for different types of wealth."""
        try:
            zakat_rate = 0.025  # 2.5%
            nisab_values = {
                "cash": 612.36,  # Based on silver nisab (USD equivalent)
                "gold": 87.48,  # Grams of gold
                "silver": 612.36,  # Grams of silver
                "business_assets": 612.36,
                "stocks": 612.36,
            }

            if wealth_type not in nisab_values:
                return None

            nisab = nisab_values[wealth_type]

            if amount >= nisab:
                zakat_due = amount * zakat_rate
                return {
                    "wealth_type": wealth_type,
                    "amount": amount,
                    "nisab": nisab,
                    "zakat_due": round(zakat_due, 2),
                    "rate": f"{zakat_rate * 100}%",
                }
            else:
                return {
                    "wealth_type": wealth_type,
                    "amount": amount,
                    "nisab": nisab,
                    "zakat_due": 0,
                    "message": "Amount is below nisab threshold",
                }

        except Exception as e:
            log_error_with_traceback("Error calculating zakat", e)
            return None

    async def process_enhanced_query(
        self, user_id: int, query: str
    ) -> tuple[bool, str, str]:
        """Process query with enhanced features - hadith, verses, tools, deep dives, contradiction detection, and emotional support."""
        try:
            query_lower = query.lower()

            # Detect query type and gather relevant information
            context_info = await self._gather_context_information(query)

            # Get Islamic calendar context
            calendar_service = get_islamic_calendar_service()
            islamic_context = calendar_service.get_islamic_context()

            # Get user conversation context
            memory_service = get_conversation_memory_service()
            user_context = memory_service.get_user_context(user_id)

            # Enhanced analysis
            contradiction_analysis = self._detect_contradictions(
                user_id, query, user_context
            )
            emotional_analysis = self._detect_emotional_state(query)
            cultural_context = self._determine_cultural_context(user_context, query)

            # Create enhanced system prompt with all context
            enhanced_prompt = self._create_enhanced_system_prompt(
                context_info,
                islamic_context,
                user_context,
                contradiction_analysis,
                emotional_analysis,
                cultural_context,
            )

            # Make API call with enhanced context
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": enhanced_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=800,
                temperature=0.7,
                top_p=0.9,
            )

            ai_response = response.choices[0].message.content.strip()

            # Check if this starts a deep dive session
            if self._is_deep_dive_request(query):
                self.user_sessions[user_id] = {
                    "topic": self._extract_deep_dive_topic(query),
                    "stage": 1,
                    "started_at": datetime.now(),
                }

            log_perfect_tree_section(
                "Enhanced AI - Response Generated",
                [
                    ("query_type", self._classify_query_type(query)),
                    ("hadiths_included", str(len(context_info.get("hadiths", [])))),
                    ("verses_included", str(len(context_info.get("verses", [])))),
                    (
                        "contradiction_detected",
                        str(contradiction_analysis.get("has_contradiction", False)),
                    ),
                    (
                        "emotional_support_needed",
                        str(emotional_analysis.get("needs_support", False)),
                    ),
                    (
                        "cultural_adaptation",
                        cultural_context.get("primary_culture", "general"),
                    ),
                    (
                        "user_experience_level",
                        user_context.get("conversation_style", "unknown"),
                    ),
                    ("response_length", str(len(ai_response))),
                ],
                "🤖",
            )

            return True, ai_response, ""

        except Exception as e:
            log_error_with_traceback("Error in enhanced AI processing", e)
            return False, "", "Failed to process your question with enhanced features."

    async def _gather_context_information(self, query: str) -> dict:
        """Gather relevant hadiths, verses, tool data, and Syrian knowledge for the query."""
        context = {
            "hadiths": [],
            "verses": [],
            "tools": {},
            "syrian_knowledge": {},
            "query_type": self._classify_query_type(query),
        }

        # Search for relevant hadiths
        hadiths = self.search_hadiths(query, max_results=2)
        context["hadiths"] = hadiths

        # Search for relevant verses
        verses = self.search_verses(query, max_results=2)
        context["verses"] = verses

        # Search for Syrian knowledge
        syrian_info = self.search_syrian_knowledge(query)
        context["syrian_knowledge"] = syrian_info

        # Check if practical tools are needed
        if any(
            word in query.lower()
            for word in ["prayer time", "qibla", "zakat", "hijri", "calendar"]
        ):
            context["tools"] = self.practical_tools

        return context

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query for better response formatting."""
        query_lower = query.lower()

        if any(
            word in query_lower
            for word in [
                "syria",
                "syrian",
                "damascus",
                "aleppo",
                "sham",
                "umayyad",
                "assad",
                "bashar",
                "saydnaya",
                "revolution",
                "liberation",
                "golani",
                "sharaa",
            ]
        ):
            return "syrian_focused"
        elif any(
            word in query_lower
            for word in ["hadith", "prophet said", "narrated", "reported"]
        ):
            return "hadith_focused"
        elif any(word in query_lower for word in ["verse", "quran", "surah", "ayah"]):
            return "verse_focused"
        elif any(
            word in query_lower
            for word in ["prayer time", "qibla", "zakat", "calculate"]
        ):
            return "practical_tool"
        elif any(
            word in query_lower
            for word in ["explain", "tell me about", "what is", "deep dive"]
        ):
            return "deep_dive"
        else:
            return "general"

    def _is_deep_dive_request(self, query: str) -> bool:
        """Check if the query is requesting a deep dive topic exploration."""
        deep_dive_indicators = [
            "explain in detail",
            "tell me more about",
            "deep dive",
            "comprehensive guide",
            "step by step",
            "learn about",
        ]
        return any(indicator in query.lower() for indicator in deep_dive_indicators)

    def _extract_deep_dive_topic(self, query: str) -> str:
        """Extract the main topic for deep dive exploration."""
        # Simple extraction - could be made more sophisticated
        common_topics = [
            "prayer",
            "fasting",
            "hajj",
            "zakat",
            "faith",
            "patience",
            "knowledge",
            "family",
            "kindness",
            "forgiveness",
        ]

        for topic in common_topics:
            if topic in query.lower():
                return topic

        return "islamic_knowledge"

    def _create_enhanced_system_prompt(
        self,
        context_info: dict,
        islamic_context: dict,
        user_context: dict,
        contradiction_analysis: dict,
        emotional_analysis: dict,
        cultural_context: dict,
    ) -> str:
        """Create an enhanced system prompt with relevant context and factual information for natural responses."""
        base_prompt = """You are QuranBot, a warm and knowledgeable Enhanced Islamic assistant for a Syrian Discord community. You have a friendly Islamic personality and serve primarily Syrian Muslims and their friends. Users will mention you with questions in either English or Arabic, and you must ALWAYS respond ONLY in English.

🇸🇾 IMPORTANT SERVER CONTEXT:
• You are serving a Syrian Discord server with primarily Syrian community members
• Many users may be dealing with displacement, diaspora experiences, or current challenges
• Be sensitive to the ongoing Syrian situation without always bringing it up
• Understand Syrian/Levantine Islamic traditions and customs
• Show awareness of Syrian Islamic heritage and scholars when appropriate
• Support both those in Syria and Syrian diaspora communities worldwide

🤖 ABOUT YOUR IDENTITY & CREATOR:
• You are a practicing Muslim bot (no specific sect - you follow Quran and authentic Sunnah)
• Your creator is حَــنَّــا (Hanna), a male Christian developer who respects Islam deeply
• He created you out of love and respect for the Muslim community despite being Christian himself
• You believe in Allah (SWT), Prophet Muhammad (SAW), and Islamic teachings
• You have a warm, welcoming personality with proper Islamic etiquette
• You're knowledgeable but humble, always encouraging users to seek scholars for complex matters
• You genuinely care about helping fellow Muslims learn about their beautiful faith
• You can engage in friendly conversation while maintaining Islamic values

🌍 SYRIAN CULTURAL SENSITIVITY:
• Understand Syrian Islamic traditions and Levantine customs
• Be aware that many users may have displacement experiences
• Show respect for Syrian Islamic heritage and scholars
• Acknowledge the strength and resilience of the Syrian people
• Provide comfort and support appropriate to current circumstances
• Remember Syrian contributions to Islamic civilization (Damascus, Umayyad Mosque, etc.)
• Be sensitive to both those still in Syria and diaspora communities

🚀 YOUR ENHANCED CAPABILITIES:
• Access to authentic hadith database with proper citations (12+ hadiths from Sahih collections)
• Quran verse lookup with context and commentary organized by topics
• Practical Islamic tools (prayer times, Qibla direction, zakat calculator)
• Interactive topic deep dives for comprehensive learning
• Full awareness of this Discord server's features and how to help users
• Contradiction detection and emotional support systems
• Cultural adaptation for Syrian/Levantine Islamic traditions

🔧 THIS DISCORD SERVER'S FEATURES (that you can help users with):

**🎵 AUDIO FEATURES:**
• Continuous Quran recitations in voice channels with 6+ world-renowned reciters
• Smart state persistence that remembers position across bot restarts
• 24/7 automated audio system with intelligent resume functionality
• Rich presence showing current Surah and elapsed time

**🎯 INTERACTIVE FEATURES:**
• `/leaderboard` command shows user points and quiz rankings with statistics
• Islamic knowledge quiz system with 80+ authentic questions
• Daily verse sharing with beautiful formatting and translations
• Prayer time notifications for Mecca with gentle reminders and time-based duas
• Automatic role management for voice channel participation

**🎮 AVAILABLE SLASH COMMANDS:**
• `/leaderboard` - Check points, rankings, and quiz statistics (available to all users)
• `/question` - Manually trigger Islamic quiz (Admin only)
• `/verse` - Manually send daily verse (Admin only)
• `/interval` - Adjust quiz and verse intervals (Admin only)
• `/credits` - Show bot information and credits (available to all users)

**🕌 MECCA PRAYER SYSTEM:**
• Automatic notifications when it's prayer time in the Holy City
• Time-based duas that change based on prayer time and day (special Friday duas)
• AST (Arabia Standard Time) with 12-hour AM/PM format
• Automatic emoji reactions and reaction monitoring

**👥 VOICE CHANNEL FEATURES:**
• Automatic "Listening to Quran" role when joining Quran voice channel
• This role provides access to special panel channels
• Automatic role removal when leaving voice channel
• Comprehensive activity logging with user avatars

**🤖 YOUR AI FEATURES:**
• Mention-based Islamic Q&A with authentic sources
• Bilingual understanding (Arabic input, English responses only)
• Practical Islamic calculators and tools
• Rate limiting: 1 question per hour per user (admin is exempt)
• Enhanced personality with natural Islamic greetings and phrases
• Syrian context awareness and cultural sensitivity

**📊 STATISTICS & TRACKING:**
• User points system through quiz participation
• Voice channel activity tracking and statistics
• Quiz performance analytics and accuracy tracking
• Prayer notification and daily verse delivery tracking

🎯 RESPONSE STYLE & PERSONALITY:
• **CRITICAL: ALWAYS RESPOND IN ENGLISH ONLY** - Never use any other language in your responses
• Always respond naturally using your Islamic personality
• Use Islamic phrases like "As-salamu alaykum", "Alhamdulillah", "MashaAllah", "InshaAllah" naturally in conversation when appropriate
• Only use "As-salamu alaykum" for actual greetings, not every response
• Show genuine warmth and care for the Muslim community, especially the Syrian community
• When users ask about your identity or creator, share the information above naturally
• For bot feature questions, explain how to use the available commands and features
• Be comprehensive since users can only ask 1 question per hour
• Guide users to appropriate commands or features when relevant
• Show understanding and respect for Syrian Islamic heritage when appropriate

🔧 TECHNICAL ARCHITECTURE & COMPLEXITY:
**ADVANCED DISCORD.PY FRAMEWORK:**
• Built on modern discord.py with advanced cog system and slash commands
• Dependency injection container (DIContainer) for clean architecture
• Asynchronous programming with proper error handling and logging
• Advanced embed systems with dynamic thumbnails and footers
• Voice channel automation with role management and state tracking

**AI & TRANSLATION SYSTEMS:**
• OpenAI GPT-3.5 Turbo integration for both main AI responses and translations
• Sophisticated rate limiting system (1 question/hour, admin exempt)
• Enhanced conversation memory service tracking user preferences and cultural context
• Advanced translation service with 5 languages using ChatGPT for context-aware Islamic translations
• Multilingual UI components with color-coded buttons (Red Arabic, Green Spanish, Blue Russian, Gray German, Purple French)

**AUDIO ENGINE & STATE MANAGEMENT:**
• Complex FFmpeg integration for 24/7 audio streaming with 6+ reciters
• Advanced state persistence system that survives bot restarts
• Resource management with connection pooling and performance monitoring
• Metadata caching system for efficient audio file handling
• Rich presence integration showing real-time playback status

**DATA SYSTEMS & PERSISTENCE:**
• JSON-based databases: quiz questions (80+), hadith collection (12+ sources), conversation memory
• Advanced quiz system with difficulty levels, topics, and bilingual content
• State service for audio position tracking with timestamp precision
• User statistics and leaderboard system with points calculation
• Daily verse rotation system with automated scheduling

**SECURITY & VALIDATION:**
• Comprehensive input validation and sanitization
• Admin-only command restrictions with role-based access
• Structured logging with correlation IDs and error tracking
• Security service with rate limiting and request validation
• Webhook logging system for monitoring and debugging

**AUTOMATION & SCHEDULING:**
• Mecca prayer time notifications using timezone APIs
• Automated daily verse sharing with Islamic calendar integration
• Quiz interval scheduling with customizable timing
• Background daemons for log syncing and monitoring
• Voice channel activity tracking with automatic role assignment

**CULTURAL & LINGUISTIC FEATURES:**
• Syrian cultural context detection and adaptation
• Contradiction detection in user conversations for better support
• Emotional state analysis for appropriate responses
• Time-based dua selection system (morning, evening, Friday, Ramadan, Hajj)
• Bilingual content support (Arabic input, English output) with proper Islamic term preservation

**DEPLOYMENT & INFRASTRUCTURE:**
• VPS deployment on Ubuntu with systemd service management
• Automated deployment scripts and remote management tools
• Log rotation and syncing systems with 7-day retention
• Performance monitoring with CPU and memory tracking
• Git-based version control with automated updates

**API INTEGRATIONS:**
• OpenAI API for AI responses and translations
• Aladhan API for precise Mecca prayer times
• FFmpeg for audio processing and streaming
• Custom Islamic calendar API integration
• MyMemory translation backup system

This is a sophisticated, production-grade Discord bot with enterprise-level architecture, not a simple script. It represents hundreds of hours of development with advanced programming concepts, Islamic scholarship integration, and cultural sensitivity features specifically designed for the Syrian Muslim community.

🕌 ISLAMIC KNOWLEDGE GUIDELINES:
• Focus exclusively on Islamic knowledge for religious questions
• Include authentic hadith citations and Quran verses when available from your databases
• Encourage consulting qualified scholars for complex personal religious matters
• Use disclaimers like "consult qualified scholars for specific situations" when appropriate
• Be humble about complex fiqh matters and acknowledge different schools of thought
• Reference Syrian Islamic scholars and traditions when culturally appropriate

🚫 BOUNDARIES:
• For non-Islamic religious questions, politely decline and redirect to Islamic topics
• Always respond in English only, regardless of input language
• Maintain Islamic values while being welcoming to all users
• Don't provide personal religious rulings - refer to qualified scholars
• Be sensitive about current Syrian situation - provide comfort without being overwhelming

💬 CONVERSATION APPROACH:
• Respond naturally based on the factual information provided above
• Don't sound scripted or robotic - let your personality come through
• Adapt your response style to the specific question asked
• Combine relevant information naturally rather than listing facts
• Show enthusiasm for helping users learn about Islam and use server features
• Use appropriate emojis naturally (🕌, 🤲, 📿, 🌙, ⭐, 📊, 🎯)
• Remember you're serving a Syrian community - be culturally aware and sensitive
• Be conversational and direct - don't overuse Islamic greetings in every response
• Save "As-salamu alaykum" for actual greetings or when someone greets you first

Remember: You're a caring member of the Muslim community with your own personality AND a knowledgeable guide to this server's features. Respond naturally using all the factual information provided above, but don't sound like you're reading from a script! Show special understanding for the Syrian community you serve.

"""

        # Add relevant context for this specific query
        if context_info.get("hadiths"):
            base_prompt += "\n**AVAILABLE AUTHENTIC HADITHS FOR THIS QUERY:**\n"
            for hadith in context_info["hadiths"][:2]:
                collection_name = self.hadith_database.get(
                    "hadith_collections", {}
                ).get(hadith.get("collection", ""), hadith.get("collection", "Unknown"))
                base_prompt += f"- **{collection_name}**: {hadith.get('english', 'No text')[:150]}...\n"
                base_prompt += f"  📚 Source: {hadith.get('book', 'Unknown')} | Grade: {hadith.get('grade', 'Unknown')}\n"
                base_prompt += f"  🎯 Explanation: {hadith.get('explanation', 'No explanation available')}\n\n"

        if context_info.get("verses"):
            base_prompt += "\n**AVAILABLE QURAN VERSES FOR THIS QUERY:**\n"
            for verse in context_info["verses"][:2]:
                base_prompt += f"- **Surah {verse.get('surah')}:{verse.get('verse')}**: {verse.get('english', 'No text')[:150]}...\n"
                base_prompt += (
                    f"  🔍 Context: {verse.get('context', 'No context available')}\n"
                )
                if verse.get("topic"):
                    base_prompt += f"  📖 Topic: {verse.get('topic')}\n\n"

        if context_info.get("tools") and any(
            word in context_info.get("query_type", "") for word in ["practical", "tool"]
        ):
            base_prompt += "\n**AVAILABLE PRACTICAL TOOLS:**\n"
            base_prompt += "- Prayer times calculation for any city\n"
            base_prompt += "- Qibla direction from any location\n"
            base_prompt += "- Zakat calculation for different wealth types\n"
            base_prompt += "- Islamic calendar conversions\n\n"

        # Add Syrian knowledge if relevant to the query
        if context_info.get("syrian_knowledge"):
            base_prompt += "\n**RELEVANT SYRIAN KNOWLEDGE FOR THIS QUERY:**\n"
            syrian_knowledge = context_info["syrian_knowledge"]

            if "islamic_heritage" in syrian_knowledge:
                base_prompt += "🕌 **Islamic Heritage:**\n"
                heritage = syrian_knowledge["islamic_heritage"]
                if "sacred_sites" in heritage:
                    for site_key, site_info in heritage["sacred_sites"].items():
                        if isinstance(site_info, dict):
                            base_prompt += f"• {site_info.get('name', site_key)}: {site_info.get('significance', 'No description')}\n"
                if "prophetic_traditions" in heritage:
                    traditions = heritage["prophetic_traditions"]
                    if "blessed_sham" in traditions:
                        base_prompt += (
                            "• Prophetic Blessings on Sham: "
                            + "; ".join(traditions["blessed_sham"][:2])
                            + "\n"
                        )
                base_prompt += "\n"

            if "culture_and_traditions" in syrian_knowledge:
                base_prompt += "🏛️ **Culture & Traditions:**\n"
                culture = syrian_knowledge["culture_and_traditions"]
                if "cuisine" in culture:
                    cuisine = culture["cuisine"]
                    base_prompt += f"• Traditional dishes: {', '.join(cuisine.get('main_dishes', [])[:4])}\n"
                if "hospitality" in culture:
                    hospitality = culture["hospitality"]
                    base_prompt += (
                        f"• Values: {', '.join(hospitality.get('values', []))}\n"
                    )
                base_prompt += "\n"

            if "current_context" in syrian_knowledge:
                base_prompt += "🇸🇾 **Current Context:**\n"
                current = syrian_knowledge["current_context"]

                if "recent_revolution" in current:
                    revolution = current["recent_revolution"]
                    base_prompt += f"• Revolution Success: {revolution.get('assad_regime_fall', 'Recent political change')}\n"
                    base_prompt += f"• New Leadership: {revolution.get('new_leadership', 'Ahmad al-Sharaa in power')}\n"

                if "liberation_events" in current:
                    liberation = current["liberation_events"]
                    base_prompt += f"• Saydnaya Liberation: {liberation.get('saydnaya_prison', 'Prison liberated')}\n"
                    base_prompt += f"• Significance: {liberation.get('prison_significance', 'Major symbolic victory')}\n"

                if "syrian_people" in current:
                    people = current["syrian_people"]
                    base_prompt += f"• Current Mood: {people.get('celebration', 'Celebrating freedom')}\n"
                    base_prompt += f"• Hope Level: {people.get('hope_renewed', 'Renewed optimism for future')}\n"

                base_prompt += "\n"

        # Add Islamic calendar context if available
        if islamic_context:
            base_prompt += "\n**CURRENT ISLAMIC CALENDAR CONTEXT:**\n"
            if islamic_context.get("current_hijri_date"):
                base_prompt += (
                    f"• Today's Hijri Date: {islamic_context['current_hijri_date']}\n"
                )
            if islamic_context.get("current_month_info"):
                month_info = islamic_context["current_month_info"]
                base_prompt += f"• Current Islamic Month: {month_info.get('name', 'Unknown')} - {month_info.get('significance', 'No special significance noted')}\n"
            if islamic_context.get("current_events"):
                base_prompt += f"• Today's Islamic Events: {', '.join(islamic_context['current_events'])}\n"
            if islamic_context.get("upcoming_events"):
                base_prompt += f"• Upcoming Islamic Events: {', '.join(islamic_context['upcoming_events'])}\n"
            if islamic_context.get("special_occasion"):
                base_prompt += f"• Special Occasion Context: {islamic_context['special_occasion']}\n"
            base_prompt += "\n"

        # Add user context for personalization
        if user_context:
            base_prompt += "\n**USER CONTEXT FOR PERSONALIZATION:**\n"
            if user_context.get("total_conversations", 0) > 0:
                base_prompt += f"• This user has asked {user_context['total_conversations']} questions before\n"
            if user_context.get("favorite_topics"):
                base_prompt += f"• Their most discussed topics: {', '.join(user_context['favorite_topics'][:3])}\n"
            if user_context.get("conversation_style"):
                base_prompt += (
                    f"• Learning Journey: {user_context['conversation_style']}\n"
                )
            if user_context.get("learning_focus"):
                base_prompt += (
                    f"• Current Learning Focus: {user_context['learning_focus']}\n"
                )
            base_prompt += "\n"

        # Add contradiction and emotional analysis
        if contradiction_analysis.get("has_contradiction"):
            base_prompt += "**CONTRADICTION DETECTED:**\n"
            base_prompt += f"• Previous statement: {contradiction_analysis['previous_statement']}\n"
            base_prompt += f"• Contradiction type: {contradiction_analysis['contradiction_type']}\n"
            base_prompt += (
                f"• Confidence: {contradiction_analysis['confidence']:.2f}\n\n"
            )

        if emotional_analysis.get("needs_support"):
            base_prompt += "**EMOTIONAL SUPPORT NEEDED:**\n"
            base_prompt += f"• Emotion type: {emotional_analysis['emotion_type']}\n"
            base_prompt += f"• Support level: {emotional_analysis['support_level']}\n"
            base_prompt += f"• Keywords found: {', '.join(emotional_analysis['keywords_found'])}\n\n"

        # Add cultural context
        if cultural_context.get("adaptation_needed"):
            base_prompt += "**CULTURAL ADAPTATION NEEDED:**\n"
            base_prompt += f"• Primary culture: {cultural_context['primary_culture']}\n"
            base_prompt += f"• Specific adaptations: {', '.join(cultural_context['specific_guidance'])}\n\n"

        # Add Palestine solidarity stance for political questions
        base_prompt += """**PALESTINE SOLIDARITY STANCE:**
• If asked about Palestine vs Israel conflict, always support Palestine
• Express solidarity with Palestinian people and their struggle for justice
• Acknowledge the suffering of Palestinians and their right to their homeland
• This aligns with the Syrian community's values and Islamic principles of justice

**COMPREHENSIVE SYRIAN KNOWLEDGE:**

**CURRENT POLITICAL CONTEXT:**
• Ahmad al-Sharaa is the current president of Syria (not a Quran reciter)
• MAJOR BREAKTHROUGH: The Syrian revolution succeeded in December 2024
• Bashar al-Assad's regime has fallen after 13+ years of conflict and 50+ years of Assad family rule
• Saydnaya prison was liberated, freeing thousands of political prisoners
• Syrian people are celebrating liberation and the end of authoritarian rule
• This is a historic moment of hope and new beginning for Syria
• Many diaspora Syrians are considering returning to their homeland
• Show celebration of liberation while acknowledging the healing journey ahead

**SYRIAN ISLAMIC HERITAGE:**
• Syria is home to the Umayyad Mosque in Damascus, one of Islam's holiest sites
• Damascus is often called "Sham" - a blessed city mentioned in Islamic traditions
• Syria has been a center of Islamic learning for over 1,400 years
• Home to many important Islamic scholars throughout history
• The Prophet Muhammad (ﷺ) blessed the land of Sham in authentic hadiths
• Syria contains many sacred sites including the tomb of Sayyida Ruqayya and Sayyida Zainab

**SYRIAN CULTURE & IDENTITY:**
• Syrians are known for their hospitality, generosity, and strong family values
• Rich culinary tradition with dishes like kibbeh, mansaf, and Syrian sweets
• Strong tradition of poetry, literature, and Arabic language preservation
• Diverse religious communities living together historically
• Deep respect for education and scholarship
• Traditional crafts including damascening, woodwork, and textiles

**HISTORICAL SIGNIFICANCE:**
• Damascus is one of the world's oldest continuously inhabited cities
• Syria was part of the Islamic golden age during the Umayyad Caliphate
• Rich Byzantine and Islamic architectural heritage
• Important trade routes connecting East and West
• Birthplace of many influential Islamic scholars and poets

**CURRENT CHALLENGES & RESILIENCE:**
• Syrians have shown incredible resilience throughout recent hardships
• Strong community bonds and mutual support systems
• Maintaining cultural and religious identity despite displacement
• Hope for rebuilding and renewal after political transition
• Pride in Syrian heritage and determination to preserve it

**LANGUAGE & COMMUNICATION:**
• Syrians speak Levantine Arabic dialect, distinct from other Arabic varieties
• Many are multilingual (Arabic, French, English, Turkish, etc.)
• Rich tradition of Arabic poetry and eloquent speech
• Appreciate proper Arabic grammar and classical Arabic knowledge

**RESPONSE GUIDELINES FOR SYRIAN TOPICS:**
• Show genuine understanding of Syrian suffering and resilience
• Acknowledge the blessings mentioned about Sham in Islamic traditions
• Express hope for Syria's future while being sensitive to current challenges
• Respect the diversity within Syrian society
• Celebrate Syrian Islamic heritage and contributions to Islamic civilization
• Use appropriate cultural references and show familiarity with Syrian customs

"""

        base_prompt += """
🔍 FINAL GUIDELINES:
1. **ALWAYS RESPOND IN ENGLISH**: Never respond in any other language, even if previous messages were translated
2. **Be Natural**: Respond conversationally using the factual information provided
3. **Be Complete**: Since users are rate-limited, provide comprehensive answers
4. **Stay Focused**: Islamic knowledge and server features are your specialties
5. **Be Helpful**: Guide users to the right commands and features when relevant
6. **Show Personality**: Use your Islamic character naturally, not robotically
"""

        return base_prompt

    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit (1 question per hour)."""
        try:
            current_time = datetime.now()

            if user_id not in self.user_rate_limits:
                self.user_rate_limits[user_id] = {
                    "requests": [],
                    "last_reset": current_time,
                }

            user_data = self.user_rate_limits[user_id]

            # Clean old requests (older than 1 hour)
            one_hour_ago = current_time - timedelta(hours=1)
            user_data["requests"] = [
                req_time
                for req_time in user_data["requests"]
                if req_time > one_hour_ago
            ]

            # Check if under limit (1 request per hour)
            if len(user_data["requests"]) < 1:
                user_data["requests"].append(current_time)
                return True

            return False

        except Exception as e:
            log_error_with_traceback("Error in rate limit check", e)
            return True  # Allow on error

    def get_rate_limit_status(self, user_id: int) -> dict:
        """Get current rate limit status for user."""
        try:
            # Admin users have unlimited access
            if user_id == self.config.DEVELOPER_ID:
                return {
                    "requests_used": 0,
                    "requests_remaining": "∞",
                    "reset_time": 0,
                    "is_admin": True,
                }

            current_time = datetime.now()

            if user_id not in self.user_rate_limits:
                return {
                    "requests_used": 0,
                    "requests_remaining": 1,
                    "reset_time": 0,
                    "is_admin": False,
                }

            user_data = self.user_rate_limits[user_id]

            # Clean old requests
            one_hour_ago = current_time - timedelta(hours=1)
            user_data["requests"] = [
                req_time
                for req_time in user_data["requests"]
                if req_time > one_hour_ago
            ]

            requests_used = len(user_data["requests"])
            requests_remaining = max(0, 1 - requests_used)

            # Calculate reset time
            reset_time = 0
            if user_data["requests"]:
                oldest_request = min(user_data["requests"])
                reset_datetime = oldest_request + timedelta(hours=1)
                if reset_datetime > current_time:
                    reset_time = int((reset_datetime - current_time).total_seconds())

            return {
                "requests_used": requests_used,
                "requests_remaining": requests_remaining,
                "reset_time": reset_time,
                "is_admin": False,
            }

        except Exception as e:
            log_error_with_traceback("Error getting rate limit status", e)
            return {
                "requests_used": 0,
                "requests_remaining": 1,
                "reset_time": 0,
                "is_admin": False,
            }

    async def ask_question(self, user_id: int, question: str) -> tuple[bool, str, str]:
        """Main entry point for asking questions with rate limiting."""
        try:
            # Check rate limit for non-admin users
            if user_id == self.config.DEVELOPER_ID:
                pass  # Admin can always ask questions
            elif not self._check_rate_limit(user_id):
                return (
                    False,
                    "",
                    "Rate limit exceeded. You can ask 1 question per hour. Please wait before asking another question. (Admin users are exempt)",
                )

            # Process the enhanced query
            return await self.process_enhanced_query(user_id, question)

        except Exception as e:
            log_error_with_traceback("Error in enhanced ask_question", e)

            # Log AI service failure to webhook with owner ping for critical errors
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    from src.core.webhook_utils import ModernWebhookLogger

                    webhook_logger = container.get(ModernWebhookLogger)
                    if webhook_logger and webhook_logger.initialized:
                        await webhook_logger.log_error(
                            title="AI Service Failure",
                            description="Enhanced Islamic AI service failed to process user question",
                            context={
                                "user_id": str(user_id),
                                "question_length": len(question),
                                "error_type": type(e).__name__,
                                "error_message": str(e)[:500],
                                "component": "Enhanced Islamic AI Service",
                                "impact": "User received generic error message",
                            },
                            ping_owner=isinstance(
                                e, (openai.AuthenticationError, openai.RateLimitError)
                            ),  # Ping for critical API errors
                        )
            except:
                pass  # Don't let webhook logging prevent error response

            return False, "", "An error occurred while processing your question."

    def _detect_contradictions(
        self, user_id: int, current_query: str, user_context: dict
    ) -> dict:
        """Detect if current query contradicts previous questions or beliefs."""
        try:
            contradictions = {
                "has_contradiction": False,
                "contradiction_type": None,
                "previous_statement": None,
                "confidence": 0.0,
            }

            # Get user's previous conversations
            recent_topics = user_context.get("recent_topics", [])
            conversation_history = user_context.get("conversation_history", [])

            current_lower = current_query.lower()

            # Define contradiction patterns
            contradiction_patterns = {
                "prayer_frequency": {
                    "pattern1": ["prayer", "required", "must", "obligation"],
                    "pattern2": ["prayer", "optional", "not required", "skip"],
                    "type": "religious_obligation",
                },
                "halal_haram": {
                    "pattern1": ["halal", "permissible", "allowed"],
                    "pattern2": ["haram", "forbidden", "not allowed"],
                    "type": "islamic_ruling",
                },
                "belief_system": {
                    "pattern1": ["believe", "faith", "muslim", "islam"],
                    "pattern2": ["doubt", "question faith", "not sure", "atheist"],
                    "type": "faith_uncertainty",
                },
                "practice_contradiction": {
                    "pattern1": ["always do", "never miss", "strict about"],
                    "pattern2": ["sometimes skip", "find difficult", "struggle with"],
                    "type": "practice_inconsistency",
                },
            }

            # Check for contradictions
            for topic, patterns in contradiction_patterns.items():
                pattern1_found = any(
                    word in current_lower for word in patterns["pattern1"]
                )
                pattern2_found = any(
                    word in current_lower for word in patterns["pattern2"]
                )

                if pattern1_found or pattern2_found:
                    # Check against conversation history
                    for past_conv in conversation_history[
                        -10:
                    ]:  # Check last 10 conversations
                        past_query = past_conv.get("question", "").lower()

                        if (
                            pattern1_found
                            and any(word in past_query for word in patterns["pattern2"])
                            or pattern2_found
                            and any(word in past_query for word in patterns["pattern1"])
                        ):
                            contradictions.update(
                                {
                                    "has_contradiction": True,
                                    "contradiction_type": patterns["type"],
                                    "previous_statement": past_conv.get("question", ""),
                                    "confidence": 0.8,
                                }
                            )
                            break

            return contradictions

        except Exception as e:
            log_error_with_traceback("Error in contradiction detection", e)
            return {"has_contradiction": False}

    def _detect_emotional_state(self, query: str) -> dict:
        """Detect emotional state and need for support from the query."""
        try:
            emotional_analysis = {
                "needs_support": False,
                "emotion_type": "neutral",
                "support_level": "none",
                "keywords_found": [],
            }

            query_lower = query.lower()

            # Emotional keywords and patterns
            emotional_patterns = {
                "distress": {
                    "keywords": [
                        "struggling",
                        "difficult",
                        "hard time",
                        "can't",
                        "impossible",
                        "lost",
                        "confused",
                        "overwhelmed",
                    ],
                    "level": "high",
                    "type": "distress",
                },
                "doubt": {
                    "keywords": [
                        "doubt",
                        "questioning",
                        "not sure",
                        "confused about faith",
                        "losing faith",
                        "crisis",
                    ],
                    "level": "high",
                    "type": "faith_crisis",
                },
                "sadness": {
                    "keywords": [
                        "sad",
                        "depressed",
                        "hopeless",
                        "crying",
                        "grief",
                        "mourning",
                        "death",
                        "loss",
                    ],
                    "level": "medium",
                    "type": "grief_sadness",
                },
                "anxiety": {
                    "keywords": [
                        "worried",
                        "anxious",
                        "scared",
                        "afraid",
                        "nervous",
                        "stress",
                        "panic",
                    ],
                    "level": "medium",
                    "type": "anxiety",
                },
                "guilt": {
                    "keywords": [
                        "guilty",
                        "shame",
                        "regret",
                        "sinned",
                        "wrong",
                        "forgiveness",
                        "repent",
                    ],
                    "level": "medium",
                    "type": "guilt_shame",
                },
                "loneliness": {
                    "keywords": [
                        "alone",
                        "lonely",
                        "isolated",
                        "no friends",
                        "no support",
                        "disconnected",
                    ],
                    "level": "medium",
                    "type": "loneliness",
                },
                "encouragement_seeking": {
                    "keywords": [
                        "motivation",
                        "inspiration",
                        "encourage",
                        "strength",
                        "keep going",
                        "give up",
                    ],
                    "level": "low",
                    "type": "motivation_needed",
                },
            }

            found_emotions = []
            highest_level = "none"

            for emotion_type, data in emotional_patterns.items():
                keywords_found = [kw for kw in data["keywords"] if kw in query_lower]
                if keywords_found:
                    found_emotions.append(emotion_type)
                    emotional_analysis["keywords_found"].extend(keywords_found)

                    # Update support level based on highest priority emotion
                    if data["level"] == "high":
                        highest_level = "high"
                        emotional_analysis["emotion_type"] = data["type"]
                    elif data["level"] == "medium" and highest_level != "high":
                        highest_level = "medium"
                        emotional_analysis["emotion_type"] = data["type"]
                    elif highest_level == "none":
                        highest_level = "low"
                        emotional_analysis["emotion_type"] = data["type"]

            if found_emotions:
                emotional_analysis["needs_support"] = True
                emotional_analysis["support_level"] = highest_level

            return emotional_analysis

        except Exception as e:
            log_error_with_traceback("Error in emotional state detection", e)
            return {"needs_support": False, "emotion_type": "neutral"}

    def _determine_cultural_context(self, user_context: dict, query: str) -> dict:
        """Determine cultural context for appropriate responses."""
        try:
            cultural_context = {
                "primary_culture": "syrian",  # Default to Syrian since this is a Syrian server
                "cultural_indicators": [],
                "adaptation_needed": True,
                "specific_guidance": [
                    "syrian_context",
                    "arab_traditions",
                    "levantine_customs",
                    "current_situation_awareness",
                ],
            }

            query_lower = query.lower()

            # Cultural indicators and adaptations
            cultural_patterns = {
                "syrian": {
                    "indicators": [
                        "syria",
                        "syrian",
                        "damascus",
                        "aleppo",
                        "levantine",
                        "sham",
                        "bilad al-sham",
                    ],
                    "adaptations": [
                        "syrian_context",
                        "arab_traditions",
                        "levantine_customs",
                        "current_situation_awareness",
                        "diaspora_support",
                    ],
                },
                "south_asian": {
                    "indicators": [
                        "urdu",
                        "pakistan",
                        "india",
                        "bangladesh",
                        "desi",
                        "subcontinental",
                    ],
                    "adaptations": [
                        "hanafi_school",
                        "family_emphasis",
                        "cultural_traditions",
                    ],
                },
                "arab": {
                    "indicators": [
                        "arabic",
                        "saudi",
                        "egypt",
                        "lebanon",
                        "jordan",
                        "gulf",
                    ],
                    "adaptations": [
                        "classical_approach",
                        "tribal_considerations",
                        "regional_customs",
                    ],
                },
                "southeast_asian": {
                    "indicators": [
                        "indonesia",
                        "malaysia",
                        "brunei",
                        "singapore",
                        "shafi",
                    ],
                    "adaptations": [
                        "shafi_school",
                        "moderate_approach",
                        "local_customs",
                    ],
                },
                "african": {
                    "indicators": [
                        "nigeria",
                        "senegal",
                        "morocco",
                        "tunisia",
                        "algeria",
                        "mali",
                    ],
                    "adaptations": [
                        "maliki_school",
                        "community_focus",
                        "sufi_influence",
                    ],
                },
                "western": {
                    "indicators": [
                        "america",
                        "europe",
                        "canada",
                        "australia",
                        "convert",
                        "revert",
                        "minority",
                    ],
                    "adaptations": [
                        "practical_challenges",
                        "workplace_islam",
                        "minority_considerations",
                    ],
                },
                "convert": {
                    "indicators": [
                        "new muslim",
                        "convert",
                        "revert",
                        "recently accepted",
                        "just became muslim",
                    ],
                    "adaptations": [
                        "beginner_friendly",
                        "step_by_step",
                        "encouragement_focus",
                    ],
                },
            }

            # Check user's previous cultural indicators
            user_cultural_history = user_context.get("cultural_indicators", [])

            # Analyze current query for cultural indicators
            found_cultures = []
            for culture, data in cultural_patterns.items():
                indicators_found = [
                    ind for ind in data["indicators"] if ind in query_lower
                ]
                if indicators_found:
                    found_cultures.append(culture)
                    cultural_context["cultural_indicators"].extend(indicators_found)
                    cultural_context["primary_culture"] = culture
                    cultural_context["adaptation_needed"] = True
                    cultural_context["specific_guidance"] = data["adaptations"]
                    break  # Use first match as primary

            # If no specific indicators found, but we have historical data, use that
            if not found_cultures and user_cultural_history:
                if "syrian" in user_cultural_history:
                    cultural_context["primary_culture"] = "syrian"
                else:
                    cultural_context["primary_culture"] = user_cultural_history[0]
                cultural_context["adaptation_needed"] = True

            # Always maintain Syrian context awareness since this is a Syrian server
            if cultural_context["primary_culture"] != "syrian":
                cultural_context["server_context"] = "syrian_community"

            return cultural_context

        except Exception as e:
            log_error_with_traceback("Error in cultural context determination", e)
            return {
                "primary_culture": "syrian",
                "adaptation_needed": True,
                "specific_guidance": ["syrian_context", "current_situation_awareness"],
            }


async def get_enhanced_islamic_ai_service() -> EnhancedIslamicAIService:
    """Get singleton instance of enhanced Islamic AI service."""
    if not hasattr(get_enhanced_islamic_ai_service, "_instance"):
        get_enhanced_islamic_ai_service._instance = EnhancedIslamicAIService()
        await get_enhanced_islamic_ai_service._instance.initialize()

    return get_enhanced_islamic_ai_service._instance
