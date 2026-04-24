---
description: "Run OQ's strict automated review loop including LOW severity findings."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

`/speckit.auto-review`의 엄격 버전. 모든 severity(CRITICAL~LOW)를 수정하고, Claude 셀프 리뷰 루프로 수정 재검증까지 한다. 머지 전 최종 품질 게이트.

## Prerequisites

- `codex` CLI installed and authenticated (`codex login`)
- `gh` CLI installed and authenticated (`gh auth login`)
- Git repo with remote configured
- Feature branch (not main)

## Workflow

### Step 0: Pre-flight Checks

Same as `/speckit.auto-review`.

### Step 1: Detect Stage + Generate Context

Same as `/speckit.auto-review`.

### Step 1.5: Three Review Axes (STRICT)

모든 리뷰는 **3가지 축 × ALL severity levels**를 점검한다.
기본 auto-review와 달리 **LOW도 수정 대상**이다.

#### Axis 1: Spec Gap (기획 정합성)
- spec ↔ plan ↔ tasks 간 누락/불일치가 없는지
- 구현이 spec의 요구사항(FR)과 성공 기준(SC)을 충족하는지
- 용어가 문서 간 통일되어 있는지
- spec에 정의된 edge case가 구현/계획에 반영되었는지
- **[STRICT]** 문서 스타일 일관성 (마크다운 포맷, 헤딩 레벨)
- **[STRICT]** 참조 경로의 정확성 (존재하지 않는 파일 참조 없는지)

#### Axis 2: Software Defect (결함 탐지)
- 로직 오류, off-by-one, null or undefined 처리 누락
- 보안 취약점 (injection, 인증/인가 누락, 민감정보 노출)
- 동시성/경쟁 조건, 리소스 누수
- 에러 핸들링 누락 또는 부적절한 에러 전파
- 성능 병목 (N+1 쿼리, 불필요한 반복 등)
- **[STRICT]** 변수 미사용, 데드 코드
- **[STRICT]** 하드코딩된 값 (config로 추출해야 할 것)
- **[STRICT]** 셸 스크립트: 변수 미인용, word splitting 위험

#### Axis 3: Test Coverage (테스트 보완)
- 새로 추가/변경된 기능에 대한 테스트가 있는지
- edge case와 실패 시나리오에 대한 테스트가 있는지
- spec의 acceptance scenario가 테스트로 커버되는지
- 기존 테스트가 변경으로 인해 깨지지 않는지
- **[STRICT]** 각 Phase checkpoint의 검증 가능성
- **[STRICT]** 수동 테스트 절차의 구체성

**Severity 분류**: CRITICAL > HIGH > MEDIUM > LOW 모두 수정 대상.

### Step 2: Create GitHub Issue

Title에 `[STRICT]` 마커 추가:
- Title: `[STRICT] Auto Review: {feature} — {STAGE}`

### Step 3: Run Codex Review

Same as `/speckit.auto-review`.

### Step 4: Parse Codex Output + Claude 심층 리뷰

**기본과 다른 점**:

1. Codex findings 파싱 (동일)
2. **Claude 3축 심층 리뷰 — 반드시 수행** (Codex LGTM이어도)
3. **LOW까지 포함하여 전체 findings 목록 생성**
4. findings를 severity별로 정렬: CRITICAL → HIGH → MEDIUM → LOW

### Step 5: Post Findings to Issue

Severity별 분류 테이블로 게시:

```markdown
## Codex + Claude Strict Review Round {N}

### 🔴 CRITICAL
...
### 🟠 HIGH
...
### 🟡 MEDIUM
...
### 🔵 LOW
...
```

### Step 6: Fix ALL Findings (LOW 포함)

기본 auto-review는 HIGH or MEDIUM만 수정하지만, **strict는 LOW도 수정**:

1. CRITICAL → HIGH → MEDIUM → LOW 순서로 수정
2. 각 수정 후 **셀프 체크** (아래 Step 6.5)
3. 모든 수정 완료 후 커밋 + 푸시

### Step 6.5: 셀프 리뷰 (Self-Check) ⭐ NEW

**매 수정 후** Claude가 자체 재검증:

```text
수정 적용 후:
  1. 수정이 원래 finding을 실제로 해결했는지 확인
  2. 수정이 새로운 문제를 도입하지 않았는지 확인
  3. 수정이 다른 파일의 기존 코드와 일관성을 유지하는지 확인

  결과:
  - ✅ PASS → 다음 finding으로
  - ❌ FAIL → 수정 재시도 (최대 2회)
  - ⚠️ PARTIAL → 부분 수정 기록 + 다음 finding으로
```

### Step 7: Post Fix Summary

Same as `/speckit.auto-review` + 셀프 체크 결과 포함:

```markdown
## Round {N} Fixes (STRICT)

| # | Severity | Finding | Fix | Self-Check |
|---|----------|---------|-----|------------|
| 1 | HIGH | ... | ... | ✅ PASS |
| 2 | MEDIUM | ... | ... | ✅ PASS |
| 3 | LOW | ... | ... | ⚠️ PARTIAL |
```

### Step 8: Re-Run Codex + Claude

Codex review 재실행 + Claude 3축 재점검.

### Step 9: Loop or Complete

- findings 있음 → Step 4
- findings 없음 → **Step 9.5 (Final Self-Review)**

### Step 9.5: Final Self-Review ⭐ NEW

Codex + Claude 모두 LGTM 후, **마지막 셀프 리뷰 루프**:

```text
최종 셀프 리뷰:
  1. 전체 diff (main...HEAD) 한번 더 읽기
  2. 이번 리뷰에서 수정한 모든 파일을 다시 확인
  3. 체크리스트:
     - [ ] 모든 finding이 실제로 수정되었는가
     - [ ] 수정이 새로운 문제를 도입하지 않았는가
     - [ ] 코드/문서 스타일이 일관적인가
     - [ ] 하드코딩, 데드코드, 미사용 변수가 없는가
     - [ ] 참조 경로가 모두 유효한가

  결과:
  - 전부 ✅ → Sign-off
  - 일부 ❌ → 수정 후 다시 Step 9.5 (최대 2회)
```

### Step 10: Completion

```bash
gh issue close {issue_number} --comment "[STRICT] Auto review complete — {N} rounds, {total_fixes} fixes, {self_check_count} self-checks."
```

Output:

```text
## [STRICT] Auto Review 완료 🎉

총 라운드: {N}
총 수정: {total_fixes} (CRITICAL: {c}, HIGH: {h}, MEDIUM: {m}, LOW: {l})
셀프 체크: {self_check_count}회 ({pass_count} pass, {partial_count} partial)
최종 셀프 리뷰: ✅ PASS
GitHub Issue: {issue_url} (closed)
최종 상태: Sign-off (STRICT)

### 다음 단계
- main 머지 준비 완료 (strict 검증 통과)
```

## Auto-Detect Test Command

Same as `/speckit.auto-review`.

## Behavior Rules

- Maximum **15 rounds** (기본은 10) — strict는 LOW 수정으로 라운드가 늘어날 수 있음
- **ALL severity levels** 수정 대상 (기본은 HIGH or MEDIUM만)
- **셀프 체크** 매 수정 후 + 최종 1회
- 셀프 체크 실패 시 **최대 2회 재시도** 후 PARTIAL로 기록
- 최종 셀프 리뷰도 **최대 2회 재시도**
- Post every round to the tracking GitHub issue
- If codex review command fails, fall back to Claude-only strict review (Codex 없이도 진행)
- Never ignore findings — fix or defer with explanation
- Honestly mark stubs or placeholders

## Fallback

If `codex` CLI is not available:

```text
⚠️ codex CLI not available. Claude-only strict review로 진행합니다.
(Codex 대신 Claude가 3축 전체를 단독 수행)
```

## 기본 auto-review와의 차이 요약

| 항목 | auto-review | auto-review-strict |
|------|-------------|-------------------|
| 수정 대상 | HIGH + MEDIUM | ALL (CRITICAL~LOW) |
| 셀프 체크 | 없음 | 매 수정 후 재검증 |
| 최종 셀프 리뷰 | 없음 | Codex+Claude LGTM 후 1회 |
| 최대 라운드 | 10 | 15 |
| Codex 없을 때 | fallback to manual | Claude-only로 계속 진행 |
| LOW 항목 | 무시 | 수정 |
| 추가 체크 | — | 데드코드, 하드코딩, 변수 미인용, 참조 경로 유효성 |
| Issue 제목 | Auto Review | [STRICT] Auto Review |

## Context

{ARGS}
