#!/usr/bin/env python3
"""
Quick test to verify webhook footer formatting shows only EST time
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import pytz
from src.core.webhook_logger import WebhookFormatter, WebhookConfig, WebhookMessage, LogLevel

def test_footer_format():
    """Test that webhook footer shows only EST time without duplicate timestamps."""
    
    # Create a webhook config
    config = WebhookConfig(
        webhook_url="https://discord.com/api/webhooks/test/test",
        timezone="US/Eastern"
    )
    
    # Create formatter
    formatter = WebhookFormatter(config)
    
    # Create a test message
    message = WebhookMessage(
        title="Test Message",
        description="Testing footer format",
        level=LogLevel.INFO
    )
    
    # Format the message
    formatted = formatter.format_message(message)
    
    print("=== Webhook Embed Structure ===")
    print(f"Title: {formatted['embeds'][0]['title']}")
    print(f"Description: {formatted['embeds'][0]['description']}")
    print(f"Footer: {formatted['embeds'][0]['footer']['text']}")
    
    # Check that there's no 'timestamp' field (which would cause duplicate times)
    embed = formatted['embeds'][0]
    if 'timestamp' in embed:
        print("❌ ERROR: Found duplicate timestamp field!")
        print(f"Timestamp field: {embed['timestamp']}")
    else:
        print("✅ SUCCESS: No duplicate timestamp field found")
    
    # Verify footer format
    footer_text = embed['footer']['text']
    if 'EST' in footer_text and '/' in footer_text:
        print("✅ SUCCESS: Footer contains EST timezone and date format")
    else:
        print("❌ ERROR: Footer format incorrect")
    
    print(f"\nExpected format: MM/DD/YYYY HH:MM AM/PM EST")
    print(f"Actual footer: {footer_text}")

if __name__ == "__main__":
    test_footer_format()