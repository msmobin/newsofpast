#!/bin/bash
# One-time GitHub setup script.
# Run this once after creating the GitHub repo.

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

REPO="msmobin/newsofpast"
REMOTE="https://github.com/$REPO.git"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   War Room — GitHub Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Preflight: repo must exist on GitHub ─────────────────────────────────
echo "⚠️  Before continuing, confirm you have:"
echo "   1. Created a PUBLIC repo at: https://github.com/new"
echo "      Name it exactly:  newsofpast"
echo "   2. Left it completely empty (no README, no .gitignore)"
echo ""
read -rp "   Repo created and ready? (y/n): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo "   Aborted. Create the repo first then re-run this script."
  exit 0
fi

# ── Git identity (required for commits) ──────────────────────────────────
GIT_NAME="$(git config --global user.name 2>/dev/null || true)"
GIT_EMAIL="$(git config --global user.email 2>/dev/null || true)"

if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
  echo ""
  echo "📝 Git needs your name and email for commits (stored globally)."
  if [ -z "$GIT_NAME" ]; then
    read -rp "   Your name  (e.g. Mohammad Mobin): " GIT_NAME
    git config --global user.name "$GIT_NAME"
  fi
  if [ -z "$GIT_EMAIL" ]; then
    read -rp "   Your email (e.g. md.s.mobin@gmail.com): " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
  fi
  echo "   ✓ Identity saved."
fi

# ── Git init ─────────────────────────────────────────────────────────────
if [ ! -d ".git" ]; then
  echo ""
  echo "📁 Initializing git repository…"
  git init
  git branch -M main
else
  echo ""
  echo "📁 Git already initialized — re-using existing repo."
  # Ensure we're on main branch
  git checkout -B main 2>/dev/null || true
fi

# ── Remote ───────────────────────────────────────────────────────────────
EXISTING_REMOTE="$(git remote get-url origin 2>/dev/null || true)"
if [ -n "$EXISTING_REMOTE" ]; then
  echo "   Remote 'origin' already set: $EXISTING_REMOTE"
else
  echo ""
  echo "🔗 Adding remote: $REMOTE"
  git remote add origin "$REMOTE"
fi

# ── First commit & push ──────────────────────────────────────────────────
echo ""
echo "📤 Staging all files…"
git add -A

# Show what's being committed
STAGED="$(git diff --cached --name-only | wc -l | tr -d ' ')"
echo "   $STAGED files staged."

echo ""
echo "💾 Creating initial commit…"
git commit -m "initial: War Room project setup"

echo ""
echo "🚀 Pushing to GitHub…"
echo "   (A browser window may open asking you to log in to GitHub)"
echo ""
git push -u origin main

echo ""
echo "✅  Done! Your repo is live at:"
echo "   https://github.com/$REPO"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   NEXT STEPS  (do these in the browser)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Open: https://github.com/$REPO/settings/pages"
echo "     • Source  →  'Deploy from a branch'"
echo "     • Branch  →  main   /  (root)"
echo "     • Click Save"
echo ""
echo "  2. In the same Pages settings page, under 'Custom domain':"
echo "     • Enter:  www.newsofpast.com"
echo "     • Click Save  (GitHub will verify DNS — may take a few minutes)"
echo "     • Check 'Enforce HTTPS' once it appears"
echo ""
echo "  3. Add DNS records in Squarespace (see SETUP.md for details)"
echo ""
