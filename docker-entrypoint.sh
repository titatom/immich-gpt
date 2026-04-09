#!/bin/sh
# =============================================================================
# Immich GPT — Docker entrypoint
#
# Ensures a persistent SECRET_KEY exists before starting the application.
# If SECRET_KEY is not supplied via environment, it is auto-generated on
# first boot and stored in /data/.secret_key so it survives container
# restarts and upgrades.
# =============================================================================

set -e

SECRET_KEY_FILE="/data/.secret_key"

# Only auto-generate when SECRET_KEY is missing, empty, or still the
# well-known placeholder that the app refuses to start with.
_is_weak_key() {
    case "$SECRET_KEY" in
        ""|"change-me-in-production"|"secret"|"changeme"|"insecure"|"dev")
            return 0 ;;
        *)
            return 1 ;;
    esac
}

if _is_weak_key; then
    if [ -f "$SECRET_KEY_FILE" ]; then
        # Re-use the key generated on first boot.
        SECRET_KEY="$(cat "$SECRET_KEY_FILE")"
        export SECRET_KEY
        echo "[entrypoint] Loaded persisted SECRET_KEY from $SECRET_KEY_FILE"
    else
        # First boot: generate a cryptographically strong key and persist it.
        SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
        export SECRET_KEY
        # /data must exist (mounted volume); write with restrictive permissions.
        mkdir -p /data
        printf '%s' "$SECRET_KEY" > "$SECRET_KEY_FILE"
        chmod 600 "$SECRET_KEY_FILE"
        echo "[entrypoint] Generated new SECRET_KEY and saved to $SECRET_KEY_FILE"
    fi
fi

exec "$@"
