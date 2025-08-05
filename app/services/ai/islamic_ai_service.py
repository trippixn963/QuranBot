# =============================================================================
# QuranBot - Islamic AI Service
# =============================================================================
# Islamic knowledge enhancement and response formatting service
# =============================================================================

import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from ...config import get_config
from ...core.logger import TreeLogger
from ...data.surahs_data import COMPLETE_SURAHS_DATA
from ..core.base_service import BaseService


class IslamicAIService(BaseService):
    """
    Islamic AI Service for knowledge enhancement and validation.
    
    Features:
    - Islamic greeting detection and response
    - Quran/Hadith reference formatting
    - Context awareness (current surah playing)
    - Response validation and enhancement
    """
    
    def __init__(self, bot):
        """Initialize Islamic AI service."""
        super().__init__("IslamicAIService")
        self.bot = bot
        self.config = get_config()
        
        TreeLogger.debug("Islamic AI Service instance created", service=self.service_name)
        
        # Islamic greetings patterns
        self.greeting_patterns = {
            'salam': r'\b(assalam|salam|salaam)\b',
            'greeting': r'\b(hello|hi|hey)\b',
            'morning': r'\b(good morning|morning)\b',
            'evening': r'\b(good evening|evening)\b'
        }
        
        # Islamic phrases to preserve
        self.islamic_terms = [
            'Allah', 'Quran', 'Prophet', 'Muhammad', 'PBUH', 'ﷺ',
            'SubhanAllah', 'Alhamdulillah', 'InshaAllah', 'MashaAllah',
            'JazakAllah', 'BarakAllah', 'Bismillah', 'Astaghfirullah',
            'hadith', 'sunnah', 'fiqh', 'tafsir', 'tajweed',
            'salah', 'salat', 'zakat', 'hajj', 'umrah', 'sawm',
            'iman', 'islam', 'ihsan', 'taqwa', 'dhikr',
            'Ramadan', 'Eid', 'Kaaba', 'Mecca', 'Medina'
        ]
    
    async def _initialize(self) -> bool:
        """Initialize the Islamic AI service."""
        try:
            TreeLogger.info("Initializing Islamic AI Service", service=self.service_name)
            
            TreeLogger.debug("Islamic patterns loaded", {
                "greeting_patterns": len(self.greeting_patterns),
                "islamic_terms": len(self.islamic_terms)
            }, service=self.service_name)
            
            TreeLogger.info("Islamic AI Service initialized successfully", service=self.service_name)
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "islamic_ai_initialization"}
            )
            return False
    
    async def _start(self) -> bool:
        """Start the Islamic AI service."""
        TreeLogger.info("Islamic AI Service started", service=self.service_name)
        return True
    
    async def _stop(self) -> bool:
        """Stop the Islamic AI service."""
        TreeLogger.info("Islamic AI Service stopped", service=self.service_name)
        return True
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check on Islamic AI service."""
        return {
            "is_healthy": True,
            "greeting_patterns": len(self.greeting_patterns),
            "islamic_terms": len(self.islamic_terms)
        }
    
    def detect_greeting(self, message: str) -> Optional[str]:
        """
        Detect Islamic or regular greetings in message.
        
        Returns appropriate Islamic greeting response.
        """
        TreeLogger.debug("Detecting greeting in message", {
            "message_length": len(message)
        }, service=self.service_name)
        
        message_lower = message.lower()
        
        # Check for Islamic greeting
        if re.search(self.greeting_patterns['salam'], message_lower):
            TreeLogger.debug("Islamic greeting detected", {
                "pattern": "salam"
            }, service=self.service_name)
            return "Wa Alaikum Assalam wa Rahmatullahi wa Barakatuh! 🕌"
        
        # Check for regular greetings
        if re.search(self.greeting_patterns['greeting'], message_lower):
            return "Assalamu Alaikum! 🌙"
        
        if re.search(self.greeting_patterns['morning'], message_lower):
            return "Assalamu Alaikum! May Allah bless your morning! ☀️"
        
        if re.search(self.greeting_patterns['evening'], message_lower):
            return "Assalamu Alaikum! May Allah bless your evening! 🌙"
        
        return None
    
    def get_current_playing_context(self) -> Dict[str, Any]:
        """Get context about currently playing audio."""
        try:
            TreeLogger.debug("Getting current playing context", service=self.service_name)
            
            audio_service = self.bot.services.get("audio")
            if not audio_service:
                TreeLogger.debug("Audio service not available", service=self.service_name)
                return {}
            
            # Check if playing
            if not hasattr(audio_service, 'voice_client') or not audio_service.voice_client:
                return {}
            
            if not audio_service.voice_client.is_playing():
                return {}
            
            # Get current surah and reciter
            current_surah_info = audio_service.get_current_surah()
            current_reciter_info = audio_service.get_current_reciter()
            
            if not current_surah_info:
                return {}
            
            context = {
                "current_surah": current_surah_info,
                "reciter": current_reciter_info.get("name", "Unknown") if current_reciter_info else "Unknown"
            }
            
            TreeLogger.debug("Playing context retrieved", {
                "surah_name": current_surah_info.get("name"),
                "surah_number": current_surah_info.get("number"),
                "reciter": context["reciter"]
            }, service=self.service_name)
            
            return context
            
        except Exception as e:
            TreeLogger.error("Error getting playing context", e, {
                "error_type": type(e).__name__
            }, service=self.service_name)
            return {}
    
    def enhance_response(self, response: str) -> str:
        """
        Enhance AI response with Islamic formatting.
        
        - Preserves Islamic terms
        - Formats Quran references
        - Adds appropriate emojis
        """
        TreeLogger.debug("Enhancing AI response", {
            "original_length": len(response)
        }, service=self.service_name)
        
        original_response = response
        # Format Quran references (e.g., "Surah Al-Baqarah 2:255" → "📖 Surah Al-Baqarah (2:255)")
        response = re.sub(
            r'Surah\s+([A-Za-z\-\s]+)\s*(\d+):(\d+)',
            r'📖 Surah \1 (\2:\3)',
            response
        )
        
        # Format standalone verse references (e.g., "verse 255" → "verse 255")
        response = re.sub(
            r'\bverse\s+(\d+)\b',
            r'verse \1',
            response,
            flags=re.IGNORECASE
        )
        
        # Add Hadith book emojis
        response = re.sub(
            r'\b(Sahih\s+)?(Bukhari|Muslim)\b',
            r'📚 \1\2',
            response
        )
        
        # Ensure proper formatting for Prophet's name
        response = re.sub(
            r'Prophet\s+Muhammad(?:\s+\(PBUH\))?',
            'Prophet Muhammad ﷺ',
            response
        )
        
        # Log enhancement stats
        if response != original_response:
            TreeLogger.debug("Response enhanced", {
                "original_length": len(original_response),
                "enhanced_length": len(response),
                "changes_made": response != original_response
            }, service=self.service_name)
        
        return response
    
    def validate_islamic_content(self, text: str) -> bool:
        """
        Validate that content is appropriate for Islamic context.
        
        Returns True if content is appropriate.
        """
        TreeLogger.debug("Validating Islamic content", {
            "text_length": len(text)
        }, service=self.service_name)
        
        # List of terms that might indicate inappropriate content
        inappropriate_patterns = [
            r'\b(hate|violence|extremis[mt])\b',
            r'\b(sect|sectarian|division)\b',
            r'\b(bid\'?ah|innovation)\s+is\s+good\b',  # Theological disputes
        ]
        
        text_lower = text.lower()
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                TreeLogger.warning("Potentially inappropriate content detected", {
                    "pattern": pattern
                }, service=self.service_name)
                return False
        
        return True
    
    def extract_islamic_references(self, text: str) -> Dict[str, List[str]]:
        """
        Extract Quran and Hadith references from text.
        
        Returns dict with 'quran' and 'hadith' lists.
        """
        TreeLogger.debug("Extracting Islamic references", {
            "text_length": len(text)
        }, service=self.service_name)
        
        references = {
            'quran': [],
            'hadith': []
        }
        
        # Extract Quran references
        quran_pattern = r'Surah\s+([A-Za-z\-\s]+)\s*(?:\()?(\d+):(\d+)(?:\))?'
        for match in re.finditer(quran_pattern, text):
            surah_name = match.group(1).strip()
            chapter = match.group(2)
            verse = match.group(3)
            references['quran'].append(f"{surah_name} {chapter}:{verse}")
        
        # Extract Hadith references
        hadith_pattern = r'(Sahih\s+)?(Bukhari|Muslim|Abu\s+Dawud|Tirmidhi|Nasa\'?i|Ibn\s+Majah)(?:,?\s+(?:Book|Volume|Hadith)\s+)?(\d+)'
        for match in re.finditer(hadith_pattern, text, re.IGNORECASE):
            collection = match.group(2)
            number = match.group(3) if match.group(3) else ""
            reference = f"{collection}"
            if number:
                reference += f" {number}"
            references['hadith'].append(reference)
        
        TreeLogger.debug("References extracted", {
            "quran_references": len(references['quran']),
            "hadith_references": len(references['hadith'])
        }, service=self.service_name)
        
        return references
    
    def get_related_suggestions(self, topic: str) -> List[str]:
        """
        Get related Islamic topics for further exploration.
        
        Returns list of suggested questions/topics.
        """
        TreeLogger.debug("Generating related suggestions", {
            "topic_length": len(topic)
        }, service=self.service_name)
        
        # Simple keyword-based suggestions
        suggestions = []
        topic_lower = topic.lower()
        
        if 'prayer' in topic_lower or 'salah' in topic_lower:
            suggestions.extend([
                "What are the conditions for valid prayer?",
                "Can you explain the importance of Khushu in Salah?",
                "What are the Sunnah prayers?"
            ])
        elif 'quran' in topic_lower:
            suggestions.extend([
                "What are the virtues of reading Quran daily?",
                "Can you explain the concept of Tadabbur?",
                "What is the significance of Surah Al-Fatihah?"
            ])
        elif 'ramadan' in topic_lower or 'fasting' in topic_lower:
            suggestions.extend([
                "What are the spiritual benefits of fasting?",
                "Can you explain the night of Qadr?",
                "What breaks the fast?"
            ])
        else:
            # Generic suggestions
            suggestions.extend([
                "Can you tell me about the five pillars of Islam?",
                "What is the importance of Dhikr?",
                "Can you explain the concept of Tawakkul?"
            ])
        
        # Return top 3 suggestions
        final_suggestions = suggestions[:3]
        
        TreeLogger.debug("Suggestions generated", {
            "total_suggestions": len(suggestions),
            "returned_suggestions": len(final_suggestions)
        }, service=self.service_name)
        
        return final_suggestions
    
    async def _cleanup(self) -> None:
        """Clean up Islamic AI service resources."""
        try:
            TreeLogger.debug("Cleaning up Islamic AI service resources", service=self.service_name)
            
            # Clear cached greetings
            if hasattr(self, 'greetings_cache'):
                self.greetings_cache = None
                TreeLogger.debug("Greetings cache cleared", service=self.service_name)
            
            TreeLogger.info("Islamic AI service cleanup completed", service=self.service_name)
            
        except Exception as e:
            TreeLogger.error("Error during Islamic AI service cleanup", e, {
                "error_type": type(e).__name__
            }, service=self.service_name)
            # Don't raise - cleanup should be best effort