# =============================================================================
# QuranBot - Islamic Knowledge Base
# =============================================================================
# Quranic verses, hadith references, and Islamic knowledge for AI responses
# =============================================================================

import random
import traceback
from typing import Any

from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger


class IslamicKnowledge:
    """
    Comprehensive Islamic knowledge base for context-aware AI responses.
    """

    def __init__(self) -> None:
        self.service_name = "IslamicKnowledge"
        self.error_handler = ErrorHandler()

        try:
            TreeLogger.info(
                "Initializing Islamic knowledge base", service=self.service_name
            )

            # Quranic verses by topic
            self.verses_by_topic = {
                "patience": [
                    {
                        "reference": "2:153",
                        "text": "O you who believe! Seek help through patience and prayer. Indeed, Allah is with the patient.",
                    },
                    {
                        "reference": "3:200",
                        "text": "O you who believe! Be patient, compete in patience, and remain stationed. And fear Allah that you may be successful.",
                    },
                    {
                        "reference": "16:127",
                        "text": "And be patient, and your patience is not but through Allah.",
                    },
                    {
                        "reference": "39:10",
                        "text": "Indeed, those who are patient will be given their reward without account.",
                    },
                ],
                "prayer": [
                    {
                        "reference": "2:45",
                        "text": "And seek help through patience and prayer, and indeed, it is difficult except for the humbly submissive.",
                    },
                    {
                        "reference": "4:103",
                        "text": "Indeed, prayer has been decreed upon the believers a decree of specified times.",
                    },
                    {
                        "reference": "20:14",
                        "text": "Indeed, I am Allah. There is no deity except Me, so worship Me and establish prayer for My remembrance.",
                    },
                    {
                        "reference": "29:45",
                        "text": "Recite what has been revealed to you of the Book and establish prayer. Indeed, prayer prohibits immorality and wrongdoing.",
                    },
                ],
                "gratitude": [
                    {
                        "reference": "14:7",
                        "text": "If you are grateful, I will surely increase you [in favor].",
                    },
                    {
                        "reference": "16:18",
                        "text": "And if you should count the favors of Allah, you could not enumerate them.",
                    },
                    {
                        "reference": "31:12",
                        "text": "And whoever is grateful is grateful for [the benefit of] himself.",
                    },
                    {
                        "reference": "39:66",
                        "text": "Rather, worship Allah and be among the grateful.",
                    },
                ],
                "forgiveness": [
                    {
                        "reference": "39:53",
                        "text": "Say, 'O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins.'",
                    },
                    {
                        "reference": "4:110",
                        "text": "And whoever does a wrong or wrongs himself but then seeks forgiveness of Allah will find Allah Forgiving and Merciful.",
                    },
                    {
                        "reference": "3:135",
                        "text": "And those who, when they commit an immorality or wrong themselves, remember Allah and seek forgiveness for their sins.",
                    },
                    {
                        "reference": "24:22",
                        "text": "Would you not like that Allah should forgive you? And Allah is Forgiving and Merciful.",
                    },
                ],
                "trust": [
                    {
                        "reference": "3:159",
                        "text": "Then when you have decided, then rely upon Allah. Indeed, Allah loves those who rely [upon Him].",
                    },
                    {
                        "reference": "65:3",
                        "text": "And whoever relies upon Allah - then He is sufficient for him.",
                    },
                    {
                        "reference": "9:51",
                        "text": "Say, 'Never will we be struck except by what Allah has decreed for us; He is our protector.'",
                    },
                    {
                        "reference": "25:58",
                        "text": "And rely upon the Ever-Living who does not die.",
                    },
                ],
                "anxiety": [
                    {
                        "reference": "13:28",
                        "text": "Those who have believed and whose hearts are assured by the remembrance of Allah. Unquestionably, by the remembrance of Allah hearts are assured.",
                    },
                    {
                        "reference": "94:5-6",
                        "text": "For indeed, with hardship [will be] ease. Indeed, with hardship [will be] ease.",
                    },
                    {
                        "reference": "9:40",
                        "text": "Do not grieve; indeed Allah is with us.",
                    },
                    {
                        "reference": "20:124",
                        "text": "And whoever turns away from My remembrance - indeed, he will have a depressed life.",
                    },
                ],
                "guidance": [
                    {
                        "reference": "2:2",
                        "text": "This is the Book about which there is no doubt, a guidance for those conscious of Allah.",
                    },
                    {"reference": "1:6", "text": "Guide us to the straight path."},
                    {
                        "reference": "16:89",
                        "text": "And We have sent down to you the Book as clarification for all things and as guidance and mercy and good tidings for the Muslims.",
                    },
                    {
                        "reference": "17:9",
                        "text": "Indeed, this Quran guides to that which is most suitable.",
                    },
                ],
            }

            # Emotional state mappings
            self.emotional_verses = {
                "sad": ["patience", "trust", "forgiveness"],
                "anxious": ["anxiety", "trust", "prayer"],
                "grateful": ["gratitude", "prayer"],
                "lost": ["guidance", "trust", "prayer"],
                "guilty": ["forgiveness", "prayer"],
                "worried": ["anxiety", "trust", "patience"],
            }

            # Common duas
            self.duas = {
                "anxiety": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ (O Allah, I seek refuge in You from anxiety and sorrow)",
                "guidance": "اللَّهُمَّ اهْدِنِي وَسَدِّدْنِي (O Allah, guide me and direct me)",
                "forgiveness": "رَبِّ اغْفِرْ لِي وَتُبْ عَلَيَّ (My Lord, forgive me and accept my repentance)",
                "gratitude": "الْحَمْدُ لِلَّهِ الَّذِي بِنِعْمَتِهِ تَتِمُّ الصَّالِحَاتُ (All praise is due to Allah by whose favor good deeds are completed)",
                "difficulty": "لَا إِلَهَ إِلَّا أَنْتَ سُبْحَانَكَ إِنِّي كُنْتُ مِنَ الظَّالِمِينَ (There is no deity except You; exalted are You. Indeed, I have been of the wrongdoers)",
                "decision": "اللَّهُمَّ خِرْ لِي وَاخْتَرْ لِي (O Allah, choose for me and make the choice for me)",
            }

            # Islamic calendar events
            self.islamic_events = {
                "ramadan": "The blessed month of fasting, mercy, and Quran",
                "eid_fitr": "The celebration marking the end of Ramadan",
                "eid_adha": "The festival of sacrifice commemorating Prophet Ibrahim's devotion",
                "muharram": "The sacred month marking the Islamic New Year",
                "mawlid": "The birth of Prophet Muhammad ﷺ",
                "isra_miraj": "The night journey and ascension of Prophet Muhammad ﷺ",
                "laylatul_qadr": "The Night of Power, better than a thousand months",
            }

            # Prophet stories by theme
            self.prophet_stories = {
                "patience": [
                    "Prophet Ayyub (Job) - patience through severe illness and loss",
                    "Prophet Yaqub (Jacob) - patience through the loss of Yusuf",
                    "Prophet Nuh (Noah) - patience in calling his people for 950 years",
                ],
                "trust": [
                    "Prophet Ibrahim (Abraham) - trust when thrown into the fire",
                    "Prophet Musa's (Moses) mother - trust when placing her baby in the river",
                    "Prophet Muhammad ﷺ - trust in the cave of Thawr",
                ],
                "forgiveness": [
                    "Prophet Yusuf (Joseph) - forgiving his brothers",
                    "Prophet Muhammad ﷺ - forgiving the people of Taif",
                    "Prophet Muhammad ﷺ - forgiving the Meccans after conquest",
                ],
            }

            TreeLogger.info(
                "Islamic knowledge base initialized",
                {
                    "verse_topics": len(self.verses_by_topic),
                    "total_verses": sum(
                        len(verses) for verses in self.verses_by_topic.values()
                    ),
                    "emotional_mappings": len(self.emotional_verses),
                    "duas": len(self.duas),
                    "events": len(self.islamic_events),
                    "prophet_story_themes": len(self.prophet_stories),
                },
                service=self.service_name,
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to initialize Islamic knowledge base",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )
            raise

    def get_relevant_verses(self, topic: str, count: int = 2) -> list[dict[str, str]]:
        """
        Get relevant Quranic verses for a topic.

        Args:
            topic: Topic to get verses for
            count: Number of verses to return

        Returns:
            List of verse dictionaries
        """
        try:
            TreeLogger.debug(
                "Getting relevant verses",
                {"topic": topic, "requested_count": count},
                service=self.service_name,
            )

            if not topic:
                TreeLogger.warning(
                    "Empty topic provided for verse lookup", service=self.service_name
                )
                return []

            verses = self.verses_by_topic.get(topic, [])

            if not verses:
                # Try to find related topic
                topic_lower = topic.lower()
                for key in self.verses_by_topic:
                    if topic_lower in key or key in topic_lower:
                        verses = self.verses_by_topic[key]
                        TreeLogger.debug(
                            "Found verses through fuzzy match",
                            {
                                "original_topic": topic,
                                "matched_topic": key,
                                "verse_count": len(verses),
                            },
                            service=self.service_name,
                        )
                        break

            if not verses:
                TreeLogger.debug(
                    "No verses found for topic",
                    {"topic": topic},
                    service=self.service_name,
                )
                return []

            # Return random selection
            result = verses if len(verses) <= count else random.sample(verses, count)

            TreeLogger.debug(
                "Verses retrieved",
                {
                    "topic": topic,
                    "available_verses": len(verses),
                    "returned_verses": len(result),
                },
                service=self.service_name,
            )

            return result

        except Exception as e:
            TreeLogger.error(
                "Error getting relevant verses",
                e,
                {
                    "topic": topic,
                    "count": count,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            return []

    def get_emotional_support(self, emotion: str) -> dict[str, Any]:
        """
        Get Islamic support for emotional states.

        Args:
            emotion: Emotional state

        Returns:
            Dictionary with verses, duas, and guidance
        """
        try:
            TreeLogger.debug(
                "Getting emotional support",
                {"emotion": emotion},
                service=self.service_name,
            )

            # Default support structure
            support = {"verses": [], "dua": None, "guidance": ""}

            if not emotion:
                TreeLogger.warning("Empty emotion provided", service=self.service_name)
                return support

            # Get relevant verse topics
            topics = self.emotional_verses.get(emotion, ["guidance"])

            TreeLogger.debug(
                "Found emotional verse topics",
                {"emotion": emotion, "topics": topics},
                service=self.service_name,
            )

            # Get verses from relevant topics
            for topic in topics[:2]:  # Get from first 2 topics
                try:
                    verses = self.get_relevant_verses(topic, 1)
                    support["verses"].extend(verses)
                except Exception as e:
                    TreeLogger.warning(
                        "Error getting verses for emotional support",
                        e,
                        {"emotion": emotion, "topic": topic},
                        service=self.service_name,
                    )

            # Get relevant dua
            support["dua"] = self.duas.get(emotion)

            # Add contextual guidance
            guidance_map = {
                "sad": "Remember that Allah tests those He loves. This difficulty is temporary and your patience is being rewarded.",
                "sadness": "Remember that Allah tests those He loves. This difficulty is temporary and your patience is being rewarded.",
                "anxious": "Turn to Allah in prayer and dhikr. He is Al-Mujeeb (The Responder) and hears every whisper of your heart.",
                "anxiety": "Turn to Allah in prayer and dhikr. He is Al-Mujeeb (The Responder) and hears every whisper of your heart.",
                "grateful": "Alhamdulillah! Gratitude increases blessings. Continue to thank Allah in all circumstances.",
                "gratitude": "Alhamdulillah! Gratitude increases blessings. Continue to thank Allah in all circumstances.",
                "lonely": "You are never alone. Allah is closer to you than your jugular vein. Turn to Him in prayer.",
                "loneliness": "You are never alone. Allah is closer to you than your jugular vein. Turn to Him in prayer.",
                "guilty": "Allah's mercy encompasses all things. Sincere repentance erases sins as if they never existed.",
                "guilt": "Allah's mercy encompasses all things. Sincere repentance erases sins as if they never existed.",
            }

            support["guidance"] = guidance_map.get(
                emotion,
                "Turn to Allah with your feelings. He understands what's in your heart.",
            )

            TreeLogger.info(
                "Emotional support prepared",
                {
                    "emotion": emotion,
                    "has_verses": len(support["verses"]) > 0,
                    "has_dua": support["dua"] is not None,
                    "has_guidance": bool(support["guidance"]),
                },
                service=self.service_name,
            )

            return support

        except Exception as e:
            TreeLogger.error(
                "Failed to get emotional support",
                e,
                {
                    "emotion": emotion,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            # Return default support structure
            return {
                "verses": [],
                "dua": None,
                "guidance": "Turn to Allah with your concerns. He is the Most Compassionate, the Most Merciful.",
            }

    def detect_question_type(self, question: str) -> str:
        """
        Detect the type of question being asked.

        Args:
            question: User's question

        Returns:
            Question type
        """
        try:
            TreeLogger.debug(
                "Detecting question type",
                {"question_length": len(question) if question else 0},
                service=self.service_name,
            )

            if not question:
                TreeLogger.warning(
                    "Empty question provided for type detection",
                    service=self.service_name,
                )
                return "general"

            question_lower = question.lower()

            # Question type patterns with priority order
            type_patterns = [
                # Emotional support (highest priority)
                {
                    "type": "emotional_support",
                    "patterns": [
                        "sad",
                        "depressed",
                        "anxious",
                        "worried",
                        "scared",
                        "stressed",
                        "lonely",
                        "crying",
                        "suffering",
                        "hurt",
                        "pain",
                        "difficult",
                        "hard time",
                    ],
                },
                # Definition questions
                {
                    "type": "definition",
                    "patterns": [
                        "what is",
                        "what are",
                        "who is",
                        "who was",
                        "define",
                        "meaning of",
                        "explain",
                        "tell me about",
                    ],
                },
                # Guidance questions
                {
                    "type": "guidance",
                    "patterns": [
                        "how should i",
                        "how do i",
                        "how can i",
                        "what should i",
                        "is it permissible",
                        "is it halal",
                        "is it haram",
                        "can i",
                        "am i allowed",
                        "should i",
                    ],
                },
                # Verse requests
                {
                    "type": "verse_request",
                    "patterns": [
                        "verse about",
                        "quran say",
                        "ayah about",
                        "surah about",
                        "verse on",
                        "verses about",
                        "what does allah say",
                    ],
                },
                # Story requests
                {
                    "type": "story",
                    "patterns": [
                        "tell me about prophet",
                        "story of",
                        "what happened to",
                        "prophet story",
                        "tell me the story",
                    ],
                },
                # Prayer related
                {
                    "type": "prayer",
                    "patterns": [
                        "how to pray",
                        "prayer time",
                        "salah",
                        "wudu",
                        "ablution",
                        "rakah",
                        "sunnah prayer",
                    ],
                },
                # Dua requests
                {
                    "type": "dua",
                    "patterns": ["dua for", "supplication", "prayer for", "what dua"],
                },
            ]

            # Check patterns in priority order
            for type_info in type_patterns:
                for pattern in type_info["patterns"]:
                    if pattern in question_lower:
                        TreeLogger.debug(
                            "Question type detected",
                            {"type": type_info["type"], "matched_pattern": pattern},
                            service=self.service_name,
                        )
                        return type_info["type"]

            # Default to general
            TreeLogger.debug(
                "No specific pattern matched, defaulting to general",
                service=self.service_name,
            )
            return "general"

        except Exception as e:
            TreeLogger.error(
                "Error detecting question type",
                e,
                {"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                service=self.service_name,
            )

            return "general"

    def get_related_topics(self, topic: str) -> list[str]:
        """
        Get topics related to the given topic.

        Args:
            topic: Main topic

        Returns:
            List of related topics
        """
        try:
            TreeLogger.debug(
                "Getting related topics", {"topic": topic}, service=self.service_name
            )

            if not topic:
                TreeLogger.warning(
                    "Empty topic provided for related topics", service=self.service_name
                )
                return []

            # Comprehensive related topics mapping
            related_topics = {
                "prayer": [
                    "wudu",
                    "qibla",
                    "prayer times",
                    "sunnah prayers",
                    "tahajjud",
                    "istikhara",
                ],
                "salah": [
                    "wudu",
                    "qibla",
                    "prayer times",
                    "sunnah prayers",
                    "tahajjud",
                    "istikhara",
                ],
                "fasting": [
                    "ramadan",
                    "suhoor",
                    "iftar",
                    "voluntary fasting",
                    "i'tikaf",
                    "laylatul qadr",
                ],
                "sawm": [
                    "ramadan",
                    "suhoor",
                    "iftar",
                    "voluntary fasting",
                    "i'tikaf",
                    "laylatul qadr",
                ],
                "hajj": [
                    "umrah",
                    "ihram",
                    "tawaf",
                    "sa'i",
                    "mina",
                    "arafat",
                    "muzdalifah",
                ],
                "umrah": ["hajj", "ihram", "tawaf", "sa'i", "mecca", "madinah"],
                "zakat": [
                    "sadaqah",
                    "charity",
                    "nisab",
                    "zakat calculation",
                    "zakat al-fitr",
                ],
                "charity": ["zakat", "sadaqah", "helping others", "generosity"],
                "marriage": [
                    "nikah",
                    "mahr",
                    "walimah",
                    "rights of spouses",
                    "family",
                    "divorce",
                ],
                "nikah": [
                    "marriage",
                    "mahr",
                    "walimah",
                    "spouse rights",
                    "family life",
                ],
                "quran": [
                    "tajweed",
                    "memorization",
                    "tafsir",
                    "recitation",
                    "understanding quran",
                ],
                "death": ["janazah", "afterlife", "barzakh", "day of judgment", "qadr"],
                "dua": ["supplication", "dhikr", "prayer", "asking allah"],
                "ramadan": [
                    "fasting",
                    "tarawih",
                    "laylatul qadr",
                    "eid",
                    "quran in ramadan",
                ],
                "eid": ["eid al-fitr", "eid al-adha", "celebration", "eid prayer"],
                "prophet": [
                    "sunnah",
                    "hadith",
                    "seerah",
                    "companions",
                    "prophetic guidance",
                ],
                "faith": [
                    "iman",
                    "belief",
                    "tawheed",
                    "pillars of islam",
                    "articles of faith",
                ],
                "repentance": [
                    "tawbah",
                    "forgiveness",
                    "istighfar",
                    "returning to allah",
                ],
            }

            # Try exact match first
            topic_lower = topic.lower()
            topics = related_topics.get(topic_lower, [])

            # If no exact match, try fuzzy matching
            if not topics:
                for key, values in related_topics.items():
                    if topic_lower in key or key in topic_lower:
                        topics = values
                        TreeLogger.debug(
                            "Found related topics through fuzzy match",
                            {"original_topic": topic, "matched_key": key},
                            service=self.service_name,
                        )
                        break

            TreeLogger.debug(
                "Related topics retrieved",
                {"topic": topic, "related_count": len(topics)},
                service=self.service_name,
            )

            return topics

        except Exception as e:
            TreeLogger.error(
                "Error getting related topics",
                e,
                {
                    "topic": topic,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                service=self.service_name,
            )

            return []
