from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Look for .env in the project root (two levels up from this file) AND the CWD,
# so the app works whether you run `uvicorn` from backend/ or via docker-compose.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


# Default local-dev Postgres URLs (used by docker-compose). Local SQLite is
# typically provided by the tests via env overrides; in production both URLs
# are derived from a single DATABASE_URL env var (Supabase-style).
_DEFAULT_ASYNC_URL = "postgresql+asyncpg://smartstore:smartstore@postgres:5432/smartstore"
_DEFAULT_SYNC_URL = "postgresql+psycopg2://smartstore:smartstore@postgres:5432/smartstore"


def _is_postgres(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql")


def _strip_driver(url: str) -> str:
    """Return the URL with any SQLAlchemy +driver suffix stripped from the scheme."""
    scheme, rest = url.split("://", 1)
    base_scheme = scheme.split("+", 1)[0]
    # Normalize postgres:// -> postgresql:// (Render/Heroku style)
    if base_scheme == "postgres":
        base_scheme = "postgresql"
    return f"{base_scheme}://{rest}"


def _set_query_param(url: str, key: str, value: str, *, remove_keys: tuple[str, ...] = ()) -> str:
    """Return url with `key=value` set in the query string. Drops any keys in remove_keys."""
    parts = urlsplit(url)
    pairs = [(k, v) for (k, v) in parse_qsl(parts.query, keep_blank_values=True)
             if k != key and k not in remove_keys]
    pairs.append((key, value))
    new_query = urlencode(pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def _to_async_postgres_url(plain_url: str) -> str:
    """Convert a plain postgresql:// URL to postgresql+asyncpg:// with ssl=require.

    asyncpg uses `ssl=require` (not `sslmode=require`). Also drops `sslmode`
    if present, since asyncpg doesn't understand it.
    """
    base = _strip_driver(plain_url)  # postgresql://...
    # Swap scheme to postgresql+asyncpg
    parts = urlsplit(base)
    async_scheme = "postgresql+asyncpg"
    base = urlunsplit((async_scheme, parts.netloc, parts.path, parts.query, parts.fragment))
    # Only attach SSL for real hosts (not the docker-compose 'postgres' host).
    host = urlsplit(base).hostname or ""
    if host and host not in ("postgres", "localhost", "127.0.0.1"):
        base = _set_query_param(base, "ssl", "require", remove_keys=("sslmode",))
    return base


def _to_sync_postgres_url(plain_url: str) -> str:
    """Convert a plain postgresql:// URL to postgresql+psycopg2:// with sslmode=require."""
    base = _strip_driver(plain_url)
    parts = urlsplit(base)
    sync_scheme = "postgresql+psycopg2"
    base = urlunsplit((sync_scheme, parts.netloc, parts.path, parts.query, parts.fragment))
    host = urlsplit(base).hostname or ""
    if host and host not in ("postgres", "localhost", "127.0.0.1"):
        # psycopg2 wants sslmode=require, not ssl=require.
        base = _set_query_param(base, "sslmode", "require", remove_keys=("ssl",))
    return base


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(_REPO_ROOT_ENV), ".env"), extra="ignore")

    # These can be set directly (backward compatible) OR auto-derived from a
    # single plain `DATABASE_URL` env var via the model_validator below.
    DATABASE_URL: str = _DEFAULT_ASYNC_URL
    SYNC_DATABASE_URL: str = _DEFAULT_SYNC_URL

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 7

    FRONTEND_ORIGIN: str = "http://localhost:5173"

    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"
    GEMINI_VISION_MODEL: str = "gemini-2.0-flash"

    UPLOAD_DIR: str = "/app/uploads"

    SEED_TENANT_NAME: str = "Raj Grocery"
    SEED_ADMIN_EMAIL: str = "admin@smartstore.app"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_STAFF_EMAIL: str = "staff@smartstore.app"
    SEED_STAFF_PASSWORD: str = "staff123"

    @model_validator(mode="after")
    def _derive_db_urls(self) -> "Settings":
        """If DATABASE_URL is a plain postgres URL (Supabase / Render / Heroku style),
        auto-derive the asyncpg + psycopg2 variants. If SYNC_DATABASE_URL was left at
        its default while DATABASE_URL was customized, fill SYNC_DATABASE_URL too.

        Behavior:
          - If DATABASE_URL is already `postgresql+asyncpg://...`, leave it alone.
          - If DATABASE_URL is plain `postgresql://...` or `postgres://...`, rewrite
            it to the asyncpg variant (and add `ssl=require` for remote hosts).
          - If SYNC_DATABASE_URL is still the default OR points at the same DB as
            DATABASE_URL (driver-stripped match), derive a psycopg2 variant from
            DATABASE_URL with `sslmode=require` for remote hosts.
          - Non-postgres URLs (e.g. sqlite+aiosqlite for tests) are untouched.
        """
        db_url = self.DATABASE_URL
        sync_url = self.SYNC_DATABASE_URL

        if not _is_postgres(db_url):
            # sqlite / other dialects: leave both as-is.
            return self

        # Normalize the async URL.
        if "+asyncpg" not in db_url.split("://", 1)[0]:
            # plain postgres:// or postgresql:// (no driver) -> add asyncpg driver.
            self.DATABASE_URL = _to_async_postgres_url(db_url)

        # Decide whether to override SYNC_DATABASE_URL. Override if:
        #   (a) it's still the hardcoded local default, OR
        #   (b) it points at the same host/db as DATABASE_URL (i.e. user only set
        #       DATABASE_URL and SYNC was implicitly the default).
        should_override_sync = (
            sync_url == _DEFAULT_SYNC_URL
            or _strip_driver(sync_url) == _strip_driver(db_url)
        )
        if should_override_sync:
            self.SYNC_DATABASE_URL = _to_sync_postgres_url(db_url)
        elif _is_postgres(sync_url) and "+psycopg2" not in sync_url.split("://", 1)[0]:
            # User supplied a plain SYNC_DATABASE_URL: add psycopg2 driver + sslmode.
            self.SYNC_DATABASE_URL = _to_sync_postgres_url(sync_url)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
