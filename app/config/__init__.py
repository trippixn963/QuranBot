# =============================================================================
# QuranBot - Configuration Package
# =============================================================================
# Centralized configuration system for single-server Discord bot deployment.
# Provides type-safe, validated configuration with environment variable support.
# with comprehensive configuration loading monitoring and validation.
# =============================================================================

import time
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from .timezone import APP_TIMEZONE
from pathlib import Path

# Track configuration package import performance
_config_import_start = time.time()
_config_import_errors: List[str] = []
_config_import_warnings: List[str] = []
_config_package_metadata: Dict[str, Any] = {
    "package_name": "app.config",
    "import_start": datetime.now(APP_TIMEZONE).isoformat(),
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "env_file_exists": Path(".env").exists(),
    "env_file_size": Path(".env").stat().st_size if Path(".env").exists() else 0,
    "imports_attempted": 0,
    "imports_successful": 0
}

# Import configuration components with comprehensive error tracking
_config_components = {}

try:
    _config_package_metadata["imports_attempted"] += 1
    
    # Import main configuration classes and functions
    from .config import (
        QuranBotConfig, 
        get_config, 
        reload_config,
        ReciterName, 
        Environment, 
        LogLevel,
        get_config_metadata,
        validate_critical_config,
        validate_configuration_with_logging
    )
    
    _config_components["main_config"] = {
        "QuranBotConfig": QuranBotConfig,
        "get_config": get_config,
        "reload_config": reload_config,
        "get_config_metadata": get_config_metadata,
        "validate_critical_config": validate_critical_config,
        "validate_configuration_with_logging": validate_configuration_with_logging,
        "status": "✅ Success",
        "import_time_ms": f"{(time.time() - _config_import_start) * 1000:.2f}"
    }
    
    _config_components["enums"] = {
        "ReciterName": ReciterName,
        "Environment": Environment,
        "LogLevel": LogLevel,
        "status": "✅ Success",
        "enum_count": 3
    }
    
    _config_package_metadata["imports_successful"] += 1
    
    # Test configuration loading immediately
    try:
        config_test_start = time.time()
        test_config = get_config()
        config_test_time = time.time() - config_test_start
        
        _config_components["config_instance"] = {
            "status": "✅ Loaded successfully",
            "load_time_ms": f"{config_test_time * 1000:.2f}",
            "environment": test_config.environment.value,
            "log_level": test_config.log_level.value,
            "guild_configured": test_config.guild_id is not None,
            "audio_folder_exists": test_config.audio_folder.exists(),
            "ffmpeg_available": test_config.ffmpeg_path.exists()
        }
        
        # Get configuration metadata for detailed logging
        config_metadata = get_config_metadata()
        _config_components["config_metadata"] = {
            "status": "✅ Available",
            "total_errors": len(config_metadata.get("errors", [])),
            "total_warnings": len(config_metadata.get("warnings", [])),
            "metadata_keys": len(config_metadata.get("metadata", {}))
        }
        
        # Validate critical configuration
        is_critical_valid, critical_errors = validate_critical_config()
        _config_components["critical_validation"] = {
            "status": "✅ Valid" if is_critical_valid else "❌ Invalid",
            "critical_errors": len(critical_errors),
            "errors": critical_errors if not is_critical_valid else []
        }
        
        if not is_critical_valid:
            _config_import_errors.extend(critical_errors)
        
        # Add any configuration warnings
        if config_metadata.get("warnings"):
            _config_import_warnings.extend(config_metadata["warnings"])
            
    except Exception as e:
        _config_import_errors.append(f"Configuration loading test failed: {e}")
        _config_components["config_instance"] = {
            "status": "❌ Failed to load",
            "error": str(e)
        }

except ImportError as e:
    _config_import_errors.append(f"Configuration import failed: {e}")
    _config_package_metadata["imports_successful"] = 0
    _config_components["main_config"] = {
        "status": "❌ Import failed",
        "error": str(e)
    }

# Calculate total import time and update metadata
_total_config_import_time = time.time() - _config_import_start
_config_package_metadata.update({
    "total_import_time_ms": f"{_total_config_import_time * 1000:.2f}",
    "import_end": datetime.now(APP_TIMEZONE).isoformat(),
    "success_rate": f"{(_config_package_metadata['imports_successful'] / _config_package_metadata['imports_attempted'] * 100):.1f}%" if _config_package_metadata['imports_attempted'] > 0 else "0%",
    "total_errors": len(_config_import_errors),
    "total_warnings": len(_config_import_warnings)
})

# Log configuration package loading if possible
try:
    # Try to import log_event from core package
    from ..core.logger import log_event, TreeLogger
    
    # Create comprehensive status report
    config_status = {
        "import_time_ms": _config_package_metadata["total_import_time_ms"],
        "success_rate": _config_package_metadata["success_rate"],
        "env_file": "✅ Found" if _config_package_metadata["env_file_exists"] else "❌ Missing",
        "env_file_size": f"{_config_package_metadata['env_file_size']} bytes" if _config_package_metadata["env_file_exists"] else "N/A",
        "main_config": _config_components.get("main_config", {}).get("status", "Unknown"),
        "enums": _config_components.get("enums", {}).get("status", "Unknown"),
        "config_instance": _config_components.get("config_instance", {}).get("status", "Unknown"),
        "critical_validation": _config_components.get("critical_validation", {}).get("status", "Unknown")
    }
    
    # Add environment-specific information if config loaded
    if "config_instance" in _config_components and _config_components["config_instance"]["status"] == "✅ Loaded successfully":
        config_status.update({
            "environment": _config_components["config_instance"]["environment"],
            "log_level": _config_components["config_instance"]["log_level"],
            "guild_configured": "✅ Yes" if _config_components["config_instance"]["guild_configured"] else "❌ No",
            "audio_folder": "✅ Exists" if _config_components["config_instance"]["audio_folder_exists"] else "❌ Missing",
            "ffmpeg": "✅ Available" if _config_components["config_instance"]["ffmpeg_available"] else "❌ Missing"
        })
    
    TreeLogger.info("⚙️ Configuration Package Loaded", config_status, service="Config")
    
    # Log configuration errors if any
    if _config_import_errors:
        log_event(
            "ERROR",
            "❌ Configuration Errors",
            {f"error_{i+1}": error for i, error in enumerate(_config_import_errors)}
        )
    
    # Log configuration warnings if any
    if _config_import_warnings:
        log_event(
            "WARNING",
            "⚠️ Configuration Warnings",
            {f"warning_{i+1}": warning for i, warning in enumerate(_config_import_warnings)}
        )
        
except ImportError:
    # Fallback to stderr if TreeLogger not available during early startup
    import sys
    sys.stderr.write(f"Configuration package loaded in {_config_package_metadata['total_import_time_ms']}ms\n")
    if _config_import_errors:
        sys.stderr.write(f"Configuration errors: {len(_config_import_errors)}\n")
        for error in _config_import_errors:
            sys.stderr.write(f"  - {error}\n")
    sys.stderr.flush()

# Export successful imports only
__all__ = []
_exported_config_components = {}

if "main_config" in _config_components and _config_components["main_config"]["status"] == "✅ Success":
    config_exports = [
        'QuranBotConfig', 
        'get_config', 
        'reload_config',
        'get_config_metadata',
        'validate_critical_config',
        'validate_configuration_with_logging'
    ]
    __all__.extend(config_exports)
    
    for export_name in config_exports:
        _exported_config_components[export_name] = _config_components["main_config"][export_name]

if "enums" in _config_components and _config_components["enums"]["status"] == "✅ Success":
    enum_exports = ['ReciterName', 'Environment', 'LogLevel']
    __all__.extend(enum_exports)
    
    for export_name in enum_exports:
        _exported_config_components[export_name] = _config_components["enums"][export_name]

# Make components available at module level
globals().update(_exported_config_components)

# Configuration package validation function
def validate_config_package() -> Dict[str, Any]:
    """
    Validate configuration package and return comprehensive status.
    
    Returns:
        Dict containing validation results and component status
    """
    validation_results = {
        "package_valid": len(_config_import_errors) == 0,
        "import_metadata": _config_package_metadata.copy(),
        "component_status": {name: comp.get("status", "Unknown") for name, comp in _config_components.items()},
        "available_exports": __all__.copy(),
        "import_errors": _config_import_errors.copy(),
        "import_warnings": _config_import_warnings.copy(),
        "validation_timestamp": datetime.now(APP_TIMEZONE).isoformat()
    }
    
    # Test configuration functionality if available
    if "get_config" in _exported_config_components:
        try:
            test_config = _exported_config_components["get_config"]()
            validation_results["config_functional"] = "✅ Functional"
            validation_results["config_environment"] = test_config.environment.value
            validation_results["config_ready"] = test_config.discord_token is not None
        except Exception as e:
            validation_results["config_functional"] = f"❌ Error: {e}"
    
    # Test enum functionality if available
    if "ReciterName" in _exported_config_components:
        try:
            reciter_enum = _exported_config_components["ReciterName"]
            validation_results["enum_functional"] = "✅ Functional"
            validation_results["available_reciters"] = len(list(reciter_enum))
        except Exception as e:
            validation_results["enum_functional"] = f"❌ Error: {e}"
    
    return validation_results

def get_config_package_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the configuration package.
    
    Returns:
        Dict containing package information and statistics
    """
    return {
        "package_info": {
            "name": "app.config",
            "description": "Configuration management for QuranBot",
            "version": "2.0.0",
            "components": len(_config_components),
            "exports": len(__all__)
        },
        "import_performance": {
            "total_time_ms": _config_package_metadata["total_import_time_ms"],
            "success_rate": _config_package_metadata["success_rate"],
            "env_file_processed": _config_package_metadata["env_file_exists"]
        },
        "component_details": _config_components.copy(),
        "health_status": "healthy" if len(_config_import_errors) == 0 else "degraded",
        "configuration_status": _config_components.get("config_instance", {}).get("status", "Unknown"),
        "last_import": _config_package_metadata["import_end"]
    }

# Add metadata to module for external access
__package_metadata__ = _config_package_metadata
__package_components__ = _config_components
__package_errors__ = _config_import_errors
__package_warnings__ = _config_import_warnings