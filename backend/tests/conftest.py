"""Test configuration and shared fixtures."""
import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def load_fixture(filename: str) -> str:
    """Load a test fixture file as a string."""
    with open(os.path.join(FIXTURES_DIR, filename), 'r', encoding='utf-8') as f:
        return f.read()


def load_fixture_bytes(filename: str) -> bytes:
    """Load a test fixture file as bytes."""
    with open(os.path.join(FIXTURES_DIR, filename), 'rb') as f:
        return f.read()
