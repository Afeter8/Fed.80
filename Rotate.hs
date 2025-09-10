#!/usr/bin/env bash
# Crea branch rotativa y hace push (usa credenciales ya configuradas en repo)
set -e
BASE=/opt/star-tigo-defensa
cd "$BASE" || exit 1
BRANCH="rot-$(date +%s)-$RANDOM"
git checkout -b "$BRANCH"
git add rotated/
git commit -m "Auto-rotated artifacts $BRANCH" || true
git push origin "$BRANCH"
git checkout main || git checkout master || true
echo "Pushed $BRANCH"
