---
description: "Run OQ's end-to-end spec-to-merge pipeline."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Fully autonomous spec-to-merge pipeline. Runs all stages sequentially, only pausing for user confirmation at the final merge step.

## Pipeline

### Phase 1: Prepare
- Run `/speckit.prepare {ARGS}`
- During clarify, provide **recommended answers** with trade-off tables for each question
- **사용자 확인을 기다린다** — 추천을 제시하고 "추천대로 진행할까요?" 로 묻기
- 사용자가 "네/OK/ㅇㅇ" → 추천으로 진행, 수정 의견 → 반영 후 진행
- If the user has previously established patterns (for example deep merge in 002), follow those patterns

### Phase 2: Pre-Implementation Review
- Run `/speckit.auto-review-strict {ARGS}`
- Fix all findings including LOW severity
- Ensure spec, plan, and tasks are clean before implementation

### Phase 3: Implement
- Run `/speckit.implement {ARGS}`
- Execute all tasks in dependency order
- Run tests after each phase
- Commit progress incrementally

### Phase 4: Post-Implementation Review
- Run `/speckit.auto-review-strict {ARGS}`
- Fix all findings including LOW severity
- Ensure code quality is production-ready

### Phase 5: Postmortem
- Write `POSTMORTEM.md` in the spec folder (`specs/{feature}/POSTMORTEM.md`)
- Include: 산출물, 파일 구조, 테스트 결과, auto-review 결과, 핵심 설계 결정, 후속 작업
- Commit the postmortem

### Phase 6: Merge Confirmation
- Push all changes to remote
- Create PR (target: `dev` branch)
- Display summary:

```text
## Full Auto Complete

| Phase | Status |
|-------|--------|
| Prepare | ✅ |
| Pre-Review | ✅ N rounds, M fixes |
| Implement | ✅ N tasks completed |
| Post-Review | ✅ N rounds, M fixes |
| Postmortem | ✅ |
| PR | ✅ {pr_url} |

**머지하시겠습니까?** PR 확인 후 "머지" 또는 "수정 필요" 로 답변해주세요.
```

- **Wait for user confirmation** before merging
- On "머지" → merge PR, sync local
- On "수정 필요" → wait for instructions

## Behavior Rules

- Each phase must complete successfully before moving to the next
- If any phase fails, stop and report the failure with context
- Maximum 10 review rounds per auto-review phase
- Commit after each major milestone (prepare, review fixes, each implementation task, postmortem)
- Follow existing project patterns (`CLAUDE.md`, constitution, previous specs)
- For clarify: recommend based on project patterns, simplicity principle, and scope minimization
