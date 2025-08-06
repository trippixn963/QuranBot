# =============================================================================
# QuranBot - Base UI Components
# =============================================================================
# Base classes and mixins providing common functionality for Discord UI
# components including activity tracking, smart updates, and logging.
# =============================================================================

import asyncio
from datetime import datetime
from typing import Any

import discord

from ...config.timezone import APP_TIMEZONE
from ...core.logger import TreeLogger


def create_developer_footer(
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
) -> tuple[str, str | None]:
    """
    Create standardized developer footer text and icon URL.

    Args:
        bot: Discord client for fetching developer info
        guild: Discord guild to get member-specific avatar

    Returns:
        tuple: (footer_text, developer_icon_url)
    """
    from ...config import get_config

    config = get_config()

    # Use Arabic name for footer (Discord embed footers don't support clickable mentions)
    footer_text = "Developed by حَـــــنَّـــــا"

    # Try to get developer avatar if bot is provided
    developer_icon_url = None
    if bot and config.developer_id:
        try:
            # If guild is provided, try to get member-specific avatar first
            if guild:
                member = guild.get_member(config.developer_id)
                if member:
                    # Try to get server-specific avatar first, fall back to user avatar
                    if member.guild_avatar:
                        developer_icon_url = member.guild_avatar.url
                    elif member.avatar:
                        developer_icon_url = member.avatar.url
            
            # If no guild or member not found, fall back to user avatar
            if not developer_icon_url:
                developer = bot.get_user(config.developer_id)
                if developer and developer.avatar:
                    developer_icon_url = developer.avatar.url
        except:
            pass

    return footer_text, developer_icon_url


class ActivityTrackingMixin:
    """Mixin for tracking user activity and interactions."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_activity: dict[int, dict[str, Any]] = {}
        self.last_activity_update = datetime.now(APP_TIMEZONE)

    def track_user_activity(
        self, user: discord.User, action: str, context: dict[str, Any] | None = None
    ):
        """Track user activity with timestamp and context."""
        user_id = user.id
        now = datetime.now(APP_TIMEZONE)

        if user_id not in self.user_activity:
            self.user_activity[user_id] = {
                "username": user.display_name,
                "avatar_url": str(user.display_avatar.url),
                "first_interaction": now,
                "total_interactions": 0,
                "recent_actions": [],
            }

        activity = self.user_activity[user_id]
        activity["last_interaction"] = now
        activity["total_interactions"] += 1
        activity["recent_actions"].append(
            {"action": action, "timestamp": now, "context": context or {}}
        )

        # Keep only last 10 actions
        if len(activity["recent_actions"]) > 10:
            activity["recent_actions"] = activity["recent_actions"][-10:]

        self.last_activity_update = now

        TreeLogger.debug(
            f"User activity tracked: {action}",
            {
                "user_id": user_id,
                "username": user.display_name,
                "action": action,
                "total_interactions": activity["total_interactions"],
            },
            service="UI",
        )

    def get_recent_activity(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent user activity across all users."""
        all_actions = []

        for user_id, activity in self.user_activity.items():
            for action_data in activity["recent_actions"]:
                all_actions.append(
                    {
                        "user_id": user_id,
                        "username": activity["username"],
                        "avatar_url": activity["avatar_url"],
                        **action_data,
                    }
                )

        # Sort by timestamp, most recent first
        all_actions.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_actions[:limit]

    def get_activity_summary(self) -> dict[str, Any]:
        """Get summary of user activity."""
        now = datetime.now(APP_TIMEZONE)
        total_users = len(self.user_activity)
        total_interactions = sum(
            activity["total_interactions"] for activity in self.user_activity.values()
        )

        # Users active in last 5 minutes
        active_users = sum(
            1
            for activity in self.user_activity.values()
            if activity.get("last_interaction")
            and (now - activity["last_interaction"]).total_seconds() < 300
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_interactions": total_interactions,
            "last_activity_update": self.last_activity_update,
        }


class UpdateableMixin:
    """Mixin for components that need smart update intervals."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_interval = 5  # Default 5 seconds
        self.last_update_time = datetime.now(APP_TIMEZONE)
        self.update_task: asyncio.Task | None = None
        self.is_updating = False

    def get_smart_update_interval(self, audio_manager=None) -> int:
        """Calculate smart update interval based on state."""
        if not audio_manager:
            return 15  # Default when no audio manager

        # Faster updates when audio is playing
        if hasattr(audio_manager, "is_playing") and audio_manager.is_playing():
            return 3

        # Slower updates when paused or stopped
        return 10

    async def start_updates(self, audio_manager=None):
        """Start the update loop."""
        if self.update_task and not self.update_task.done():
            return

        self.is_updating = True
        self.update_task = asyncio.create_task(self._update_loop(audio_manager))

    async def stop_updates(self):
        """Stop the update loop."""
        self.is_updating = False
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

    async def _update_loop(self, audio_manager=None):
        """Internal update loop with smart intervals."""
        while self.is_updating:
            try:
                # Update interval based on current state
                self.update_interval = self.get_smart_update_interval(audio_manager)

                # Perform the update
                if hasattr(self, "update_display"):
                    await self.update_display()

                self.last_update_time = datetime.now(APP_TIMEZONE)

                # Wait for next update
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                TreeLogger.error(f"Error in update loop: {e}", service="UI")
                await asyncio.sleep(self.update_interval)


class LoggingMixin:
    """Mixin for consistent interaction logging."""

    def log_interaction(
        self,
        interaction: discord.Interaction,
        action: str,
        context: dict[str, Any] | None = None,
    ):
        """Log user interaction with consistent format."""
        TreeLogger.info(
            f"UI Interaction: {action}",
            {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id if interaction.channel else None,
                "action": action,
                "context": context or {},
            },
            service="UI",
        )

    def log_error(self, error: Exception, context: dict[str, Any] | None = None):
        """Log error with consistent format."""
        TreeLogger.error(
            f"UI Error: {error!s}", error=error, context=context, service="UI"
        )

    def log_state_change(self, component: str, old_state: Any, new_state: Any):
        """Log state changes for debugging."""
        TreeLogger.debug(
            f"State change in {component}",
            {
                "component": component,
                "old_state": str(old_state),
                "new_state": str(new_state),
            },
            service="UI",
        )


class BaseView(discord.ui.View, ActivityTrackingMixin, UpdateableMixin, LoggingMixin):
    """
    Base view class with common functionality for all Discord UI views.

    Combines activity tracking, smart updates, and logging into a single
    base class that all UI components can inherit from.
    """

    def __init__(self, *, timeout: float | None = 300, **kwargs):
        # Initialize discord.ui.View first
        discord.ui.View.__init__(self, timeout=timeout)
        # Initialize all mixins
        ActivityTrackingMixin.__init__(self)
        UpdateableMixin.__init__(self)
        LoggingMixin.__init__(self)
        # Initialize our own attributes
        self.creation_time = datetime.now(APP_TIMEZONE)
        self.interaction_count = 0

    async def on_timeout(self):
        """Handle view timeout by disabling all components."""
        for item in self.children:
            item.disabled = True

        TreeLogger.info(
            "UI View timed out",
            {
                "view_type": self.__class__.__name__,
                "timeout_seconds": self.timeout,
                "interaction_count": self.interaction_count,
                "lifetime_seconds": (
                    datetime.now(APP_TIMEZONE) - self.creation_time
                ).total_seconds(),
            },
            service="UI",
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        """Handle view errors with comprehensive logging."""
        self.log_error(
            error,
            {
                "view_type": self.__class__.__name__,
                "item_type": item.__class__.__name__,
                "user_id": interaction.user.id,
                "interaction_count": self.interaction_count,
            },
        )

        # Send user-friendly error message
        embed = discord.Embed(
            title="❌ Interaction Error",
            description="An error occurred while processing your request. Please try again.",
            color=0xFF6B6B,
        )

        # Add bot thumbnail
        if interaction.client.user and interaction.client.user.avatar:
            try:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)
            except:
                pass

        # Create standardized developer footer
        footer_text, developer_icon_url = create_developer_footer(
            interaction.client, interaction.guild
        )

        embed.set_footer(text=footer_text, icon_url=developer_icon_url)

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            pass  # Silently handle if we can't respond

    def track_interaction(
        self,
        interaction: discord.Interaction,
        action: str,
        context: dict[str, Any] | None = None,
    ):
        """Track and log an interaction."""
        self.interaction_count += 1
        self.track_user_activity(interaction.user, action, context)
        self.log_interaction(interaction, action, context)
