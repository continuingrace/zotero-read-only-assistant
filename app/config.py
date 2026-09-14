from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    """Raised when a security-sensitive configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    auth_token: str
    zotero_base_url: str = "http://127.0.0.1:23119/api/"
    bind_host: str = "127.0.0.1"
    port: int = 8787
    max_request_bytes: int = 262_144
    max_results: int = 100
    rate_limit_per_minute: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BRIDGE_AUTH_TOKEN", "")
        if len(token) < 32:
            raise ConfigurationError(
                "BRIDGE_AUTH_TOKEN must contain at least 32 characters"
            )

        base_url = os.getenv("ZOTERO_BASE_URL", cls.zotero_base_url)
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ConfigurationError(
                "ZOTERO_BASE_URL must be an HTTP URL bound to localhost/loopback"
            )
        if not base_url.endswith("/"):
            base_url += "/"

        bind_host = os.getenv("BRIDGE_BIND_HOST", cls.bind_host)
        if bind_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ConfigurationError(
                "BRIDGE_BIND_HOST must remain on the loopback interface"
            )

        return cls(
            auth_token=token,
            zotero_base_url=base_url,
            bind_host=bind_host,
            port=_int_env("BRIDGE_PORT", cls.port, 1, 65535),
            max_request_bytes=_int_env(
                "BRIDGE_MAX_REQUEST_BYTES", cls.max_request_bytes, 4096, 1_048_576
            ),
            max_results=_int_env("BRIDGE_MAX_RESULTS", cls.max_results, 1, 100),
            rate_limit_per_minute=_int_env(
                "BRIDGE_RATE_LIMIT_PER_MINUTE", cls.rate_limit_per_minute, 1, 600
            ),
        )

    def token_matches(self, presented: str) -> bool:
        return secrets.compare_digest(self.auth_token, presented)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return parsed
