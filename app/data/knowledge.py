# =============================================================================
# QuranBot - Islamic Knowledge Base
# =============================================================================
# Loads and provides access to Islamic knowledge data for AI responses
# =============================================================================

import json
from pathlib import Path
from typing import Dict, Any

# Load Islamic knowledge base from JSON file
def _load_islamic_knowledge() -> Dict[str, Any]:
    """Load Islamic knowledge base from JSON file."""
    try:
        knowledge_file = Path(__file__).parent / "islamic_knowledge.json"
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load Islamic knowledge base: {e}")
        return {}

# Load the knowledge base
ISLAMIC_KNOWLEDGE_BASE = _load_islamic_knowledge()

__all__ = ['ISLAMIC_KNOWLEDGE_BASE'] 