"""
Secure credential storage.

Uses the OS system keyring (Windows Credential Manager, macOS Keychain,
libsecret on Linux) when available.  Falls back to plain-text
~/.webresearch/config.env when keyring is not installed or raises an error
(e.g. headless server, CI environment).

Priority for reads:  keyring  >  environment variable  >  None
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_SERVICE = "webresearch-agent"

try:
    import keyring as _keyring
    import keyring.errors as _keyring_errors
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False


def keyring_available() -> bool:
    return _KEYRING_AVAILABLE


def set_credential(key: str, value: str) -> bool:
    """
    Store a credential in the system keyring.
    Returns True on success, False if keyring is unavailable or fails.
    """
    if not _KEYRING_AVAILABLE:
        return False
    try:
        _keyring.set_password(_SERVICE, key, value)
        return True
    except Exception as exc:
        logger.warning("keyring: could not store %s: %s", key, exc)
        return False


def get_credential(key: str) -> Optional[str]:
    """
    Retrieve a credential.

    Priority: keyring  >  environment variable.
    Returns None if the credential is not found anywhere.
    """
    if _KEYRING_AVAILABLE:
        try:
            val = _keyring.get_password(_SERVICE, key)
            if val:
                return val
        except Exception as exc:
            logger.warning("keyring: could not read %s: %s", key, exc)
    return os.getenv(key)


def delete_credential(key: str) -> bool:
    """Delete a stored credential from the keyring. Returns True on success."""
    if not _KEYRING_AVAILABLE:
        return False
    try:
        _keyring.delete_password(_SERVICE, key)
        return True
    except Exception:
        return False


# Ordered list of all credentials the agent uses.
# Required keys must be provided; optional ones activate fallback providers.
REQUIRED_CREDENTIALS = ("GEMINI_API_KEY", "SERPER_API_KEY")
OPTIONAL_CREDENTIALS = ("GROQ_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL")
ALL_CREDENTIALS = REQUIRED_CREDENTIALS + OPTIONAL_CREDENTIALS
