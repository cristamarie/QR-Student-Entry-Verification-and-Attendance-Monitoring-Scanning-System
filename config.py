"""
config.py
=========
Single place where the whole system reads its settings.

Values come from environment variables, Streamlit secrets, or the ".env" file
(see ".env.example"). Environment variables take precedence, followed by
Streamlit secrets, then defaults. Nothing else in the project should read
configuration directly - they all import `settings` from here.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from datetime import time
from urllib.parse import quote

import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

# Load the .env file that sits next to this file.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

_URLSAFE_BASE64_RE = re.compile(r"[A-Za-z0-9_-]+")
_MIN_SECRET_KEY_BYTES = 32


def _is_secure_secret_key(secret_key: str) -> bool:
    """Require a canonical URL-safe base64 key with at least 256 bits."""
    if not secret_key or not _URLSAFE_BASE64_RE.fullmatch(secret_key):
        return False
    try:
        key_bytes = base64.b64decode(
            secret_key + "=" * (-len(secret_key) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, UnicodeEncodeError):
        return False
    return (
        len(key_bytes) >= _MIN_SECRET_KEY_BYTES
        and base64.urlsafe_b64encode(key_bytes).decode("ascii").rstrip("=") == secret_key
    )


def _to_time(raw: str, default: str) -> time:
    """Turn "08:00" into a real datetime.time object. Falls back to a default."""
    text = (raw or default).strip()
    try:
        hour, minute = text.split(":")[:2]
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, AttributeError):
        hour, minute = default.split(":")
        return time(hour=int(hour), minute=int(minute))


def _config_value(name: str, default: str) -> str:
    """Read a setting from the environment, then Streamlit secrets, then default."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        value = st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default
    return str(value) if value is not None else default


@dataclass(frozen=True)
class Settings:
    """Every setting the system needs, already converted to the right type."""

    # --- Database ---
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "student_system"
    db_user: str = "postgres"
    db_password: str = ""

    # --- Application ---
    secret_key: str = ""
    school_name: str = "Student Attendance System"
    school_year: str = "2026-2027"

    # --- Attendance rules ---
    late_cutoff: time = field(default_factory=lambda: time(8, 0))
    day_start: time = field(default_factory=lambda: time(6, 0))
    scan_cooldown_seconds: int = 60
    kiosk_online_seconds: int = 120

    # ------------------------------------------------------------------
    @property
    def database_url(self) -> str:
        """The connection string SQLAlchemy uses to reach PostgreSQL."""
        user = quote(self.db_user)
        password = quote(self.db_password)
        db_name = quote(self.db_name)
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{db_name}"
        )

    @property
    def is_secret_key_set(self) -> bool:
        """Return whether the signing key meets the minimum strength and format."""
        return _is_secure_secret_key(self.secret_key)


def load_settings() -> Settings:
    """Read configuration from environment variables, Streamlit secrets, and defaults."""
    loaded_settings = Settings(
        db_host=_config_value("DB_HOST", "localhost"),
        db_port=_config_value("DB_PORT", "5432"),
        db_name=_config_value("DB_NAME", "student_system"),
        db_user=_config_value("DB_USER", "postgres"),
        db_password=_config_value("DB_PASSWORD", ""),
        secret_key=_config_value("SECRET_KEY", "").strip(),
        school_name=_config_value("SCHOOL_NAME", "Student Attendance System"),
        school_year=_config_value("SCHOOL_YEAR", "2026-2027"),
        late_cutoff=_to_time(_config_value("LATE_CUTOFF", "08:00"), "08:00"),
        day_start=_to_time(_config_value("DAY_START", "06:00"), "06:00"),
        scan_cooldown_seconds=int(_config_value("SCAN_COOLDOWN_SECONDS", "60")),
        kiosk_online_seconds=int(_config_value("KIOSK_ONLINE_SECONDS", "120")),
    )
    if not loaded_settings.is_secret_key_set:
        raise RuntimeError(
            "SECRET_KEY must be set to a URL-safe random value containing at least 32 bytes. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    return loaded_settings


# Import this object everywhere:  from config import settings
settings = load_settings()
