#!/usr/bin/env python3
# =============================================================================
# Translation Service - Multilingual AI Response Translation with ChatGPT
# =============================================================================
# This service handles translation of AI responses into multiple languages
# using OpenAI ChatGPT for high-quality, context-aware translations while 
# preserving the original embed structure.
# =============================================================================

import asyncio
import json
from typing import Dict, Optional, Tuple
import openai

from src.config.bot_config import BotConfig
from src.utils.tree_log import log_perfect_tree_section, log_error_with_traceback


class TranslationService:
    """Handles translation of AI responses into multiple languages using ChatGPT."""
    
    def __init__(self):
        self.config = BotConfig()
        self.openai_client = openai.AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
        
        self.supported_languages = {
            'en': {'name': 'English', 'flag': '🇺🇸', 'code': 'en'},
            'ar': {'name': 'العربية', 'flag': '🇸🇦', 'code': 'ar'},
            'de': {'name': 'Deutsch', 'flag': '🇩🇪', 'code': 'de'},
            'es': {'name': 'Español', 'flag': '🇪🇸', 'code': 'es'}
        }
        
        # Translation cache for performance
        self.translation_cache: Dict[str, Dict[str, str]] = {}
        
    async def translate_text(self, text: str, target_language: str) -> Tuple[bool, str]:
        """
        Translate text to target language using ChatGPT for high-quality translation.
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'ar', 'ur', 'tr')
            
        Returns:
            Tuple of (success, translated_text or error_message)
        """
        try:
            # Special case: English returns original text (no translation needed)
            if target_language == 'en':
                return True, text
                
            # Check cache first
            cache_key = f"{text[:50]}_{target_language}"
            if cache_key in self.translation_cache:
                return True, self.translation_cache[cache_key]
                
            if target_language not in self.supported_languages:
                return False, f"Language '{target_language}' not supported"
                
            # Get language display name for ChatGPT
            language_info = self.supported_languages[target_language]
            language_name = language_info['name']
            
            # Create system prompt for high-quality Islamic translation
            system_prompt = f"""You are a professional translator specializing in Islamic content. 
            
Your task is to translate the given English Islamic response into {language_name} ({target_language}).

CRITICAL REQUIREMENTS:
1. PRESERVE all Islamic terms in their original form (Allah, Quran, hadith, inshallah, etc.)
2. Maintain the spiritual and scholarly tone
3. Keep cultural sensitivity and religious accuracy
4. Do NOT translate names of people, places, or Islamic concepts
5. Provide natural, fluent translation that Muslims would use
6. ONLY return the translated text, no explanations or additions

Examples of terms to PRESERVE:
- Allah (never translate as "God")
- Quran, Quranic
- Prophet Muhammad (ﷺ), Prophet (ﷺ)
- hadith, sunnah, fiqh
- salah, zakat, hajj, sawm
- inshallah, alhamdulillah, subhanallah
- ummah, tawhid, shirk
- Any Arabic phrases in the original text

Translate naturally while preserving the Islamic authenticity."""

            # Make the translation request
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Translate this Islamic response to {language_name}:\n\n{text}"}
                ],
                max_tokens=1500,
                temperature=0.1,  # Low temperature for consistent translations
                top_p=0.9
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Cache the translation
            self.translation_cache[cache_key] = translated_text
            
            # Limit cache size
            if len(self.translation_cache) > 1000:
                # Remove oldest entries
                keys_to_remove = list(self.translation_cache.keys())[:100]
                for key in keys_to_remove:
                    del self.translation_cache[key]
                    
            return True, translated_text
                        
        except Exception as e:
            log_error_with_traceback("ChatGPT translation error", e)
            return False, f"Translation failed: {str(e)}"
            
    async def translate_ai_response(self, ai_response: str, target_language: str) -> Tuple[bool, str]:
        """
        Translate AI response using ChatGPT for high-quality, context-aware translation.
        
        Args:
            ai_response: The AI response text to translate
            target_language: Target language code
            
        Returns:
            Tuple of (success, translated_response or error_message)
        """
        # Since ChatGPT can handle Islamic terms naturally, we can use the main translate method
        return await self.translate_text(ai_response, target_language)
            
    def get_language_options(self) -> Dict[str, Dict[str, str]]:
        """Get available language options for UI."""
        return self.supported_languages
        
    def get_language_display_name(self, language_code: str) -> str:
        """Get display name for language code."""
        lang_info = self.supported_languages.get(language_code, {})
        return f"{lang_info.get('flag', '🌍')} {lang_info.get('name', 'Unknown')}"


# Global instance
translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get singleton instance of translation service."""
    global translation_service
    
    if translation_service is None:
        translation_service = TranslationService()
        
    return translation_service 