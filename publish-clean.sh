#!/usr/bin/env bash
#
# publish-clean.sh
#
# Mirrors this private project into its sibling public folder. It shows the
# public repository status and asks before committing or pushing. It never
# commits, pushes, or rewrites history in the private folder.

set -euo pipefail

# --- Resolve private (source) and public (destination) folders ---------------
# Private = wherever this script lives, so it works no matter the current dir.
PRIVATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$PRIVATE_DIR")"
PROJECT_NAME="$(basename "$PRIVATE_DIR")"
PUBLIC_DIR="$PARENT_DIR/${PROJECT_NAME}-public"

echo "Private (source): $PRIVATE_DIR"
echo "Public  (target): $PUBLIC_DIR"
echo

# --- Safety checks: stop immediately if anything is off ----------------------
if [[ "$PRIVATE_DIR" == *-public ]]; then
  echo "ERROR: Run this from the PRIVATE folder, not a -public one." >&2
  exit 1
fi
if [[ "$PUBLIC_DIR" == "$PRIVATE_DIR" ]]; then
  echo "ERROR: Public and private resolved to the same path. Aborting." >&2
  exit 1
fi
if [[ ! -d "$PUBLIC_DIR" ]]; then
  echo "ERROR: Public folder is missing: $PUBLIC_DIR" >&2
  echo "Create it first (git init, or clone your public repo there), then re-run." >&2
  exit 1
fi
if [[ ! -d "$PUBLIC_DIR/.git" ]]; then
  echo "ERROR: Public folder is not a git repository (no .git): $PUBLIC_DIR" >&2
  exit 1
fi

# --- Confirm before overwriting the public folder ----------------------------
# rsync --delete makes the public folder a mirror of the private project, so
# files only in the public folder (outside .git and the ignored caches) get
# removed. Ask first because this overwrites the public working tree.
echo "This will MIRROR the private project into the public folder."
echo "Files in the public folder that are not in the private project"
echo "(excluding .git and the ignored caches) will be REMOVED."
read -r -p "Continue and overwrite '$PUBLIC_DIR'? [y/N] " copy_answer
case "$copy_answer" in
  [Yy]|[Yy][Ee][Ss]) ;;
  *) echo "Aborted before copying. Nothing was changed."; exit 0 ;;
esac
echo

# --- Copy project, excluding caches / venvs / editor + VCS metadata ----------
# publish-clean.sh itself is private tooling, so it is not copied.
echo "Copying project into public folder..."
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  --exclude='.pytest_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='publish-clean.sh' \
  "$PRIVATE_DIR"/ "$PUBLIC_DIR"/
echo "Copy complete."
echo

# --- Show git status in the public folder ------------------------------------
echo "==================== git status (public) ===================="
git -C "$PUBLIC_DIR" status
echo "============================================================="
echo

# --- Confirm before committing -----------------------------------------------
read -r -p "Commit these changes in the PUBLIC folder? [y/N] " commit_answer
case "$commit_answer" in
  [Yy]|[Yy][Ee][Ss]) ;;
  *) echo "Stopped. Public working tree updated; nothing committed."; exit 0 ;;
esac

read -r -p "Commit message (blank = 'Publish clean snapshot'): " commit_message
[[ -z "$commit_message" ]] && commit_message="Publish clean snapshot"

git -C "$PUBLIC_DIR" add -A
git -C "$PUBLIC_DIR" commit -m "$commit_message"
echo

# --- Confirm before pushing --------------------------------------------------
read -r -p "Push the public commit to its remote? [y/N] " push_answer
case "$push_answer" in
  [Yy]|[Yy][Ee][Ss]) ;;
  *) echo "Committed in public folder, but not pushed."; exit 0 ;;
esac

git -C "$PUBLIC_DIR" push
echo "Pushed from public folder."
