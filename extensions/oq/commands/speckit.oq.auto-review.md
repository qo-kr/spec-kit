---
description: "Run OQ's fully automated Codex-backed review loop."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Fully automated collaborative review loop using `codex review` CLI. No user relay needed — Claude drives the entire cycle: create issue → run codex → parse findings → fix → repeat until clean.

## Prerequisites

- `codex` CLI installed and authenticated (`codex login`)
- `gh` CLI installed and authenticated (`gh auth login`)
- Git repo with remote configured
- Feature branch (not main)

## Workflow

### Step 0: Pre-flight Checks

Before starting, verify the environment is ready:

1. **codex CLI**: `which codex` — must exist. The wrapper `.specify/extensions/oq/scripts/bash/codex-review.sh` must exist and be executable (reinstall the `oq` extension if not)
2. **gh CLI**: `which gh` — must exist
3. **Git branch**: not on main — must be on a feature branch
4. **No cargo/build locks**: check for `target/debug/.cargo-lock` or running cargo processes. If found, warn and wait or kill.
5. **Clean working tree**: `git status --porcelain` — uncommitted changes should be committed or stashed first
6. **Remote push**: verify branch is pushed to remote

If any check fails, report and suggest fix before proceeding.

### Step 1: Detect Stage + Generate Context

Detect SPEC/PLAN/IMPLEMENTATION/FINAL_REVIEW from the current spec-kit artifacts.

### Step 1.5: Three Review Axes

모든 리뷰는 반드시 아래 **3가지 축**을 명시적으로 점검해야 한다.
Codex review + Claude 자체 심층 리뷰 모두에 적용.

#### Axis 1: Spec Gap (기획 정합성)
- spec ↔ plan ↔ tasks 간 누락/불일치가 없는지
- 구현이 spec의 요구사항(FR)과 성공 기준(SC)을 충족하는지
- 용어가 문서 간 통일되어 있는지
- spec에 정의된 edge case가 구현/계획에 반영되었는지

#### Axis 2: Software Defect (결함 탐지)
- 로직 오류, off-by-one, null or undefined 처리 누락
- 보안 취약점 (injection, 인증/인가 누락, 민감정보 노출)
- 동시성/경쟁 조건, 리소스 누수
- 에러 핸들링 누락 또는 부적절한 에러 전파
- 성능 병목 (N+1 쿼리, 불필요한 반복 등)

#### Axis 3: Test Coverage (테스트 보완)
- 새로 추가/변경된 기능에 대한 테스트가 있는지
- edge case와 실패 시나리오에 대한 테스트가 있는지
- spec의 acceptance scenario가 테스트로 커버되는지
- 기존 테스트가 변경으로 인해 깨지지 않는지

**각 축별로 findings를 분류하여 보고한다.**

### Step 2: Create GitHub Issue

Create a tracking issue with `gh issue create`:
- Title: `Auto Review: {feature} — {STAGE}`
- Body: review context (branch, files, check-for list)
- Save the issue number for later comments.

### Step 3: Run Codex Review

**Always run Codex through the OQ wrapper script. Never call `codex review` directly.**

```bash
# For SPEC_REVIEW / PLAN_REVIEW (docs-only): add a docs focus prompt.
# Codex handles Axis 2 (defects in doc structure). Claude supplements Axis 1 (spec gap) + Axis 3 (test coverage planning).
printf '%s\n' "Focus on document consistency: spec↔plan↔tasks alignment, terminology drift, missing acceptance criteria, ambiguous requirements, API naming conflicts between documents." > /tmp/oq-review-focus.txt
.specify/extensions/oq/scripts/bash/codex-review.sh --prompt-file /tmp/oq-review-focus.txt

# For IMPLEMENTATION_REVIEW / FINAL_REVIEW (code changes):
# Codex handles Axis 2 (code defects). Claude supplements Axis 1 (spec gap) + Axis 3 (test coverage).
.specify/extensions/oq/scripts/bash/codex-review.sh
```

What the script guarantees, so you do not re-check it by hand:
- **Model is pinned** to `gpt-6.1-sol` (override only via `OQ_REVIEW_MODEL`; Astra and `*-ultrafast` are refused). The Codex banner's `model:` line must match, otherwise the script exits 4.
- **Base is the open PR's base branch** (for OQ service repos usually `dev`), fetched from `origin`. Pass `--base <branch>` only when no PR exists yet.
- **Reviewed SHA is recorded.** The tree must be clean (exit 3 otherwise) and HEAD must not move during the review. On success the script prints `OQ_REVIEWED_SHA=<sha>` and appends it to `.git/oq-reviews/ledger.tsv`, which the merge gate reads.
- The full Codex output is at the path printed as `OQ_REVIEW_OUTPUT=`. Read that file for Step 4.

**Codex review 후, Claude는 반드시 3축 심층 리뷰를 별도로 수행한다.**
Codex가 LGTM이더라도 Claude가 3축 점검을 건너뛰어서는 안 된다.

**IMPORTANT**:
- A non-zero exit from the script means **no review happened for this SHA**. Do not count the round, do not treat it as sign-off. Report the exit code and the script's stderr line.
- `codex review` (0.166) rejects `--base` together with a prompt and has no `-m` flag; the script already works around both. Do not "fix" it by calling Codex directly.

### Step 4: Parse Codex Output

The codex output typically ends with a structured review summary. Parse it for:
- Severity levels (if mentioned)
- File locations
- Issue descriptions
- Recommendations

**3축 분류**: 파싱한 findings를 Axis 1 (Spec Gap) / Axis 2 (Defect) / Axis 3 (Test Coverage)로 분류한다.

If codex output contains no actionable findings (for example "no issues found", "LGTM", or just summary without problems), **Codex는 sign-off이지만 Claude 3축 심층 리뷰는 계속 진행한다.**

### Step 5: Post Findings to Issue

Post the codex review output as a comment on the tracking issue:

```bash
gh issue comment {issue_number} --body "## Codex Review Round {N}\n\n{codex_output_summary}"
```

### Step 6: Fix Findings

For each finding:
1. Read the referenced file
2. Apply the fix
3. Run project tests (auto-detect: `cargo test`, `npm test`, `pytest`, etc.)
4. Commit: `fix: address auto-review round N — {summary}`
5. Push

### Step 7: Post Fix Summary to Issue

```bash
gh issue comment {issue_number} --body "## Round {N} Fixes\n\n{fix_table}\n\nCommit: {hash}"
```

### Step 8: Re-Run Codex Review

Run `.specify/extensions/oq/scripts/bash/codex-review.sh` again on the updated, committed code.

### Step 9: Loop, Stop, or Complete

Before starting the next round, tag every new finding as either **regression** (caused by the previous round's fix) or **fresh** (was already there). Then:

1. **Stop rule** — if regressions are the majority of this round's findings, stop patching. Report the two options below and let the user choose; do not start another fix round on your own.

   | | ① Follow-up issue, then merge | ② Refactor the core module |
   |---|---|---|
   | Allowed when | only P2/P3 remain | P0/P1 remain, or the same file/boundary keeps coming back |
   | Touches | reversible surface (wording, test hygiene) | irreversible actions, external sends, credentials, data integrity, security |
   | Leaves behind | an issue (what, why, counter-example, close condition) | a design with a *why* and a before/after diagram, then review from scratch |

   If the call is split (e.g. P2 on a security boundary), lean to ②.
2. **Round 4 and later** — before fixing anything in round 4, write a one-time refactor review into the tracking issue: does the same file show up every round? Are most findings regressions? Does one function hold several policies that fail in different directions? How many things must a newcomer hold at once to change it? Conclude (a) split now, (b) follow-up issue, or (c) not needed + why. Skipping the review is the only thing not allowed.
3. **Invariant ledger** — from round 3, keep an invariant ledger in the tracking issue (one line = invariant + round that added it + what it prevents). Read it top to bottom before each fix and check the fix does not undo an earlier line.
4. **P0/P1 never remain at sign-off.** Fix them, or stop and report.
5. If codex output has no actionable findings and Claude's 3-axis review is clean → Sign-off **for the SHA printed as `OQ_REVIEWED_SHA`**. Any later commit (merge from base, conflict fix, version bump) needs another review round.

### Step 10: Completion

```bash
gh issue close {issue_number} --comment "Auto review complete — {N} rounds, {total_fixes} fixes."
```

Output:

```text
## Auto Review 완료 🎉

총 라운드: {N}
총 수정: {total_fixes}
리뷰 모델: {OQ_REVIEW_MODEL} · 기준: {OQ_REVIEW_BASE}
리뷰한 SHA: {OQ_REVIEWED_SHA}
GitHub Issue: {issue_url} (closed)
최종 상태: Sign-off

### 다음 단계
- 머지 전 `.specify/extensions/oq/scripts/bash/merge-gate.sh --pr <N> --feature-dir <specs/NNN-…>` 실행
```

## Auto-Detect Test Command

Look for these in order:
1. `Cargo.toml` exists → `cargo test --workspace`
2. `package.json` exists → `npm test`
3. `pyproject.toml` or `setup.py` → `pytest`
4. `go.mod` → `go test ./...`
5. `Makefile` with test target → `make test`
6. Fallback: skip tests

## Behavior Rules

- Rounds end by the stop rule in Step 9, not by "until clean". Hard ceiling: 10 rounds — if reached, stop and report
- Each round: codex review (via the wrapper script) + parse + fix + test + commit + push
- Post every round to the tracking GitHub issue
- If codex review command fails (timeout, auth error), stop and report the exact command, stderr, and next manual recovery step
- Never ignore findings — fix or defer with explanation
- Honestly mark stubs or placeholders

## Fallback

If `codex` CLI is not available or fails:

```text
⚠️ codex CLI not available. Automated review cannot continue.
Install or authenticate Codex, then retry `/speckit.auto-review {ARGS}`.
```

## Context

{ARGS}
