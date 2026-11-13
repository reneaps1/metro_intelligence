"""Opt-in: run the line bundle load next to the API (ADR-004).

For a deployment whose only compute is the API service. When both
``LINE_BUNDLE_RUN_IN_API`` is true and ``LINE_BUNDLE_URL`` is set, the API
starts ``python -m app.cli.load_line_bundle`` once at startup as a separate
process: requests keep being served while it runs, and its output goes to the
service log. The command holds a database advisory lock, so overlapping
instances during a deploy never load twice, and it exits at once when the
bundle is already loaded. Started from the API it waits up to 30 minutes
for the lock, which an instance being replaced by a deploy may still hold.
Unset ``LINE_BUNDLE_RUN_IN_API`` once the load is done.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes"}
LOCK_WAIT_SECONDS = 1800


def start_if_configured() -> subprocess.Popen[bytes] | None:
    """Start the load process when opted in; return it, or None."""
    if os.getenv("LINE_BUNDLE_RUN_IN_API", "").strip().lower() not in TRUE_VALUES:
        return None
    if not os.getenv("LINE_BUNDLE_URL", "").strip():
        logger.warning("LINE_BUNDLE_RUN_IN_API is set but LINE_BUNDLE_URL is not; not starting the load.")
        return None
    # The instance being replaced may still hold the load lock: wait for it.
    env = {**os.environ}
    env.setdefault("LINE_BUNDLE_LOCK_WAIT_SECONDS", str(LOCK_WAIT_SECONDS))
    env["PYTHONUNBUFFERED"] = "1"  # progress reaches the service log as it happens
    process = subprocess.Popen([sys.executable, "-m", "app.cli.load_line_bundle"], env=env)  # noqa: S603
    # Reap the child when it exits so it never lingers as a zombie.
    threading.Thread(target=process.wait, name="line-bundle-load", daemon=True).start()
    logger.info("Started the line bundle load (pid %s).", process.pid)
    return process
