#!/usr/bin/env python3
"""Create/private-link the thoughts repo on GitHub using GITHUB_TOKEN.

Usage:
  GITHUB_TOKEN=... ./scripts/setup_github_remote.py [repo-name]

The token needs `repo` scope. This script never prints the token.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPO_NAME = "hermes-thoughts"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_DIR, text=True, capture_output=True, check=check)


def gh_api(method: str, path: str, token: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    req = Request(
        f"https://api.github.com{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "HermesThoughtsSetup/1.0",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except HTTPError as e:
        detail = e.read().decode(errors="ignore")
        raise SystemExit(f"GitHub API error {e.code} for {method} {path}: {detail[:500]}") from e


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN with repo scope before running.")
    repo_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO_NAME
    user = gh_api("GET", "/user", token)
    owner = user["login"]

    # Create if absent, otherwise reuse.
    try:
        repo = gh_api("GET", f"/repos/{owner}/{repo_name}", token)
    except SystemExit as exc:
        if "GitHub API error 404" not in str(exc):
            raise
        repo = gh_api("POST", "/user/repos", token, {
            "name": repo_name,
            "description": "Private Hermes thought capture and synthesis corpus",
            "private": True,
            "has_issues": False,
            "has_projects": False,
            "has_wiki": False,
            "auto_init": False,
        })

    clone_url = repo["clone_url"]
    safe_push_url = clone_url.replace("https://", f"https://{owner}:<TOKEN>@")
    push_url = clone_url.replace("https://", f"https://{owner}:{token}@")

    existing = run(["git", "remote"], check=False).stdout.splitlines()
    if "origin" not in existing:
        run(["git", "remote", "add", "origin", clone_url])
    else:
        run(["git", "remote", "set-url", "origin", clone_url])
    run(["git", "remote", "set-url", "--push", "origin", push_url])

    branch = run(["git", "branch", "--show-current"], check=False).stdout.strip() or "master"
    run(["git", "push", "-u", "origin", f"{branch}:main"])
    print(f"Created/linked private GitHub repo: {repo['html_url']}")
    print(f"Push URL configured with token hidden: {safe_push_url}")


if __name__ == "__main__":
    main()
