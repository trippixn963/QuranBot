# =============================================================================
# QuranBot - Emotional Intelligence Module
# =============================================================================
# Detects emotional states and provides appropriate Islamic comfort
# =============================================================================

import re
import traceback
from typing import Dict, List, Optional, Tuple

from ...core.logger import TreeLogger
from ...core.errors import ErrorHandler


class EmotionalIntelligence:
    """
    Detects emotional states in messages and provides appropriate Islamic responses.
    """
    
    def __init__(self):
        self.service_name = "EmotionalIntelligence"
        self.error_handler = ErrorHandler()
        
        try:
            TreeLogger.info("Initializing emotional intelligence module", service=self.service_name)
            
            # Emotional patterns with keywords and phrases
            self.emotional_patterns = {
                "sadness": {
                    "keywords": ["sad", "depressed", "down", "unhappy", "miserable", "heartbroken", "crying", "tears"],
                    "phrases": ["feel sad", "feeling down", "lost someone", "miss my", "passed away", "died"],
                    "intensity": 0
                },
                "anxiety": {
                    "keywords": ["anxious", "worried", "scared", "nervous", "panic", "stress", "stressed", "overwhelming"],
                    "phrases": ["can't sleep", "worried about", "scared of", "what if", "anxiety attack", "freaking out"],
                    "intensity": 0
                },
                "anger": {
                    "keywords": ["angry", "mad", "furious", "upset", "frustrated", "annoyed", "irritated"],
                    "phrases": ["so angry", "makes me mad", "hate when", "fed up", "can't stand"],
                    "intensity": 0
                },
                "guilt": {
                    "keywords": ["guilty", "ashamed", "regret", "remorse", "sorry", "mistake", "wrong", "sin", "sinned"],
                    "phrases": ["feel guilty", "did something wrong", "made a mistake", "feel bad about", "can't forgive myself"],
                    "intensity": 0
                },
                "loneliness": {
                    "keywords": ["lonely", "alone", "isolated", "nobody", "friendless"],
                    "phrases": ["feel alone", "no one understands", "by myself", "don't have anyone", "feel isolated"],
                    "intensity": 0
                },
                "confusion": {
                    "keywords": ["confused", "lost", "unsure", "uncertain", "doubt", "questioning"],
                    "phrases": ["don't know what", "confused about", "lost my way", "questioning my", "having doubts"],
                    "intensity": 0
                },
                "gratitude": {
                    "keywords": ["grateful", "thankful", "blessed", "alhamdulillah", "happy", "joy", "pleased"],
                    "phrases": ["thank you", "feeling blessed", "so grateful", "allah blessed", "good news"],
                    "intensity": 0
                },
                "hope": {
                    "keywords": ["hope", "hopeful", "optimistic", "inshallah", "better", "improve"],
                    "phrases": ["hope for", "things will get", "looking forward", "pray for", "wish for"],
                    "intensity": 0
                }
            }
            
            # Islamic comfort responses by emotion
            self.comfort_responses = {
                "sadness": [
                    "I can sense you're going through a difficult time. Remember, Allah promises that 'Indeed, with hardship comes ease' (94:5-6).",
                    "Your sadness is valid, and Allah sees your pain. He is closer to you than your jugular vein and hears even the whispers of your heart.",
                    "In times of sadness, Prophet Yaqub (AS) said 'I only complain of my suffering and my grief to Allah' (12:86). Turn to Him in prayer."
                ],
                "anxiety": [
                    "I understand you're feeling anxious. Allah reminds us: 'Those who believe and whose hearts find comfort in the remembrance of Allah. Indeed, in the remembrance of Allah do hearts find comfort' (13:28).",
                    "When anxiety overwhelms you, remember that Allah never burdens a soul beyond what it can bear (2:286). You are stronger than you think.",
                    "Try this dua for anxiety: 'اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ' (O Allah, I seek refuge in You from anxiety and sorrow)."
                ],
                "guilt": [
                    "Feeling guilty shows your heart is alive and seeking righteousness. Allah says: 'O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins' (39:53).",
                    "Your remorse is the first step toward repentance. Allah loves those who turn to Him. He is At-Tawwab (The Accepter of Repentance).",
                    "Remember, the Prophet ﷺ said: 'All children of Adam are sinners, but the best of sinners are those who repent.'"
                ],
                "loneliness": [
                    "You're never truly alone. Allah says: 'We are closer to him than his jugular vein' (50:16). He is always with you.",
                    "In your loneliness, remember Prophet Yunus (AS) in the whale's belly. His dua saved him: 'لَا إِلَهَ إِلَّا أَنْتَ سُبْحَانَكَ إِنِّي كُنْتُ مِنَ الظَّالِمِينَ'",
                    "The Prophet ﷺ also felt lonely at times. Find comfort in prayer - it's your direct connection with Allah."
                ]
            }
            
            # Supportive phrases to add warmth
            self.supportive_phrases = [
                "I'm here to listen and help in any way I can.",
                "Your feelings are valid and important.",
                "May Allah ease your heart and grant you peace.",
                "You're not alone in this journey.",
                "Take it one step at a time, with Allah's help."
            ]
            
            TreeLogger.info("Emotional intelligence module initialized", {
                "emotion_types": len(self.emotional_patterns),
                "comfort_responses": len(self.comfort_responses),
                "supportive_phrases": len(self.supportive_phrases)
            }, service=self.service_name)
            
        except Exception as e:
            TreeLogger.error("Failed to initialize emotional intelligence module", e, {
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, service=self.service_name)
            raise
    
    def detect_emotion(self, message: str) -> Tuple[Optional[str], float]:
        """
        Detect the primary emotion in a message.
        
        Args:
            message: User's message
            
        Returns:
            Tuple of (emotion, confidence_score)
        """
        try:
            TreeLogger.debug("Detecting emotion in message", {
                "message_length": len(message) if message else 0
            }, service=self.service_name)
            
            if not message:
                TreeLogger.warning("Empty message provided for emotion detection", service=self.service_name)
                return None, 0.0
            
            message_lower = message.lower()
            emotion_scores = {}
            
            for emotion, patterns in self.emotional_patterns.items():
                score = 0
                matched_keywords = []
                matched_phrases = []
                
                # Check keywords
                for keyword in patterns["keywords"]:
                    if keyword in message_lower:
                        score += 2
                        matched_keywords.append(keyword)
                
                # Check phrases (weighted higher)
                for phrase in patterns["phrases"]:
                    if phrase in message_lower:
                        score += 3
                        matched_phrases.append(phrase)
                
                # Check for intensity modifiers
                intensity_words = ["very", "so", "really", "extremely", "completely", "totally", "too"]
                intensity_count = 0
                for word in intensity_words:
                    if word in message_lower:
                        score += 1
                        intensity_count += 1
                
                if score > 0:
                    emotion_scores[emotion] = {
                        "score": score,
                        "matched_keywords": matched_keywords,
                        "matched_phrases": matched_phrases,
                        "intensity_count": intensity_count
                    }
            
            if not emotion_scores:
                TreeLogger.debug("No emotions detected in message", service=self.service_name)
                return None, 0.0
            
            # Find the emotion with highest score
            best_emotion = max(emotion_scores.keys(), key=lambda e: emotion_scores[e]["score"])
            best_score = emotion_scores[best_emotion]["score"]
            
            # Calculate confidence (normalize to 0-1 range)
            max_possible_score = 10  # Reasonable max score
            confidence = min(best_score / max_possible_score, 1.0)
            
            TreeLogger.debug("Emotion detected", {
                "emotion": best_emotion,
                "confidence": confidence,
                "score": best_score,
                "matched_keywords": emotion_scores[best_emotion]["matched_keywords"],
                "matched_phrases": emotion_scores[best_emotion]["matched_phrases"]
            }, service=self.service_name)
            
            return best_emotion, confidence
            
        except Exception as e:
            TreeLogger.error("Error detecting emotion", e, {
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, service=self.service_name)
            
            return None, 0.0
    
    def get_emotional_response(self, emotion: str, confidence: float) -> Dict[str, any]:
        """
        Get appropriate Islamic response for detected emotion.
        
        Args:
            emotion: Detected emotion
            confidence: Confidence score (0-1)
            
        Returns:
            Dictionary with response components
        """
        try:
            TreeLogger.debug("Getting emotional response", {
                "emotion": emotion,
                "confidence": confidence
            }, service=self.service_name)
            
            if not emotion or confidence < 0.3:
                TreeLogger.debug("Low confidence emotion, using general response", service=self.service_name)
                return {
                    "response": "I'm here to help you with any questions or concerns you might have.",
                    "emotion": None,
                    "confidence": 0.0,
                    "islamic_guidance": False
                }
            
            # Get comfort response for the emotion
            comfort_responses = self.comfort_responses.get(emotion, [])
            
            if not comfort_responses:
                TreeLogger.debug("No specific comfort response for emotion", {
                    "emotion": emotion
                }, service=self.service_name)
                return {
                    "response": "I understand you're going through something difficult. Remember that Allah is always with you and hears your prayers.",
                    "emotion": emotion,
                    "confidence": confidence,
                    "islamic_guidance": True
                }
            
            # Select a response based on confidence
            import random
            selected_response = random.choice(comfort_responses)
            
            # Add a supportive phrase
            supportive_phrase = random.choice(self.supportive_phrases)
            full_response = f"{selected_response} {supportive_phrase}"
            
            TreeLogger.info("Emotional response prepared", {
                "emotion": emotion,
                "confidence": confidence,
                "response_length": len(full_response),
                "has_islamic_guidance": True
            }, service=self.service_name)
            
            return {
                "response": full_response,
                "emotion": emotion,
                "confidence": confidence,
                "islamic_guidance": True
            }
            
        except Exception as e:
            TreeLogger.error("Error getting emotional response", e, {
                "emotion": emotion,
                "confidence": confidence,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, service=self.service_name)
            
            return {
                "response": "I'm here to help you with any questions or concerns you might have.",
                "emotion": None,
                "confidence": 0.0,
                "islamic_guidance": False
            }
    
    def analyze_emotional_context(self, message: str) -> Dict[str, any]:
        """
        Comprehensive emotional analysis of a message.
        
        Args:
            message: User's message
            
        Returns:
            Dictionary with emotional analysis
        """
        try:
            TreeLogger.debug("Analyzing emotional context", {
                "message_length": len(message) if message else 0
            }, service=self.service_name)
            
            if not message:
                TreeLogger.warning("Empty message provided for emotional analysis", service=self.service_name)
                return {
                    "primary_emotion": None,
                    "confidence": 0.0,
                    "emotional_intensity": "low",
                    "needs_support": False,
                    "response": None
                }
            
            # Detect primary emotion
            emotion, confidence = self.detect_emotion(message)
            
            # Determine emotional intensity
            if confidence >= 0.7:
                intensity = "high"
            elif confidence >= 0.4:
                intensity = "medium"
            else:
                intensity = "low"
            
            # Determine if support is needed
            needs_support = emotion in ["sadness", "anxiety", "guilt", "loneliness"] and confidence >= 0.4
            
            # Get response if needed
            response = None
            if needs_support:
                response_data = self.get_emotional_response(emotion, confidence)
                response = response_data["response"]
            
            analysis = {
                "primary_emotion": emotion,
                "confidence": confidence,
                "emotional_intensity": intensity,
                "needs_support": needs_support,
                "response": response
            }
            
            TreeLogger.info("Emotional analysis completed", {
                "primary_emotion": emotion,
                "confidence": confidence,
                "intensity": intensity,
                "needs_support": needs_support,
                "has_response": response is not None
            }, service=self.service_name)
            
            return analysis
            
        except Exception as e:
            TreeLogger.error("Error analyzing emotional context", e, {
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, service=self.service_name)
            
            return {
                "primary_emotion": None,
                "confidence": 0.0,
                "emotional_intensity": "low",
                "needs_support": False,
                "response": None
            }
    
    def get_emotion_aware_greeting(self, emotion: Optional[str]) -> Optional[str]:
        """
        Get an emotion-aware greeting based on detected emotion.
        
        Args:
            emotion: Detected emotion (optional)
            
        Returns:
            Emotion-aware greeting or None
        """
        try:
            if not emotion:
                return None
            
            greetings = {
                "sadness": "Assalamu alaikum. I can sense you're going through a difficult time. How can I help you today?",
                "anxiety": "Assalamu alaikum. I understand you might be feeling anxious. Remember, Allah is with you. What's on your mind?",
                "gratitude": "Assalamu alaikum! Alhamdulillah for your grateful heart. How can I assist you today?",
                "hope": "Assalamu alaikum! InshaAllah, I'm here to help you. What would you like to know?",
                "loneliness": "Assalamu alaikum. You're not alone - I'm here to help. What would you like to discuss?"
            }
            
            greeting = greetings.get(emotion)
            
            if greeting:
                TreeLogger.debug("Emotion-aware greeting provided", {
                    "emotion": emotion,
                    "greeting_length": len(greeting)
                }, service=self.service_name)
            
            return greeting
            
        except Exception as e:
            TreeLogger.error("Error getting emotion-aware greeting", e, {
                "emotion": emotion,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, service=self.service_name)
            
            return None