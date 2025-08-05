# =============================================================================
# QuranBot - Rich Presence Service
# =============================================================================
# Professional Discord rich presence system with template support, state
# management, and comprehensive error handling.
# =============================================================================

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

import discord
from aiohttp.client_exceptions import ClientConnectionResetError

from ..core.base_service import BaseService
from ...config import get_config
from ...core.logger import TreeLogger
from ...core.errors import ErrorHandler
from ...config.timezone import APP_TIMEZONE


class PresenceService(BaseService):
    """
    Professional Discord rich presence system with templates.
    
    Key Features:
    - Template-based presence updates
    - Activity type management
    - State persistence
    - Elapsed time tracking
    - Error handling
    - Silent operation mode
    
    Activity Types:
    - playing: Standard game activity
    - streaming: Streaming status
    - listening: Audio content
    - watching: Viewing content
    - competing: Competition status
    
    Templates Available:
    1. Listening Template:
       - Status: {emoji} {surah}
       - Details: Verse {verse} of {total}
       - State: Recited by {reciter}
       
    2. Idle Template:
       - Status: QuranBot
       - Details: Ready to play Quran
       - State: 24/7 Continuous Recitation
       
    3. Playing Template:
       - Status: {surah}
       - Details: {reciter}
       - State: Verse {verse} of {total}
    """
    
    ACTIVITY_TYPES = {
        "playing": discord.ActivityType.playing,
        "streaming": discord.ActivityType.streaming,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing,
    }
    
    PRESENCE_TEMPLATES = {
        "listening": {
            "status": "🎧 {surah}",
            "details": "Verse {verse} of {total}",
            "state": "Recited by {reciter}",
            "activity_type": "listening"
        },
        "idle": {
            "status": "QuranBot",
            "details": "Ready to play Quran",
            "state": "24/7 Continuous Recitation",
            "activity_type": "playing"
        },
        "playing": {
            "status": "{emoji} {surah}",
            "details": "{reciter}",
            "state": "Verse {verse} of {total}",
            "activity_type": "listening"
        },
        "connecting": {
            "status": "QuranBot",
            "details": "Connecting",
            "state": "Continuous Quran Recitation",
            "activity_type": "playing"
        }
    }
    
    def __init__(self, bot: discord.Client):
        """
        Initialize the presence service with comprehensive state management.
        
        Args:
            bot: Discord bot instance for presence updates
            
        State Management:
        - Persistent state across restarts
        - Activity type tracking
        - Elapsed time management
        - Template-based updates
        """
        super().__init__("PresenceService")
        
        self.bot = bot
        self.config = get_config()
        self.error_handler = ErrorHandler()
        
        # State management
        self.state_file = Path("data/state/presence.json")
        self.is_enabled = True
        self.current_status = ""
        self.current_details = ""
        self.current_state = ""
        self.current_activity_type = "playing"
        self.start_time: Optional[datetime] = None
        
        # Performance tracking
        self.update_count = 0
        self.last_update_time: Optional[datetime] = None
        self.failed_updates = 0
        
        TreeLogger.debug("Initializing presence service", {
            "state_file": str(self.state_file),
            "templates_available": list(self.PRESENCE_TEMPLATES.keys()),
            "activity_types": list(self.ACTIVITY_TYPES.keys())
        }, service="PresenceService")
        
        # Create state directory if it doesn't exist
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            TreeLogger.debug(f"State directory ensured: {self.state_file.parent}", service="PresenceService")
        except Exception as e:
            TreeLogger.error(f"Failed to create state directory: {e}", {
                "directory": str(self.state_file.parent),
                "error_type": type(e).__name__
            }, service="PresenceService")
    
    async def _initialize(self) -> bool:
        """
        Initialize the presence service with state restoration.
        
        Initialization Steps:
        1. Load persistent state from disk
        2. Validate saved state integrity
        3. Set initial connecting presence
        4. Verify Discord connection
        
        Returns:
            bool: True if initialization successful
        """
        try:
            TreeLogger.debug("Starting presence service initialization", service="PresenceService")
            
            # STEP 1: Load saved state
            state_loaded = self.load_state()
            TreeLogger.debug(f"State loading {'successful' if state_loaded else 'failed'}", {
                "has_saved_state": self.state_file.exists(),
                "is_enabled": self.is_enabled,
                "last_status": self.current_status or "None"
            }, service="PresenceService")
            
            # STEP 2: Validate bot connection
            if not self.bot or not hasattr(self.bot, 'change_presence'):
                raise ValueError("Invalid bot instance or missing change_presence method")
            
            # STEP 3: Set initial presence
            TreeLogger.debug("Setting initial connecting presence", service="PresenceService")
            initial_update = await self.update_presence_with_template("connecting", silent=True)
            
            if not initial_update:
                TreeLogger.warning("Failed to set initial presence", service="PresenceService")
            
            TreeLogger.info("Presence service initialized successfully", {
                "is_enabled": self.is_enabled,
                "templates_loaded": len(self.PRESENCE_TEMPLATES),
                "state_restored": state_loaded,
                "initial_presence_set": initial_update
            }, service="PresenceService")
            
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "presence_initialization",
                    "service_name": "PresenceService",
                    "state_file_exists": self.state_file.exists(),
                    "bot_connected": bool(self.bot)
                }
            )
            return False
    
    async def update_presence(
        self,
        status: str,
        details: str,
        state: str,
        activity_type: str = "playing",
        start_time: Optional[datetime] = None,
        silent: bool = False
    ) -> bool:
        """
        Update Discord rich presence with comprehensive validation.
        
        This method handles all presence updates with proper error handling,
        state management, and performance tracking. It validates activity types,
        manages timestamps, and ensures state persistence.
        
        Args:
            status: Main status text (e.g., "Al-Fatiha")
            details: Secondary details (e.g., "Verse 1 of 7")
            state: Additional state info (e.g., "Recited by Mishary Alafasy")
            activity_type: Discord activity type (playing/listening/watching)
            start_time: Optional start timestamp for elapsed time display
            silent: Whether to suppress info logs
            
        Returns:
            bool: True if presence updated successfully
            
        Error Handling:
            - Validates activity type against allowed values
            - Handles Discord API failures gracefully
            - Tracks failed update attempts
            - Falls back to previous state on error
        """
        try:
            # STEP 1: Check if presence is enabled
            if not self.is_enabled:
                TreeLogger.debug("Presence update skipped - service disabled", 
                               service="PresenceService")
                return True
            
            # STEP 2: Validate activity type
            if activity_type not in self.ACTIVITY_TYPES:
                TreeLogger.error(f"Invalid activity type: {activity_type}", {
                    "requested_type": activity_type,
                    "valid_types": list(self.ACTIVITY_TYPES.keys()),
                    "fallback_type": "playing"
                }, service="PresenceService")
                # Fallback to playing instead of failing
                activity_type = "playing"
            
            # STEP 3: Log update attempt for debugging
            TreeLogger.debug("Attempting presence update", {
                "status": status[:50],  # Truncate for logging
                "details": details[:50],
                "state": state[:50],
                "activity_type": activity_type,
                "has_start_time": bool(start_time),
                "is_silent": silent,
                "update_count": self.update_count + 1
            }, service="PresenceService")
            
            # STEP 4: Create activity with timestamp if provided
            activity_kwargs = {
                "type": self.ACTIVITY_TYPES[activity_type],
                "name": status,
                "details": details,
                "state": state,
            }
            
            if start_time:
                # Validate timestamp is not in the future
                now = datetime.now(APP_TIMEZONE)
                if start_time > now:
                    TreeLogger.warning("Start time is in the future, using current time", {
                        "provided_time": start_time.isoformat(),
                        "current_time": now.isoformat()
                    }, service="PresenceService")
                    start_time = now
                    
                activity_kwargs["timestamps"] = {"start": int(start_time.timestamp())}
                self.start_time = start_time
            
            # STEP 5: Create activity object
            activity = discord.Activity(**activity_kwargs)
            
            # STEP 6: Update Discord presence
            update_start = datetime.now(APP_TIMEZONE)
            
            # Check if bot is ready and has websocket connection
            if not self.bot.ws:
                TreeLogger.warning("Bot websocket not ready, skipping presence update", {
                    "is_ready": self.bot.is_ready(),
                    "is_closed": self.bot.is_closed()
                }, service="PresenceService")
                self.failed_updates += 1
                return False
                
            await self.bot.change_presence(activity=activity)
            update_duration = (datetime.now(APP_TIMEZONE) - update_start).total_seconds()
            
            # STEP 7: Update internal state
            self.current_status = status
            self.current_details = details
            self.current_state = state
            self.current_activity_type = activity_type
            
            # STEP 8: Update performance metrics
            self.update_count += 1
            self.last_update_time = datetime.now(APP_TIMEZONE)
            
            # STEP 9: Save state to disk
            state_saved = self.save_state(silent=silent)
            
            # STEP 10: Log success if not silent
            if not silent:
                TreeLogger.info("Rich presence updated successfully", {
                    "status": status,
                    "details": details,
                    "state": state,
                    "activity_type": activity_type,
                    "update_duration_ms": round(update_duration * 1000, 2),
                    "state_saved": state_saved,
                    "total_updates": self.update_count
                }, service="PresenceService")
            else:
                TreeLogger.debug("Silent presence update completed", {
                    "update_duration_ms": round(update_duration * 1000, 2)
                }, service="PresenceService")
            
            return True
            
        except ClientConnectionResetError as e:
            # This is expected during shutdown - just log as debug
            TreeLogger.debug("Presence update skipped - connection closing during shutdown", {
                "is_shutting_down": self.bot.is_closed() if self.bot else True
            }, service="PresenceService")
            return False
            
        except discord.HTTPException as e:
            # Handle Discord API specific errors
            self.failed_updates += 1
            TreeLogger.error(f"Discord API error updating presence: {e}", {
                "status_code": getattr(e, 'status', None),
                "error_text": getattr(e, 'text', str(e)),
                "failed_updates": self.failed_updates,
                "retry_possible": True
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "update_presence_discord_api",
                    "status": status,
                    "activity_type": activity_type,
                    "failed_updates": self.failed_updates
                }
            )
            return False
            
        except Exception as e:
            # Check if this is a connection closing error (expected during shutdown)
            error_message = str(e).lower()
            if "cannot write to closing transport" in error_message or "websocket is closed" in error_message:
                TreeLogger.debug("Presence update skipped - connection closing (likely during shutdown)", {
                    "error_type": type(e).__name__,
                    "is_shutting_down": self.bot.is_closed() if self.bot else True
                }, service="PresenceService")
                return False
            
            # Handle other general errors
            self.failed_updates += 1
            TreeLogger.error(f"Unexpected error updating presence: {e}", {
                "error_type": type(e).__name__,
                "failed_updates": self.failed_updates,
                "has_bot_connection": bool(self.bot and hasattr(self.bot, 'change_presence'))
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "update_presence",
                    "status": status,
                    "activity_type": activity_type,
                    "error_type": type(e).__name__
                }
            )
            return False
    
    async def update_presence_with_template(
        self,
        template_name: str,
        data: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        silent: bool = False
    ) -> bool:
        """
        Update presence using a predefined template with data validation.
        
        Templates provide consistent presence formatting across the bot.
        This method handles template selection, data validation, string
        formatting, and graceful fallbacks for missing data.
        
        Args:
            template_name: Name of template to use (e.g., "listening", "idle")
            data: Dictionary of values to fill template placeholders
            start_time: Optional timestamp for elapsed time display
            silent: Whether to suppress info logs
            
        Returns:
            bool: True if presence updated successfully
            
        Template Placeholders:
            - {surah}: Surah name
            - {reciter}: Reciter name
            - {verse}: Current verse number
            - {total}: Total verses
            - {emoji}: Status emoji
            
        Error Handling:
            - Validates template exists
            - Handles missing placeholder data
            - Falls back to template defaults
            - Logs all formatting issues
        """
        try:
            # STEP 1: Validate template exists
            if template_name not in self.PRESENCE_TEMPLATES:
                TreeLogger.error(f"Invalid template requested: {template_name}", {
                    "requested_template": template_name,
                    "valid_templates": list(self.PRESENCE_TEMPLATES.keys()),
                    "falling_back_to": "idle"
                }, service="PresenceService")
                # Fallback to idle template
                template_name = "idle"
            
            # STEP 2: Get template and prepare data
            template = self.PRESENCE_TEMPLATES[template_name]
            data = data or {}
            
            TreeLogger.debug(f"Using template '{template_name}' for presence update", {
                "template_name": template_name,
                "data_keys": list(data.keys()),
                "has_start_time": bool(start_time),
                "template_type": template.get("activity_type", "playing")
            }, service="PresenceService")
            
            # STEP 3: Extract template components
            status_template = template.get("status", "QuranBot")
            details_template = template.get("details", "")
            state_template = template.get("state", "")
            activity_type = template.get("activity_type", "playing")
            
            # STEP 4: Format template strings with error handling
            status = self._format_template(status_template, data)
            details = self._format_template(details_template, data)
            state = self._format_template(state_template, data)
            
            # STEP 5: Validate formatted strings
            if not status:
                TreeLogger.warning("Empty status after formatting, using default", {
                    "template": status_template,
                    "data": data
                }, service="PresenceService")
                status = "QuranBot"
            
            # STEP 6: Log formatted result for debugging
            TreeLogger.debug("Template formatted successfully", {
                "status": status[:50],
                "details": details[:50] if details else "(empty)",
                "state": state[:50] if state else "(empty)",
                "activity_type": activity_type
            }, service="PresenceService")
            
            # STEP 7: Update presence with formatted values
            return await self.update_presence(
                status=status,
                details=details,
                state=state,
                activity_type=activity_type,
                start_time=start_time,
                silent=silent
            )
            
        except KeyError as e:
            # Handle missing template keys
            TreeLogger.error(f"Template formatting error - missing key: {e}", {
                "template_name": template_name,
                "missing_key": str(e),
                "provided_data": list(data.keys()) if data else []
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "update_presence_template_format",
                    "template": template_name,
                    "missing_key": str(e)
                }
            )
            return False
            
        except Exception as e:
            # Handle general errors
            TreeLogger.error(f"Unexpected error using template '{template_name}': {e}", {
                "error_type": type(e).__name__,
                "template_name": template_name,
                "has_data": bool(data)
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "update_presence_with_template",
                    "template": template_name,
                    "data": data,
                    "error_type": type(e).__name__
                }
            )
            return False
    
    def _format_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        Format template string with data using safe substitution.
        
        This method handles template string formatting with comprehensive
        error handling for missing placeholders and invalid formats.
        
        Args:
            template: Template string with {placeholder} format
            data: Dictionary of values for placeholders
            
        Returns:
            str: Formatted string or original template on error
            
        Error Handling:
            - Missing placeholders: Returns template with unfilled placeholders
            - Invalid format: Returns original template
            - Empty data: Returns template as-is
        """
        try:
            # Handle empty template
            if not template:
                TreeLogger.debug("Empty template provided", service="PresenceService")
                return ""
                
            # Handle empty data
            if not data:
                TreeLogger.debug("No data provided for template formatting", {
                    "template": template
                }, service="PresenceService")
                return template
            
            # Log formatting attempt for complex templates
            if template.count("{") > 2:
                TreeLogger.debug("Formatting complex template", {
                    "placeholder_count": template.count("{"),
                    "data_keys": list(data.keys())
                }, service="PresenceService")
            
            # Format with all available data
            formatted = template.format(**data)
            
            # Validate result
            if "{" in formatted and "}" in formatted:
                TreeLogger.warning("Template may have unfilled placeholders", {
                    "template": template,
                    "result": formatted,
                    "data_keys": list(data.keys())
                }, service="PresenceService")
            
            return formatted
            
        except KeyError as e:
            # Handle missing placeholder gracefully
            missing_key = str(e).strip("'")
            TreeLogger.warning(f"Missing template placeholder: {missing_key}", {
                "template": template,
                "missing_key": missing_key,
                "available_data": list(data.keys()),
                "suggestion": f"Add '{missing_key}' to data dictionary"
            }, service="PresenceService")
            
            # Try partial formatting with available data
            try:
                # Use string.Template for partial substitution
                from string import Template
                safe_template = Template(template.replace("{", "${"))
                partial_result = safe_template.safe_substitute(data)
                return partial_result.replace("${", "{").replace("}", "}")
            except:
                return template
                
        except ValueError as e:
            # Handle invalid format strings
            TreeLogger.error(f"Invalid template format: {e}", {
                "template": template,
                "error_detail": str(e)
            }, service="PresenceService")
            return template
            
        except Exception as e:
            # Handle unexpected errors
            TreeLogger.error(f"Unexpected error formatting template: {e}", {
                "template": template,
                "error_type": type(e).__name__,
                "data_keys": list(data.keys()) if data else []
            }, service="PresenceService")
            return template
    
    async def update_for_playback(
        self,
        surah_name: str,
        surah_number: int,
        reciter_name: str,
        current_verse: int = 1,
        total_verses: int = 0,
        emoji: str = "🎧"
    ) -> bool:
        """
        Update presence for active Quran playback with validation.
        
        This method is called when playback starts or changes. It validates
        all parameters and uses the playing template for consistent display.
        
        Args:
            surah_name: Name of the surah being played
            surah_number: Surah number (1-114)
            reciter_name: Name of the reciter
            current_verse: Current verse being played (default: 1)
            total_verses: Total verses in the surah
            
        Returns:
            bool: True if presence updated successfully
            
        Validation:
            - Surah number must be 1-114
            - Verse numbers must be positive
            - Names must not be empty
        """
        try:
            # STEP 1: Validate inputs
            if not surah_name or not reciter_name:
                TreeLogger.error("Invalid playback data - missing names", {
                    "has_surah_name": bool(surah_name),
                    "has_reciter_name": bool(reciter_name),
                    "surah_number": surah_number
                }, service="PresenceService")
                return False
                
            if not 1 <= surah_number <= 114:
                TreeLogger.warning(f"Invalid surah number: {surah_number}", {
                    "provided_number": surah_number,
                    "valid_range": "1-114",
                    "using_default": 1
                }, service="PresenceService")
                surah_number = 1
                
            if current_verse < 1:
                TreeLogger.warning(f"Invalid verse number: {current_verse}", {
                    "provided_verse": current_verse,
                    "using_default": 1
                }, service="PresenceService")
                current_verse = 1
            
            # STEP 2: Log playback update
            TreeLogger.debug("Updating presence for playback", {
                "surah": f"{surah_number}. {surah_name}",
                "reciter": reciter_name,
                "progress": f"{current_verse}/{total_verses}" if total_verses > 0 else f"Verse {current_verse}",
                "template": "playing"
            }, service="PresenceService")
            
            # STEP 3: Prepare template data
            data = {
                "surah": surah_name,
                "surah_number": surah_number,
                "reciter": reciter_name,
                "verse": current_verse,
                "total": total_verses,
                "emoji": emoji
            }
            
            # STEP 4: Update presence with playing template
            success = await self.update_presence_with_template(
                "playing",
                data,
                start_time=datetime.now(APP_TIMEZONE),
                silent=True  # Silent to avoid log spam during playback
            )
            
            if success:
                TreeLogger.info("Playback presence updated", {
                    "surah": f"{surah_number}. {surah_name}",
                    "reciter": reciter_name
                }, service="PresenceService")
            else:
                TreeLogger.warning("Failed to update playback presence", {
                    "surah": surah_name,
                    "is_enabled": self.is_enabled
                }, service="PresenceService")
                
            return success
            
        except Exception as e:
            TreeLogger.error(f"Error updating playback presence: {e}", {
                "error_type": type(e).__name__,
                "surah_name": surah_name,
                "reciter_name": reciter_name,
                "traceback": True  # Include full traceback for debugging
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "update_for_playback",
                    "surah": f"{surah_number}. {surah_name}",
                    "reciter": reciter_name
                }
            )
            return False
    
    async def update_to_idle(self) -> bool:
        """
        Update presence to idle state when playback stops.
        
        This method is called when the bot stops playing audio and returns
        to an idle state. It uses the idle template for consistent display.
        
        Returns:
            bool: True if presence updated successfully
            
        Idle State Shows:
            - Status: QuranBot
            - Details: Ready to play Quran
            - State: 24/7 Continuous Recitation
        """
        try:
            TreeLogger.debug("Updating presence to idle state", {
                "previous_status": self.current_status,
                "was_playing": self.current_activity_type == "listening"
            }, service="PresenceService")
            
            # Clear any existing start time for idle state
            self.start_time = None
            
            # Update to idle template
            success = await self.update_presence_with_template("idle", silent=True)
            
            if success:
                TreeLogger.info("Presence updated to idle", service="PresenceService")
            else:
                TreeLogger.warning("Failed to update to idle presence", {
                    "is_enabled": self.is_enabled
                }, service="PresenceService")
                
            return success
            
        except Exception as e:
            TreeLogger.error(f"Error updating to idle presence: {e}", {
                "error_type": type(e).__name__,
                "traceback": True
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {"operation": "update_to_idle"}
            )
            return False
    
    async def clear_presence(self) -> bool:
        """
        Clear all rich presence and reset to default Discord state.
        
        This method removes all custom presence information and returns
        the bot to Discord's default online state without any activity.
        
        Returns:
            bool: True if presence cleared successfully
            
        State Changes:
            - Removes all activity information
            - Clears internal state tracking
            - Saves cleared state to disk
            - Resets performance counters
        """
        try:
            TreeLogger.debug("Clearing rich presence", {
                "current_status": self.current_status,
                "had_activity": bool(self.current_status)
            }, service="PresenceService")
            
            # STEP 1: Clear Discord presence
            clear_start = datetime.now(APP_TIMEZONE)
            
            # Check if bot is ready and has websocket connection
            if not self.bot.ws:
                TreeLogger.warning("Bot websocket not ready, skipping presence clear", {
                    "is_ready": self.bot.is_ready(),
                    "is_closed": self.bot.is_closed()
                }, service="PresenceService")
                return False
                
            await self.bot.change_presence(activity=None)
            clear_duration = (datetime.now(APP_TIMEZONE) - clear_start).total_seconds()
            
            # STEP 2: Reset all internal state
            previous_status = self.current_status
            self.current_status = ""
            self.current_details = ""
            self.current_state = ""
            self.current_activity_type = "playing"
            self.start_time = None
            
            # STEP 3: Save cleared state
            state_saved = self.save_state(silent=True)
            
            TreeLogger.info("Rich presence cleared successfully", {
                "previous_status": previous_status,
                "clear_duration_ms": round(clear_duration * 1000, 2),
                "state_saved": state_saved
            }, service="PresenceService")
            
            return True
            
        except ClientConnectionResetError as e:
            # This is expected during shutdown - just log as debug
            TreeLogger.debug("Presence clear skipped - connection closing during shutdown", {
                "is_shutting_down": self.bot.is_closed() if self.bot else True
            }, service="PresenceService")
            return False
            
        except discord.HTTPException as e:
            TreeLogger.error(f"Discord API error clearing presence: {e}", {
                "status_code": getattr(e, 'status', None),
                "error_text": getattr(e, 'text', str(e))
            }, service="PresenceService")
            return False
            
        except Exception as e:
            # Check if this is a connection closing error (expected during shutdown)
            error_message = str(e).lower()
            if "cannot write to closing transport" in error_message or "websocket is closed" in error_message:
                TreeLogger.debug("Presence clear skipped - connection closing (likely during shutdown)", {
                    "error_type": type(e).__name__,
                    "is_shutting_down": self.bot.is_closed() if self.bot else True
                }, service="PresenceService")
                return False
            
            TreeLogger.error(f"Error clearing presence: {e}", {
                "error_type": type(e).__name__,
                "has_bot_connection": bool(self.bot)
            }, service="PresenceService")
            
            await self.error_handler.handle_error(
                e,
                {"operation": "clear_presence"}
            )
            return False
    
    def toggle_presence(self) -> bool:
        """
        Toggle rich presence on/off with state management.
        
        This method allows users to enable/disable presence updates.
        When disabled, it clears any existing presence immediately.
        
        Returns:
            bool: True if toggle successful
            
        State Changes:
            - Toggles is_enabled flag
            - Clears presence if disabling
            - Saves new state to disk
            - Creates async task for clearing
        """
        try:
            # Log current state before toggle
            previous_state = self.is_enabled
            TreeLogger.debug("Toggling presence state", {
                "current_state": "enabled" if self.is_enabled else "disabled",
                "new_state": "disabled" if self.is_enabled else "enabled"
            }, service="PresenceService")
            
            # Toggle the state
            self.is_enabled = not self.is_enabled
            
            # Clear presence if disabling
            if not self.is_enabled:
                TreeLogger.info("Presence disabled - clearing activity", service="PresenceService")
                # Create async task to clear presence without blocking
                task = asyncio.create_task(self.clear_presence())
                # Add task name for debugging
                task.set_name("presence_clear_on_disable")
            else:
                TreeLogger.info("Presence enabled - ready for updates", service="PresenceService")
            
            # Save the new state
            state_saved = self.save_state()
            
            TreeLogger.info(f"Rich presence {'enabled' if self.is_enabled else 'disabled'}", {
                "previous_state": "enabled" if previous_state else "disabled",
                "new_state": "enabled" if self.is_enabled else "disabled",
                "state_saved": state_saved
            }, service="PresenceService")
            
            return True
            
        except Exception as e:
            TreeLogger.error(f"Error toggling presence: {e}", {
                "error_type": type(e).__name__,
                "current_state": "enabled" if self.is_enabled else "disabled"
            }, service="PresenceService")
            
            # Revert state on error
            self.is_enabled = previous_state
            return False
    
    def save_state(self, silent: bool = False) -> bool:
        """
        Save current presence state to persistent storage.
        
        This method serializes the current presence state to JSON format
        and saves it to disk. The state is restored on bot restart to
        maintain continuity.
        
        Args:
            silent: Whether to suppress debug logs
            
        Returns:
            bool: True if state saved successfully
            
        State Contents:
            - is_enabled: Whether presence updates are active
            - current_status: Main status text
            - current_details: Secondary details
            - current_state: Additional state info
            - current_activity_type: Discord activity type
            - start_time: Timestamp for elapsed time
            
        Error Handling:
            - Creates directory if missing
            - Handles file permissions errors
            - Validates JSON serialization
        """
        try:
            # STEP 1: Prepare state dictionary
            state = {
                "is_enabled": self.is_enabled,
                "current_status": self.current_status,
                "current_details": self.current_details,
                "current_state": self.current_state,
                "current_activity_type": self.current_activity_type,
                "start_time": self.start_time.timestamp() if self.start_time else None,
                # Add metadata for debugging
                "last_saved": datetime.now(APP_TIMEZONE).isoformat(),
                "update_count": self.update_count,
                "failed_updates": self.failed_updates
            }
            
            # STEP 2: Ensure directory exists
            if not self.state_file.parent.exists():
                TreeLogger.debug(f"Creating state directory: {self.state_file.parent}", 
                               service="PresenceService")
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # STEP 3: Write state to temporary file first (atomic write)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            # STEP 4: Move temp file to final location (atomic on most systems)
            temp_file.replace(self.state_file)
            
            # STEP 5: Log success if not silent
            if not silent:
                TreeLogger.debug("Presence state saved successfully", {
                    "is_enabled": self.is_enabled,
                    "has_activity": bool(self.current_status),
                    "file_size": self.state_file.stat().st_size,
                    "update_count": self.update_count
                }, service="PresenceService")
            
            return True
            
        except PermissionError as e:
            TreeLogger.error(f"Permission denied saving presence state: {e}", {
                "file_path": str(self.state_file),
                "directory_exists": self.state_file.parent.exists(),
                "is_writable": os.access(str(self.state_file.parent), os.W_OK)
            }, service="PresenceService")
            return False
            
        except json.JSONEncodeError as e:
            TreeLogger.error(f"JSON encoding error saving state: {e}", {
                "error_detail": str(e),
                "state_keys": list(state.keys()) if 'state' in locals() else []
            }, service="PresenceService")
            return False
            
        except Exception as e:
            TreeLogger.error(f"Unexpected error saving presence state: {e}", {
                "error_type": type(e).__name__,
                "file_path": str(self.state_file)
            }, service="PresenceService")
            return False
    
    def load_state(self) -> bool:
        """
        Load presence state from persistent storage.
        
        This method restores the previous presence state from disk,
        allowing the bot to maintain continuity across restarts.
        
        Returns:
            bool: True if state loaded successfully or no state exists
            
        State Restoration:
            - Validates loaded data integrity
            - Handles corrupted state files
            - Applies sensible defaults
            - Validates timestamp data
            
        Error Recovery:
            - Corrupted files: Uses defaults
            - Missing files: Normal startup
            - Invalid data: Partial restoration
        """
        try:
            # STEP 1: Check if state file exists
            if not self.state_file.exists():
                TreeLogger.debug("No saved presence state found, using defaults", {
                    "state_file": str(self.state_file)
                }, service="PresenceService")
                return True  # Not an error - first run
            
            # STEP 2: Read and parse state file
            TreeLogger.debug(f"Loading presence state from {self.state_file}", 
                           service="PresenceService")
            
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # STEP 3: Validate state structure
            if not isinstance(state, dict):
                TreeLogger.warning("Invalid state file format, using defaults", {
                    "state_type": type(state).__name__
                }, service="PresenceService")
                return True
            
            # STEP 4: Restore state with validation
            self.is_enabled = state.get("is_enabled", True)
            self.current_status = state.get("current_status", "")
            self.current_details = state.get("current_details", "")
            self.current_state = state.get("current_state", "")
            self.current_activity_type = state.get("current_activity_type", "playing")
            
            # Validate activity type
            if self.current_activity_type not in self.ACTIVITY_TYPES:
                TreeLogger.warning(f"Invalid saved activity type: {self.current_activity_type}", {
                    "using_default": "playing"
                }, service="PresenceService")
                self.current_activity_type = "playing"
            
            # STEP 5: Restore timestamp with validation
            start_time = state.get("start_time")
            if start_time:
                try:
                    restored_time = datetime.fromtimestamp(start_time, tz=APP_TIMEZONE)
                    # Don't restore timestamps older than 24 hours
                    if datetime.now(APP_TIMEZONE) - restored_time < timedelta(hours=24):
                        self.start_time = restored_time
                    else:
                        TreeLogger.debug("Ignoring old start time (>24 hours)", 
                                       service="PresenceService")
                        self.start_time = None
                except (ValueError, TypeError) as e:
                    TreeLogger.warning(f"Invalid start time in saved state: {e}", 
                                     service="PresenceService")
                    self.start_time = None
            else:
                self.start_time = None
            
            # STEP 6: Restore performance metrics if available
            self.update_count = state.get("update_count", 0)
            self.failed_updates = state.get("failed_updates", 0)
            
            # STEP 7: Log successful restoration
            last_saved = state.get("last_saved", "unknown")
            TreeLogger.info("Presence state loaded successfully", {
                "is_enabled": self.is_enabled,
                "has_saved_activity": bool(self.current_status),
                "activity_type": self.current_activity_type,
                "last_saved": last_saved,
                "update_count": self.update_count,
                "failed_updates": self.failed_updates
            }, service="PresenceService")
            
            return True
            
        except json.JSONDecodeError as e:
            TreeLogger.error(f"Corrupted presence state file: {e}", {
                "file_path": str(self.state_file),
                "error_position": f"Line {e.lineno}, Column {e.colno}" if hasattr(e, 'lineno') else "unknown",
                "using_defaults": True
            }, service="PresenceService")
            # Continue with defaults on corrupted file
            return True
            
        except PermissionError as e:
            TreeLogger.error(f"Permission denied reading presence state: {e}", {
                "file_path": str(self.state_file),
                "is_readable": os.access(str(self.state_file), os.R_OK)
            }, service="PresenceService")
            return False
            
        except Exception as e:
            TreeLogger.error(f"Unexpected error loading presence state: {e}", {
                "error_type": type(e).__name__,
                "file_exists": self.state_file.exists(),
                "file_size": self.state_file.stat().st_size if self.state_file.exists() else 0
            }, service="PresenceService")
            # Continue with defaults on unexpected errors
            return True
    
    async def _start(self) -> bool:
        """
        Start the presence service with state restoration.
        
        This method is called when the bot starts up. It ensures
        the service is ready to handle presence updates.
        
        Returns:
            bool: True if service started successfully
            
        Startup Tasks:
            - Validate bot connection
            - Restore saved state
            - Set initial presence
        """
        try:
            TreeLogger.debug("Starting presence service", service="PresenceService")
            
            # Validate bot connection
            if not self.bot:
                TreeLogger.error("Cannot start presence service without bot instance", 
                               service="PresenceService")
                return False
            
            # Service is ready
            TreeLogger.info("Presence service started successfully", {
                "is_enabled": self.is_enabled,
                "has_saved_state": bool(self.current_status)
            }, service="PresenceService")
            
            return True
            
        except Exception as e:
            TreeLogger.error(f"Error starting presence service: {e}", {
                "error_type": type(e).__name__
            }, service="PresenceService")
            return False
    
    async def _stop(self) -> bool:
        """
        Stop the presence service gracefully.
        
        This method is called when the bot is shutting down. It ensures
        clean shutdown with state persistence.
        
        Returns:
            bool: True if service stopped successfully
            
        Shutdown Tasks:
            - Clear active presence
            - Save final state
            - Log statistics
        """
        try:
            TreeLogger.debug("Stopping presence service", {
                "is_enabled": self.is_enabled,
                "has_activity": bool(self.current_status)
            }, service="PresenceService")
            
            # Clear presence if enabled
            if self.is_enabled and self.current_status:
                TreeLogger.info("Clearing presence before shutdown", service="PresenceService")
                try:
                    # Check if bot connection is still active
                    if self.bot and self.bot.ws and not self.bot.is_closed():
                        await self.clear_presence()
                    else:
                        TreeLogger.debug("Skipping presence clear - bot connection already closed", service="PresenceService")
                except Exception as e:
                    # Log but don't fail shutdown for presence clearing errors
                    TreeLogger.debug(f"Could not clear presence during shutdown: {e}", {
                        "error_type": type(e).__name__,
                        "is_closed": self.bot.is_closed() if self.bot else True
                    }, service="PresenceService")
            
            # Save final state
            self.save_state(silent=True)
            
            # Log service statistics
            TreeLogger.info("Presence service stopped", {
                "total_updates": self.update_count,
                "failed_updates": self.failed_updates,
                "success_rate": f"{((self.update_count - self.failed_updates) / self.update_count * 100):.1f}%" if self.update_count > 0 else "N/A"
            }, service="PresenceService")
            
            return True
            
        except Exception as e:
            TreeLogger.error(f"Error stopping presence service: {e}", {
                "error_type": type(e).__name__
            }, service="PresenceService")
            return False
    
    async def _cleanup(self) -> bool:
        """
        Cleanup presence service resources.
        
        This method is called during final cleanup. It ensures
        all resources are properly released.
        
        Returns:
            bool: True if cleanup successful
            
        Cleanup Tasks:
            - Clear any remaining presence
            - Reset all state variables
            - Close any open resources
        """
        try:
            TreeLogger.debug("Cleaning up presence service", service="PresenceService")
            
            # Reset all state
            self.current_status = ""
            self.current_details = ""
            self.current_state = ""
            self.current_activity_type = "playing"
            self.start_time = None
            
            TreeLogger.info("Presence service cleanup completed", service="PresenceService")
            return True
            
        except Exception as e:
            TreeLogger.error(f"Error during presence service cleanup: {e}", {
                "error_type": type(e).__name__
            }, service="PresenceService")
            return False
    
    async def _health_check(self) -> Dict[str, Any]:
        """
        Perform health check on presence service.
        
        This method validates the service is functioning correctly
        and can update presence when needed.
        
        Returns:
            Dict[str, Any]: Health check results
            
        Health Checks:
            - Bot connection validity
            - State file accessibility  
            - Update failure threshold
            - Last update recency
        """
        try:
            is_healthy = True
            issues = []
            
            # Check bot connection
            has_bot = self.bot and hasattr(self.bot, 'change_presence')
            if not has_bot:
                TreeLogger.warning("Presence service unhealthy - invalid bot instance", 
                                 service="PresenceService")
                is_healthy = False
                issues.append("Invalid bot instance")
            
            # Check failure rate
            failure_rate = 0.0
            if self.update_count > 10:
                failure_rate = self.failed_updates / self.update_count
                if failure_rate > 0.5:
                    TreeLogger.warning("Presence service unhealthy - high failure rate", {
                        "total_updates": self.update_count,
                        "failed_updates": self.failed_updates,
                        "failure_rate": f"{(failure_rate * 100):.1f}%"
                    }, service="PresenceService")
                    is_healthy = False
                    issues.append(f"High failure rate: {failure_rate * 100:.1f}%")
            
            # Check state file accessibility
            can_write_state = True
            if self.state_file.parent.exists() and not os.access(str(self.state_file.parent), os.W_OK):
                TreeLogger.warning("Presence service unhealthy - cannot write state", {
                    "state_directory": str(self.state_file.parent)
                }, service="PresenceService")
                is_healthy = False
                can_write_state = False
                issues.append("Cannot write state file")
            
            # Check last update time (warn if stale when enabled)
            time_since_update = None
            if self.is_enabled and self.last_update_time:
                time_since_update = datetime.now(APP_TIMEZONE) - self.last_update_time
                if time_since_update > timedelta(hours=1):
                    TreeLogger.debug("Presence not updated recently", {
                        "last_update": self.last_update_time.isoformat(),
                        "hours_ago": round(time_since_update.total_seconds() / 3600, 1)
                    }, service="PresenceService")
            
            return {
                "is_healthy": is_healthy,
                "has_bot_connection": has_bot,
                "can_write_state": can_write_state,
                "update_count": self.update_count,
                "failed_updates": self.failed_updates,
                "failure_rate": f"{failure_rate * 100:.1f}%",
                "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
                "time_since_update": str(time_since_update) if time_since_update else None,
                "is_enabled": self.is_enabled,
                "issues": issues
            }
            
        except Exception as e:
            TreeLogger.error(f"Error during presence health check: {e}", {
                "error_type": type(e).__name__
            }, service="PresenceService")
            return {
                "is_healthy": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "issues": ["Health check failed with exception"]
            }