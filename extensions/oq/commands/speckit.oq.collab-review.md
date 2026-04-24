---
description: "Run the collaborative Claude plus Codex review loop with the user as relay."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Run a collaborative review loop between Claude (fixer) and Codex (reviewer), with the user as relay. Each round: Claude prepares context → user sends to Codex → Codex finds issues → user pastes findings → Claude fixes all → repeat until clean.

## Workflow

### Step 1: Detect Current Stage

Determine what to review based on the current branch state:

```text
If spec.md exists but no plan.md → Stage: SPEC_REVIEW
If plan.md exists but no tasks.md → Stage: PLAN_REVIEW
If tasks.md exists but not all [x] → Stage: IMPLEMENTATION_REVIEW
If all tasks [x] → Stage: FINAL_REVIEW (pre-merge)
```

Report the detected stage to the user.

### Step 1.5: Three Review Axes

모든 리뷰는 반드시 아래 **3가지 축**을 명시적으로 점검해야 한다.

#### Axis 1: Spec Gap (기획 정합성)
- spec ↔ plan ↔ tasks 간 누락/불일치가 없는지
- 구현이 spec의 요구사항(FR)과 성공 기준(SC)을 충족하는지
- 용어가 문서 간 통일되어 있는지
- spec에 정의된 edge case가 구현/계획에 반영되었는지

#### Axis 2: Software Defect (결함 탐지)
- 로직 오류, off-by-one, null/undefined 처리 누락
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

### Step 2: Generate Review Request

Based on the detected stage, create a **review request document** with the right context:

#### SPEC_REVIEW context:

```markdown
## Review Request: Spec Review — {feature}
**Branch**: {branch}
**Focus**: spec.md 완성도, 요구사항 명확성, scope 적절성
**Files to review**: specs/{feature}/spec.md
**Check for**:
- 모호한 요구사항 (measurable criteria 없는 것)
- scope 누락/과잉
- 용어 일관성
- acceptance criteria 테스트 가능성
```

#### PLAN_REVIEW context:

```markdown
## Review Request: Plan Review — {feature}
**Branch**: {branch}
**Focus**: plan.md ↔ spec.md 정합성, 아키텍처 결정, 기술 리스크
**Files to review**: specs/{feature}/plan.md, spec.md
**Check for**:
- spec 요구사항이 plan에 빠짐없이 반영되었는지
- 아키텍처 결정의 근거
- 기술 리스크와 대응 방안
- 파일/모듈 구조 합리성
```

#### IMPLEMENTATION_REVIEW context:

```markdown
## Review Request: Implementation Review — {feature}
**Branch**: {branch}
**Focus**: 코드 정확성, 테스트 커버리지, spec/plan 대비 갭
**Files to review**: (git diff main...HEAD --stat 결과)
**Check for**:
- 버그, 패닉, 에러 핸들링 누락
- 테스트 커버리지 갭
- spec/plan과 구현의 불일치
- task 완료 표시와 실제 구현의 불일치 (stub/placeholder를 완료로 체크한 것)
- 보안 이슈 (credential 누출, injection 등)
```

#### FINAL_REVIEW context:

```markdown
## Review Request: Pre-Merge Final Review — {feature}
**Branch**: {branch}
**Focus**: 머지 준비 상태, 문서 정합성, 잔여 이슈
**Files to review**: 전체 브랜치 diff
**Check for**:
- tasks.md [~] partial 항목이 정직하게 표시되었는지
- CLAUDE.md, play-language-reference.md 동기화
- cargo test --workspace 결과
- Known gaps가 문서화되었는지
- 머지 커밋 메시지에 포함할 내용
```

### Step 3: Save Review Request + Create GitHub Issue

1. Write the review request to `specs/{feature}/codex-review-{feature}.md` (or update if exists).
2. Commit and push the review request file.
3. **Create a GitHub issue** for the review using `gh issue create`:
   - Title: `Codex Review Request: {feature} — {STAGE}`
   - Body: the review request content (same as the `.md` file)
   - Label: none, unless available
4. Report the issue URL to the user.

### Step 4: Prompt User for Relay

Output:

```text
## 코덱스 리뷰 요청 준비 완료

📋 리뷰 요청서: `specs/{feature}/codex-review-{feature}.md`
🔗 GitHub Issue: **{issue_url}** ← 코덱스에게 이 링크를 전달해주세요
📌 단계: {STAGE}
🌿 브랜치: `{branch}`

### 다음 행동
1. 위 **GitHub Issue 링크**를 코덱스에게 전달해주세요
2. 코덱스의 **Findings** 결과를 여기에 붙여넣어 주세요
3. 또는 "no findings" / "sign-off" 라고 입력하면 종료합니다

대기 중...
```

### Step 5: Parse Findings

When user pastes Codex findings:

1. Parse each finding:
   - Severity (Critical / High / Medium / Low)
   - Location (file:line)
   - Description
   - Recommendation

2. Report parsed findings:

```text
## 파싱된 Findings

| # | Severity | Location | Summary |
|---|----------|----------|---------|
| 1 | HIGH | lib.rs:123 | ... |
| 2 | MEDIUM | spec.md:45 | ... |

총 N건. 자동 수정을 시작합니다.
```

### Step 6: Fix All

For each finding:
1. Read the referenced file
2. Apply the fix
3. If the fix is ambiguous, ask user for clarification (counts as same round)
4. Mark as fixed

After all fixes:
1. Run `cargo test --workspace` (if implementation stage)
2. Commit with message: `fix: address codex review round N — {summary}`
3. Push

### Step 7: Request Re-Review

1. **Post a comment on the GitHub issue** using `gh issue comment`:
   - Body: Round N 수정 요약 + 커밋 해시 + re-review 요청
2. Output to user:

```text
## Round {N} 수정 완료

| # | Finding | Status |
|---|---------|--------|
| 1 | {summary} | ✅ Fixed |
| 2 | {summary} | ✅ Fixed |

커밋: {hash}
푸시: ✅
GitHub Issue 댓글: ✅ (re-review 요청)

### 다음 행동
코덱스에게 re-review를 요청해주세요.
결과를 붙여넣어 주세요. "no findings" 이면 종료합니다.
```

### Step 8: Loop or Complete

- If user pastes new findings → Go to Step 5
- If user says "no findings", "sign-off", "clean", or "done" → Proceed to completion

### Step 9: Completion

```text
## 코덱스 리뷰 완료 🎉

총 라운드: {N}
총 수정: {total_fixes}
최종 상태: Sign-off

### 다음 단계 제안
- `/speckit.implement {feature}` — 구현 시작 (if spec/plan stage)
- main 머지 준비 완료 (if final review)
```

## Behavior Rules

- **절대 findings를 무시하지 않는다** — 모든 finding에 대해 fix 시도
- fix가 불가능하면 (아키텍처 변경 필요 등) 이유를 설명하고 deferred로 표시
- **정직하게** — stub or placeholder를 완료로 체크하지 않는다
- 각 라운드 후 반드시 커밋 + 푸시
- 최대 10 라운드 — 10라운드 초과 시 "리뷰가 수렴하지 않음" 경고
- 사용자가 "stop", "abort", or "skip" 하면 즉시 중단

## Context

{ARGS}
