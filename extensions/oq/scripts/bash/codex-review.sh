#!/usr/bin/env bash
# OQ Codex review wrapper.
#
# Why this exists: the review rules (pinned review model, review against the
# PR's real base branch, "reviewed SHA = merge SHA") used to live only as prose
# in the auto-review command, so nothing noticed when an agent skipped them.
# This script makes them mechanical:
#   - the model is pinned (default gpt-6.1-sol) and the Codex banner's
#     `model:` line must match it, otherwise the run fails;
#   - the base is the open PR's base branch (or --base), fetched from origin;
#   - the tree must be clean and HEAD must not move during the review;
#   - every successful review is appended to a ledger inside .git so the
#     merge gate can check that the SHA being merged is the SHA reviewed.
#
# Note: `codex review` (0.166) rejects `--base` together with a prompt, and has
# no `-m` flag. So the base is passed inside the prompt and the model through
# `-c review_model=... -c model=...`.
#
# Usage: codex-review.sh [--base BRANCH] [--prompt-file FILE]
# Output (stdout, last lines):
#   OQ_REVIEW_MODEL=<model>
#   OQ_REVIEW_BASE=origin/<branch>
#   OQ_REVIEWED_SHA=<40-char sha>
#   OQ_REVIEW_OUTPUT=<path to full codex output>
# Exit codes: 0 ok · 2 bad input/config · 3 dirty tree or HEAD moved
#             4 banner model mismatch · other = codex's own exit code

set -uo pipefail

die() { local code="$1"; shift; echo "oq-codex-review: $*" >&2; exit "$code"; }

BASE=""
PROMPT_FILE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --base) [ $# -ge 2 ] || die 2 "--base needs a value"; BASE="$2"; shift 2 ;;
        --prompt-file) [ $# -ge 2 ] || die 2 "--prompt-file needs a value"; PROMPT_FILE="$2"; shift 2 ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) die 2 "unknown argument: $1" ;;
    esac
done

MODEL="${OQ_REVIEW_MODEL:-gpt-6.1-sol}"
case "$MODEL" in
    ""|*[!A-Za-z0-9._-]*) die 2 "OQ_REVIEW_MODEL has invalid characters: '$MODEL'" ;;
esac
case "$MODEL" in
    *astra*) die 2 "model '$MODEL' is not allowed for reviews (Astra is reserved for design work)" ;;
    *ultrafast*) die 2 "model '$MODEL' is API-only and rejected by ChatGPT-account Codex" ;;
esac

command -v codex >/dev/null 2>&1 || die 2 "codex CLI not found"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 2 "not inside a git work tree"

# shellcheck source=oq-common.sh
. "$(dirname "$0")/oq-common.sh"
REPO="$(oq_origin_repo)"
BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [ -z "$BASE" ] && [ -n "$REPO" ] && [ -n "$BRANCH" ] && command -v gh >/dev/null 2>&1; then
    BASE="$(gh pr view "$BRANCH" -R "$REPO" --json baseRefName -q .baseRefName 2>/dev/null || true)"
fi
if [ -z "$BASE" ]; then
    BASE="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
    BASE="${BASE#origin/}"
fi
[ -n "$BASE" ] || die 2 "cannot determine base branch: no open PR, no origin/HEAD; pass --base"
case "$BASE" in
    -*|*..*|*[!A-Za-z0-9._/-]*) die 2 "invalid base branch name: '$BASE'" ;;
esac

git fetch --quiet origin "$BASE" || die 2 "git fetch origin $BASE failed"
BASE_REF="origin/$BASE"
git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null || die 2 "$BASE_REF does not exist"

[ -z "$(git status --porcelain)" ] || die 3 "working tree is dirty; commit first so the reviewed SHA covers every change"
HEAD_SHA="$(git rev-parse HEAD)"

PROMPT="Review the changes shown by: git diff ${BASE_REF}...${HEAD_SHA} (merge-base diff of this branch against ${BASE_REF}). Report every finding with a severity P0 (blocker), P1 (must fix before merge), P2 or P3, the file and line, and a concrete failure scenario. If there are no findings, say so explicitly."
if [ -n "$PROMPT_FILE" ]; then
    [ -f "$PROMPT_FILE" ] || die 2 "prompt file not found: $PROMPT_FILE"
    PROMPT="${PROMPT}

$(cat "$PROMPT_FILE")"
fi

GIT_DIR="$(git rev-parse --absolute-git-dir)"
REVIEW_DIR="$GIT_DIR/oq-reviews"
mkdir -p "$REVIEW_DIR" || die 2 "cannot create $REVIEW_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REVIEW_DIR/${HEAD_SHA:0:12}-${STAMP}.txt"

codex review -c "review_model=\"$MODEL\"" -c "model=\"$MODEL\"" "$PROMPT" >"$OUT" 2>&1
RC=$?

BANNER_MODEL="$(grep -m1 '^model: ' "$OUT" | sed 's/^model: //' | tr -d '\r' || true)"
if [ "$BANNER_MODEL" != "$MODEL" ]; then
    die 4 "codex banner reports model '${BANNER_MODEL:-<none>}', expected '$MODEL' (output: $OUT)"
fi
[ "$RC" -eq 0 ] || die "$RC" "codex review exited with $RC (output: $OUT)"

[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] || die 3 "HEAD moved during the review; the review does not cover the new HEAD"
[ -z "$(git status --porcelain)" ] || die 3 "the review left the working tree dirty; inspect before continuing"

printf '%s\t%s\t%s\t%s\t%s\n' "$HEAD_SHA" "$BASE_REF" "$MODEL" "$STAMP" "$OUT" >>"$REVIEW_DIR/ledger.tsv"

echo "OQ_REVIEW_MODEL=$MODEL"
echo "OQ_REVIEW_BASE=$BASE_REF"
echo "OQ_REVIEWED_SHA=$HEAD_SHA"
echo "OQ_REVIEW_OUTPUT=$OUT"
