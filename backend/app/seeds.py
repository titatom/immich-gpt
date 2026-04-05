"""
Legacy global seed module.
In Phase 2, defaults are seeded per-user on account creation via user_service._seed_user_defaults().
This module is retained as a no-op to avoid import errors from existing code paths.
"""


def seed_defaults():
    """No-op in Phase 2. Per-user defaults are seeded in user_service.create_user()."""
    pass
