# =============================================================================
# QuranBot - Webhook Service Factory
# =============================================================================
# Factory for creating and configuring webhook logging services based on
# the bot configuration. Handles both single-channel legacy mode and 
# multi-channel enhanced routing.
# =============================================================================

from typing import Any, Optional

from .enhanced_webhook_router import EnhancedWebhookRouter
from .webhook_logger import ModernWebhookLogger, WebhookConfig
from .structured_logger import StructuredLogger
from src.config.bot_config import BotConfig


class WebhookServiceFactory:
    """Factory for creating webhook logging services based on configuration."""
    
    @staticmethod
    async def create_webhook_service(
        config: BotConfig,
        logger: StructuredLogger,
        container: Any = None,
        bot: Any = None,
    ) -> Optional[EnhancedWebhookRouter | ModernWebhookLogger]:
        """
        Create the appropriate webhook service based on configuration.
        
        Args:
            config: Bot configuration
            logger: Structured logger
            container: DI container
            bot: Discord bot instance
            
        Returns:
            EnhancedWebhookRouter if multi-channel webhooks are configured,
            ModernWebhookLogger for single-channel legacy mode, or None if disabled
        """
        if not config.USE_WEBHOOK_LOGGING:
            await logger.info("Webhook logging is disabled")
            return None
        
        # Check if multi-channel webhooks are configured
        multi_channel_urls = [
            config.WEBHOOK_BOT_STATUS,
            config.WEBHOOK_QURAN_AUDIO,
            config.WEBHOOK_COMMANDS_PANEL,
            config.WEBHOOK_USER_ACTIVITY,
            config.WEBHOOK_DATA_ANALYTICS,
            config.WEBHOOK_ERRORS_ALERTS,
            config.WEBHOOK_DAILY_REPORTS,
        ]
        
        has_multi_channel = any(url for url in multi_channel_urls)
        
        if has_multi_channel:
            # Create enhanced multi-channel router
            await logger.info("Creating enhanced multi-channel webhook router")
            
            router = EnhancedWebhookRouter(
                config=config,
                logger=logger,
                container=container,
                bot=bot,
            )
            
            if await router.initialize():
                await logger.info("Enhanced webhook router initialized successfully")
                return router
            else:
                await logger.error("Failed to initialize enhanced webhook router")
                return None
        
        elif config.DISCORD_WEBHOOK_URL:
            # Create legacy single-channel logger
            await logger.info("Creating legacy single-channel webhook logger")
            
            webhook_config = WebhookConfig(
                webhook_url=config.DISCORD_WEBHOOK_URL,
                owner_user_id=config.DEVELOPER_ID,
                timezone="US/Eastern",
                enable_pings=True,
            )
            
            webhook_logger = ModernWebhookLogger(
                config=webhook_config,
                logger=logger,
                container=container,
                bot=bot,
            )
            
            if await webhook_logger.initialize():
                await logger.info("Legacy webhook logger initialized successfully")
                return webhook_logger
            else:
                await logger.error("Failed to initialize legacy webhook logger")
                return None
        
        else:
            await logger.warning("Webhook logging enabled but no webhook URLs configured")
            return None
    
    @staticmethod
    def get_webhook_service_info(config: BotConfig) -> dict[str, Any]:
        """
        Get information about the webhook service configuration.
        
        Args:
            config: Bot configuration
            
        Returns:
            Dictionary with webhook service information
        """
        if not config.USE_WEBHOOK_LOGGING:
            return {
                "enabled": False,
                "type": "disabled",
                "channels": 0,
                "urls_configured": 0,
            }
        
        # Count configured webhook URLs
        multi_channel_urls = [
            config.WEBHOOK_BOT_STATUS,
            config.WEBHOOK_QURAN_AUDIO,
            config.WEBHOOK_COMMANDS_PANEL,
            config.WEBHOOK_USER_ACTIVITY,
            config.WEBHOOK_DATA_ANALYTICS,
            config.WEBHOOK_ERRORS_ALERTS,
            config.WEBHOOK_DAILY_REPORTS,
        ]
        
        multi_channel_count = sum(1 for url in multi_channel_urls if url)
        has_legacy_url = bool(config.DISCORD_WEBHOOK_URL)
        
        if multi_channel_count > 0:
            service_type = "multi_channel"
            total_channels = multi_channel_count
        elif has_legacy_url:
            service_type = "single_channel"
            total_channels = 1
        else:
            service_type = "misconfigured"
            total_channels = 0
        
        return {
            "enabled": True,
            "type": service_type,
            "channels": total_channels,
            "urls_configured": multi_channel_count + (1 if has_legacy_url else 0),
            "multi_channel_urls": multi_channel_count,
            "has_legacy_url": has_legacy_url,
            "channel_breakdown": {
                "bot_status": bool(config.WEBHOOK_BOT_STATUS),
                "quran_audio": bool(config.WEBHOOK_QURAN_AUDIO),
                "commands_panel": bool(config.WEBHOOK_COMMANDS_PANEL),
                "user_activity": bool(config.WEBHOOK_USER_ACTIVITY),
                "data_analytics": bool(config.WEBHOOK_DATA_ANALYTICS),
                "errors_alerts": bool(config.WEBHOOK_ERRORS_ALERTS),
                "daily_reports": bool(config.WEBHOOK_DAILY_REPORTS),
                "legacy": has_legacy_url,
            },
        }


# Convenience function for easy integration
async def create_webhook_service(
    config: BotConfig,
    logger: StructuredLogger,
    container: Any = None,
    bot: Any = None,
) -> Optional[EnhancedWebhookRouter | ModernWebhookLogger]:
    """
    Convenience function to create webhook service.
    
    This is a shortcut to WebhookServiceFactory.create_webhook_service()
    for easier integration in existing code.
    """
    return await WebhookServiceFactory.create_webhook_service(
        config=config,
        logger=logger,
        container=container,
        bot=bot,
    )