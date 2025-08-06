"""Module for token tracker functionality."""

# =============================================================================
# QuranBot - Token Tracking Service.
# =============================================================================
# Tracks OpenAI API usage, costs, and budget management
# =============================================================================

import calendar
from datetime import datetime, timedelta
from typing import Any

from ...config import get_config
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class TokenTracker(BaseService):

    """
    Token tracking service for OpenAI usage monitoring.

    Features:
    - Real-time token counting.
    - Cost calculation and tracking
    - Monthly budget management
    - Usage warnings and alerts
    - Per-user statistics
    """

    def __init__(self, bot):
        """Initialize token tracker."""
        super().__init__("TokenTracker")
        self.bot = bot
        self.config = get_config()
        self.database_service = None

        TreeLogger.debug(
            "Token Tracker instance created",
            {"monthly_budget": f"${self.config.openai_monthly_budget}"},
            service=self.service_name,
        )

        # Pricing constants (GPT-3.5 Turbo as of 2024)
        self.PRICE_PER_1K_INPUT = 0.001
        self.PRICE_PER_1K_OUTPUT = 0.002

        # Alert thresholds
        self.ALERT_THRESHOLDS = [0.5, 0.75, 0.9, 1.0]  # 50%, 75%, 90%, 100%
        self.last_alert_level = 0

    async def _initialize(self) -> bool:
        """Initialize the token tracker."""
        try:
            TreeLogger.info("Initializing Token Tracker", service=self.service_name)

            # Get database service
            self.database_service = self.bot.services.get("database")
            if not self.database_service:
                raise Exception("Database service not available")

            # Create tables if not exist
            TreeLogger.debug("Creating database tables", service=self.service_name)
            await self._create_tables()

            # Load current month stats
            TreeLogger.debug(
                "Loading current month statistics", service=self.service_name
            )
            await self._load_current_month_stats()

            TreeLogger.info(
                "Token Tracker initialized",
                {
                    "monthly_budget": f"${self.config.openai_monthly_budget}",
                    "price_per_1k_input": f"${self.PRICE_PER_1K_INPUT}",
                    "price_per_1k_output": f"${self.PRICE_PER_1K_OUTPUT}",
                },
                service=self.service_name,
            )

            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "token_tracker_initialization"}
            )
            return False

    async def _start(self) -> bool:
        """Start the token tracker."""
        TreeLogger.info("Token Tracker started", service=self.service_name)
        return True

    async def _stop(self) -> bool:
        """Stop the token tracker."""
        TreeLogger.info("Token Tracker stopped", service=self.service_name)
        return True

    async def _health_check(self) -> dict[str, Any]:
        """Perform health check on token tracker."""
        current_usage = await self.get_current_month_usage()
        return {
            "is_healthy": True,
            "has_database": self.database_service is not None,
            "current_month_cost": f"${current_usage.get('total_cost', 0):.2f}",
            "budget_remaining": f"${self.config.openai_monthly_budget - current_usage.get('total_cost', 0):.2f}",
        }

    async def _create_tables(self) -> None:
        """Create necessary database tables."""
        TreeLogger.debug("Creating AI usage tables", service=self.service_name)
        
        await self.database_service.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                question TEXT,
                response_preview TEXT,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                model TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.database_service.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_monthly_stats (
                month TEXT PRIMARY KEY,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0,
                request_count INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.database_service.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_usage_timestamp 
            ON ai_usage(timestamp)
        """)
        
        await self.database_service.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_usage_user_id 
            ON ai_usage(user_id)
        """)
        
        TreeLogger.debug(
            "Database tables created successfully", service=self.service_name
        )

    async def track_usage(
        self,
        user_id: int,
        username: str,
        question: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost: float,
    ) -> None:
        """
        Track AI usage for a user.

        Args:
            user_id: Discord user ID.
            username: Discord username
            question: User's question
            response: AI response
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: OpenAI model used
            cost: Calculated cost in USD
        """
        try:
            TreeLogger.debug(
                "Tracking AI usage",
                {
                    "user_id": user_id,
                    "username": username,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": f"${cost:.6f}",
                },
                service=self.service_name,
            )

            # Truncate question and response for storage
            question_preview = question[:500] if len(question) > 500 else question
            response_preview = response[:500] if len(response) > 500 else response

            # Insert usage record
            await self.database_service.execute(
                """
                INSERT INTO ai_usage 
                (user_id, username, question, response_preview, input_tokens, 
                 output_tokens, total_tokens, cost, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(user_id),
                    username,
                    question_preview,
                    response_preview,
                    input_tokens,
                    output_tokens,
                    input_tokens + output_tokens,
                    cost,
                    model,
                ),
            )

            # Update monthly stats.
            await self._update_monthly_stats(input_tokens + output_tokens, cost)

            # Check budget alerts
            await self._check_budget_alerts()

            TreeLogger.info(
                "AI usage tracked",
                {
                    "user": username,
                    "tokens": input_tokens + output_tokens,
                    "cost": f"${cost:.6f}",
                    "model": model,
                },
                service=self.service_name,
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "track_ai_usage", "user_id": user_id}
            )

    async def _update_monthly_stats(self, tokens: int, cost: float) -> None:
        """Update monthly statistics."""
        current_month = datetime.now().strftime("%Y-%m")
        
        TreeLogger.debug(
            "Updating monthly statistics",
            {"month": current_month, "tokens": tokens, "cost": f"${cost:.6f}"},
            service=self.service_name,
        )

        # Get current unique users count for this month
        result = await self.database_service.fetch_one(
            """
            SELECT COUNT(DISTINCT user_id) as count
            FROM ai_usage 
            WHERE strftime('%Y-%m', timestamp) = ?
        """,
            (current_month,),
        )
        unique_users = result["count"] if result else 0

        await self.database_service.execute(
            """INSERT INTO ai_monthly_stats (month, total_tokens, total_cost, request_count, unique_users)
                        VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(month) DO UPDATE SET
                total_tokens = total_tokens + ?,
                total_cost = total_cost + ?,
                request_count = request_count + 1,
                unique_users = ?,
                last_updated = CURRENT_TIMESTAMP
        """,
            (
                current_month,
                tokens,
                cost,
                unique_users or 1,
                tokens,
                cost,
                unique_users or 1,
            ),
        )

    async def _load_current_month_stats(self) -> None:
        """Load current month statistics."""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Ensure current month exists
        await self.database_service.execute(
            """
            INSERT OR IGNORE INTO ai_monthly_stats (month) VALUES (?)
        """,
            (current_month,),
        )

    async def get_current_month_usage(self) -> dict[str, Any]:
        """Get current month's usage statistics."""
        current_month = datetime.now().strftime("%Y-%m")
        
        TreeLogger.debug(
            "Fetching current month usage",
            {"month": current_month},
            service=self.service_name,
        )

        stats = await self.database_service.fetch_one(
            """
            SELECT total_tokens, total_cost, request_count, unique_users
            FROM ai_monthly_stats
            WHERE month = ?
        """,
            (current_month,),
        )

        if not stats:
            TreeLogger.debug(
                "No usage stats found for current month",
                {"month": current_month},
                service=self.service_name,
            )

            return {
                "month": current_month,
                "total_tokens": 0,
                "total_cost": 0.0,
                "request_count": 0,
                "unique_users": 0,
                "budget_used_percent": 0.0,
                "budget_remaining": self.config.openai_monthly_budget,
            }

        total_cost = stats["total_cost"] or 0
        budget_used_percent = (
            (total_cost / self.config.openai_monthly_budget * 100)
            if self.config.openai_monthly_budget > 0
            else 0
        )

        TreeLogger.debug(
            "Current month usage retrieved",
            {
                "total_cost": f"${total_cost:.2f}",
                "budget_used_percent": f"{budget_used_percent:.1f}%",
                "request_count": stats["request_count"] or 0,
            },
            service=self.service_name,
        )

        return {
            "month": current_month,
            "total_tokens": stats["total_tokens"] or 0,
            "total_cost": total_cost,
            "request_count": stats["request_count"] or 0,
            "unique_users": stats["unique_users"] or 0,
            "budget_used_percent": budget_used_percent,
            "budget_remaining": max(0, self.config.openai_monthly_budget - total_cost),
        }

    async def get_user_usage(self, user_id: int, days: int = 30) -> dict[str, Any]:
        """Get usage statistics for a specific user."""
        since_date = datetime.now() - timedelta(days=days)
        
        stats = await self.database_service.fetch_one(
            """
            SELECT 
                COUNT(*) as request_count,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                MIN(timestamp) as first_use,
                MAX(timestamp) as last_use.
            FROM ai_usage
            WHERE user_id = ? AND timestamp >= ?
        """,
            (str(user_id), since_date),
        )

        if not stats or not stats["request_count"]:
            return {
                "request_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "first_use": None,
                "last_use": None,
                "average_tokens_per_request": 0,
            }

        return {
            "request_count": stats["request_count"],
            "total_tokens": stats["total_tokens"] or 0,
            "total_cost": stats["total_cost"] or 0.0,
            "first_use": stats["first_use"],
            "last_use": stats["last_use"],
            "average_tokens_per_request": (stats["total_tokens"] or 0)
            // stats["request_count"],
        }

    async def get_daily_breakdown(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily usage breakdown."""
        since_date = datetime.now() - timedelta(days=days)
        
        breakdown = await self.database_service.fetch_all(
            """
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as requests,
                SUM(total_tokens) as tokens,
                SUM(cost) as cost,
                COUNT(DISTINCT user_id) as unique_users
            FROM ai_usage
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """,
            (since_date,),
        )

        return [
            {
                "date": row["date"],
                "requests": row["requests"],
                "tokens": row["tokens"] or 0,
                "cost": row["cost"] or 0.0,
                "unique_users": row["unique_users"],
            }
            for row in breakdown
        ]

    async def _check_budget_alerts(self) -> None:
        """Check if budget alerts need to be sent."""
        current_usage = await self.get_current_month_usage()
        usage_percent = current_usage["budget_used_percent"] / 100

        TreeLogger.debug(
            "Checking budget alerts",
            {
                "usage_percent": f"{usage_percent * 100:.1f}%",
                "last_alert_level": f"{self.last_alert_level * 100:.0f}%",
            },
            service=self.service_name,
        )

        # Find which threshold we've crossed
        for i, threshold in enumerate(self.ALERT_THRESHOLDS):
            if usage_percent >= threshold and self.last_alert_level < threshold:
                self.last_alert_level = threshold
                TreeLogger.warning(
                    f"Budget threshold crossed: {int(threshold * 100)}%",
                    {
                        "threshold": threshold,
                        "usage_percent": f"{usage_percent * 100:.1f}%",
                        "total_cost": f"${current_usage['total_cost']:.2f}",
                    },
                    service=self.service_name,
                )
                await self._send_budget_alert(threshold, current_usage)
                break

    async def get_usage_summary(self) -> dict[str, Any]:
        """
        Get usage summary for OpenAI usage tracker.

        Returns:
        --------
        Usage summary dictionary.

        """
        return await self.get_current_month_usage()
        
    async def _send_budget_alert(self, threshold: float, usage: dict[str, Any]) -> None:
        """Send budget alert to developer."""
        if not self.config.developer_id:
            return

        try:
            user = await self.bot.fetch_user(self.config.developer_id)
            if not user:
                return

            # Create alert embed
            import discord

            if threshold >= 1.0:
                color = 0xFF0000  # Red
                title = "🚨 AI Budget Limit Reached!"
                description = "The monthly AI budget has been exhausted. AI features will be disabled until the budget resets."
            elif threshold >= 0.9:
                color = 0xFF6B6B  # Orange-red
                title = "⚠️ AI Budget Critical - 90% Used"
                description = "Only 10% of the monthly AI budget remains."
            elif threshold >= 0.75:
                color = 0xFFA500  # Orange
                title = "⚠️ AI Budget Warning - 75% Used"
                description = "Three quarters of the monthly AI budget has been used."
            else:
                color = 0xFFFF00  # Yellow
                title = "📊 AI Budget Notice - 50% Used"
                description = "Half of the monthly AI budget has been used."

            embed = discord.Embed(title=title, description=description, color=color)

            # Add bot thumbnail
            if self.bot and self.bot.user and self.bot.user.avatar:
                try:
                    embed.set_thumbnail(url=self.bot.user.avatar.url)
                except:
                    pass

            embed.add_field(
                name="📈 Current Usage",
                value=f"**Total Cost:** ${usage['total_cost']:.2f}\n"
                f"**Budget:** ${self.config.openai_monthly_budget:.2f}\n"
                f"**Remaining:** ${usage['budget_remaining']:.2f}",
                inline=True,
            )

            embed.add_field(
                name="📊 Statistics",
                value=f"**Requests:** {usage['request_count']}\n"
                f"**Tokens:** {usage['total_tokens']:,}\n"
                f"**Users:** {usage['unique_users']}",
                inline=True,
            )

            # Calculate days until reset
            now = datetime.now()
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            days_until_reset = days_in_month - now.day + 1

            embed.add_field(
                name="📅 Budget Reset",
                value=f"**Resets in:** {days_until_reset} days\n"
                f"**Reset date:** {now.replace(day=1).strftime('%B 1, %Y')}",
                inline=False,
            )

            # Get developer avatar
            developer_icon_url = None
            if self.bot and self.config.developer_id:
                try:
                    developer = self.bot.get_user(self.config.developer_id)
                    if developer and developer.avatar:
                        developer_icon_url = developer.avatar.url
                except:
                    pass

            embed.set_footer(
                text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
            )

            await user.send(embed=embed)

            TreeLogger.warning(
                f"Budget alert sent: {int(threshold * 100)}% used",
                {
                    "threshold": threshold,
                    "total_cost": usage["total_cost"],
                    "budget": self.config.openai_monthly_budget,
                },
                service=self.service_name,
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to send budget alert",
                e,
                {"threshold": threshold, "developer_id": self.config.developer_id},
                service=self.service_name,
            )
            await self.error_handler.handle_error(
                e, {"operation": "send_budget_alert", "threshold": threshold}
            )

    def is_budget_exceeded(self) -> bool:
        """Check if monthly budget is exceeded."""
        # This will be checked synchronously by other services.
        exceeded = self.last_alert_level >= 1.0

        if exceeded:
            TreeLogger.debug(
                "Budget exceeded check: True",
                {"last_alert_level": f"{self.last_alert_level * 100:.0f}%"},
                service=self.service_name,
            )

        return exceeded

    async def reset_monthly_alerts(self) -> None:
        """Reset monthly alert level (called on new month)."""
        self.last_alert_level = 0.0
        TreeLogger.info("Monthly alerts reset", service=self.service_name)

    async def _cleanup(self) -> None:
        """Clean up token tracker resources."""
        try:
            TreeLogger.debug(
                "Cleaning up token tracker resources", service=self.service_name
            )

            # No specific resources to clean up for token tracker
            # It's mainly database-based, and database service handles its own cleanup

            TreeLogger.info(
                "Token tracker cleanup completed", service=self.service_name
            )

        except Exception as e:
            TreeLogger.error(
                "Error during token tracker cleanup",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )
            # Don't raise - cleanup should be best effort
