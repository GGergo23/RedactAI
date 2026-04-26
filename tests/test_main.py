"""
Basic sanity tests for the RedactAI application.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main


def test_main_exists():
    """Test that the main function exists and is callable."""
    assert callable(main)


def test_main_returns_int():
    """Test that main() can be called and returns an int (or can be converted to int)."""
    # We can't actually call it in a test (it creates a GUI window),
    # but we can verify the function signature
    import inspect
    sig = inspect.signature(main)
    assert sig.return_annotation == int or str(sig.return_annotation) == "<class 'int'>"