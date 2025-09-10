#!/usr/bin/env bash
set -e
BASE_DIR="/opt/star-tigo-defensa/git_sync"
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"
REPOS=(
  "FernandoGuadalupeMendezEspinoza/proyecto-1"
  "FernandoGuadalupeMendezEspinoza/proyecto-IA"
  "FernandoGuadalupeMendezEspinoza/proyecto-robotics"
)
for repo in "${REPOS[@]}"; do
  name=$(basename "$repo")
  dir="$BASE_DIR/$name"
  if [ -d "$dir/.git" ]; then
    git -C "$dir" fetch --all --prune
    git -C "$dir" reset --hard origin/main || git -C "$dir" pull
  else
    if [ -n "$GITHUB_TOKEN" ]; then
      url="https://${GITHUB_TOKEN}@github.com/${repo}.git"
    else
      url="git@github.com:${repo}.git"
    fi
    git clone --depth 1 "$url" "$dir"
  fi
done
echo "[sync] done"
