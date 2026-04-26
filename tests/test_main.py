"""
Basic sanity tests for the RedactAI application.
"""

import inspect

from src.main import main


def test_main_exists():
    """Test that the main function exists and is callable."""
    assert callable(main)


def test_main_returns_int():
    """Test that main() returns int (verified via signature)."""
    # We can't actually call it in a test (it creates a GUI window),
    # but we can verify the function signature
    sig = inspect.signature(main)
    is_int = sig.return_annotation == int
    assert is_int or str(sig.return_annotation) == "<class 'int'>"
