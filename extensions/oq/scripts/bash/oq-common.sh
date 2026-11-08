#!/usr/bin/env bash
# Shared helpers for the OQ scripts. Source it; do not execute it.

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
