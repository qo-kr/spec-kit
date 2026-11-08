#!/usr/bin/env bash
# OQ merge gate: checks that a PR may be merged under OQ's rules.
#
# Every check prints PASS, FAIL or UNMEASURED. UNMEASURED is never folded into
# PASS: the gate passes only when every check is PASS.
#
#   1. pr-head        the PR's head SHA equals local HEAD (what you reviewed is what is pushed)
#   2. reviewed-sha   codex-review.sh recorded a successful review of exactly that SHA
#                     against the PR's current base branch
#   3. value-doc      <feature-dir>/VALUE.md is a committed regular file with content
#   4. postmortem     <feature-dir>/POSTMORTEM.md exists and is not empty
#
# Usage: merge-gate.sh --pr NUMBER --feature-dir specs/NNN-name [--method squash|merge|rebase]
# On success prints:  OQ_MERGE_COMMAND=gh pr merge <N> -R <owner/name> --<method> --match-head-commit <sha>
# Exit: 0 all PASS · 1 any FAIL or UNMEASURED · 2 bad input

set -uo pipefail

die() { echo "oq-merge-gate: $*" >&2; exit 2; }

PR=""
FEATURE_DIR=""
METHOD="squash"
while [ $# -gt 0 ]; do
    case "$1" in
        --pr) [ $# -ge 2 ] || die "--pr needs a value"; PR="$2"; shift 2 ;;
        --feature-dir) [ $# -ge 2 ] || die "--feature-dir needs a value"; FEATURE_DIR="$2"; shift 2 ;;
        --method) [ $# -ge 2 ] || die "--method needs a value"; METHOD="$2"; shift 2 ;;
        -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done
case "$PR" in ""|*[!0-9]*) die "--pr must be a PR number" ;; esac
case "$METHOD" in squash|merge|rebase) ;; *) die "--method must be squash, merge or rebase" ;; esac
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git work tree"

FAILED=0
report() { # name status detail
    printf '%-13s %-10s %s\n' "$1" "$2" "$3"
    [ "$2" = "PASS" ] || FAILED=1
}

# shellcheck source=oq-common.sh
. "$(dirname "$0")/oq-common.sh"
LOCAL_HEAD="$(git rev-parse HEAD)"
PR_HEAD=""
PR_BASE=""
REPO="$(oq_origin_repo)"
if [ -n "$REPO" ] && command -v gh >/dev/null 2>&1; then
    PR_HEAD="$(gh pr view "$PR" -R "$REPO" --json headRefOid -q .headRefOid 2>/dev/null || true)"
    PR_BASE="$(gh pr view "$PR" -R "$REPO" --json baseRefName -q .baseRefName 2>/dev/null || true)"
fi

if [ -z "$PR_HEAD" ]; then
    report pr-head UNMEASURED "could not read PR #$PR head SHA with gh"
elif [ "$PR_HEAD" = "$LOCAL_HEAD" ]; then
    report pr-head PASS "$PR_HEAD"
else
    report pr-head FAIL "PR head $PR_HEAD != local HEAD $LOCAL_HEAD (push or pull first)"
fi

LEDGER="$(oq_review_dir 2>/dev/null)/ledger.tsv"
TARGET="${PR_HEAD:-$LOCAL_HEAD}"
# A review only counts when it reviewed this exact SHA against the PR's
# *current* base branch: a review against another base (or an empty diff) says
# nothing about what this merge brings in, and --match-head-commit does not
# protect against a PR being retargeted after the review.
if [ -z "$PR_BASE" ]; then
    report reviewed-sha UNMEASURED "could not read PR #$PR base branch with gh"
elif [ ! -f "$LEDGER" ]; then
    report reviewed-sha FAIL "no review ledger at $LEDGER (run codex-review.sh)"
elif awk -F'\t' -v s="$TARGET" -v b="origin/$PR_BASE" '$1 == s && $2 == b { found = 1 } END { exit !found }' "$LEDGER"; then
    report reviewed-sha PASS "$(awk -F'\t' -v s="$TARGET" -v b="origin/$PR_BASE" '$1 == s && $2 == b { line = $3 " vs " $2 " at " $4 } END { print line }' "$LEDGER")"
elif awk -F'\t' -v s="$TARGET" '$1 == s { found = 1 } END { exit !found }' "$LEDGER"; then
    report reviewed-sha FAIL "$TARGET was reviewed, but not against the PR base origin/$PR_BASE; re-run codex-review.sh"
else
    report reviewed-sha FAIL "$TARGET was never reviewed; re-run codex-review.sh on this SHA"
fi

check_doc() { # name file
    if [ -z "$FEATURE_DIR" ]; then
        report "$1" UNMEASURED "no --feature-dir given"
    else
        # Read the committed file at the SHA being merged, not the working tree:
        # an uncommitted VALUE.md would otherwise pass a gate it never reaches.
        local path="${FEATURE_DIR%/}/$2" entry mode type
        # Must be a regular file (not a directory, not a symlink) with
        # non-blank content in the commit being merged.
        entry="$(git ls-tree "$TARGET" -- "$path" 2>/dev/null)"
        mode="${entry%% *}"
        type="$(printf '%s' "$entry" | awk '{print $2}')"
        if [ -z "$entry" ]; then
            report "$1" FAIL "$path is missing at ${TARGET:0:12}"
        elif [ "$type" != "blob" ] || { [ "$mode" != "100644" ] && [ "$mode" != "100755" ]; }; then
            report "$1" FAIL "$path is not a regular file at ${TARGET:0:12} (mode $mode, $type)"
        elif ! git cat-file blob "$TARGET:$path" 2>/dev/null | grep -q '[^[:space:]]'; then
            report "$1" FAIL "$path is empty at ${TARGET:0:12}"
        else
            report "$1" PASS "$path at ${TARGET:0:12}"
        fi
    fi
}
check_doc value-doc VALUE.md
check_doc postmortem POSTMORTEM.md

if [ -z "$REPO" ]; then
    report repo UNMEASURED "origin is not a GitHub URL; cannot name the repository for gh -R"
fi

if [ "$FAILED" -ne 0 ]; then
    echo "OQ_MERGE_GATE=FAIL"
    exit 1
fi
echo "OQ_MERGE_GATE=PASS"
echo "OQ_MERGE_COMMAND=gh pr merge $PR -R $REPO --$METHOD --match-head-commit $PR_HEAD"
