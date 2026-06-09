# Project Map

This file is the durable lookup table for Hermes when it needs to know which code repo, Railway service, live URL, and local path belong together.

Update this whenever a new project is added or a service/repo mapping changes.

## Format

- Project name
- Source of truth repo
- Railway project/service
- Live URL / health endpoint
- Local path
- Notes

## Current projects

### HealthOS
- Source repo: `djm-new/healthos`
- Railway project: `chief-cloud`
- Railway service: `healthos`
- Live URL: `https://healthos-production-beab.up.railway.app`
- Health endpoint: `https://healthos-production-beab.up.railway.app/api/health`
- Local path: `/opt/data/projects/healthos`
- Notes: GitHub pushes to `main` auto-deploy to Railway.

### Chief cloud state backup
- Source repo: `djm-new/chief-cloud-state-backup`
- Railway relation: runtime-state backup repo, not an app deploy target
- Local path: `/opt/data/github/chief-cloud-state-backup`
- Notes: stores durable Hermes/Chief runtime state, skills, scripts, and related backup material.

### Thoughts repo
- Source repo: private remote
- Local path: separate private thoughts repo
- Railway relation: not part of the HealthOS deploy path
- Notes: keep separate from runtime/state backup and app repos.
