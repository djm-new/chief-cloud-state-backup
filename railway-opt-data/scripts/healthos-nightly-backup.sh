#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://healthos-production-beab.up.railway.app"
BACKUP_USERNAME="dj"
BACKUP_PASSWORD="${HEALTHOS_BACKUP_PASSWORD:-GupqN2VVsPN/IOwieQ6fLiOl}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

login_json=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
  -H 'content-type: application/json' \
  --data "$(printf '{"username":"%s","password":"%s"}' "$BACKUP_USERNAME" "$BACKUP_PASSWORD")" \
  -c "$COOKIE_JAR")

if [[ "$login_json" != *'"ok":true'* ]]; then
  echo "HealthOS nightly backup failed: login did not return ok=true"
  exit 1
fi

backup_json=$(curl -fsS -X POST "$BASE_URL/api/backup" -b "$COOKIE_JAR")

if [[ "$backup_json" != *'"ok":true'* ]]; then
  echo "HealthOS nightly backup failed: $backup_json"
  exit 1
fi

# Success: stay silent so Telegram is not spammed nightly.
