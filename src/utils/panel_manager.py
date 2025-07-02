"""
Panel Manager for QuranBot Control Panel.
Manages panel updates through event-driven system.
"""

import discord
import asyncio
from typing import Optional, TYPE_CHECKING
from .log_helpers import log_operation

if TYPE_CHECKING:
    from cogs.user_commands.control_panel import ControlPanelView

class PanelManager:
    """Singleton manager for control panel updates with comprehensive error handling."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PanelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.panel_view: Optional['ControlPanelView'] = None
            self.bot = None
            self._update_in_progress = False
            self._update_timeout = 30.0  # 30 second timeout for panel updates
            self._initialized = True
            log_operation("panel_manager", "INFO", {
                "action": "panel_manager_initialized",
                "update_timeout": self._update_timeout
            })
    
    def register_panel(self, panel_view: 'ControlPanelView'):
        """Register the control panel view for updates with validation."""
        if not panel_view:
            log_operation("panel_manager", "ERROR", {
                "action": "register_panel_failed",
                "reason": "panel_view_is_none"
            })
            return
            
        if not hasattr(panel_view, 'bot'):
            log_operation("panel_manager", "ERROR", {
                "action": "register_panel_failed", 
                "reason": "panel_view_missing_bot_attribute",
                "panel_type": type(panel_view).__name__
            })
            return
            
        if not panel_view.bot:
            log_operation("panel_manager", "ERROR", {
                "action": "register_panel_failed",
                "reason": "panel_view_bot_is_none"
            })
            return
        
        # Unregister previous panel if exists
        if self.panel_view:
            log_operation("panel_manager", "INFO", {
                "action": "unregistering_previous_panel",
                "old_panel_id": id(self.panel_view),
                "new_panel_id": id(panel_view)
            })
            self.unregister_panel()
        
        self.panel_view = panel_view
        self.bot = panel_view.bot
        
        # Subscribe to state manager events with validation
        if hasattr(self.bot, 'state_manager') and self.bot.state_manager:
            try:
                self.bot.state_manager.add_event_listener('state_updated', self._on_state_updated)
                log_operation("panel_manager", "INFO", {
                    "action": "panel_registered_and_subscribed",
                    "panel_id": id(panel_view),
                    "bot_user_id": self.bot.user.id if self.bot.user else None,
                    "bot_user_name": self.bot.user.name if self.bot.user else None
                })
            except Exception as e:
                log_operation("panel_manager", "ERROR", {
                    "action": "event_listener_registration_failed",
                    "panel_id": id(panel_view),
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
        else:
            log_operation("panel_manager", "WARNING", {
                "action": "panel_registered_without_state_manager",
                "panel_id": id(panel_view),
                "has_state_manager": hasattr(self.bot, 'state_manager'),
                "state_manager_value": getattr(self.bot, 'state_manager', 'missing') 
            })
    
    def unregister_panel(self):
        """Unregister the current panel with proper cleanup."""
        if not self.panel_view:
            log_operation("panel_manager", "DEBUG", {
                "action": "unregister_panel_no_panel_registered"
            })
            return
            
        panel_id = id(self.panel_view)
        
        # Remove event listener if possible
        if self.bot and hasattr(self.bot, 'state_manager') and self.bot.state_manager:
            try:
                self.bot.state_manager.remove_event_listener('state_updated', self._on_state_updated)
                log_operation("panel_manager", "INFO", {
                    "action": "event_listener_removed",
                    "panel_id": panel_id
                })
            except Exception as e:
                log_operation("panel_manager", "WARNING", {
                    "action": "event_listener_removal_failed",
                    "panel_id": panel_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
        
        log_operation("panel_manager", "INFO", {
            "action": "panel_unregistered",
            "panel_id": panel_id,
            "update_in_progress": self._update_in_progress
        })
        
        self.panel_view = None
        self.bot = None
    
    async def _on_state_updated(self, data=None):
        """Handle state update events by updating the panel with timeout protection."""
        if not self.panel_view:
            log_operation("panel_manager", "WARNING", {
                "action": "state_update_event_no_panel",
                "event_data": data if data else "no_data"
            })
            return
            
        if self._update_in_progress:
            log_operation("panel_manager", "WARNING", {
                "action": "state_update_event_update_in_progress",
                "event_data": data if data else "no_data"
            })
            return
        
        self._update_in_progress = True
        
        try:
            # Use timeout to prevent hanging
            await asyncio.wait_for(
                self.panel_view.update_panel_status(),
                timeout=self._update_timeout
            )
            
            log_operation("panel_manager", "INFO", {
                "action": "panel_updated_via_event",
                "event_data": data if data else "no_data",
                "panel_id": id(self.panel_view)
            })
            
        except asyncio.TimeoutError:
            log_operation("panel_manager", "ERROR", {
                "action": "panel_update_timeout",
                "timeout_seconds": self._update_timeout,
                "event_data": data if data else "no_data",
                "panel_id": id(self.panel_view)
            })
            
        except discord.NotFound as e:
            log_operation("panel_manager", "ERROR", {
                "action": "panel_update_discord_not_found",
                "error": str(e),
                "panel_id": id(self.panel_view),
                "event_data": data if data else "no_data"
            }, e)
            
        except discord.Forbidden as e:
            log_operation("panel_manager", "ERROR", {
                "action": "panel_update_discord_forbidden",
                "error": str(e),
                "panel_id": id(self.panel_view),
                "event_data": data if data else "no_data"
            }, e)
            
        except discord.HTTPException as e:
            log_operation("panel_manager", "ERROR", {
                "action": "panel_update_discord_http_error",
                "error": str(e),
                "status": getattr(e, 'status', 'unknown'),
                "code": getattr(e, 'code', 'unknown'),
                "panel_id": id(self.panel_view),
                "event_data": data if data else "no_data"
            }, e)
            
        except Exception as e:
            log_operation("panel_manager", "ERROR", {
                "action": "panel_update_failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "panel_id": id(self.panel_view),
                "event_data": data if data else "no_data"
            }, e)
            
        finally:
            self._update_in_progress = False
    
    async def trigger_manual_update(self):
        """Manually trigger a panel update with comprehensive error handling."""
        if not self.panel_view:
            log_operation("panel_manager", "WARNING", {
                "action": "manual_update_no_panel_registered"
            })
            return
            
        if self._update_in_progress:
            log_operation("panel_manager", "WARNING", {
                "action": "manual_update_already_in_progress",
                "panel_id": id(self.panel_view)
            })
            return
        
        self._update_in_progress = True
        
        try:
            # Use timeout to prevent hanging
            await asyncio.wait_for(
                self.panel_view.update_panel_status(),
                timeout=self._update_timeout
            )
            
            log_operation("panel_manager", "INFO", {
                "action": "manual_panel_update_successful",
                "panel_id": id(self.panel_view)
            })
            
        except asyncio.TimeoutError:
            log_operation("panel_manager", "ERROR", {
                "action": "manual_panel_update_timeout",
                "timeout_seconds": self._update_timeout,
                "panel_id": id(self.panel_view)
            })
            
        except discord.NotFound as e:
            log_operation("panel_manager", "ERROR", {
                "action": "manual_update_discord_not_found",
                "error": str(e),
                "panel_id": id(self.panel_view)
            }, e)
            
        except discord.Forbidden as e:
            log_operation("panel_manager", "ERROR", {
                "action": "manual_update_discord_forbidden", 
                "error": str(e),
                "panel_id": id(self.panel_view)
            }, e)
            
        except discord.HTTPException as e:
            log_operation("panel_manager", "ERROR", {
                "action": "manual_update_discord_http_error",
                "error": str(e),
                "status": getattr(e, 'status', 'unknown'),
                "code": getattr(e, 'code', 'unknown'),
                "panel_id": id(self.panel_view)
            }, e)
            
        except Exception as e:
            log_operation("panel_manager", "ERROR", {
                "action": "manual_panel_update_failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "panel_id": id(self.panel_view)
            }, e)
            
        finally:
            self._update_in_progress = False

    def get_status(self) -> dict:
        """Get current panel manager status for debugging."""
        return {
            "has_panel": self.panel_view is not None,
            "has_bot": self.bot is not None,
            "update_in_progress": self._update_in_progress,
            "update_timeout": self._update_timeout,
            "panel_id": id(self.panel_view) if self.panel_view else None,
            "bot_user_id": self.bot.user.id if self.bot and self.bot.user else None,
            "bot_ready": self.bot.is_ready() if self.bot else None,
            "has_state_manager": hasattr(self.bot, 'state_manager') if self.bot else None
        }

    async def cleanup(self):
        """Cleanup panel manager on shutdown."""
        log_operation("panel_manager", "INFO", {
            "action": "cleanup_started",
            "has_panel": self.panel_view is not None,
            "update_in_progress": self._update_in_progress
        })
        
        # Wait for any ongoing updates to complete
        if self._update_in_progress:
            max_wait = 5  # Wait up to 5 seconds
            wait_count = 0
            while self._update_in_progress and wait_count < max_wait:
                await asyncio.sleep(1)
                wait_count += 1
                log_operation("panel_manager", "DEBUG", {
                    "action": "cleanup_waiting_for_update",
                    "wait_count": wait_count,
                    "max_wait": max_wait
                })
            
            if self._update_in_progress:
                log_operation("panel_manager", "WARNING", {
                    "action": "cleanup_update_still_in_progress",
                    "waited_seconds": max_wait
                })
        
        # Unregister panel
        self.unregister_panel()
        
        log_operation("panel_manager", "INFO", {
            "action": "cleanup_completed"
        })

    def is_healthy(self) -> bool:
        """Check if panel manager is in a healthy state."""
        try:
            status = self.get_status()
            
            # Basic health checks
            if not status["has_panel"]:
                return False
                
            if not status["has_bot"]:
                return False
                
            if status["bot_ready"] is False:
                return False
                
            if not status["has_state_manager"]:
                return False
                
            # Panel should have required attributes
            if self.panel_view and not hasattr(self.panel_view, 'update_panel_status'):
                log_operation("panel_manager", "ERROR", {
                    "action": "health_check_panel_missing_update_method",
                    "panel_type": type(self.panel_view).__name__
                })
                return False
            
            return True
            
        except Exception as e:
            log_operation("panel_manager", "ERROR", {
                "action": "health_check_failed",
                "error": str(e),
                "error_type": type(e).__name__
            }, e)
            return False


# Global panel manager instance
panel_manager = PanelManager() 