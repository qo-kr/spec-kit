#!/usr/bin/env bash
# Shared helpers for the OQ scripts. Source it; do not execute it.

# Succeed only when the work tree is clean. Untracked files and submodule
# changes count, whatever status.showUntrackedFiles / submodule settings say,
# and a failing `git status` counts as not clean.
oq_is_clean() {
    local out
    out="$(git -c status.showUntrackedFiles=all status --porcelain \
        --untracked-files=all --ignore-submodules=none 2>/dev/null)" || return 1
    [ -z "$out" ]
}

# Print the directory that holds the review ledger. It lives in the git
# *common* dir, so a review made in one worktree is visible to the gate in
# another worktree of the same repository.
oq_review_dir() {
    local common
    common="$(git rev-parse --git-common-dir 2>/dev/null)" || return 1
    common="$(cd "$common" 2>/dev/null && pwd -P)" || return 1
    printf '%s/oq-reviews\n' "$common"
}

# Print "owner/name" of the GitHub repository behind the `origin` remote, or
# nothing when origin is not a GitHub URL.
#
# Why not `gh repo view`: in a fork that also has an `upstream` remote, gh
# resolves the *upstream* repository by default, so PR lookups and the merge
# command's -R would silently target the wrong repo. The raw configured URL is
# read (not `git remote get-url`, which applies insteadOf rewrites).
oq_origin_repo() {
    local url path
    url="$(git config --get remote.origin.url 2>/dev/null || true)"
    case "$url" in
        git@github.com:*) path="${url#git@github.com:}" ;;
        ssh://git@github.com/*) path="${url#ssh://git@github.com/}" ;;
        https://github.com/*) path="${url#https://github.com/}" ;;
        *) return 0 ;;
    esac
    path="${path%.git}"
    path="${path%/}"
    case "$path" in
        */*/*|*[!A-Za-z0-9._/-]*|/*|*/) return 0 ;;
        */*) printf '%s\n' "$path" ;;
    esac
}
