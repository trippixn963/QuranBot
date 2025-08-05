# =============================================================================
# QuranBot - UI Package
# =============================================================================
# Modern, modular Discord UI system for interactive control panels and forms.
# Provides base components, control panels, and search interfaces.
# =============================================================================

from .control_panel import ControlPanelManager
from .search import SurahSearchModal

__all__ = ["ControlPanelManager", "SurahSearchModal"]
