# OQ Workflow Pack

Bundled OQ-specific Speckit workflows for preparation, automated review, and full-auto execution.

## Install

```bash
specify extension add oq
```

For local extension development:

```bash
specify extension add --dev /path/to/spec-kit/extensions/oq
```

## Commands

Canonical names:

- `speckit.oq.prepare`
- `speckit.oq.auto-review`
- `speckit.oq.auto-review-strict`
- `speckit.oq.full-auto`

Alias names preserved for the existing OQ workflow:

- `speckit.prepare`
- `speckit.auto-review`
- `speckit.auto-review-strict`
- `speckit.full-auto`

When a project uses agent skills, installing this extension also registers the alias forms as project-local skills such as `.agents/skills/speckit-prepare/` and `.agents/skills/speckit-full-auto/`.

## Notes

- `prepare`, `auto-review`, and `full-auto` assume a GitHub-backed workflow and reference `git`, `gh`, and `codex` where available.
- These commands intentionally preserve the existing OQ wording and `specs/{feature}` conventions.

## Scripts (1.1.0)

The review and merge rules are enforced by two scripts, not by command wording alone. They are installed with the extension at `.specify/extensions/oq/scripts/bash/` (bash; Linux and macOS).

| Script | What it guarantees |
| --- | --- |
| `codex-review.sh [--base BRANCH] [--prompt-file FILE]` | Review model pinned to `gpt-6.1-sol` (`OQ_REVIEW_MODEL` overrides; Astra and `*-ultrafast` refused) and checked against the Codex banner. Base = the open PR's base branch, fetched from `origin`. Tree must be clean and HEAD must not move. Records the reviewed SHA in `.git/oq-reviews/ledger.tsv`. |
| `merge-gate.sh --pr N --feature-dir specs/NNN-name [--method squash]` | PASS / FAIL / UNMEASURED per check: PR head = local HEAD, that SHA was reviewed, `VALUE.md` and `POSTMORTEM.md` committed and non-empty. Passes only when every check is PASS, then prints the `gh pr merge N -R owner/name --squash --match-head-commit <sha>` command to run. |

`codex review` 0.166 rejects `--base` together with a prompt and has no `-m` flag, so `codex-review.sh` passes the base inside the prompt and the model with `-c review_model=… -c model=…`.

`/speckit.taskstoissues` moved out of spec-kit core in 1.3. Install the bundled `github` extension (`specify extension add github`) and use `/speckit.github.taskstoissues`.
