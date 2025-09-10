#!/usr/bin/env bash
BRANCH="rot-$(date +%s)-$(head /dev/urandom | tr -dc a-z0-9 | head -c6)"
git checkout -b "$BRANCH"
git add rotated/manifest.json rotated/
git commit -m "Auto-rotated artifacts $BRANCH" || true
git push origin "$BRANCH"
git checkout main || git checkout master || true
echo "Pushed branch $BRANCH"
