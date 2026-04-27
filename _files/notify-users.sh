#!/usr/bin/env bash
# notify-users.sh — send a desktop notification to all currently logged-in users.
#
# Usage: notify-users.sh <title> <message> [urgency]
#   urgency: low | normal | critical  (default: normal)
#
# Requires: libnotify (notify-send), loginctl
# Called by: notenix-autoupdate.service

set -euo pipefail

TITLE="${1:-System}"
MESSAGE="${2:-Update complete.}"
URGENCY="${3:-normal}"

NOTIFY_SEND="$(command -v notify-send 2>/dev/null || echo "")"
if [ -z "$NOTIFY_SEND" ]; then
  echo "notify-users: notify-send not found, skipping notification." >&2
  exit 0
fi

# Walk every active user session
while IFS= read -r uid_path; do
  uid=$(basename "$uid_path")
  user=$(id -nu "$uid" 2>/dev/null || true)
  [ -z "$user" ] && continue

  bus="unix:path=/run/user/$uid/bus"
  [ -S "/run/user/$uid/bus" ] || continue

  echo "notify-users: notifying $user (uid=$uid)"
  DBUS_SESSION_BUS_ADDRESS="$bus" \
    DISPLAY=":0" \
    runuser -u "$user" -- \
    "$NOTIFY_SEND" \
      --app-name="notenix" \
      --urgency="$URGENCY" \
      "$TITLE" "$MESSAGE" 2>/dev/null || true
done < <(find /run/user -maxdepth 1 -mindepth 1 -type d -name '[0-9]*' 2>/dev/null)
