# =============================================================================
# QuranBot - Language Detection Module
# =============================================================================
# Detects language preferences and provides appropriate responses
# =============================================================================

import re
import traceback

from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger


class LanguageDetection:
    """
    Detects language in messages and determines response language.
    """

    def __init__(self) -> None:
        self.service_name = "LanguageDetection"
        self.error_handler = ErrorHandler()

        try:
            TreeLogger.info(
                "Initializing language detection module", service=self.service_name
            )

            # Arabic character ranges
            self.arabic_pattern = re.compile(
                r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
            )

            # Common Arabic Islamic phrases
            self.arabic_phrases = [
                "السلام عليكم",
                "وعليكم السلام",
                "جزاك الله",
                "بارك الله",
                "ما شاء الله",
                "الحمد لله",
                "سبحان الله",
                "استغفر الله",
                "إن شاء الله",
                "اللهم",
                "صلى الله عليه وسلم",
            ]

            # Common transliterated Islamic phrases
            self.transliterated_phrases = [
                "assalamu alaikum",
                "wa alaikum",
                "jazakallah",
                "barakallah",
                "mashallah",
                "alhamdulillah",
                "subhanallah",
                "astaghfirullah",
                "inshallah",
                "inshaallah",
            ]

            # Language indicators
            self.arabic_indicators = [
                "؟",
                "،",
                "أ",
                "إ",
                "ال",
                "في",
                "من",
                "على",
                "ما",
                "هل",
            ]
            self.english_indicators = [
                "the",
                "is",
                "are",
                "what",
                "how",
                "when",
                "where",
                "why",
            ]

            TreeLogger.info(
                "Language detection module initialized",
                {
                    "arabic_phrases": len(self.arabic_phrases),
                    "transliterated_phrases": len(self.transliterated_phrases),
                    "arabic_indicators": len(self.arabic_indicators),
                    "english_indicators": len(self.english_indicators),
                },
                service=self.service_name,
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to initialize language detection module",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )
            raise

    def detect_language(self, message: str) -> tuple[str, float]:
        """
        Detect the primary language of a message.

        Args:
            message: User's message

        Returns:
            Tuple of (language_code, confidence)
        """
        try:
            TreeLogger.debug(
                "Detecting language",
                {"message_length": len(message) if message else 0},
                service=self.service_name,
            )

            if not message:
                TreeLogger.warning(
                    "Empty message for language detection", service=self.service_name
                )
                return "en", 1.0

            message_lower = message.lower()

            # Count Arabic characters
            arabic_chars = len(self.arabic_pattern.findall(message))
            total_chars = len(message.replace(" ", ""))

            if total_chars == 0:
                TreeLogger.debug("No characters to analyze", service=self.service_name)
                return "en", 1.0

            arabic_ratio = arabic_chars / total_chars

            # Check for Arabic phrases
            arabic_phrase_count = sum(
                1 for phrase in self.arabic_phrases if phrase in message
            )

            # Check for Arabic indicators
            arabic_indicator_count = sum(
                1 for indicator in self.arabic_indicators if indicator in message
            )

            # Check for English indicators
            english_indicator_count = sum(
                1 for indicator in self.english_indicators if indicator in message_lower
            )

            # Calculate scores
            arabic_score = (
                (arabic_ratio * 10) + (arabic_phrase_count * 2) + arabic_indicator_count
            )
            english_score = english_indicator_count + (1 - arabic_ratio) * 5

            TreeLogger.debug(
                "Language scores calculated",
                {
                    "arabic_chars": arabic_chars,
                    "total_chars": total_chars,
                    "arabic_ratio": round(arabic_ratio, 2),
                    "arabic_phrases": arabic_phrase_count,
                    "arabic_indicators": arabic_indicator_count,
                    "english_indicators": english_indicator_count,
                    "arabic_score": round(arabic_score, 2),
                    "english_score": round(english_score, 2),
                },
                service=self.service_name,
            )

            # Determine language
            if arabic_score > english_score:
                confidence = min(arabic_score / 15, 1.0)
                language = "ar"
            else:
                confidence = min(english_score / 10, 1.0)
                language = "en"

            TreeLogger.info(
                "Language detected",
                {
                    "language": language,
                    "confidence": round(confidence, 2),
                    "arabic_score": round(arabic_score, 2),
                    "english_score": round(english_score, 2),
                },
                service=self.service_name,
            )

            return language, confidence

        except Exception as e:
            TreeLogger.error(
                "Error detecting language",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )

            return "en", 1.0

    def detect_mixed_language(self, message: str) -> dict:
        """
        Detect if message contains mixed languages.

        Args:
            message: User's message

        Returns:
            Dictionary with language analysis
        """
        try:
            TreeLogger.debug(
                "Detecting mixed language",
                {"message_length": len(message) if message else 0},
                service=self.service_name,
            )

            if not message:
                TreeLogger.warning(
                    "Empty message for mixed language detection",
                    service=self.service_name,
                )
                return {
                    "is_mixed": False,
                    "primary_language": "en",
                    "secondary_language": None,
                    "confidence": 1.0,
                }

            # Detect primary language
            primary_lang, primary_conf = self.detect_language(message)

            # Check for mixed content
            arabic_chars = len(self.arabic_pattern.findall(message))
            english_words = len(
                [word for word in message.split() if word.isalpha() and word.isascii()]
            )

            total_chars = len(message.replace(" ", ""))
            total_words = len(message.split())

            if total_chars == 0 or total_words == 0:
                TreeLogger.debug(
                    "No content to analyze for mixed language",
                    service=self.service_name,
                )
                return {
                    "is_mixed": False,
                    "primary_language": primary_lang,
                    "secondary_language": None,
                    "confidence": primary_conf,
                }

            # Calculate ratios
            arabic_ratio = arabic_chars / total_chars if total_chars > 0 else 0
            english_ratio = english_words / total_words if total_words > 0 else 0

            # Determine if mixed
            is_mixed = arabic_ratio > 0.1 and english_ratio > 0.1

            secondary_lang = None
            if is_mixed:
                secondary_lang = "en" if primary_lang == "ar" else "ar"

            TreeLogger.info(
                "Mixed language analysis completed",
                {
                    "is_mixed": is_mixed,
                    "primary_language": primary_lang,
                    "secondary_language": secondary_lang,
                    "arabic_ratio": round(arabic_ratio, 2),
                    "english_ratio": round(english_ratio, 2),
                    "confidence": round(primary_conf, 2),
                },
                service=self.service_name,
            )

            return {
                "is_mixed": is_mixed,
                "primary_language": primary_lang,
                "secondary_language": secondary_lang,
                "confidence": primary_conf,
            }

        except Exception as e:
            TreeLogger.error(
                "Error detecting mixed language",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )

            return {
                "is_mixed": False,
                "primary_language": "en",
                "secondary_language": None,
                "confidence": 1.0,
            }

    def should_respond_in_arabic(
        self, message: str, user_preference: str | None = None
    ) -> bool:
        """
        Determine if response should be in Arabic.

        Args:
            message: User's message
            user_preference: User's language preference

        Returns:
            True if should respond in Arabic
        """
        try:
            TreeLogger.debug(
                "Determining response language",
                {
                    "message_length": len(message) if message else 0,
                    "user_preference": user_preference,
                },
                service=self.service_name,
            )

            # Check user preference first
            if user_preference:
                TreeLogger.debug(
                    "Using user preference for language",
                    {"preference": user_preference},
                    service=self.service_name,
                )
                return user_preference.lower() == "ar"

            if not message:
                TreeLogger.debug(
                    "No message, defaulting to English", service=self.service_name
                )
                return False

            # Detect language
            language, confidence = self.detect_language(message)

            # Check for Arabic phrases even in English messages
            arabic_phrase_found = any(
                phrase in message for phrase in self.arabic_phrases
            )
            transliterated_found = any(
                phrase in message.lower() for phrase in self.transliterated_phrases
            )

            should_respond_arabic = (
                language == "ar"
                or (confidence > 0.6 and language == "ar")
                or arabic_phrase_found
                or transliterated_found
            )

            TreeLogger.info(
                "Response language determined",
                {
                    "should_respond_arabic": should_respond_arabic,
                    "detected_language": language,
                    "confidence": round(confidence, 2),
                    "arabic_phrase_found": arabic_phrase_found,
                    "transliterated_found": transliterated_found,
                },
                service=self.service_name,
            )

            return should_respond_arabic

        except Exception as e:
            TreeLogger.error(
                "Error determining response language",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )

            return False

    def get_language_appropriate_response(
        self, response: str, target_language: str
    ) -> str:
        """
        Get language-appropriate response.

        Args:
            response: Original response
            target_language: Target language code

        Returns:
            Language-appropriate response
        """
        try:
            TreeLogger.debug(
                "Getting language-appropriate response",
                {"target_language": target_language, "response_length": len(response)},
                service=self.service_name,
            )

            if not response:
                TreeLogger.warning("Empty response provided", service=self.service_name)
                return ""

            # For now, return the original response
            # In the future, this could include translation logic
            TreeLogger.debug(
                "Returning original response",
                {"target_language": target_language},
                service=self.service_name,
            )

            return response

        except Exception as e:
            TreeLogger.error(
                "Error getting language-appropriate response",
                e,
                {
                    "target_language": target_language,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            return response

    def extract_islamic_phrases(self, message: str) -> dict:
        """
        Extract Islamic phrases from message.

        Args:
            message: User's message

        Returns:
            Dictionary with extracted phrases
        """
        try:
            TreeLogger.debug(
                "Extracting Islamic phrases",
                {"message_length": len(message) if message else 0},
                service=self.service_name,
            )

            if not message:
                TreeLogger.warning(
                    "Empty message for phrase extraction", service=self.service_name
                )
                return {
                    "arabic_phrases": [],
                    "transliterated_phrases": [],
                    "total_phrases": 0,
                }

            # Extract Arabic phrases
            arabic_phrases = [
                phrase for phrase in self.arabic_phrases if phrase in message
            ]

            # Extract transliterated phrases
            message_lower = message.lower()
            transliterated_phrases = [
                phrase
                for phrase in self.transliterated_phrases
                if phrase in message_lower
            ]

            total_phrases = len(arabic_phrases) + len(transliterated_phrases)

            TreeLogger.info(
                "Islamic phrases extracted",
                {
                    "arabic_phrases": len(arabic_phrases),
                    "transliterated_phrases": len(transliterated_phrases),
                    "total_phrases": total_phrases,
                },
                service=self.service_name,
            )

            return {
                "arabic_phrases": arabic_phrases,
                "transliterated_phrases": transliterated_phrases,
                "total_phrases": total_phrases,
            }

        except Exception as e:
            TreeLogger.error(
                "Error extracting Islamic phrases",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )

            return {
                "arabic_phrases": [],
                "transliterated_phrases": [],
                "total_phrases": 0,
            }
