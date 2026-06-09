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
