#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/djm-new/chief-cloud-state-backup.git"
REPO_DIR="/opt/data/github/chief-cloud-state-backup"
SNAPSHOT_DIR="$REPO_DIR/railway-opt-data"
BRANCH="main"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "Chief cloud-state GitHub sync skipped: GITHUB_TOKEN is not set in Railway variables."
  exit 0
fi

auth_url="https://x-access-token:${GITHUB_TOKEN}@github.com/djm-new/chief-cloud-state-backup.git"
mkdir -p /opt/data/github

if [ ! -d "$REPO_DIR/.git" ]; then
  rm -rf "$REPO_DIR"
  git clone "$auth_url" "$REPO_DIR" >/dev/null 2>&1
fi

cd "$REPO_DIR"
git config user.name "Railway Chief"
git config user.email "djm-new@users.noreply.github.com"
git remote set-url origin "$auth_url"

git fetch origin "$BRANCH" >/dev/null 2>&1 || true
git checkout "$BRANCH" >/dev/null 2>&1 || git checkout -b "$BRANCH" >/dev/null 2>&1
git pull --ff-only origin "$BRANCH" >/dev/null 2>&1 || true

rm -rf "$SNAPSHOT_DIR"
mkdir -p "$SNAPSHOT_DIR"

cat > "$SNAPSHOT_DIR/BACKUP_POLICY.md" <<'POLICY'
# Railway `/opt/data` backup policy

This folder is a selective snapshot from Railway Chief's persistent `/opt/data` volume.

It intentionally includes runtime state that is useful for restoring Chief:

- cron job definitions
- sync/maintenance scripts
- curated memory markdown files
- installed/learned skills
- `SOUL.md` if present

It intentionally excludes secrets and raw private history:

- `.env`
- `auth.json`
- OAuth/token JSON files
- Google credential/token JSON files
- SQLite state databases
- `sessions/`
- `logs/`
- cache files
- platform pairing files

Do not replace this selective sync with a blind copy of all `/opt/data`.
POLICY

copy_file() {
  local src="$1"
  local dest="$2"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
  fi
}

copy_dir_filtered() {
  local src="$1"
  local dest="$2"
  if [ -d "$src" ]; then
    mkdir -p "$dest"
    (cd "$src" && tar \
      --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='*.pyo' \
      --exclude='*.log' \
      --exclude='*.db' \
      --exclude='*.db-*' \
      --exclude='.env' \
      --exclude='auth.json' \
      --exclude='google_token.json' \
      --exclude='google_client_secret.json' \
      --exclude='google_accounts/*.json' \
      -cf - .) | (cd "$dest" && tar -xf -)
  fi
}

copy_file /opt/data/SOUL.md "$SNAPSHOT_DIR/SOUL.md"
copy_file /opt/data/cron/jobs.json "$SNAPSHOT_DIR/cron/jobs.json"
copy_dir_filtered /opt/data/scripts "$SNAPSHOT_DIR/scripts"
copy_dir_filtered /opt/data/memories "$SNAPSHOT_DIR/memories"
copy_dir_filtered /opt/data/skills "$SNAPSHOT_DIR/skills"
copy_dir_filtered /opt/data/health "$SNAPSHOT_DIR/health"

# Preserve empty allowlisted directories like memories/ before committing.
find "$SNAPSHOT_DIR" -type d -empty -exec touch {}/.gitkeep \;

# Remove any sensitive filenames if they slipped through nested folders.
find "$SNAPSHOT_DIR" -type f \( \
  -name '.env' -o \
  -name 'auth.json' -o \
  -name 'google_token.json' -o \
  -name 'google_client_secret.json' -o \
  -name '*.db' -o \
  -name '*.db-shm' -o \
  -name '*.db-wal' -o \
  -name '*.log' \
\) -delete

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "chore: Railway Chief cloud-state snapshot $(date +%Y-%m-%d)" >/dev/null
  git push origin "$BRANCH" >/dev/null 2>&1
  echo "Chief cloud-state GitHub sync pushed commit $(git rev-parse --short HEAD)."
fi
