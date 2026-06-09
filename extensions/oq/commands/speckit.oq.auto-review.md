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

1. **codex CLI**: `which codex` — must exist
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

Execute `codex review --base main` with a **stage-specific prompt**:

```bash
# For SPEC_REVIEW / PLAN_REVIEW (docs-only):
# Codex handles Axis 2 (defects in doc structure). Claude supplements Axis 1 (spec gap) + Axis 3 (test coverage planning).
codex review --base main "Focus on document consistency: spec↔plan↔tasks alignment, terminology drift, missing acceptance criteria, ambiguous requirements, API naming conflicts between documents." 2>&1

# For IMPLEMENTATION_REVIEW / FINAL_REVIEW (code changes):
# Codex handles Axis 2 (code defects). Claude supplements Axis 1 (spec gap) + Axis 3 (test coverage).
codex review --base main 2>&1
```

**Codex review 후, Claude는 반드시 3축 심층 리뷰를 별도로 수행한다.**
Codex가 LGTM이더라도 Claude가 3축 점검을 건너뛰어서는 안 된다.

**Stage-specific prompts** ensure docs-only changes get proper review (codex defaults to code-focused analysis without guidance).

**IMPORTANT**:
- `codex review` runs non-interactively — it reads the git diff and outputs findings.
- Capture the ENTIRE stdout output.
- The output may be long (includes diff inspection + analysis + findings).
- Timeout: 5 minutes max.
- If `--base` and prompt conflict, use prompt only: `codex review "Review changes on branch X against main. Focus on..."` with `--base main` omitted.

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

Run `codex review --base main` again on the updated code.

### Step 9: Loop or Complete

- If codex finds more issues → Go to Step 4
- If codex output has no actionable findings → Sign-off

### Step 10: Completion

```bash
gh issue close {issue_number} --comment "Auto review complete — {N} rounds, {total_fixes} fixes."
```

Output:

```text
## Auto Review 완료 🎉

총 라운드: {N}
총 수정: {total_fixes}
GitHub Issue: {issue_url} (closed)
최종 상태: Sign-off

### 다음 단계
- main 머지 준비 완료
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

- Maximum 10 rounds — if not converging, stop and report
- Each round: codex review + parse + fix + test + commit + push
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
