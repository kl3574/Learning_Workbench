"""Explicit local runtime configuration (PRODUCT_DESIGN sections 14 and 20.4)."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def default_data_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "learning-workbench"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=default_data_dir)
    host: str = "127.0.0.1"
    port: int = 8765
    ui_origin: str | None = None
    migrations_dir: Path = REPOSITORY_ROOT / "migrations"
    static_dir: Path = REPOSITORY_ROOT / "apps/web/dist"
    session_seconds: int = 43200
    bootstrap_seconds: int = 120
    max_request_bytes: int = 2_097_152

    def __post_init__(self) -> None:
        if self.host not in {"127.0.0.1", "::1"}:
            raise ValueError("Public deployment is not supported; use a loopback bind address.")
        if not 1 <= self.port <= 65535:
            raise ValueError("Invalid local port.")
        if self.data_dir.resolve().is_relative_to(REPOSITORY_ROOT):
            raise ValueError("Application data must be outside the source repository.")
        if self.ui_origin:
            parsed = urlsplit(self.ui_origin)
            if (
                parsed.scheme != "http"
                or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.port is None
            ):
                raise ValueError("Development UI must use an explicit loopback HTTP origin.")

    @property
    def origin(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    @property
    def allowed_origins(self) -> frozenset[str]:
        return frozenset(origin for origin in (self.origin, self.ui_origin) if origin)

    @property
    def allowed_hosts(self) -> frozenset[str]:
        return frozenset(urlsplit(origin).netloc for origin in self.allowed_origins)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.environ.get("LEARNING_DATA_DIR", default_data_dir())),
            host=os.environ.get("LEARNING_HOST", "127.0.0.1"),
            port=int(os.environ.get("LEARNING_PORT", "8765")),
            ui_origin=os.environ.get("LEARNING_UI_ORIGIN") or None,
        )
