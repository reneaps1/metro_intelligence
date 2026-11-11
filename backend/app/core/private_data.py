"""IQ-F21 (plan decisions D8, D15): may this process offer PRIVATE customer data at all?

Real customer datasets are converted offline into a private folder and are
meant for the presenter's own machine only. Pointing a variable at that folder
is not enough to serve them: every one of these must also hold, so a server
that inherits a copied ``.env`` stays closed (fail-closed):

1. ``APP_ENV`` is not ``production``;
2. every allowed browser origin (``CORS_ORIGINS``) is a loopback address, i.e.
   the UI is opened on this same machine;
3. no hosted-platform marker variable is present in the environment.

The hosted demo (a public SaaS) fails 2 and 3, so it can only ever show the
synthetic and fictitious datasets. Nothing here logs paths or values.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

from app.core.config import Settings, get_settings

# Variables that hosting platforms set on every service they run. Their mere
# presence means "this is not the presenter's machine". Values are not read.
HOSTED_PLATFORM_MARKERS: tuple[str, ...] = (
    "RENDER",
    "RENDER_SERVICE_ID",
    "FLY_APP_NAME",
    "K_SERVICE",
    "DYNO",
    "VERCEL",
    "RAILWAY_ENVIRONMENT",
    "WEBSITE_SITE_NAME",
)

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _origins(raw: str) -> list[str]:
    """CORS origins written either as a JSON list or comma separated (both appear in env files)."""
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except ValueError:
            return [text]
        return [str(o).strip() for o in parsed if str(o).strip()] if isinstance(parsed, list) else [text]
    return [o.strip() for o in text.split(",") if o.strip()]


def only_loopback_origins(raw: str) -> bool:
    """True when at least one origin is configured and every one of them is loopback."""
    origins = _origins(raw)
    if not origins:
        return False
    for origin in origins:
        try:
            host = urlsplit(origin).hostname
        except ValueError:
            return False
        if host is None or host.lower() not in LOOPBACK_HOSTS:
            return False
    return True


def hosted_platform_detected(environ: os._Environ[str] | dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return any(marker in env for marker in HOSTED_PLATFORM_MARKERS)


def private_data_allowed(settings: Settings | None = None) -> bool:
    """The three runtime barriers of D15. All must hold to offer any private dataset."""
    s = settings or get_settings()
    return (
        s.app_env != "production" and only_loopback_origins(s.cors_origins) and not hosted_platform_detected()
    )
