#!/usr/bin/env python3
# =============================================================================
# Islamic Calendar Service - Hijri Dates & Islamic Events
# =============================================================================
# This service provides Islamic calendar functionality including Hijri date
# conversion, Islamic month information, and awareness of special Islamic
# events and occasions for contextualized AI responses.
# =============================================================================

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests

from src.utils.tree_log import log_perfect_tree_section, log_error_with_traceback


class IslamicCalendarService:
    """Manages Islamic calendar dates, events, and contextual information."""
    
    def __init__(self):
        self.calendar_cache_file = Path("data/islamic_calendar_cache.json")
        self.islamic_events_file = Path("data/islamic_events.json")
        
        # Islamic months with their significance
        self.islamic_months = {
            1: {
                'name_arabic': 'مُحَرَّم',
                'name_english': 'Muharram',
                'significance': 'Sacred month, contains Day of Ashura',
                'virtues': ['First month of Islamic year', 'Sacred month - no fighting', 'Contains Day of Ashura (10th)']
            },
            2: {
                'name_arabic': 'صَفَر',
                'name_english': 'Safar',
                'significance': 'Regular month, no special restrictions',
                'virtues': ['Travel month', 'Time for trade and business']
            },
            3: {
                'name_arabic': 'رَبِيع الأَوَّل',
                'name_english': "Rabi' al-Awwal",
                'significance': 'Month of Prophet Muhammad (ﷺ) birth',
                'virtues': ['Birth month of Prophet (ﷺ)', 'Month of sending Salawat', 'Mawlid celebrations']
            },
            4: {
                'name_arabic': 'رَبِيع الثَّانِي',
                'name_english': "Rabi' al-Thani",
                'significance': 'Second spring month',
                'virtues': ['Continuation of spring season', 'Good time for worship']
            },
            5: {
                'name_arabic': 'جُمَادَىٰ الأُولَىٰ',
                'name_english': 'Jumada al-Awwal',
                'significance': 'Dry month, minimal rainfall',
                'virtues': ['Time for reflection', 'Preparation for upcoming sacred months']
            },
            6: {
                'name_arabic': 'جُمَادَىٰ الآخِرَة',
                'name_english': 'Jumada al-Akhirah',
                'significance': 'Second dry month',
                'virtues': ['Final preparation before sacred months', 'Time for spiritual preparation']
            },
            7: {
                'name_arabic': 'رَجَب',
                'name_english': 'Rajab',
                'significance': 'Sacred month, preparation for Ramadan',
                'virtues': ['Sacred month - no fighting', 'Isra and Mi\'raj occurred', 'Preparation for Ramadan']
            },
            8: {
                'name_arabic': 'شَعْبَان',
                'name_english': "Sha'ban",
                'significance': 'Month of preparation for Ramadan',
                'virtues': ['Ramadan preparation month', 'Increased fasting recommended', 'Night of Bara\'at (15th)']
            },
            9: {
                'name_arabic': 'رَمَضَان',
                'name_english': 'Ramadan',
                'significance': 'Holy month of fasting and Quran revelation',
                'virtues': ['Month of fasting', 'Quran revealed', 'Laylat al-Qadr', 'Increased reward for good deeds']
            },
            10: {
                'name_arabic': 'شَوَّال',
                'name_english': 'Shawwal',
                'significance': 'Month of Eid al-Fitr celebration',
                'virtues': ['Eid al-Fitr (1st)', 'Six days of Shawwal fasting', 'Wedding month']
            },
            11: {
                'name_arabic': 'ذُو القَعْدَة',
                'name_english': "Dhu al-Qi'dah",
                'significance': 'Sacred month, Hajj preparation',
                'virtues': ['Sacred month - no fighting', 'Hajj preparation begins', 'Umrah season']
            },
            12: {
                'name_arabic': 'ذُو الحِجَّة',
                'name_english': 'Dhu al-Hijjah',
                'significance': 'Sacred month of Hajj and Eid al-Adha',
                'virtues': ['Sacred month', 'Hajj pilgrimage', 'Eid al-Adha (10th)', 'First 10 days are blessed', 'Day of Arafah (9th)']
            }
        }
        
        # Load Islamic events
        self._load_islamic_events()
        
        # Cache for API calls
        self.hijri_cache: Dict[str, Dict] = {}
        
    def _load_islamic_events(self):
        """Load Islamic events and occasions."""
        try:
            if self.islamic_events_file.exists():
                with open(self.islamic_events_file, 'r', encoding='utf-8') as f:
                    self.islamic_events = json.load(f)
            else:
                # Create default Islamic events
                self.islamic_events = self._create_default_events()
                self._save_islamic_events()
                
        except Exception as e:
            log_error_with_traceback("Error loading Islamic events", e)
            self.islamic_events = self._create_default_events()
            
    def _create_default_events(self) -> Dict:
        """Create default Islamic events calendar."""
        return {
            "annual_events": {
                "muharram_1": {
                    "name": "Islamic New Year",
                    "hijri_date": {"month": 1, "day": 1},
                    "significance": "Beginning of the Islamic calendar year",
                    "recommended_actions": ["Make dua for the new year", "Reflect on the past year", "Set Islamic goals"]
                },
                "muharram_10": {
                    "name": "Day of Ashura",
                    "hijri_date": {"month": 1, "day": 10},
                    "significance": "Day when Allah saved Prophet Musa (AS) from Pharaoh",
                    "recommended_actions": ["Fast this day", "Remember Allah's mercy", "Give charity"]
                },
                "rabi_awwal_12": {
                    "name": "Mawlid an-Nabi",
                    "hijri_date": {"month": 3, "day": 12},
                    "significance": "Birth of Prophet Muhammad (ﷺ)",
                    "recommended_actions": ["Send Salawat on the Prophet", "Study Seerah", "Increase good deeds"]
                },
                "rajab_27": {
                    "name": "Isra and Mi'raj",
                    "hijri_date": {"month": 7, "day": 27},
                    "significance": "Night journey of Prophet Muhammad (ﷺ)",
                    "recommended_actions": ["Night prayers", "Remembrance of Allah", "Study the journey"]
                },
                "shaban_15": {
                    "name": "Laylat al-Bara'at",
                    "hijri_date": {"month": 8, "day": 15},
                    "significance": "Night of forgiveness and destiny",
                    "recommended_actions": ["Night prayers", "Seek forgiveness", "Make dua", "Give charity"]
                },
                "ramadan_1": {
                    "name": "Beginning of Ramadan",
                    "hijri_date": {"month": 9, "day": 1},
                    "significance": "Start of the holy month of fasting",
                    "recommended_actions": ["Begin fasting", "Increase Quran reading", "Night prayers"]
                },
                "ramadan_laylat_qadr": {
                    "name": "Laylat al-Qadr",
                    "hijri_date": {"month": 9, "day": "last_10_odd"},
                    "significance": "Night of Power when Quran was revealed",
                    "recommended_actions": ["I'tikaf", "Extra prayers", "Seek this night", "Make abundant dua"]
                },
                "shawwal_1": {
                    "name": "Eid al-Fitr",
                    "hijri_date": {"month": 10, "day": 1},
                    "significance": "Festival celebrating end of Ramadan",
                    "recommended_actions": ["Eid prayers", "Zakat al-Fitr", "Family gatherings", "Charity"]
                },
                "dhul_hijjah_1_10": {
                    "name": "First 10 Days of Dhul Hijjah",
                    "hijri_date": {"month": 12, "day": "1-10"},
                    "significance": "Most blessed days of the year",
                    "recommended_actions": ["Increase good deeds", "Fast on Day of Arafah", "Dhikr and Takbir"]
                },
                "dhul_hijjah_9": {
                    "name": "Day of Arafah",
                    "hijri_date": {"month": 12, "day": 9},
                    "significance": "Pilgrims stand at Arafah, day of forgiveness",
                    "recommended_actions": ["Fast if not on Hajj", "Make abundant dua", "Seek forgiveness"]
                },
                "dhul_hijjah_10": {
                    "name": "Eid al-Adha",
                    "hijri_date": {"month": 12, "day": 10},
                    "significance": "Festival of sacrifice, commemorating Ibrahim (AS)",
                    "recommended_actions": ["Eid prayers", "Qurbani/sacrifice", "Family gatherings", "Charity"]
                }
            },
            "weekly_events": {
                "friday": {
                    "name": "Jumu'ah",
                    "significance": "Weekly congregational prayer",
                    "recommended_actions": ["Attend Jumu'ah prayer", "Read Surah Kahf", "Send Salawat", "Make dua"]
                }
            },
            "monthly_events": {
                "white_days": {
                    "name": "Ayyam al-Bid (White Days)",
                    "dates": [13, 14, 15],
                    "significance": "Three blessed days of each month",
                    "recommended_actions": ["Fast these three days", "Increase worship", "Give charity"]
                }
            }
        }
        
    def _save_islamic_events(self):
        """Save Islamic events to file."""
        try:
            self.islamic_events_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.islamic_events_file, 'w', encoding='utf-8') as f:
                json.dump(self.islamic_events, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error_with_traceback("Error saving Islamic events", e)
            
    async def get_current_hijri_date(self) -> Optional[Dict[str, Any]]:
        """Get current Hijri date using API."""
        try:
            today = datetime.now().strftime('%d-%m-%Y')
            
            # Check cache first
            if today in self.hijri_cache:
                return self.hijri_cache[today]
                
            # Use AlAdhan API for Hijri date
            url = f"http://api.aladhan.com/v1/gToH/{today}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    hijri_data = data['data']['hijri']
                    
                    result = {
                        'day': int(hijri_data['day']),
                        'month': int(hijri_data['month']['number']),
                        'year': int(hijri_data['year']),
                        'month_name_arabic': hijri_data['month']['ar'],
                        'month_name_english': hijri_data['month']['en'],
                        'weekday_arabic': hijri_data['weekday']['ar'],
                        'weekday_english': hijri_data['weekday']['en'],
                        'formatted': f"{hijri_data['day']} {hijri_data['month']['en']} {hijri_data['year']} AH"
                    }
                    
                    # Cache the result
                    self.hijri_cache[today] = result
                    
                    return result
                    
        except Exception as e:
            log_error_with_traceback("Error getting Hijri date", e)
            
        return None
        
    def get_islamic_context(self) -> Dict[str, Any]:
        """Get current Islamic calendar context for AI responses."""
        try:
            context = {
                'current_hijri': None,
                'current_month_info': None,
                'current_events': [],
                'upcoming_events': [],
                'month_virtues': [],
                'special_occasion': None,
                'recommended_actions': []
            }
            
            # Get current Hijri date (skip for now to avoid async issues)
            try:
                # For now, we'll skip the async hijri date call to avoid issues
                # This can be improved later by making the whole context call async
                context['current_hijri'] = None
                
                # Use Gregorian date for basic month calculations
                now = datetime.now()
                gregorian_month = now.month
                
                # Basic Islamic month mapping (approximate - this is simplified)
                # In a full implementation, proper Hijri calendar calculation would be used
                if gregorian_month in [9, 10]:  # Approximate Ramadan season
                    context['current_month_info'] = {
                        'name': 'Ramadan Season (Approximate)',
                        'significance': 'Month of fasting and spiritual reflection'
                    }
                elif gregorian_month in [7, 8]:  # Approximate Dhul Hijjah season  
                    context['current_month_info'] = {
                        'name': 'Hajj Season (Approximate)',
                        'significance': 'Time of pilgrimage to Mecca'
                    }
                
                # Check for current events (simplified)
                current_events = []
                context['current_events'] = current_events
                
                # Check for upcoming events (simplified)
                upcoming_events = []
                context['upcoming_events'] = upcoming_events
                
                # Special occasions (simplified)
                special_occasion = None
                context['special_occasion'] = special_occasion
                
            except Exception as e:
                log_error_with_traceback("Error getting calendar context", e)
                
            # Weekly context (Friday)
            weekday = datetime.now().weekday()
            if weekday == 4:  # Friday (0=Monday)
                context['current_events'].append({
                    'name': 'Jumu\'ah (Friday)',
                    'significance': 'Weekly congregational prayer day',
                    'recommended_actions': ['Attend Jumu\'ah prayer', 'Read Surah Kahf', 'Send Salawat on Prophet']
                })
                
            return context
            
        except Exception as e:
            log_error_with_traceback("Error getting Islamic context", e)
            return {}
            
    def _get_events_for_date(self, month: int, day: int) -> List[Dict]:
        """Get Islamic events for specific Hijri date."""
        events = []
        
        try:
            annual_events = self.islamic_events.get('annual_events', {})
            
            for event_key, event_data in annual_events.items():
                hijri_date = event_data.get('hijri_date', {})
                
                if (hijri_date.get('month') == month and 
                    hijri_date.get('day') == day):
                    events.append(event_data)
                    
        except Exception as e:
            log_error_with_traceback("Error getting events for date", e)
            
        return events
        
    def _get_upcoming_events(self, current_month: int, current_day: int) -> List[Dict]:
        """Get upcoming Islamic events in the next 30 days."""
        upcoming = []
        
        try:
            annual_events = self.islamic_events.get('annual_events', {})
            
            for event_key, event_data in annual_events.items():
                hijri_date = event_data.get('hijri_date', {})
                event_month = hijri_date.get('month')
                event_day = hijri_date.get('day')
                
                if isinstance(event_day, int):
                    # Calculate if event is in next 30 days (simplified)
                    if event_month == current_month and event_day > current_day:
                        days_until = event_day - current_day
                        event_data['days_until'] = days_until
                        upcoming.append(event_data)
                    elif event_month == current_month + 1 or (current_month == 12 and event_month == 1):
                        # Next month events
                        event_data['days_until'] = f"Next month"
                        upcoming.append(event_data)
                        
        except Exception as e:
            log_error_with_traceback("Error getting upcoming events", e)
            
        return upcoming[:3]  # Return max 3 upcoming events
        
    def _get_special_occasion(self, month: int, day: int) -> Optional[str]:
        """Get special occasion context for current date."""
        try:
            # Ramadan period
            if month == 9:
                if day <= 10:
                    return "early_ramadan"
                elif day >= 21:
                    return "last_10_ramadan"
                else:
                    return "mid_ramadan"
                    
            # Dhul Hijjah first 10 days
            elif month == 12 and day <= 10:
                return "dhul_hijjah_blessed_days"
                
            # Sacred months
            elif month in [1, 7, 11, 12]:
                return "sacred_month"
                
            # Sha'ban (Ramadan preparation)
            elif month == 8:
                return "ramadan_preparation"
                
        except Exception as e:
            log_error_with_traceback("Error getting special occasion", e)
            
        return None
        
    def get_islamic_greeting_context(self) -> str:
        """Get contextual Islamic greeting based on current time/date."""
        try:
            context = self.get_islamic_context()
            current_events = context.get('current_events', [])
            special_occasion = context.get('special_occasion')
            
            # Special event greetings
            if current_events:
                event = current_events[0]
                event_name = event.get('name', '')
                
                if 'Eid' in event_name:
                    return f"Eid Mubarak! {event_name} brings joy and blessings."
                elif 'Ramadan' in event_name:
                    return "Ramadan Mubarak! May this blessed month bring you closer to Allah."
                elif 'Ashura' in event_name:
                    return "May Allah accept your fasting on this blessed Day of Ashura."
                    
            # Special occasion greetings
            elif special_occasion:
                if special_occasion == "early_ramadan":
                    return "Ramadan Mubarak! May Allah accept your fasting and prayers."
                elif special_occasion == "last_10_ramadan":
                    return "These are the blessed last 10 nights of Ramadan - seek Laylat al-Qadr!"
                elif special_occasion == "dhul_hijjah_blessed_days":
                    return "These are the blessed first 10 days of Dhul Hijjah - increase your good deeds!"
                elif special_occasion == "sacred_month":
                    return "We are in a sacred month - a blessed time for worship and reflection."
                    
            return "As-salamu alaykum wa rahmatullahi wa barakatuh!"
            
        except Exception as e:
            log_error_with_traceback("Error getting greeting context", e)
            return "As-salamu alaykum wa rahmatullahi wa barakatuh!"


# Global instance
islamic_calendar_service: Optional[IslamicCalendarService] = None


def get_islamic_calendar_service() -> IslamicCalendarService:
    """Get singleton instance of Islamic calendar service."""
    global islamic_calendar_service
    
    if islamic_calendar_service is None:
        islamic_calendar_service = IslamicCalendarService()
        
    return islamic_calendar_service 