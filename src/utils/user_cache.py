# =============================================================================
# QuranBot - User Cache Utility
# =============================================================================
# Utility for caching Discord user information for dashboard display
# =============================================================================

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# Data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_CACHE_FILE = DATA_DIR / "user_cache.json"

def update_user_cache(user_id: int, display_name: str, avatar_url: Optional[str] = None):
    """
    Update the user cache with Discord user information.
    
    Args:
        user_id: Discord user ID
        display_name: User's display name
        avatar_url: User's avatar URL (optional)
    """
    try:
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)
        
        # Load existing cache
        cache_data = {
            'users': {},
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'total_cached_users': 0
        }
        
        if USER_CACHE_FILE.exists():
            try:
                with open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception:
                pass  # Use default cache_data if file is corrupted
        
        # Update user info
        user_id_str = str(user_id)
        cache_data['users'][user_id_str] = {
            'display_name': display_name,
            'avatar_url': avatar_url,
            'last_seen': datetime.now(timezone.utc).isoformat()
        }
        
        # Update metadata
        cache_data['last_updated'] = datetime.now(timezone.utc).isoformat()
        cache_data['total_cached_users'] = len(cache_data['users'])
        
        # Save cache
        with open(USER_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        # Fail silently to not interfere with bot operations
        pass

def get_cached_user_info(user_id: int) -> Optional[Dict]:
    """
    Get cached user information.
    
    Args:
        user_id: Discord user ID
        
    Returns:
        Dict with user info or None if not cached
    """
    try:
        if not USER_CACHE_FILE.exists():
            return None
            
        with open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        user_id_str = str(user_id)
        return cache_data.get('users', {}).get(user_id_str)
        
    except Exception:
        return None

def cache_user_from_interaction(interaction):
    """
    Cache user info from a Discord interaction.
    
    Args:
        interaction: Discord interaction object
    """
    try:
        user = interaction.user
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        update_user_cache(user.id, user.display_name, avatar_url)
    except Exception:
        pass  # Fail silently

def cache_user_from_member(member):
    """
    Cache user info from a Discord member object.
    
    Args:
        member: Discord member object
    """
    try:
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        update_user_cache(member.id, member.display_name, avatar_url)
    except Exception:
        pass  # Fail silently 