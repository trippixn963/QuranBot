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
from src.config import QuranBotConfig


class WebhookServiceFactory:
    """Factory for creating webhook logging services based on configuration."""
    
    @staticmethod
    async def create_webhook_service(
        config: QuranBotConfig,
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
        if not config.use_webhook_logging:
            await logger.info("Webhook logging is disabled")
            return None
        
        # Check if multi-channel webhooks are configured
        multi_channel_urls = [
            config.webhook_bot_status,
            config.webhook_quran_audio,
            config.webhook_commands_panel,
            config.webhook_user_activity,
            config.webhook_data_analytics,
            config.webhook_errors_alerts,
            config.webhook_daily_reports,
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
        
        elif config.discord_webhook_url:
            # Create legacy single-channel logger
            await logger.info("Creating legacy single-channel webhook logger")
            
            webhook_config = WebhookConfig(
                webhook_url=config.discord_webhook_url,
                owner_user_id=config.developer_id,
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
    def get_webhook_service_info(config: QuranBotConfig) -> dict[str, Any]:
        """
        Get information about the webhook service configuration.
        
        Args:
            config: Bot configuration
            
        Returns:
            Dictionary with webhook service information
        """
        if not config.use_webhook_logging:
            return {
                "enabled": False,
                "type": "disabled",
                "channels": 0,
                "urls_configured": 0,
            }
        
        # Count configured webhook URLs
        multi_channel_urls = [
            config.webhook_bot_status,
            config.webhook_quran_audio,
            config.webhook_commands_panel,
            config.webhook_user_activity,
            config.webhook_data_analytics,
            config.webhook_errors_alerts,
            config.webhook_daily_reports,
        ]
        
        multi_channel_count = sum(1 for url in multi_channel_urls if url)
        has_legacy_url = bool(config.discord_webhook_url)
        
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
                            "bot_status": bool(config.webhook_bot_status),
            "quran_audio": bool(config.webhook_quran_audio),
            "commands_panel": bool(config.webhook_commands_panel),
            "user_activity": bool(config.webhook_user_activity),
            "data_analytics": bool(config.webhook_data_analytics),
            "errors_alerts": bool(config.webhook_errors_alerts),
            "daily_reports": bool(config.webhook_daily_reports),
                "legacy": has_legacy_url,
            },
        }


# Convenience function for easy integration
async def create_webhook_service(
            config: QuranBotConfig,
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