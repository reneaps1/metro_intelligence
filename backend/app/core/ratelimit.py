"""F4.2 (MI-22): shared slowapi rate limiter instance.

Imported by both ``app.main`` (where it is registered on ``app.state.limiter``
and wired to the 429 handler) and the auth router (which decorates ``/auth/*``
endpoints). One instance is required so limits are enforced consistently
regardless of which app mounts the router.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
