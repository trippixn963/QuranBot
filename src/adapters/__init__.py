# =============================================================================
# QuranBot - Adapters Module
# =============================================================================
# Adapter classes for bridging different service interfaces.
# This module contains adapters that translate between different service
# interfaces to maintain compatibility while using modern architecture.
# =============================================================================

from .audio_service_adapter import AudioServiceAdapter

__all__ = [
    "AudioServiceAdapter",
]