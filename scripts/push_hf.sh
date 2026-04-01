#!/usr/bin/env bash
# push_hf.sh — Build the HF-ready README from hf.yaml + main README, then push to HF Space.
#
# Usage: ./scripts/push_hf.sh
#
# How it works:
#   1. Reads hf.yaml (HF Space YAML config — source of truth)
#   2. Resets hf-deploy to main (clean slate each push)
#   3. Injects hf.yaml as README.md frontmatter for the HF push commit
#   4. Force-pushes hf-deploy:main → hf_v2 (HF Space remote)
#   5. Returns to the original branch
#
# hf.yaml contains only the HF Space YAML config block.
# GitHub's main branch README.md stays clean — no YAML visible.

set -euo pipefail

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Build the combined README: hf.yaml frontmatter + main branch README
TMP_README=$(mktemp)
cat "${REPO_ROOT}/hf.yaml" > "${TMP_README}"
printf "\n" >> "${TMP_README}"
git show main:README.md >> "${TMP_README}"

echo "→ Preparing hf-deploy branch (reset to main)..."
git checkout hf-deploy
git reset --hard main

echo "→ Injecting HF YAML config from hf.yaml..."
cp "${TMP_README}" README.md
rm -f "${TMP_README}"
git add README.md
git commit -m "chore: inject HF YAML config from hf.yaml"

echo "→ Pushing hf-deploy → hf_v2/main..."
git push hf_v2 hf-deploy:main --force

echo "→ Back to ${CURRENT_BRANCH}"
git checkout "${CURRENT_BRANCH}"

echo "✓ HF Space updated."
