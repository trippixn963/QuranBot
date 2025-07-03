"""
Surah mapping utility for the Quran Bot.
Maps surah numbers to their names and provides utility functions.
"""

import json
import os
from typing import Optional, Dict, Any
from monitoring.logging.log_helpers import log_function_call, log_operation

# Complete mapping of surah numbers to their names
SURAH_NAMES = {
    1: ("Al-Fatiha", "الفاتحة", "The Opening"),
    2: ("Al-Baqarah", "البقرة", "The Cow"),
    3: ("Aal-Imran", "آل عمران", "The Family of Imran"),
    4: ("An-Nisa", "النساء", "The Women"),
    5: ("Al-Ma'idah", "المائدة", "The Table Spread"),
    6: ("Al-An'am", "الأنعام", "The Cattle"),
    7: ("Al-A'raf", "الأعراف", "The Heights"),
    8: ("Al-Anfal", "الأنفال", "The Spoils of War"),
    9: ("At-Tawbah", "التوبة", "The Repentance"),
    10: ("Yunus", "يونس", "Jonah"),
    11: ("Hud", "هود", "Hud"),
    12: ("Yusuf", "يوسف", "Joseph"),
    13: ("Ar-Ra'd", "الرعد", "The Thunder"),
    14: ("Ibrahim", "إبراهيم", "Abraham"),
    15: ("Al-Hijr", "الحجر", "The Rocky Tract"),
    16: ("An-Nahl", "النحل", "The Bee"),
    17: ("Al-Isra", "الإسراء", "The Night Journey"),
    18: ("Al-Kahf", "الكهف", "The Cave"),
    19: ("Maryam", "مريم", "Mary"),
    20: ("Ta-Ha", "طه", "Ta-Ha"),
    21: ("Al-Anbya", "الأنبياء", "The Prophets"),
    22: ("Al-Hajj", "الحج", "The Pilgrimage"),
    23: ("Al-Mu'minun", "المؤمنون", "The Believers"),
    24: ("An-Nur", "النور", "The Light"),
    25: ("Al-Furqan", "الفرقان", "The Criterion"),
    26: ("Ash-Shu'ara", "الشعراء", "The Poets"),
    27: ("An-Naml", "النمل", "The Ant"),
    28: ("Al-Qasas", "القصص", "The Stories"),
    29: ("Al-Ankabut", "العنكبوت", "The Spider"),
    30: ("Ar-Rum", "الروم", "The Romans"),
    31: ("Luqman", "لقمان", "Luqman"),
    32: ("As-Sajdah", "السجدة", "The Prostration"),
    33: ("Al-Ahzab", "الأحزاب", "The Combined Forces"),
    34: ("Saba", "سبإ", "Sheba"),
    35: ("Fatir", "فاطر", "Originator"),
    36: ("Ya-Sin", "يس", "Ya-Sin"),
    37: ("As-Saffat", "الصافات", "Those Who Set The Ranks"),
    38: ("Sad", "ص", "The Letter Sad"),
    39: ("Az-Zumar", "الزمر", "The Troops"),
    40: ("Ghafir", "غافر", "The Forgiver"),
    41: ("Fussilat", "فصلت", "Explained in Detail"),
    42: ("Ash-Shura", "الشورى", "The Consultation"),
    43: ("Az-Zukhruf", "الزخرف", "The Ornaments of Gold"),
    44: ("Ad-Dukhan", "الدخان", "The Smoke"),
    45: ("Al-Jathiyah", "الجاثية", "The Kneeling"),
    46: ("Al-Ahqaf", "الأحقاف", "The Wind-Curved Sandhills"),
    47: ("Muhammad", "محمد", "Muhammad"),
    48: ("Al-Fath", "الفتح", "The Victory"),
    49: ("Al-Hujurat", "الحجرات", "The Rooms"),
    50: ("Qaf", "ق", "Qaf"),
    51: ("Adh-Dhariyat", "الذاريات", "The Winnowing Winds"),
    52: ("At-Tur", "الطور", "The Mount"),
    53: ("An-Najm", "النجم", "The Star"),
    54: ("Al-Qamar", "القمر", "The Moon"),
    55: ("Ar-Rahman", "الرحمن", "The Beneficent"),
    56: ("Al-Waqi'ah", "الواقعة", "The Inevitable"),
    57: ("Al-Hadid", "الحديد", "The Iron"),
    58: ("Al-Mujadila", "المجادلة", "The Pleading Woman"),
    59: ("Al-Hashr", "الحشر", "The Exile"),
    60: ("Al-Mumtahanah", "الممتحنة", "The Woman to be Examined"),
    61: ("As-Saf", "الصف", "The Ranks"),
    62: ("Al-Jumu'ah", "الجمعة", "The Congregation"),
    63: ("Al-Munafiqun", "المنافقون", "The Hypocrites"),
    64: ("At-Taghabun", "التغابن", "The Mutual Disillusion"),
    65: ("At-Talaq", "الطلاق", "Divorce"),
    66: ("At-Tahrim", "التحريم", "The Prohibition"),
    67: ("Al-Mulk", "الملك", "The Sovereignty"),
    68: ("Al-Qalam", "القلم", "The Pen"),
    69: ("Al-Haqqah", "الحاقة", "The Reality"),
    70: ("Al-Ma'arij", "المعارج", "The Ascending Stairways"),
    71: ("Nuh", "نوح", "Noah"),
    72: ("Al-Jinn", "الجن", "The Jinn"),
    73: ("Al-Muzzammil", "المزمل", "The Enshrouded One"),
    74: ("Al-Muddathir", "المدثر", "The Cloaked One"),
    75: ("Al-Qiyamah", "القيامة", "The Resurrection"),
    76: ("Al-Insan", "الإنسان", "The Man"),
    77: ("Al-Mursalat", "المرسلات", "The Emissaries"),
    78: ("An-Naba", "النبإ", "The Tidings"),
    79: ("An-Nazi'at", "النازعات", "Those Who Drag Forth"),
    80: ("Abasa", "عبس", "He Frowned"),
    81: ("At-Takwir", "التكوير", "The Overthrowing"),
    82: ("Al-Infitar", "الإنفطار", "The Cleaving"),
    83: ("Al-Mutaffifin", "المطففين", "The Defrauding"),
    84: ("Al-Inshiqaq", "الإنشقاق", "The Splitting Open"),
    85: ("Al-Buruj", "البروج", "The Mansions of the Stars"),
    86: ("At-Tariq", "الطارق", "The Morning Star"),
    87: ("Al-A'la", "الأعلى", "The Most High"),
    88: ("Al-Ghashiyah", "الغاشية", "The Overwhelming"),
    89: ("Al-Fajr", "الفجر", "The Dawn"),
    90: ("Al-Balad", "البلد", "The City"),
    91: ("Ash-Shams", "الشمس", "The Sun"),
    92: ("Al-Layl", "الليل", "The Night"),
    93: ("Ad-Duha", "الضحى", "The Morning Hours"),
    94: ("Ash-Sharh", "الشرح", "The Relief"),
    95: ("At-Tin", "التين", "The Fig"),
    96: ("Al-'Alaq", "العلق", "The Clot"),
    97: ("Al-Qadr", "القدر", "The Power"),
    98: ("Al-Bayyinah", "البينة", "The Clear Proof"),
    99: ("Az-Zalzalah", "الزلزلة", "The Earthquake"),
    100: ("Al-'Adiyat", "العاديات", "The Coursers"),
    101: ("Al-Qari'ah", "القارعة", "The Calamity"),
    102: ("At-Takathur", "التكاثر", "The Rivalry in World Increase"),
    103: ("Al-'Asr", "العصر", "The Declining Day"),
    104: ("Al-Humazah", "الهمزة", "The Traducer"),
    105: ("Al-Fil", "الفيل", "The Elephant"),
    106: ("Quraish", "قريش", "Quraish"),
    107: ("Al-Ma'un", "الماعون", "The Small Kindnesses"),
    108: ("Al-Kawthar", "الكوثر", "The Abundance"),
    109: ("Al-Kafirun", "الكافرون", "The Disbelievers"),
    110: ("An-Nasr", "النصر", "The Divine Support"),
    111: ("Al-Masad", "المسد", "The Palm Fiber"),
    112: ("Al-Ikhlas", "الإخلاص", "The Sincerity"),
    113: ("Al-Falaq", "الفلق", "The Daybreak"),
    114: ("An-Nas", "الناس", "The Mankind")
}

# Custom mapping file path
CUSTOM_MAPPING_FILE = "custom_surah_mapping.json"

def load_custom_mapping() -> Dict[str, int]:
    """Load custom surah mapping from file."""
    if os.path.exists(CUSTOM_MAPPING_FILE):
        try:
            with open(CUSTOM_MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            from monitoring.logging.logger import logger
            logger.error(f"Error loading custom mapping: {e}")
    return {}

def save_custom_mapping(mapping: Dict[str, int]) -> bool:
    """Save custom surah mapping to file."""
    try:
        with open(CUSTOM_MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        from monitoring.logging.logger import logger
        logger.error(f"Error saving custom mapping: {e}")
        return False

def get_surah_info(surah_number: int) -> dict:
    """Get information about a surah by its number."""
    if surah_number not in SURAH_NAMES:
        return {
            "number": surah_number,
            "english_name": f"Surah {surah_number}",
            "arabic_name": f"سورة {surah_number}",
            "translation": "Unknown"
        }
    
    english_name, arabic_name, translation = SURAH_NAMES[surah_number]
    return {
        "number": surah_number,
        "english_name": english_name,
        "arabic_name": arabic_name,
        "translation": translation
    }

def get_surah_from_filename(filename: str) -> dict:
    """Extract surah information from a filename like '001.mp3', '1.mp3', '10.mp3', etc."""
    try:
        # Check custom mapping first
        custom_mapping = load_custom_mapping()
        if filename in custom_mapping:
            surah_number = custom_mapping[filename]
            return get_surah_info(surah_number)
        
        # Handle different filename formats
        # Remove .mp3 extension
        name_without_ext = filename.replace('.mp3', '')
        
        # Try to extract number from various formats
        if name_without_ext.isdigit():
            # Handle: 1.mp3, 2.mp3, 10.mp3, 100.mp3, etc.
            surah_number = int(name_without_ext)
        elif '.' in name_without_ext:
            # Handle: 001.mp3, 002.mp3, etc.
            surah_number = int(name_without_ext.split('.')[0])
        else:
            # Try to extract any number from the filename
            import re
            numbers = re.findall(r'\d+', name_without_ext)
            if numbers:
                surah_number = int(numbers[0])
            else:
                raise ValueError("No number found in filename")
        
        return get_surah_info(surah_number)
    except (ValueError, IndexError):
        return {
            "number": 0,
            "english_name": "Unknown",
            "arabic_name": "غير معروف",
            "translation": "Unknown"
        }

def get_surah_display_name(surah_number: int, include_number: bool = True) -> str:
    """Get a formatted display name for a surah."""
    surah_info = get_surah_info(surah_number)
    if include_number:
        return f"{surah_info['number']:03d}. {surah_info['english_name']}"
    return surah_info['english_name']

def get_surah_emoji(surah_number: int) -> str:
    """Get an appropriate emoji for a surah based on its theme or name."""
    # Comprehensive emoji mapping for all major surahs
    special_emojis = {
        1: "🕋",   # Al-Fatiha (The Opening)
        2: "🐄",   # Al-Baqarah (The Cow)
        3: "👨‍👩‍👧‍👦",  # Aal-Imran (The Family of Imran)
        4: "👩",   # An-Nisa (The Women)
        5: "🍽️",   # Al-Ma'idah (The Table Spread)
        6: "🐪",   # Al-An'am (The Cattle)
        7: "⛰️",   # Al-A'raf (The Heights)
        8: "⚔️",   # Al-Anfal (The Spoils of War)
        9: "🔄",   # At-Tawbah (The Repentance)
        10: "🙏",  # Yunus (Jonah)
        11: "👨",  # Hud (Hud)
        12: "👑",  # Yusuf (Joseph)
        13: "⚡",  # Ar-Ra'd (The Thunder)
        14: "👴",  # Ibrahim (Abraham)
        15: "🗿",  # Al-Hijr (The Rocky Tract)
        16: "🐝",  # An-Nahl (The Bee)
        17: "🌙",  # Al-Isra (The Night Journey)
        18: "🕳️",  # Al-Kahf (The Cave)
        19: "👸",  # Maryam (Mary)
        20: "📜",  # Ta-Ha
        21: "👥",  # Al-Anbya (The Prophets)
        22: "🕋",  # Al-Hajj (The Pilgrimage)
        23: "🙏",  # Al-Mu'minun (The Believers)
        24: "💡",  # An-Nur (The Light)
        25: "⚖️",  # Al-Furqan (The Criterion)
        26: "✍️",  # Ash-Shu'ara (The Poets)
        27: "🐜",  # An-Naml (The Ant)
        28: "📚",  # Al-Qasas (The Stories)
        29: "🕷️",  # Al-Ankabut (The Spider)
        30: "🏛️",  # Ar-Rum (The Romans)
        31: "🧙",  # Luqman (Luqman)
        32: "🙇",  # As-Sajdah (The Prostration)
        33: "🛡️",  # Al-Ahzab (The Combined Forces)
        34: "👸",  # Saba (Sheba)
        35: "🌟",  # Fatir (Originator)
        36: "📖",  # Ya-Sin
        37: "👨‍⚖️",  # As-Saffat (Those Who Set The Ranks)
        38: "📝",  # Sad (The Letter Sad)
        39: "👥",  # Az-Zumar (The Troops)
        40: "🛡️",  # Ghafir (The Forgiver)
        41: "📋",  # Fussilat (Explained in Detail)
        42: "🤝",  # Ash-Shura (The Consultation)
        43: "✨",  # Az-Zukhruf (The Ornaments of Gold)
        44: "💨",  # Ad-Dukhan (The Smoke)
        45: "🧎",  # Al-Jathiyah (The Kneeling)
        46: "🏔️",  # Al-Ahqaf (The Wind-Curved Sandhills)
        47: "👨‍🦲",  # Muhammad
        48: "🏆",  # Al-Fath (The Victory)
        49: "🏠",  # Al-Hujurat (The Rooms)
        50: "📄",  # Qaf
        51: "💨",  # Adh-Dhariyat (The Winnowing Winds)
        52: "⛰️",  # At-Tur (The Mount)
        53: "⭐",  # An-Najm (The Star)
        54: "🌙",  # Al-Qamar (The Moon)
        55: "🌺",  # Ar-Rahman (The Beneficent)
        56: "⚠️",  # Al-Waqi'ah (The Inevitable)
        57: "⚔️",  # Al-Hadid (The Iron)
        58: "👩‍⚖️",  # Al-Mujadila (The Pleading Woman)
        59: "🚪",  # Al-Hashr (The Exile)
        60: "👩‍💼",  # Al-Mumtahanah (The Woman to be Examined)
        61: "📋",  # As-Saf (The Ranks)
        62: "🕌",  # Al-Jumu'ah (The Congregation)
        63: "😈",  # Al-Munafiqun (The Hypocrites)
        64: "💔",  # At-Taghabun (The Mutual Disillusion)
        65: "💔",  # At-Talaq (Divorce)
        66: "🚫",  # At-Tahrim (The Prohibition)
        67: "👑",  # Al-Mulk (The Sovereignty)
        68: "✒️",  # Al-Qalam (The Pen)
        69: "⚖️",  # Al-Haqqah (The Reality)
        70: "🪜",  # Al-Ma'arij (The Ascending Stairways)
        71: "⛵",  # Nuh (Noah)
        72: "👻",  # Al-Jinn (The Jinn)
        73: "🛌",  # Al-Muzzammil (The Enshrouded One)
        74: "🧥",  # Al-Muddathir (The Cloaked One)
        75: "⚰️",  # Al-Qiyamah (The Resurrection)
        76: "👤",  # Al-Insan (The Man)
        77: "📧",  # Al-Mursalat (The Emissaries)
        78: "📰",  # An-Naba (The Tidings)
        79: "💨",  # An-Nazi'at (Those Who Drag Forth)
        80: "😤",  # Abasa (He Frowned)
        81: "🔄",  # At-Takwir (The Overthrowing)
        82: "💥",  # Al-Infitar (The Cleaving)
        83: "⚖️",  # Al-Mutaffifin (The Defrauding)
        84: "💥",  # Al-Inshiqaq (The Splitting Open)
        85: "⭐",  # Al-Buruj (The Mansions of the Stars)
        86: "🌟",  # At-Tariq (The Morning Star)
        87: "⬆️",  # Al-A'la (The Most High)
        88: "😰",  # Al-Ghashiyah (The Overwhelming)
        89: "🌅",  # Al-Fajr (The Dawn)
        90: "🏙️",  # Al-Balad (The City)
        91: "☀️",  # Ash-Shams (The Sun)
        92: "🌃",  # Al-Layl (The Night)
        93: "🌅",  # Ad-Duha (The Morning Hours)
        94: "😌",  # Ash-Sharh (The Relief)
        95: "🟫",  # At-Tin (The Fig)
        96: "🩸",  # Al-'Alaq (The Clot)
        97: "✨",  # Al-Qadr (The Power)
        98: "📖",  # Al-Bayyinah (The Clear Proof)
        99: "🌍",  # Az-Zalzalah (The Earthquake)
        100: "🐎", # Al-'Adiyat (The Coursers)
        101: "😨", # Al-Qari'ah (The Calamity)
        102: "🏆", # At-Takathur (The Rivalry in World Increase)
        103: "⏰", # Al-'Asr (The Declining Day)
        104: "🗣️", # Al-Humazah (The Traducer)
        105: "🐘", # Al-Fil (The Elephant)
        106: "🕋", # Quraish
        107: "🤲", # Al-Ma'un (The Small Kindnesses)
        108: "🌊", # Al-Kawthar (The Abundance)
        109: "❌", # Al-Kafirun (The Disbelievers)
        110: "🏆", # An-Nasr (The Divine Support)
        111: "🔥", # Al-Masad (The Palm Fiber)
        112: "💎", # Al-Ikhlas (The Sincerity)
        113: "🌅", # Al-Falaq (The Daybreak)
        114: "👥"  # An-Nas (The Mankind)
    }
    
    return special_emojis.get(surah_number, "📖")

def create_custom_mapping_template() -> Dict[str, int]:
    """Create a template for custom surah mapping."""
    template = {}
    for i in range(1, 115):
        template[f"{i:03d}.mp3"] = i
    return template

def verify_and_fix_mapping(reciter_name: str) -> Dict[str, int]:
    """Create a verification script to help fix surah mapping."""
    from monitoring.logging.logger import logger
    logger.info(f"🔍 Surah Mapping Verification for {reciter_name}")
    logger.info("=" * 60)
    logger.info("This will help you create a custom mapping to fix misnamed audio files.")
    logger.info("For each file, enter the actual surah number (1-114) that the file contains.")
    logger.info("Press Enter to skip a file or use the default mapping.")
    logger.info("")
    
    custom_mapping = {}
    audio_folder = f"audio/{reciter_name}"
    
    if not os.path.exists(audio_folder):
        from monitoring.logging.logger import logger
        logger.error(f"❌ Reciter folder not found: {audio_folder}")
        return custom_mapping
    
    # Get all MP3 files
    mp3_files = [f for f in os.listdir(audio_folder) if f.lower().endswith('.mp3')]
    mp3_files.sort()
    
    for filename in mp3_files:
        current_surah = get_surah_from_filename(filename)
        from monitoring.logging.logger import logger
        logger.info(f"File: {filename}")
        logger.info(f"Current mapping: {current_surah['english_name']} (Surah {current_surah['number']})")
        
        user_input = input(f"Enter actual surah number (1-114) or press Enter to keep current: ").strip()
        
        if user_input:
            try:
                surah_number = int(user_input)
                if 1 <= surah_number <= 114:
                    custom_mapping[filename] = surah_number
                    actual_surah = get_surah_info(surah_number)
                    from monitoring.logging.logger import logger
                    logger.info(f"✅ Mapped {filename} to {actual_surah['english_name']}")
                else:
                    from monitoring.logging.logger import logger
                    logger.warning(f"❌ Invalid surah number: {surah_number}")
            except ValueError:
                from monitoring.logging.logger import logger
                logger.warning(f"❌ Invalid input: {user_input}")
        else:
            from monitoring.logging.logger import logger
            logger.info(f"⏭️  Skipped {filename}")
        
        from monitoring.logging.logger import logger
        logger.info("")
    
    return custom_mapping 

def get_surah_names() -> list:
    """Get a list of all surah names."""
    surah_names = []
    for i in range(1, 115):  # 114 surahs in total
        surah_info = get_surah_info(i)
        surah_names.append(surah_info['english_name'])
    return surah_names 