#!/bin/bash
# War Room — manual run script.
# Generates today's report then auto-pushes to GitHub Pages.
# Safe to run any time; re-running today overwrites today's report.

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/warroom.log"

log() { echo "$1" | tee -a "$LOG"; }

log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "▶  War Room — $(date '+%A %B %d, %Y  %I:%M %p')"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$DIR"

# ── 1. Dependencies ────────────────────────────────────────────────────────
if ! python3 -c "import anthropic" 2>/dev/null; then
  log "📦 Installing Python dependencies…"
  pip3 install --break-system-packages -r requirements.txt 2>&1 | tee -a "$LOG"
fi

# ── 2. Generate report ─────────────────────────────────────────────────────
log ""
log "📡 Running generator…"
python3 generate_report.py 2>&1 | tee -a "$LOG"
GEN_STATUS=${PIPESTATUS[0]}

if [ "$GEN_STATUS" -ne 0 ]; then
  log ""
  log "❌  Generation failed (exit $GEN_STATUS). Not pushing to GitHub."
  log "    Check the log above or run: tail -50 $LOG"
  exit 1
fi

# ── 3. Git commit & push ───────────────────────────────────────────────────
log ""
log "🚀 Pushing to GitHub Pages…"

# Check remote is configured
if ! git remote get-url origin &>/dev/null; then
  log "⚠️  No git remote found. Run setup_github.sh first."
  open "$DIR/index.html"
  exit 1
fi

git add -A
# Only commit if there are actual changes
if git diff --cached --quiet; then
  log "   No changes to commit (report already up to date)."
else
  TODAY="$(date '+%Y-%m-%d')"
  git commit -m "report: $TODAY — $(date '+%H:%M')"
  git push origin main 2>&1 | tee -a "$LOG"
  log ""
  log "✅  Published → https://www.newsofpast.com"
  log "   (GitHub Pages may take 1-2 min to reflect the update)"
fi

# ── 4. Open locally ────────────────────────────────────────────────────────
open "$DIR/index.html"
