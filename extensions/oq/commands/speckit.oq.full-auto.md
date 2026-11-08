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

### Phase 5: Postmortem + Value
- Write `POSTMORTEM.md` in the spec folder (`specs/{feature}/POSTMORTEM.md`)
  - Include: 산출물, 파일 구조, 테스트 결과, auto-review 결과, 핵심 설계 결정, 후속 작업
- Write `VALUE.md` in the same folder, in plain words a non-developer can read (no internal jargon; explain terms in parentheses):
  - (a) 한 줄 요약 — 무엇을 해 주는가
  - (b) 왜 필요한가 — 오늘의 불편 / 대안 비교 (표 권장)
  - (c) Value Proposition 한 문장
  - (d) 구체 Use Case 2~3개 ("이전 → 이후")
  - (e) 신뢰·정직성 — 무엇을 보장하고 무엇을 보장하지 않는가
  - 운영 후속 조치(env/배포)가 있으면 한 줄
- Scope dropped for schedule or priority → open a GitHub issue for each (what, why dropped, what is lost, what to measure first next time, close condition) and list the issue numbers in VALUE.md and the PR body
- Commit both files

### Phase 6: Merge Confirmation
- Push all changes to remote
- Create PR. Base = the repository's integration branch: use `dev` if `origin/dev` exists, otherwise the default branch. **Read it back** with `gh pr view --json baseRefName` and confirm it before continuing — never assume
- Put the VALUE.md summary at the top of the PR body
- If any commit landed after the last review (merge from base, conflict fix, version bump), run one more review round on the new HEAD first
- Run the merge gate and paste its full output into the summary:

```bash
.specify/extensions/oq/scripts/bash/merge-gate.sh --pr {pr_number} --feature-dir specs/{feature}
```

  `OQ_MERGE_GATE=FAIL` (any FAIL or UNMEASURED) → do not ask for merge; fix the failing check first
- Display summary (first line = review convergence + reviewed SHA):

```text
## Full Auto Complete

리뷰 수렴: {converged|stopped by stop rule} · 리뷰한 SHA = {OQ_REVIEWED_SHA} = PR head · 모델 {OQ_REVIEW_MODEL}

| Phase | Status |
|-------|--------|
| Prepare | ✅ |
| Pre-Review | ✅ N rounds, M fixes |
| Implement | ✅ N tasks completed |
| Post-Review | ✅ N rounds, M fixes |
| Postmortem + Value | ✅ POSTMORTEM.md, VALUE.md |
| PR | ✅ {pr_url} (base: {baseRefName}) |
| Merge gate | ✅ OQ_MERGE_GATE=PASS |

**머지하시겠습니까?** PR 확인 후 "머지" 또는 "수정 필요" 로 답변해주세요.
```

- **Wait for user confirmation** before merging
- On "머지" → run exactly the `OQ_MERGE_COMMAND=` line the gate printed (`gh pr merge … --match-head-commit <reviewed sha>`), then sync local. If the PR head moved since the gate ran, GitHub refuses the merge — re-review and re-run the gate
- On "수정 필요" → wait for instructions

## Behavior Rules

- Each phase must complete successfully before moving to the next
- If any phase fails, stop and report the failure with context
- Review rounds end by the auto-review stop rule (hard ceiling 10 per phase); a stop hands the ① issue / ② refactor choice to the user
- Commit after each major milestone (prepare, review fixes, each implementation task, postmortem)
- Follow existing project patterns (`CLAUDE.md`, constitution, previous specs)
- For clarify: recommend based on project patterns, simplicity principle, and scope minimization
