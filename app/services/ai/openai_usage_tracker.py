# =============================================================================
# QuranBot - OpenAI Usage Tracker Service
# =============================================================================
# Fetches real usage data from OpenAI API
# =============================================================================

import asyncio
import calendar
from datetime import datetime, timedelta
from typing import Any

from ...config import get_config
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class OpenAIUsageTracker(BaseService):
    """
    Fetches real usage data from OpenAI API.

    Features:
    - Real-time usage data from OpenAI
    - Daily and monthly usage tracking
    - Cost calculation based on actual usage
    - Automatic synchronization with local tracking
    """

    def __init__(self, bot):
        """Initialize OpenAI usage tracker."""
        super().__init__("OpenAIUsageTracker")
        self.bot = bot
        self.config = get_config()
        self.base_url = "https://api.openai.com/v1"
        self.usage_endpoint = f"{self.base_url}/usage"

        # Cache for usage data
        self.cached_usage = None
        self.cache_timestamp = None
        self.cache_duration = timedelta(minutes=5)  # Cache for 5 minutes

        TreeLogger.debug(
            "OpenAI Usage Tracker instance created", service=self.service_name
        )

    async def _initialize(self) -> bool:
        """Initialize the usage tracker."""
        try:
            TreeLogger.info(
                "Initializing OpenAI Usage Tracker", service=self.service_name
            )

            if not self.config.openai_api_key:
                TreeLogger.warning(
                    "OpenAI API key not configured", service=self.service_name
                )
                return False

            # Test API connection
            usage = await self.fetch_current_month_usage()
            if usage:
                TreeLogger.info(
                    "OpenAI Usage Tracker initialized successfully",
                    {"current_usage": f"${usage.get('total_cost', 0):.2f}"},
                    service=self.service_name,
                )

            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "openai_usage_tracker_initialization"}
            )
            return False

    async def _start(self) -> bool:
        """Start the usage tracker."""
        TreeLogger.info("OpenAI Usage Tracker started", service=self.service_name)

        # Start periodic sync task
        asyncio.create_task(self._periodic_sync())

        return True

    async def _stop(self) -> bool:
        """Stop the usage tracker."""
        TreeLogger.info("OpenAI Usage Tracker stopped", service=self.service_name)
        return True

    async def _health_check(self) -> dict[str, Any]:
        """Perform health check on usage tracker."""
        return {
            "is_healthy": True,
            "has_api_key": bool(self.config.openai_api_key),
            "cache_valid": self._is_cache_valid(),
        }

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.cached_usage or not self.cache_timestamp:
            return False

        return datetime.now() - self.cache_timestamp < self.cache_duration

    async def fetch_current_month_usage(self) -> dict[str, Any] | None:
        """
        Fetch current month's usage from local token tracker.

        Returns:
            Dictionary with usage data or None if error
        """
        # Check cache first
        if self._is_cache_valid():
            TreeLogger.debug("Returning cached usage data", service=self.service_name)
            return self.cached_usage

        try:
            # For now, we'll use local tracking instead of OpenAI API
            # The OpenAI usage API is not publicly available
            token_tracker = self.bot.services.get("token_tracker")

            if not token_tracker:
                TreeLogger.warning(
                    "Token tracker not available", service=self.service_name
                )
                # Return default data
                usage_data = {
                    "total_cost": 0.0,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "remaining_budget": self.config.openai_monthly_budget,
                    "budget_used_percent": 0.0,
                    "daily_costs": [],
                    "model_usage": {},
                    "month": datetime.now().strftime("%Y-%m"),
                    "last_updated": datetime.now().isoformat(),
                }
            else:
                # Get usage from token tracker
                tracker_data = await token_tracker.get_usage_summary()

                # Convert to expected format
                usage_data = {
                    "total_cost": tracker_data.get("total_cost", 0.0),
                    "total_requests": tracker_data.get("total_requests", 0),
                    "total_tokens": tracker_data.get("total_tokens", 0),
                    "remaining_budget": tracker_data.get(
                        "remaining_budget", self.config.openai_monthly_budget
                    ),
                    "budget_used_percent": tracker_data.get("budget_percentage", 0.0),
                    "daily_costs": [],
                    "model_usage": {},
                    "month": datetime.now().strftime("%Y-%m"),
                    "last_updated": datetime.now().isoformat(),
                }

            # Update cache
            self.cached_usage = usage_data
            self.cache_timestamp = datetime.now()

            TreeLogger.info(
                "Usage data fetched",
                {
                    "total_cost": f"${usage_data['total_cost']:.2f}",
                    "total_requests": usage_data["total_requests"],
                    "total_tokens": usage_data["total_tokens"],
                },
                service=self.service_name,
            )

            return usage_data

        except Exception as e:
            TreeLogger.error(
                "Failed to fetch usage data",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )
            await self.error_handler.handle_error(e, {"operation": "fetch_usage_data"})
            return None

    def _process_usage_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process raw usage data from OpenAI API.

        Args:
            raw_data: Raw response from OpenAI API

        Returns:
            Processed usage data
        """
        # OpenAI returns usage in cents, convert to dollars
        total_usage_cents = raw_data.get("total_usage", 0)
        total_cost = total_usage_cents / 100

        # Calculate daily breakdown
        daily_costs = []
        if "daily_costs" in raw_data:
            for day_data in raw_data["daily_costs"]:
                daily_costs.append(
                    {
                        "date": day_data.get("timestamp"),
                        "cost": day_data.get("line_items", [{}])[0].get("cost", 0)
                        / 100,
                    }
                )

        # Get model-specific usage
        model_usage = {}
        if "usage_by_model" in raw_data:
            for model, usage in raw_data["usage_by_model"].items():
                model_usage[model] = {
                    "requests": usage.get("requests", 0),
                    "tokens": usage.get("tokens", 0),
                    "cost": usage.get("cost", 0) / 100,
                }

        # Calculate remaining budget
        remaining_budget = max(0, self.config.openai_monthly_budget - total_cost)
        budget_used_percent = (
            (total_cost / self.config.openai_monthly_budget * 100)
            if self.config.openai_monthly_budget > 0
            else 0
        )

        return {
            "total_cost": total_cost,
            "total_requests": raw_data.get("total_requests", 0),
            "total_tokens": raw_data.get("total_tokens", 0),
            "remaining_budget": remaining_budget,
            "budget_used_percent": budget_used_percent,
            "daily_costs": daily_costs,
            "model_usage": model_usage,
            "month": datetime.now().strftime("%Y-%m"),
            "last_updated": datetime.now().isoformat(),
        }

    async def get_usage_summary(self) -> dict[str, Any]:
        """
        Get a formatted summary of current usage.

        Returns:
            Usage summary with formatted strings
        """
        usage = await self.fetch_current_month_usage()

        if not usage:
            return {
                "status": "unavailable",
                "message": "Unable to fetch usage data from OpenAI",
            }

        # Calculate days remaining in month
        now = datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_remaining = days_in_month - now.day

        # Estimate daily burn rate
        days_passed = now.day
        daily_burn_rate = usage["total_cost"] / days_passed if days_passed > 0 else 0
        projected_monthly_cost = daily_burn_rate * days_in_month

        return {
            "status": "available",
            "current_cost": f"${usage['total_cost']:.2f}",
            "budget": f"${self.config.openai_monthly_budget:.2f}",
            "remaining": f"${usage['remaining_budget']:.2f}",
            "percentage_used": f"{usage['budget_used_percent']:.1f}%",
            "total_requests": f"{usage['total_requests']:,}",
            "total_tokens": f"{usage['total_tokens']:,}",
            "daily_burn_rate": f"${daily_burn_rate:.2f}/day",
            "projected_monthly": f"${projected_monthly_cost:.2f}",
            "days_remaining": days_remaining,
            "will_exceed_budget": projected_monthly_cost
            > self.config.openai_monthly_budget,
        }

    async def sync_with_local_tracker(self) -> None:
        """Update cache with latest local token tracker data."""
        try:
            # Simply refresh our cache with latest data
            await self.fetch_current_month_usage()

        except Exception as e:
            TreeLogger.error("Failed to sync usage data", e, service=self.service_name)

    async def _periodic_sync(self) -> None:
        """Periodically sync usage data."""
        while self.state == "running":
            try:
                # Sync every 30 minutes
                await asyncio.sleep(1800)
                await self.sync_with_local_tracker()

            except Exception as e:
                TreeLogger.error("Error in periodic sync", e, service=self.service_name)
                await asyncio.sleep(300)  # Retry in 5 minutes

    async def _cleanup(self) -> None:
        """Clean up OpenAI usage tracker resources."""
        try:
            TreeLogger.debug(
                "Cleaning up OpenAI usage tracker resources", service=self.service_name
            )

            # Clear cached data
            if hasattr(self, "_cache"):
                self._cache = {}
                TreeLogger.debug("Usage cache cleared", service=self.service_name)

            # Close aiohttp session if it exists and we created it
            if hasattr(self, "_session") and self._session:
                await self._session.close()
                self._session = None
                TreeLogger.debug("HTTP session closed", service=self.service_name)

            TreeLogger.info(
                "OpenAI usage tracker cleanup completed", service=self.service_name
            )

        except Exception as e:
            TreeLogger.error(
                "Error during OpenAI usage tracker cleanup",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )
            # Don't raise - cleanup should be best effort
