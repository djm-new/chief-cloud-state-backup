#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/djm-new/chief-cloud-state-backup.git"
REPO_DIR="/opt/data/github/chief-cloud-state-backup"
SNAPSHOT_DIR="$REPO_DIR/railway-opt-data"
BRANCH="main"

if [ -z "${GITHUB_TOKEN:-}" ]; then
echo "Cronjob Response: Daily Chief cloud-state GitHub backup sync not successful: GITHUB_TOKEN is not set in Railway variables."
exit 0
fi

auth_url="https://x-access-token:${GITHUB_TOKEN}@github.com/djm-new/chief-cloud-state-backup.git"
mkdir -p /opt/data/github

if [ ! -d "$REPO_DIR/.git" ]; then
rm -rf "$REPO_DIR"
if ! git clone "$auth_url" "$REPO_DIR" >/dev/null 2>&1; then
echo "Cronjob Response: Daily Chief cloud-state GitHub backup sync not successful: unable to clone from GitHub (check GITHUB_TOKEN and repo access)."
exit 1
fi
fi

cd "$REPO_DIR"
git config user.name "Railway Chief"
git config user.email "djm-new@users.noreply.github.com"
git remote set-url origin "$auth_url"

git fetch origin "$BRANCH" >/dev/null 2>&1 || true
git checkout "$BRANCH" >/dev/null 2>&1 || git checkout -b "$BRANCH" >/dev/null 2>&1
git pull --ff-only origin "$BRANCH" >/dev/null 2>&1 || true
git reset --hard "origin/$BRANCH" >/dev/null 2>&1 || true
git clean -fdx >/dev/null 2>&1 || true

rm -rf "$SNAPSHOT_DIR"
mkdir -p "$SNAPSHOT_DIR"

cat > "$SNAPSHOT_DIR/BACKUP_POLICY.md" <<'POLICY'
# Railway `/opt/data` backup policy

This folder is a selective snapshot from Railway Chief's persistent state and a few
critical app files used to run and explain the system.

It intentionally includes durable state that is useful for restoring or auditing Chief:

- cron job definitions
- sync/maintenance scripts
- curated memory markdown files
- installed/learned skills
- `SOUL.md` if present
- core Hermes config and routing notes
- podcast workflow configs and generated digest artifacts
- selected Hermes gateway source files that carry live behavior
- the local-first thoughts repo corpus (daily/weekly/monthly/quarterly notes)

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
--exclude='*.sqlite' \
--exclude='*.sqlite-*' \
--exclude='*.mp3' \
--exclude='*.m4a' \
--exclude='*.wav' \
--exclude='*.flac' \
--exclude='*.aac' \
--exclude='*.ogg' \
--exclude='*.mp4' \
--exclude='.env' \
--exclude='auth.json' \
--exclude='google_token.json' \
--exclude='google_client_secret.json' \
--exclude='google_accounts/*.json' \
-cf - .) | (cd "$dest" && tar -xf -)
fi
}

# Generate redacted session transcripts inside the thoughts repo before snapshotting.
python3 /opt/data/scripts/export_redacted_sessions.py >/dev/null

copy_file /opt/data/SOUL.md "$SNAPSHOT_DIR/SOUL.md"
copy_file /opt/data/cron/jobs.json "$SNAPSHOT_DIR/cron/jobs.json"
copy_file /opt/data/config.yaml "$SNAPSHOT_DIR/config.yaml"
copy_file /opt/data/model-routing-register.md "$SNAPSHOT_DIR/model-routing-register.md"
copy_dir_filtered /opt/data/scripts "$SNAPSHOT_DIR/scripts"
copy_dir_filtered /opt/data/memories "$SNAPSHOT_DIR/memories"
copy_dir_filtered /opt/data/skills "$SNAPSHOT_DIR/skills"
copy_dir_filtered /opt/data/health "$SNAPSHOT_DIR/health"
copy_dir_filtered /opt/data/podcast_digest "$SNAPSHOT_DIR/podcast_digest"
copy_dir_filtered /opt/hermes/gateway "$SNAPSHOT_DIR/hermes/gateway"
copy_dir_filtered /opt/data/thoughts-repo "$SNAPSHOT_DIR/thoughts-repo"

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
-name '*.sqlite' -o \
-name '*.sqlite-shm' -o \
-name '*.sqlite-wal' -o \
-name '*.log' \
\) -delete

if [ -n "$(git status --porcelain)" ]; then
git add -A
git commit -m "chore: Railway Chief cloud-state snapshot $(date +%Y-%m-%d)" >/dev/null
push_err_file="$(mktemp)"
push_ok=0
for attempt in 1 2 3; do
if git push origin "$BRANCH" >/dev/null 2>"$push_err_file"; then
push_ok=1
break
fi
sleep "$((attempt * 5))"
done
if [ "$push_ok" -ne 1 ]; then
echo "Cronjob Response: Daily Chief cloud-state GitHub backup sync not successful: git push to GitHub failed (check GITHUB_TOKEN and repo access)."
if [ -s "$push_err_file" ]; then
echo "Git stderr:"
sed -n '1,20p' "$push_err_file"
fi
rm -f "$push_err_file"
exit 1
fi
rm -f "$push_err_file"
echo "Cronjob Response: Daily Chief cloud-state GitHub backup sync successfully pushed."
fi



