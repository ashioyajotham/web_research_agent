"""Pytest configuration — ensures the project root is on sys.path."""
import os
import sys

# Add project root so `webresearch` is importable without installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
