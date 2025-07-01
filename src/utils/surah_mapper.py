"""
Surah mapping utility for the Quran Bot.
Maps surah numbers to their names and provides utility functions.
"""

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
    """Extract surah information from a filename like '001.mp3'."""
    try:
        # Extract number from filename (e.g., "001.mp3" -> 1)
        surah_number = int(filename.split('.')[0])
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
    # Special emojis for well-known surahs
    special_emojis = {
        1: "🕋",   # Al-Fatiha (The Opening)
        2: "🐄",   # Al-Baqarah (The Cow)
        18: "🕳️",  # Al-Kahf (The Cave)
        19: "👸",  # Maryam (Mary)
        36: "📖",  # Ya-Sin
        55: "🌙",  # Ar-Rahman (The Beneficent)
        67: "👑",  # Al-Mulk (The Sovereignty)
        97: "✨",  # Al-Qadr (The Power)
        112: "💎", # Al-Ikhlas (The Sincerity)
        113: "🌅", # Al-Falaq (The Daybreak)
        114: "👥"  # An-Nas (The Mankind)
    }
    
    return special_emojis.get(surah_number, "📖") 