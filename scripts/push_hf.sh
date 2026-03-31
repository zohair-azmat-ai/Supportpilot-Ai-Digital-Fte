#!/usr/bin/env bash
# push_hf.sh — Rebase hf-deploy on main and push to Hugging Face Space.
#
# Usage: ./scripts/push_hf.sh
#
# How it works:
#   1. Rebases hf-deploy on top of the current main (gets all latest changes)
#   2. Pushes hf-deploy:main → hf_v2 (HF Space remote)
#   3. Returns to main branch
#
# The hf-deploy branch is identical to main EXCEPT README.md has the
# HF YAML config block prepended (required by Hugging Face Spaces).
# GitHub's main branch stays clean with no YAML visible.

set -euo pipefail

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "→ Rebasing hf-deploy on main..."
git checkout hf-deploy
git rebase main

echo "→ Pushing hf-deploy → hf_v2/main..."
git push hf_v2 hf-deploy:main --force-with-lease

echo "→ Back to ${CURRENT_BRANCH}"
git checkout "${CURRENT_BRANCH}"

echo "✓ HF Space updated."
