"""Environment variable loader for OpenMontage.

Loads .env file and provides typed access to environment configuration.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def load_env(project_root: Optional[Path] = None) -> None:
    """Load .env file from project root."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable with optional default."""
    return os.environ.get(key, default)


def require_env(key: str) -> str:
    """Get a required environment variable. Raises if missing."""
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError(f"Required environment variable {key!r} is not set")
    return value


def env_present(key: str) -> bool:
    """True iff `key` is set to a REAL value — non-empty and not a leftover
    inline `.env` comment.

    Defense-in-depth companion to the loader fix in tools/base_tool.py: a key
    whose value is empty/whitespace, or is purely an inline comment
    (e.g. `KIE_API_KEY=   # get one at ...`), is treated as NOT present so
    availability checks don't false-positive on the unfilled .env template.
    """
    value = os.environ.get(key)
    if value is None:
        return False
    value = value.strip()
    if not value or value.startswith("#"):
        return False
    return True
