#!/usr/bin/env bash
# Sync Mac personal Books library into the AGIB repo books/ folder (gitignored),
# then optionally ingest into AGI-owned Academy knowledge.
#
# Run this ON YOUR MAC (not in a cloud agent):
#   bash scripts/sync_mac_books_to_repo.sh
#   bash scripts/sync_mac_books_to_repo.sh --ingest
set -euo pipefail

SRC="${ACADEMY_BOOKS_DIR:-/Users/shivamagarwal/Downloads/AGIB/Books}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${REPO_ROOT}/books"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: Mac Books folder not found: $SRC"
  echo "Set ACADEMY_BOOKS_DIR if your library lives elsewhere."
  exit 1
fi

mkdir -p "$DEST"
echo "Syncing PDFs/docs from:"
echo "  $SRC"
echo "to:"
echo "  $DEST"

# Copy supported book formats only (do not delete dest extras unless --delete passed)
RSYNC_FLAGS=(-av --include='*/' \
  --include='*.pdf' --include='*.PDF' \
  --include='*.epub' --include='*.EPUB' \
  --include='*.docx' --include='*.DOCX' \
  --include='*.md' --include='*.markdown' --include='*.txt' \
  --include='*.xlsx' --include='*.xls' --include='*.ods' --include='*.csv' \
  --exclude='*')

if [[ "${1:-}" == "--delete" || "${2:-}" == "--delete" ]]; then
  RSYNC_FLAGS+=(--delete)
fi

rsync "${RSYNC_FLAGS[@]}" "$SRC"/ "$DEST"/

echo
echo "Synced file counts:"
find "$DEST" -type f \( -iname '*.pdf' -o -iname '*.epub' -o -iname '*.docx' \) | wc -l | awk '{print "  books:", $1}'

if [[ "${1:-}" == "--ingest" || "${2:-}" == "--ingest" ]]; then
  echo
  echo "Ingesting into Academy Books (AGI-owned objects only)..."
  cd "$REPO_ROOT/intelligence-engine"
  PYTHONPATH=. python3 -m academy.books.cli ingest --root "$DEST"
fi

echo
echo "Done. Cloud agents can learn once these files are present under repo books/."
