#!/usr/bin/env bash
# Applies the STN v0.6.1 release-candidate additions to an existing repository,
# on a new branch. It never force-pushes and never merges. It stops on any failure.
#
# Usage:
#   chmod +x apply_stn_v0.6.1_rc.sh
#   ./apply_stn_v0.6.1_rc.sh /path/to/your/clone /path/to/STN_repo_additions_v0.6.1.zip
set -euo pipefail

REPO="${1:?Usage: $0 <repo-path> <additions-zip>}"
ZIP="${2:?Usage: $0 <repo-path> <additions-zip>}"
BRANCH="v0.6.1-rc"
REMOTE="origin"

for tool in git unzip flutter; do
  command -v "$tool" >/dev/null || { echo "Missing required tool: $tool"; exit 1; }
done
[ -f "$ZIP" ] || { echo "Zip not found: $ZIP"; exit 1; }

cd "$REPO"
git rev-parse --is-inside-work-tree >/dev/null
if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is not clean. Commit or stash your changes first."
  exit 1
fi
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "Branch $BRANCH already exists. Rename or delete it first."
  exit 1
fi

START_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git checkout -b "$BRANCH"
echo "Created $BRANCH from $START_BRANCH"

# 1. Platform folders first, so the package's own pubspec.yaml and lib/ win afterwards.
if [ ! -d android ]; then
  flutter create --platforms=android --project-name supportive_therapy_network .
fi

# 2. Overlay the v0.6.1 package (code, tests, docs, CI, README, .gitignore).
unzip -o -q "$ZIP" -d .

# 3. Lock dependencies, format, and check. Any failure stops here, with the
#    changes left unstaged on $BRANCH so you can see and fix them.
flutter pub get
dart format .
flutter analyze
flutter test --reporter expanded

# 4. Show exactly what will be committed, then ask before pushing.
git add -A
echo
git status --short
echo
git diff --cached --stat
echo
read -r -p "Review the changes above. Commit and push $BRANCH to $REMOTE? [y/N] " answer
case "$answer" in
  y|Y) ;;
  *) echo "Stopped before commit. Changes are staged on $BRANCH."; exit 0 ;;
esac

git commit -m "v0.6.1+7 private release candidate: client linkage, safety-gate coverage, export removal, governance docs, CI"
git push -u "$REMOTE" "$BRANCH"

echo
echo "Pushed $BRANCH. Open a pull request into $START_BRANCH."
echo "Do not merge while CI is red. Confirm CI passes before any release decision."
