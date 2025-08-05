# =============================================================================
# QuranBot - User Interaction Logger Service
# =============================================================================
# Comprehensive logging service for tracking user interactions including
# voice channel joins/leaves, control panel interactions, and response times.
# Follows coding best practices with structured data and performance metrics.
# =============================================================================

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time
from typing import Any

import discord

from ...config.timezone import APP_TIMEZONE
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class InteractionType(Enum):
    """Types of user interactions that can be logged."""

    VOICE_JOIN = "voice_join"
    VOICE_LEAVE = "voice_leave"
    BUTTON_CLICK = "button_click"
    DROPDOWN_SELECT = "dropdown_select"
    MODAL_SUBMIT = "modal_submit"
    COMMAND_USE = "command_use"
    SEARCH_QUERY = "search_query"


class InteractionStatus(Enum):
    """Status of interaction processing."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class UserInfo:
    """Structured user information for logging."""

    user_id: int
    username: str
    display_name: str
    discriminator: str
    is_bot: bool
    account_created: datetime
    formatted_name: str  # "discord_username (server_nickname)"
    joined_guild: datetime | None = None
    avatar_url: str | None = None
    roles: list[str] | None = None


@dataclass
class VoiceInteraction:
    """Voice channel interaction data."""

    interaction_id: str
    interaction_type: InteractionType
    user_info: UserInfo
    channel_id: int
    channel_name: str
    timestamp: datetime
    guild_id: int
    guild_name: str
    session_duration: float | None = None  # For leaves, duration in channel
    previous_channel_id: int | None = None  # For moves
    additional_data: dict[str, Any] | None = None


@dataclass
class ControlPanelInteraction:
    """Control panel interaction data."""

    interaction_id: str
    interaction_type: InteractionType
    user_info: UserInfo
    component_type: str  # button, dropdown, modal
    component_id: str
    component_label: str
    timestamp: datetime
    guild_id: int
    channel_id: int

    # State before interaction
    state_before: dict[str, Any]

    # Interaction details
    selected_values: list[str] | None = None  # For dropdowns
    input_values: dict[str, str] | None = None  # For modals

    # Response metrics
    response_time_ms: float | None = None
    processing_time_ms: float | None = None
    interaction_status: InteractionStatus | None = None

    # State after interaction
    state_after: dict[str, Any] | None = None
    changes_made: dict[str, Any] | None = None

    # Error information
    error_message: str | None = None
    error_type: str | None = None

    # Additional context
    additional_data: dict[str, Any] | None = None


class UserInteractionLogger(BaseService):
    """
    Service for comprehensive logging of user interactions.

    Features:
    - Voice channel join/leave tracking with session duration
    - Control panel interaction logging with response times
    - State change tracking (before/after comparisons)
    - Performance metrics and error tracking
    - Structured data format for easy analysis
    - Automatic cleanup of old logs
    """

    def __init__(self):
        """Initialize the user interaction logger service."""
        super().__init__("UserInteractionLogger")

        # Active voice sessions for duration tracking
        self.voice_sessions: dict[int, dict[str, Any]] = {}  # user_id -> session_data

        # Interaction cache for performance
        self.recent_interactions: list[VoiceInteraction | ControlPanelInteraction] = []
        self.max_cache_size = 1000

        # Performance metrics
        self.metrics = {
            "total_interactions": 0,
            "voice_joins": 0,
            "voice_leaves": 0,
            "button_clicks": 0,
            "dropdown_selects": 0,
            "average_response_time_ms": 0.0,
            "error_count": 0,
            "session_start": datetime.now(APP_TIMEZONE),
        }

        TreeLogger.info(
            "User interaction logger initialized",
            {
                "max_cache_size": self.max_cache_size,
                "session_start": self.metrics["session_start"].isoformat(),
            },
            service="UserInteractionLogger",
        )

    async def _initialize(self):
        """Initialize the user interaction logger service."""
        # No special initialization needed
        pass

    async def _start(self):
        """Start the user interaction logger service."""
        try:
            TreeLogger.info(
                "Starting user interaction logger service",
                service="UserInteractionLogger",
            )

            # Start periodic cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

            TreeLogger.info(
                "User interaction logger service started successfully",
                service="UserInteractionLogger",
            )

        except Exception as e:
            TreeLogger.error(
                f"Failed to start user interaction logger: {e}",
                None,
                {"service": "UserInteractionLogger"},
                service="UserInteractionLogger",
            )
            raise

    async def _stop(self):
        """Stop the user interaction logger service."""
        try:
            TreeLogger.info(
                "Stopping user interaction logger service",
                service="UserInteractionLogger",
            )

            # Cancel cleanup task
            if hasattr(self, "cleanup_task") and not self.cleanup_task.done():
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass

            # Log final metrics
            await self._log_final_metrics()

            TreeLogger.info(
                "User interaction logger service stopped successfully",
                service="UserInteractionLogger",
            )

        except Exception as e:
            TreeLogger.error(
                f"Error stopping user interaction logger: {e}",
                None,
                {"service": "UserInteractionLogger"},
                service="UserInteractionLogger",
            )

    async def _cleanup(self):
        """Cleanup resources used by the service."""
        try:
            # Clear caches
            self.voice_sessions.clear()
            self.recent_interactions.clear()

            TreeLogger.info(
                "User interaction logger cleanup completed",
                service="UserInteractionLogger",
            )

        except Exception as e:
            TreeLogger.error(
                f"Error during user interaction logger cleanup: {e}",
                None,
                {"service": "UserInteractionLogger"},
                service="UserInteractionLogger",
            )

    async def _health_check(self) -> dict[str, Any]:
        """Check the health of the user interaction logger service."""
        try:
            return {
                "healthy": True,
                "active_voice_sessions": len(self.voice_sessions),
                "cached_interactions": len(self.recent_interactions),
                "total_interactions": self.metrics["total_interactions"],
                "error_rate": (
                    self.metrics["error_count"]
                    / max(1, self.metrics["total_interactions"])
                )
                * 100,
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def _extract_user_info(
        self, user: discord.User, member: discord.Member | None = None
    ) -> UserInfo:
        """Extract structured user information."""
        roles = []
        joined_guild = None
        server_nickname = None

        if member:
            roles = [role.name for role in member.roles if role.name != "@everyone"]
            joined_guild = member.joined_at
            server_nickname = member.nick

        # Create formatted name: "discord_username (server_nickname)"
        if server_nickname and server_nickname != user.name:
            formatted_name = f"{user.name} ({server_nickname})"
        else:
            formatted_name = user.name

        return UserInfo(
            user_id=user.id,
            username=user.name,
            display_name=user.display_name,
            discriminator=user.discriminator,
            is_bot=user.bot,
            account_created=user.created_at,
            formatted_name=formatted_name,
            joined_guild=joined_guild,
            avatar_url=str(user.display_avatar.url) if user.display_avatar else None,
            roles=roles,
        )

    async def log_voice_join(
        self,
        user: discord.User,
        channel: discord.VoiceChannel,
        member: discord.Member | None = None,
    ) -> str:
        """
        Log a user joining a voice channel.

        Args:
            user: Discord user who joined
            channel: Voice channel that was joined
            member: Guild member object for additional info

        Returns:
            Interaction ID for tracking
        """
        try:
            interaction_id = f"voice_join_{user.id}_{int(time.time() * 1000)}"
            timestamp = datetime.now(APP_TIMEZONE)

            user_info = self._extract_user_info(user, member)

            # Start tracking voice session
            self.voice_sessions[user.id] = {
                "channel_id": channel.id,
                "join_time": timestamp,
                "interaction_id": interaction_id,
            }

            interaction = VoiceInteraction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.VOICE_JOIN,
                user_info=user_info,
                channel_id=channel.id,
                channel_name=channel.name,
                timestamp=timestamp,
                guild_id=channel.guild.id,
                guild_name=channel.guild.name,
                additional_data={
                    "channel_user_count": len(channel.members),
                    "channel_bitrate": channel.bitrate,
                    "channel_user_limit": channel.user_limit,
                },
            )

            # Cache interaction
            self._cache_interaction(interaction)

            # Update metrics
            self.metrics["voice_joins"] += 1
            self.metrics["total_interactions"] += 1

            # Log the interaction
            TreeLogger.info(
                "🎤 User joined voice channel",
                {
                    "user_id": user.id,
                    "username": user_info.formatted_name,
                    "discord_username": user_info.username,
                    "display_name": user_info.display_name,
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "guild_id": channel.guild.id,
                    "guild_name": channel.guild.name,
                    "interaction_id": interaction_id,
                    "channel_user_count": len(channel.members),
                    "user_roles": user_info.roles,
                    "account_age_days": (timestamp - user_info.account_created).days,
                },
                service="UserInteractionLogger",
            )

            return interaction_id

        except Exception as e:
            TreeLogger.error(
                f"Error logging voice join: {e}",
                None,
                {
                    "user_id": getattr(user, "id", None),
                    "channel_id": getattr(channel, "id", None),
                },
                service="UserInteractionLogger",
            )
            return ""

    async def log_voice_leave(
        self,
        user: discord.User,
        channel: discord.VoiceChannel,
        member: discord.Member | None = None,
    ) -> str:
        """
        Log a user leaving a voice channel.

        Args:
            user: Discord user who left
            channel: Voice channel that was left
            member: Guild member object for additional info

        Returns:
            Interaction ID for tracking
        """
        try:
            interaction_id = f"voice_leave_{user.id}_{int(time.time() * 1000)}"
            timestamp = datetime.now(APP_TIMEZONE)

            user_info = self._extract_user_info(user, member)

            # Calculate session duration
            session_duration = None
            if user.id in self.voice_sessions:
                session_data = self.voice_sessions[user.id]
                session_duration = (
                    timestamp - session_data["join_time"]
                ).total_seconds()
                del self.voice_sessions[user.id]

            interaction = VoiceInteraction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.VOICE_LEAVE,
                user_info=user_info,
                channel_id=channel.id,
                channel_name=channel.name,
                timestamp=timestamp,
                guild_id=channel.guild.id,
                guild_name=channel.guild.name,
                session_duration=session_duration,
                additional_data={
                    "channel_user_count": len(channel.members),
                    "remaining_users": [
                        m.display_name for m in channel.members if not m.bot
                    ],
                },
            )

            # Cache interaction
            self._cache_interaction(interaction)

            # Update metrics
            self.metrics["voice_leaves"] += 1
            self.metrics["total_interactions"] += 1

            # Log the interaction
            TreeLogger.info(
                "🚪 User left voice channel",
                {
                    "user_id": user.id,
                    "username": user_info.formatted_name,
                    "discord_username": user_info.username,
                    "display_name": user_info.display_name,
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "guild_id": channel.guild.id,
                    "guild_name": channel.guild.name,
                    "interaction_id": interaction_id,
                    "session_duration_seconds": session_duration,
                    "session_duration_formatted": (
                        self._format_duration(session_duration)
                        if session_duration
                        else None
                    ),
                    "channel_user_count": len(channel.members),
                    "remaining_users": [
                        self._format_member_name(m)
                        for m in channel.members
                        if not m.bot
                    ],
                },
                service="UserInteractionLogger",
            )

            return interaction_id

        except Exception as e:
            TreeLogger.error(
                f"Error logging voice leave: {e}",
                None,
                {
                    "user_id": getattr(user, "id", None),
                    "channel_id": getattr(channel, "id", None),
                },
                service="UserInteractionLogger",
            )
            return ""

    async def log_control_panel_interaction(
        self,
        interaction: discord.Interaction,
        component_type: str,
        component_id: str,
        component_label: str,
        state_before: dict[str, Any],
        selected_values: list[str] | None = None,
        input_values: dict[str, str] | None = None,
    ) -> str:
        """
        Start logging a control panel interaction.

        Args:
            interaction: Discord interaction object
            component_type: Type of component (button, dropdown, modal)
            component_id: ID of the component
            component_label: Label/name of the component
            state_before: Bot state before the interaction
            selected_values: Values selected in dropdown
            input_values: Values entered in modal

        Returns:
            Interaction ID for tracking completion
        """
        try:
            interaction_id = (
                f"{component_type}_{interaction.user.id}_{int(time.time() * 1000)}"
            )
            timestamp = datetime.now(APP_TIMEZONE)

            user_info = self._extract_user_info(
                interaction.user, getattr(interaction, "member", None)
            )

            control_interaction = ControlPanelInteraction(
                interaction_id=interaction_id,
                interaction_type=(
                    InteractionType.BUTTON_CLICK
                    if component_type == "button"
                    else InteractionType.DROPDOWN_SELECT
                ),
                user_info=user_info,
                component_type=component_type,
                component_id=component_id,
                component_label=component_label,
                timestamp=timestamp,
                guild_id=interaction.guild_id,
                channel_id=interaction.channel_id,
                state_before=state_before,
                selected_values=selected_values,
                input_values=input_values,
            )

            # Cache interaction (will be updated when completed)
            self._cache_interaction(control_interaction)

            # Update metrics
            if component_type == "button":
                self.metrics["button_clicks"] += 1
            elif component_type == "dropdown":
                self.metrics["dropdown_selects"] += 1
            self.metrics["total_interactions"] += 1

            # Log the start
            TreeLogger.info(
                f"🎛️ Control panel {component_type} interaction started",
                {
                    "user_id": interaction.user.id,
                    "username": user_info.formatted_name,
                    "discord_username": user_info.username,
                    "display_name": user_info.display_name,
                    "component_type": component_type,
                    "component_id": component_id,
                    "component_label": component_label,
                    "guild_id": interaction.guild_id,
                    "channel_id": interaction.channel_id,
                    "interaction_id": interaction_id,
                    "selected_values": selected_values,
                    "input_values": list(input_values.keys()) if input_values else None,
                    "state_before": {
                        "current_surah": state_before.get("current_surah", {}),
                        "current_reciter": state_before.get("current_reciter", {}),
                        "is_playing": state_before.get("is_playing", False),
                        "loop_mode": state_before.get("loop_mode", "off"),
                        "shuffle_mode": state_before.get("shuffle_mode", False),
                    },
                },
                service="UserInteractionLogger",
            )

            return interaction_id

        except Exception as e:
            TreeLogger.error(
                f"Error logging control panel interaction start: {e}",
                None,
                {
                    "user_id": getattr(interaction.user, "id", None),
                    "component_type": component_type,
                    "component_id": component_id,
                },
                service="UserInteractionLogger",
            )
            return ""

    async def complete_control_panel_interaction(
        self,
        interaction_id: str,
        response_time_ms: float,
        processing_time_ms: float,
        status: InteractionStatus,
        state_after: dict[str, Any] | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """
        Complete logging of a control panel interaction.

        Args:
            interaction_id: ID returned from log_control_panel_interaction
            response_time_ms: Time to respond to Discord interaction
            processing_time_ms: Time to process the request
            status: Final status of the interaction
            state_after: Bot state after the interaction
            error_message: Error message if failed
            error_type: Type of error if failed
        """
        try:
            # Find the interaction in cache
            for i, cached_interaction in enumerate(self.recent_interactions):
                if (
                    isinstance(cached_interaction, ControlPanelInteraction)
                    and cached_interaction.interaction_id == interaction_id
                ):
                    # Update the interaction
                    cached_interaction.response_time_ms = response_time_ms
                    cached_interaction.processing_time_ms = processing_time_ms
                    cached_interaction.interaction_status = status
                    cached_interaction.state_after = state_after
                    cached_interaction.error_message = error_message
                    cached_interaction.error_type = error_type

                    # Calculate changes made
                    if state_after and cached_interaction.state_before:
                        cached_interaction.changes_made = self._calculate_state_changes(
                            cached_interaction.state_before, state_after
                        )

                    # Update metrics
                    if status != InteractionStatus.SUCCESS:
                        self.metrics["error_count"] += 1

                    # Update average response time
                    self._update_average_response_time(response_time_ms)

                    # Log completion
                    TreeLogger.info(
                        "✅ Control panel interaction completed",
                        {
                            "interaction_id": interaction_id,
                            "component_type": cached_interaction.component_type,
                            "component_id": cached_interaction.component_id,
                            "component_label": cached_interaction.component_label,
                            "user_id": cached_interaction.user_info.user_id,
                            "username": cached_interaction.user_info.formatted_name,
                            "discord_username": cached_interaction.user_info.username,
                            "display_name": cached_interaction.user_info.display_name,
                            "status": status.value,
                            "response_time_ms": response_time_ms,
                            "processing_time_ms": processing_time_ms,
                            "total_time_ms": response_time_ms + processing_time_ms,
                            "changes_made": cached_interaction.changes_made,
                            "error_message": error_message,
                            "error_type": error_type,
                            "state_after": (
                                {
                                    "current_surah": (
                                        state_after.get("current_surah", {})
                                        if state_after
                                        else {}
                                    ),
                                    "current_reciter": (
                                        state_after.get("current_reciter", {})
                                        if state_after
                                        else {}
                                    ),
                                    "is_playing": (
                                        state_after.get("is_playing", False)
                                        if state_after
                                        else False
                                    ),
                                    "loop_mode": (
                                        state_after.get("loop_mode", "off")
                                        if state_after
                                        else "off"
                                    ),
                                    "shuffle_mode": (
                                        state_after.get("shuffle_mode", False)
                                        if state_after
                                        else False
                                    ),
                                }
                                if state_after
                                else None
                            ),
                        },
                        service="UserInteractionLogger",
                    )

                    break

        except Exception as e:
            TreeLogger.error(
                f"Error completing control panel interaction log: {e}",
                None,
                {"interaction_id": interaction_id},
                service="UserInteractionLogger",
            )

    def _cache_interaction(
        self, interaction: VoiceInteraction | ControlPanelInteraction
    ) -> None:
        """Cache an interaction for performance and recent access."""
        self.recent_interactions.append(interaction)

        # Maintain cache size
        if len(self.recent_interactions) > self.max_cache_size:
            self.recent_interactions = self.recent_interactions[-self.max_cache_size :]

    def _calculate_state_changes(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate what changed between before and after states."""
        changes = {}

        # Compare important fields
        fields_to_check = [
            "current_surah",
            "current_reciter",
            "is_playing",
            "is_paused",
            "loop_mode",
            "shuffle_mode",
            "position",
            "duration",
        ]

        for field in fields_to_check:
            before_val = before.get(field)
            after_val = after.get(field)

            if before_val != after_val:
                changes[field] = {"before": before_val, "after": after_val}

        return changes

    def _update_average_response_time(self, response_time_ms: float) -> None:
        """Update the running average response time."""
        current_avg = self.metrics["average_response_time_ms"]
        total_interactions = self.metrics["total_interactions"]

        if total_interactions > 1:
            self.metrics["average_response_time_ms"] = (
                current_avg * (total_interactions - 1) + response_time_ms
            ) / total_interactions
        else:
            self.metrics["average_response_time_ms"] = response_time_ms

    def _format_duration(self, seconds: float | None) -> str | None:
        """Format duration in seconds to human-readable string."""
        if seconds is None:
            return None

        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            return f"{hours}h {remaining_minutes}m"

    def _format_member_name(self, member: discord.Member) -> str:
        """Format member name as 'discord_username (server_nickname)'."""
        if member.nick and member.nick != member.name:
            return f"{member.name} ({member.nick})"
        else:
            return member.name

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old data and expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                current_time = datetime.now(APP_TIMEZONE)

                # Clean up old voice sessions (over 24 hours)
                expired_sessions = []
                for user_id, session_data in self.voice_sessions.items():
                    if (
                        current_time - session_data["join_time"]
                    ).total_seconds() > 86400:
                        expired_sessions.append(user_id)

                for user_id in expired_sessions:
                    del self.voice_sessions[user_id]

                if expired_sessions:
                    TreeLogger.info(
                        "Cleaned up expired voice sessions",
                        {"expired_count": len(expired_sessions)},
                        service="UserInteractionLogger",
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                TreeLogger.error(
                    f"Error in periodic cleanup: {e}",
                    None,
                    {"service": "UserInteractionLogger"},
                    service="UserInteractionLogger",
                )

    async def _log_final_metrics(self) -> None:
        """Log final metrics when service is stopping."""
        try:
            uptime = datetime.now(APP_TIMEZONE) - self.metrics["session_start"]

            TreeLogger.info(
                "📊 User Interaction Logger Final Metrics",
                {
                    "uptime_seconds": uptime.total_seconds(),
                    "uptime_formatted": self._format_duration(uptime.total_seconds()),
                    "total_interactions": self.metrics["total_interactions"],
                    "voice_joins": self.metrics["voice_joins"],
                    "voice_leaves": self.metrics["voice_leaves"],
                    "button_clicks": self.metrics["button_clicks"],
                    "dropdown_selects": self.metrics["dropdown_selects"],
                    "average_response_time_ms": self.metrics[
                        "average_response_time_ms"
                    ],
                    "error_count": self.metrics["error_count"],
                    "error_rate_percent": (
                        self.metrics["error_count"]
                        / max(1, self.metrics["total_interactions"])
                    )
                    * 100,
                    "active_voice_sessions": len(self.voice_sessions),
                    "cached_interactions": len(self.recent_interactions),
                },
                service="UserInteractionLogger",
            )

        except Exception as e:
            TreeLogger.error(
                f"Error logging final metrics: {e}",
                None,
                {"service": "UserInteractionLogger"},
                service="UserInteractionLogger",
            )

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for monitoring."""
        uptime = datetime.now(APP_TIMEZONE) - self.metrics["session_start"]

        return {
            **self.metrics,
            "uptime_seconds": uptime.total_seconds(),
            "active_voice_sessions": len(self.voice_sessions),
            "cached_interactions": len(self.recent_interactions),
            "error_rate_percent": (
                self.metrics["error_count"] / max(1, self.metrics["total_interactions"])
            )
            * 100,
        }
