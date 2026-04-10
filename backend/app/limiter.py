"""
Shared rate-limiter instance.

Instantiated here (not in main.py) so routers can import it without creating
a circular dependency through the main application module.

The limiter is wired to the FastAPI app in main.py via:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATELIMIT_ENABLED,
)
