#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://healthos-production-beab.up.railway.app"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

login_json=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
  -H 'content-type: application/json' \
  --data '{"username":"dj","password":"GupqN2VVsPN/IOwieQ6fLiOl"}' \
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
