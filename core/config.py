from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from core.errors import ConfigError

logger = logging.getLogger(__name__)

_REQUIRED_ENV = ["DISCORD_TOKEN", "DISCORD_APP_ID", "DATABASE_URL"]

_REQUIRED_CONFIG_KEYS = [
    "guild_id",
    "roles",
    "channels",
]


class Config:
    """YAML + .env configuration manager with hot-reload support."""

    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        self._config_path = Path(config_path)
        self._env_path = Path(env_path)
        self._data: dict[str, Any] = {}
        self._load_env()
        self.reload()

    def _load_env(self) -> None:
        load_dotenv(self._env_path)
        missing = [k for k in _REQUIRED_ENV if not os.getenv(k)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    def reload(self) -> None:
        """Reload config.yaml from disk and validate."""
        if not self._config_path.exists():
            raise ConfigError(f"Config file not found: {self._config_path}")

        with open(self._config_path, "r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ConfigError("config.yaml must be a YAML mapping")

        missing = [k for k in _REQUIRED_CONFIG_KEYS if k not in data]
        if missing:
            raise ConfigError(f"Missing required config keys: {', '.join(missing)}")

        self._data = data
        logger.info("Configuration loaded from %s", self._config_path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level config value."""
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError:
            raise ConfigError(f"Missing config key: {key}")

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def guild_id(self) -> int:
        return int(self._data["guild_id"])

    @property
    def token(self) -> str:
        return os.environ["DISCORD_TOKEN"]

    @property
    def app_id(self) -> int:
        return int(os.environ["DISCORD_APP_ID"])

    @property
    def database_url(self) -> str:
        return os.environ["DATABASE_URL"]

    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")

    @property
    def spotify_client_id(self) -> str | None:
        return os.getenv("SPOTIFY_CLIENT_ID")

    @property
    def spotify_client_secret(self) -> str | None:
        return os.getenv("SPOTIFY_CLIENT_SECRET")

    @property
    def roles(self) -> dict[str, int]:
        return self._data["roles"]

    @property
    def channels(self) -> dict[str, int]:
        return self._data["channels"]

    @property
    def xp(self) -> dict[str, Any]:
        return self._data.get("xp", {})

    @property
    def threading(self) -> dict[str, Any]:
        return self._data.get("threading", {})

    @property
    def features(self) -> dict[str, bool]:
        return self._data.get("features", {})

    @property
    def embeds(self) -> dict[str, Any]:
        return self._data.get("embeds", {})

    @property
    def rate_limits(self) -> dict[str, Any]:
        return self._data.get("rate_limits", {})
