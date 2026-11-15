# Changelog

## 2.4.0

This release adds support for running the container as a non-root user and fixes automatic update scheduling so
restarting the container no longer resets the update interval. It also updates Photon to 1.3.0 and replaces Task
with mise for local development commands.

### Features

- Support running the container as a non-root user by @rtuszik

### Changes

- Update Photon version to 1.3.0 by @rtuszik
- Migrate the development task runner from Task to mise by @rtuszik

### Fixes

- Base automatic updates on the age of the local index instead of container uptime by @aaronspruit in #303
- Retry checking for a newer index hourly once an update is due, without downloading unchanged data by @rtuszik

### Dependencies & CI

- Pin container image dependencies by @koalabot-rt[bot]
- Update Python, uv, uv_build, prek, BetterLeaks, and zizmor by @koalabot-rt[bot]
- Update GitHub Actions dependencies by @koalabot-rt[bot]
- Run workflows when entrypoint or GitHub Actions files change by @rtuszik
- Improve Renovate dependency grouping and local configuration by @rtuszik

## 2.3.1

This release adds reverse-geocoding-only JSONL imports, which reduce import time and disk usage when forward
geocoding is not needed. It also adds a notification when Photon starts successfully and updates Photon to 1.2.1.

### Features

- Add the `REVERSE_ONLY` option for reverse-geocoding-only JSONL imports by @rtuszik
- Send an Apprise notification when Photon starts successfully by @rtuszik

### Changes

- Update Photon version to 1.2.1 by @rtuszik

### Dependencies & CI

- Add `mise.toml` for consistent local tool versions and development tasks by @rtuszik
- Add deptry, betterleaks, and Renovate validation to development checks by @rtuszik
- Pin uv 0.11.28 consistently across the image and CI by @rtuszik
- Remove the unnecessary direct urllib3 dependency by @rtuszik
- Update Renovate configuration by @rtuszik

## 2.3.0

This release adds experimental **JSONL dump support**, letting you combine multiple regions/countries into a
single index instead of relying on prebuilt databases. It also bumps Photon to 1.2.0, and adds additional Apprise notifications for
download, update, and error events.

> ⚠️ **JSONL import does not support automatic updates.** The default `db` mode is unchanged and retains all existing functionality. In `jsonl` mode the index is built once
> at startup and is not updated automatically.

### Features

- Implement JSONL imports and add end-to-end tests by @rtuszik in #300, closes #122

### Changes

- Update Photon version to 1.2.0 by @rtuszik in #330
- feat: multi-stage build without uv runtime dependency by @rtuszik in #317, closes #316
- refactor: split filesystem/updater into index and update modules by @rtuszik in #328

### Fixes

- fix: reconcile partial JSONL index on startup instead of empty serve by @rtuszik in #326
- Verify the checksum and move the index into place before extraction by @rtuszik, fixes #322
- Send notifications for download, update, and error events by @rtuszik, addresses #331

### Dependencies & CI

- [Aikido] Fix security issue in urllib3 via minor version upgrade from 2.6.3 to 2.7.0 by @aikido-autofix[bot] in #320
- chore(deps): update dependency pytest to v9.0.3 [security] by @koalabot-rt[bot] in #329
- Update docker/login-action action to v4 by @rtuszik in #297
- Update docker/setup-buildx-action action to v4 by @rtuszik in #312
- increase test coverage by @rtuszik in #319

> ⚠️ JSONL imports are still experimental and do not
> support scheduled updates, `UPDATE_STRATEGY`, `UPDATE_INTERVAL`, `FILE_URL`, and
> `MD5_URL` are ignored.
