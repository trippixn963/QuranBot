"""
Panel Manager for QuranBot Control Panel.
Manages panel updates through event-driven system.
"""

import discord
import asyncio
from typing import Optional, TYPE_CHECKING
from src.monitoring.logging.tree_log import tree_log
import traceback

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
            tree_log('info', 'Panel manager initialized', {'event': 'PANEL_MANAGER_INIT', 'update_timeout': self._update_timeout})
    
    def register_panel(self, panel_view: 'ControlPanelView'):
        """Register the control panel view for updates with validation."""
        if not panel_view:
            tree_log('error', 'Register panel failed: panel_view is None', {'event': 'REGISTER_PANEL_FAILED', 'reason': 'panel_view_is_none'})
            return
            
        if not hasattr(panel_view, 'bot'):
            tree_log('error', 'Register panel failed: panel_view missing bot attribute', {'event': 'REGISTER_PANEL_FAILED', 'reason': 'panel_view_missing_bot_attribute', 'panel_type': type(panel_view).__name__})
            return
            
        if not panel_view.bot:
            tree_log('error', 'Register panel failed: panel_view.bot is None', {'event': 'REGISTER_PANEL_FAILED', 'reason': 'panel_view_bot_is_none'})
            return
        
        # Unregister previous panel if exists
        if self.panel_view:
            tree_log('info', 'Unregistering previous panel', {'event': 'UNREGISTER_PREVIOUS_PANEL', 'old_panel_id': id(self.panel_view), 'new_panel_id': id(panel_view)})
            self.unregister_panel()
        
        self.panel_view = panel_view
        self.bot = panel_view.bot
        
        # Subscribe to state manager events with validation
        if hasattr(self.bot, 'state_manager') and self.bot.state_manager:
            try:
                self.bot.state_manager.add_event_listener('state_updated', self._on_state_updated)
                tree_log('info', 'Panel registered and subscribed', {'event': 'PANEL_REGISTERED_SUBSCRIBED', 'panel_id': id(panel_view), 'bot_user_id': self.bot.user.id if self.bot.user else None, 'bot_user_name': self.bot.user.name if self.bot.user else None})
            except Exception as e:
                tree_log('error', 'Event listener registration failed', {'event': 'EVENT_LISTENER_REGISTRATION_FAILED', 'panel_id': id(panel_view), 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})
        else:
            tree_log('warning', 'Panel registered without state manager', {'event': 'PANEL_REGISTERED_NO_STATE_MANAGER', 'panel_id': id(panel_view), 'has_state_manager': hasattr(self.bot, 'state_manager'), 'state_manager_value': getattr(self.bot, 'state_manager', 'missing')})
    
    def unregister_panel(self):
        """Unregister the current panel with proper cleanup."""
        if not self.panel_view:
            tree_log('debug', 'Unregister panel: no panel registered', {'event': 'UNREGISTER_PANEL_NO_PANEL'})
            return
            
        panel_id = id(self.panel_view)
        
        # Remove event listener if possible
        if self.bot and hasattr(self.bot, 'state_manager') and self.bot.state_manager:
            try:
                self.bot.state_manager.remove_event_listener('state_updated', self._on_state_updated)
                tree_log('info', 'Event listener removed', {'event': 'EVENT_LISTENER_REMOVED', 'panel_id': panel_id})
            except Exception as e:
                tree_log('warning', 'Event listener removal failed', {'event': 'EVENT_LISTENER_REMOVAL_FAILED', 'panel_id': panel_id, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})
        
        tree_log('info', 'Panel unregistered', {'event': 'PANEL_UNREGISTERED', 'panel_id': panel_id, 'update_in_progress': self._update_in_progress})
        
        self.panel_view = None
        self.bot = None
    
    async def _on_state_updated(self, data=None):
        """Handle state update events by updating the panel with timeout protection."""
        if not self.panel_view:
            tree_log('warning', 'State update event: no panel', {'event': 'STATE_UPDATE_NO_PANEL', 'event_data': data if data else 'no_data'})
            return
            
        if self._update_in_progress:
            tree_log('warning', 'State update event: update in progress', {'event': 'STATE_UPDATE_IN_PROGRESS', 'event_data': data if data else 'no_data'})
            return
        
        self._update_in_progress = True
        
        try:
            # Use timeout to prevent hanging
            await asyncio.wait_for(
                self.panel_view.update_panel_status(),
                timeout=self._update_timeout
            )
            
            tree_log('info', 'Panel updated via event', {'event': 'PANEL_UPDATED_EVENT', 'event_data': data if data else 'no_data', 'panel_id': id(self.panel_view)})
            
        except asyncio.TimeoutError:
            tree_log('error', 'Panel update timeout', {'event': 'PANEL_UPDATE_TIMEOUT', 'timeout_seconds': self._update_timeout, 'event_data': data if data else 'no_data', 'panel_id': id(self.panel_view)})
            
        except discord.NotFound as e:
            tree_log('error', 'Panel update discord not found', {'event': 'PANEL_UPDATE_DISCORD_NOT_FOUND', 'error': str(e), 'panel_id': id(self.panel_view), 'event_data': data if data else 'no_data', 'traceback': traceback.format_exc()})
            
        except discord.Forbidden as e:
            tree_log('error', 'Panel update discord forbidden', {'event': 'PANEL_UPDATE_DISCORD_FORBIDDEN', 'error': str(e), 'panel_id': id(self.panel_view), 'event_data': data if data else 'no_data', 'traceback': traceback.format_exc()})
            
        except discord.HTTPException as e:
            tree_log('error', 'Panel update discord HTTP error', {'event': 'PANEL_UPDATE_DISCORD_HTTP_ERROR', 'error': str(e), 'status': getattr(e, 'status', 'unknown'), 'code': getattr(e, 'code', 'unknown'), 'panel_id': id(self.panel_view), 'event_data': data if data else 'no_data', 'traceback': traceback.format_exc()})
            
        except Exception as e:
            tree_log('error', 'Panel update failed', {'event': 'PANEL_UPDATE_FAILED', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc(), 'panel_id': id(self.panel_view), 'event_data': data if data else 'no_data'})
            
        finally:
            self._update_in_progress = False
    
    async def trigger_manual_update(self):
        """Manually trigger a panel update with comprehensive error handling."""
        if not self.panel_view:
            tree_log('warning', 'Manual update: no panel registered', {'event': 'MANUAL_UPDATE_NO_PANEL'})
            return
            
        if self._update_in_progress:
            tree_log('warning', 'Manual update already in progress', {'event': 'MANUAL_UPDATE_IN_PROGRESS', 'panel_id': id(self.panel_view)})
            return
        
        self._update_in_progress = True
        
        try:
            # Use timeout to prevent hanging
            await asyncio.wait_for(
                self.panel_view.update_panel_status(),
                timeout=self._update_timeout
            )
            
            tree_log('info', 'Manual panel update successful', {'event': 'MANUAL_PANEL_UPDATE_SUCCESS', 'panel_id': id(self.panel_view)})
            
        except asyncio.TimeoutError:
            tree_log('error', 'Manual panel update timeout', {'event': 'MANUAL_PANEL_UPDATE_TIMEOUT', 'timeout_seconds': self._update_timeout, 'panel_id': id(self.panel_view)})
            
        except discord.NotFound as e:
            tree_log('error', 'Manual update discord not found', {'event': 'MANUAL_UPDATE_DISCORD_NOT_FOUND', 'error': str(e), 'panel_id': id(self.panel_view), 'traceback': traceback.format_exc()})
            
        except discord.Forbidden as e:
            tree_log('error', 'Manual update discord forbidden', {'event': 'MANUAL_UPDATE_DISCORD_FORBIDDEN', 'error': str(e), 'panel_id': id(self.panel_view), 'traceback': traceback.format_exc()})
            
        except discord.HTTPException as e:
            tree_log('error', 'Manual update discord HTTP error', {'event': 'MANUAL_UPDATE_DISCORD_HTTP_ERROR', 'error': str(e), 'status': getattr(e, 'status', 'unknown'), 'code': getattr(e, 'code', 'unknown'), 'panel_id': id(self.panel_view), 'traceback': traceback.format_exc()})
            
        except Exception as e:
            tree_log('error', 'Manual panel update failed', {'event': 'MANUAL_PANEL_UPDATE_FAILED', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc(), 'panel_id': id(self.panel_view)})
            
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
        tree_log('info', 'Cleanup started', {'event': 'CLEANUP_STARTED', 'has_panel': self.panel_view is not None, 'update_in_progress': self._update_in_progress})
        
        # Wait for any ongoing updates to complete
        if self._update_in_progress:
            max_wait = 5  # Wait up to 5 seconds
            wait_count = 0
            while self._update_in_progress and wait_count < max_wait:
                await asyncio.sleep(1)
                wait_count += 1
                tree_log('debug', 'Cleanup waiting for update', {'event': 'CLEANUP_WAITING_FOR_UPDATE', 'wait_count': wait_count, 'max_wait': max_wait})
            
            if self._update_in_progress:
                tree_log('warning', 'Cleanup update still in progress', {'event': 'CLEANUP_UPDATE_STILL_IN_PROGRESS', 'waited_seconds': max_wait})
        
        # Unregister panel
        self.unregister_panel()
        
        tree_log('info', 'Cleanup completed', {'event': 'CLEANUP_COMPLETED'})

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
                tree_log('error', 'Health check: panel missing update_panel_status', {'event': 'HEALTH_CHECK_PANEL_MISSING_UPDATE', 'panel_type': type(self.panel_view).__name__})
                return False
            
            return True
            
        except Exception as e:
            tree_log('error', 'Health check failed', {'event': 'HEALTH_CHECK_FAILED', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})
            return False

    def reset(self):
        """Force reset the panel manager to clear all state."""
        tree_log('info', 'Force reset started', {'event': 'FORCE_RESET_STARTED', 'has_panel': self.panel_view is not None, 'panel_id': id(self.panel_view) if self.panel_view else None})
        
        # Unregister current panel
        self.unregister_panel()
        
        # Reset all state
        self.panel_view = None
        self.bot = None
        self._update_in_progress = False
        
        tree_log('info', 'Force reset completed', {'event': 'FORCE_RESET_COMPLETED'})


# Global panel manager instance
panel_manager = PanelManager() 