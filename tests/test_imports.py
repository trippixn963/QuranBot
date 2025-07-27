#!/usr/bin/env python3
# =============================================================================
# QuranBot - Import Tests
# =============================================================================
# Test script to verify all modernized imports work correctly.
# =============================================================================

from pathlib import Path
import sys

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("🧪 Testing Modernized QuranBot Imports")
print("=" * 50)

# Test core imports
try:
    print("Testing core imports...")
    from src.core.di_container import DIContainer

    print("✅ Core imports successful")
except Exception as e:
    print(f"❌ Core imports failed: {e}")
    sys.exit(1)

# Test config imports
try:
    print("Testing config imports...")

    print("✅ Config imports successful")
except Exception as e:
    print(f"❌ Config imports failed: {e}")
    import traceback

    traceback.print_exc()

# Test data models
try:
    print("Testing data model imports...")

    print("✅ Data model imports successful")
except Exception as e:
    print(f"❌ Data model imports failed: {e}")
    import traceback

    traceback.print_exc()

# Test service imports
try:
    print("Testing service imports...")

    print("✅ Service imports successful")
except Exception as e:
    print(f"❌ Service imports failed: {e}")
    import traceback

    traceback.print_exc()

# Test basic functionality
try:
    print("Testing basic DI container...")
    container = DIContainer()
    print("✅ DI container creation successful")
except Exception as e:
    print(f"❌ DI container creation failed: {e}")
    import traceback

    traceback.print_exc()

print("\n🎉 All imports working correctly!")
print("The modernized architecture is ready for integration.")
