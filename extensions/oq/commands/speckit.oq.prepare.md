---
description: "Run the full OQ speckit preparation workflow from specify through analyze."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Run the complete speckit preparation workflow in sequence, stopping only for user input during clarification. This is the "one command to rule them all" for preparing a new feature milestone.

## Workflow

### Step 1: Specify
- Check if `specs/{feature_number}-*/spec.md` exists
- If missing: run `/speckit.specify {ARGS}` to create it
- If exists: review spec for completeness, suggest improvements
- Create feature branch `{number}-{name}` if not on one

### Step 2: Clarify
- Run `/speckit.clarify {ARGS}`
- **IMPORTANT**: Always show trade-offs for each option (pros/cons table)
- This step is interactive — wait for user answers
- Maximum 5 questions

### Step 3: Checklist (if applicable)
- Run `/speckit.checklist {ARGS}` if the feature has UX/security/test concerns
- Skip if purely backend/infra work

### Step 4: Plan
- Run `/speckit.plan {ARGS}`
- Generate `research.md`, `data-model.md`, `contracts/` as needed

### Step 5: Tasks
- Run `/speckit.tasks {ARGS}`
- Generate `tasks.md` with full checklist format

### Step 6: Analyze
- Run `/speckit.analyze {ARGS}`
- If CRITICAL or HIGH issues found: **auto-fix them**
- If only MEDIUM/LOW: report and continue

### Step 7: Commit + Push + GitHub Issue

1. **Commit** all generated or modified artifacts with message:
   `docs: prepare {feature} — spec, plan, tasks, analyze complete`
2. **Push** the feature branch to remote
3. **Create GitHub Issue** for Codex review using `gh issue create`:
   - Title: `Codex Review Request: {feature} — PREPARATION_COMPLETE`
   - Body:
     ```markdown
     ## Preparation Complete — Ready for Review

     **Branch**: `{branch}`
     **Feature**: {feature description}

     ### Generated Artifacts
     - specs/{feature}/spec.md — feature specification
     - specs/{feature}/plan.md — implementation plan
     - specs/{feature}/tasks.md — {N} tasks
     - Analyze: {M} issues found, {K} auto-fixed

     ### Review Focus
     - spec ↔ plan ↔ tasks 정합성
     - 요구사항 누락/과잉
     - 아키텍처 결정 합리성
     - task 분해 적절성

     ### Next Step
     Review 완료 후 `/speckit.implement {feature}` 진행 예정
     ```
4. Report the issue URL to the user

### Step 8: Report

Output a summary:

```text
## Preparation Complete

| Step | Status |
|------|--------|
| Specify | ✅ spec.md created/reviewed |
| Clarify | ✅ N questions answered |
| Checklist | ✅/⏭️ |
| Plan | ✅ plan.md + artifacts |
| Tasks | ✅ N tasks generated |
| Analyze | ✅ N issues found, M fixed |
| Commit + Push | ✅ |
| GitHub Issue | ✅ |

🔗 GitHub Issue: **{issue_url}** ← 코덱스에게 이 링크를 전달해주세요
🌿 브랜치: `{branch}`

**다음 단계**:
- `/speckit.collab-review {ARGS}` — 코덱스와 협업 리뷰 시작
- `/speckit.implement {ARGS}` — 리뷰 없이 바로 구현 시작
```

## Behavior Rules

- If any step fails, stop and report the failure
- Clarify is the only interactive step — all others run automatically
- Analyze auto-fixes CRITICAL and HIGH issues without asking
- For MEDIUM or LOW: report but do not block
- If spec already exists and is complete, skip specify and go straight to clarify
- If plan or tasks already exist, skip those steps and go to analyze only

## Context

{ARGS}
