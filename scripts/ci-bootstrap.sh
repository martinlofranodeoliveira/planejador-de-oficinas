#!/usr/bin/env bash
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${CI:-}" != "true" || "${RUNNER_ENVIRONMENT:-}" != "github-hosted" || "${RUNNER_OS:-}" != "Linux" || "$EUID" -eq 0 ]]; then
  printf '%s\n' 'BOOTSTRAP_REQUIRES_HOSTED_GITHUB_LINUX_VM' >&2
  exit 2
fi
sudo -n apt-get update -qq
sudo -n apt-get install --yes --no-install-recommends bubblewrap
