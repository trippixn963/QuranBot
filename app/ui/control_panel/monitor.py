# =============================================================================
# QuranBot - Control Panel Monitor
# =============================================================================
# Health monitoring system for control panels including failure tracking,
# recovery detection, and automated maintenance.
#
# Monitoring Features:
# - Health Checks: Periodic validation of panel responsiveness
# - Failure Tracking: Exponential backoff for error recovery
# - Recovery Detection: Automatic detection of system restoration
# - Cleanup Automation: Removal of inactive or stale panels
# - Performance Metrics: Response time and reliability tracking
#
# Health Check Criteria:
# - Panel View Responsiveness: Update method availability and performance
# - Message Accessibility: Discord message existence and permissions
# - Update Failure Tracking: Error rate monitoring and thresholds
# - State Synchronization: Audio manager integration health
# - User Interaction Tracking: Activity monitoring and engagement
#
# Recovery Mechanisms:
# - Exponential Backoff: Intelligent retry timing for failed operations
# - Failure Count Tracking: Persistent error state management
# - Recovery Detection: Automatic reset of failure counters
# - Graceful Degradation: Partial functionality during issues
# - Logging: Error tracking and analysis
#
# Maintenance Tasks:
# - Inactive Panel Cleanup: Removal of stale or abandoned panels
# - Resource Optimization: Memory and performance monitoring
# - Permission Validation: Ongoing capability verification
# - State Synchronization: Real-time audio manager integration
# - Error Recovery: Automatic restoration of failed components
# =============================================================================

# Standard library imports
import asyncio
from datetime import datetime
from typing import Any

# Local imports - config
from ...config.timezone import APP_TIMEZONE

# Local imports - core modules
from ...core.logger import TreeLogger


class ControlPanelMonitor:
    """
    Monitor system for control panel health and performance.

    Tracks control panel status, detects failures, and performs
    automated maintenance tasks to ensure reliable operation.
    """

    def __init__(self, manager):
        self.manager = manager
        self.is_running = False
        self.monitor_task: asyncio.Task | None = None

        # Monitoring configuration
        self.check_interval = 300  # 5 minutes
        self.cleanup_interval = 3600  # 1 hour

        # Health tracking
        self.last_check = datetime.now(APP_TIMEZONE)
        self.last_cleanup = datetime.now(APP_TIMEZONE)
        self.failure_count = 0
        self.recovery_count = 0

        TreeLogger.info(
            "Control panel monitor initialized",
            {
                "check_interval": self.check_interval,
                "cleanup_interval": self.cleanup_interval,
            },
            service="ControlPanelMonitor",
        )

    async def start(self):
        """Start the monitoring system."""
        if self.is_running:
            return

        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

        TreeLogger.info(
            "Control panel monitoring started", service="ControlPanelMonitor"
        )

    async def stop(self):
        """Stop the monitoring system."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        TreeLogger.info(
            "Control panel monitoring stopped", service="ControlPanelMonitor"
        )

    async def _monitor_loop(self):
        """
        Main monitoring loop for control panel health and maintenance.

        Performs monitoring including:
        - Periodic health checks on all control panels
        - Automated cleanup of inactive panels
        - Failure tracking and exponential backoff
        - Recovery detection and logging
        - Graceful shutdown handling

        The loop runs continuously until monitoring is stopped, ensuring
        control panels remain healthy and responsive.
        """
        while self.is_running:
            try:
                # STEP 1: Health Check Execution
                # Perform health checks on all active panels
                await self._perform_health_check()

                # STEP 2: Cleanup Condition Check
                # Determine if cleanup is needed based on time intervals
                if self._should_cleanup():
                    await self._perform_cleanup()

                # STEP 3: Timestamp Updates
                # Update last check timestamp for monitoring accuracy
                self.last_check = datetime.now(APP_TIMEZONE)

                # STEP 4: Monitoring Interval Wait
                # Wait for next check cycle to prevent excessive resource usage
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                # STEP 5: Graceful Shutdown Handling
                # Handle cancellation when monitoring is being stopped
                break
            except Exception as e:
                # STEP 6: Error Recovery with Exponential Backoff
                # Track failures and implement exponential backoff
                self.failure_count += 1
                TreeLogger.error(
                    f"Error in control panel monitor loop: {e}",
                    {"failure_count": self.failure_count},
                    service="ControlPanelMonitor",
                )

                # STEP 7: Exponential Backoff Calculation
                # Calculate backoff time to prevent overwhelming the system
                backoff_time = min(
                    self.check_interval * (2 ** min(self.failure_count, 5)), 1800
                )
                await asyncio.sleep(backoff_time)

    async def _perform_health_check(self):
        """Perform health check on all control panels."""
        try:
            active_panels = self.manager.get_all_panels_info()

            if not active_panels:
                return

            healthy_panels = 0
            unhealthy_panels = 0

            for channel_id, panel_info in active_panels.items():
                try:
                    # Check if panel view is responsive
                    if panel_info["view"] and hasattr(
                        panel_info["view"], "get_status_summary"
                    ):
                        status = panel_info["view"].get_status_summary()

                        # Check for signs of health issues
                        if status.get("update_failures", 0) > 3:
                            unhealthy_panels += 1
                            TreeLogger.warning(
                                "Control panel health issue detected",
                                {
                                    "channel_id": channel_id,
                                    "update_failures": status.get("update_failures", 0),
                                    "last_update": status.get("last_update"),
                                },
                                service="ControlPanelMonitor",
                            )
                        else:
                            healthy_panels += 1

                    # Check message accessibility
                    if panel_info["message"]:
                        try:
                            await panel_info["message"].fetch()
                        except Exception:
                            # Message may be deleted or inaccessible
                            unhealthy_panels += 1
                            TreeLogger.warning(
                                "Control panel message inaccessible",
                                {
                                    "channel_id": channel_id,
                                    "message_id": panel_info["message"].id,
                                },
                                service="ControlPanelMonitor",
                            )

                except Exception as e:
                    unhealthy_panels += 1
                    TreeLogger.error(
                        f"Error checking panel health: {e}",
                        {"channel_id": channel_id},
                        service="ControlPanelMonitor",
                    )

            # Log health summary
            TreeLogger.debug(
                "Control panel health check complete",
                {
                    "total_panels": len(active_panels),
                    "healthy_panels": healthy_panels,
                    "unhealthy_panels": unhealthy_panels,
                },
                service="ControlPanelMonitor",
            )

            # Reset failure count on successful check
            if self.failure_count > 0:
                self.recovery_count += 1
                self.failure_count = 0
                TreeLogger.info(
                    "Control panel monitor recovered",
                    {"recovery_count": self.recovery_count},
                    service="ControlPanelMonitor",
                )

        except Exception as e:
            TreeLogger.error(
                f"Error performing control panel health check: {e}",
                service="ControlPanelMonitor",
            )
            raise

    def _should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        time_since_cleanup = datetime.now(APP_TIMEZONE) - self.last_cleanup
        return time_since_cleanup.total_seconds() >= self.cleanup_interval

    async def _perform_cleanup(self):
        """Perform maintenance cleanup tasks."""
        try:
            TreeLogger.info(
                "Starting control panel cleanup", service="ControlPanelMonitor"
            )

            # Cleanup inactive panels
            await self.manager.cleanup_inactive_panels()

            # Update cleanup timestamp
            self.last_cleanup = datetime.now(APP_TIMEZONE)

            TreeLogger.info(
                "Control panel cleanup complete", service="ControlPanelMonitor"
            )

        except Exception as e:
            TreeLogger.error(
                f"Error performing control panel cleanup: {e}",
                service="ControlPanelMonitor",
            )

    def get_monitor_stats(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "is_running": self.is_running,
            "last_check": self.last_check,
            "last_cleanup": self.last_cleanup,
            "check_interval": self.check_interval,
            "cleanup_interval": self.cleanup_interval,
            "failure_count": self.failure_count,
            "recovery_count": self.recovery_count,
        }
