---
description: "Run OQ's multi-round Markdown and spec document review workflow."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
- If user specifies a file (for example "SPEC.md"), review only that file.
- If user specifies `specs/` or a spec number (for example "01"), review only that spec folder.
- If empty, review ALL `md` files in project root + `specs/`.

## Goal

프로젝트의 마크다운 문서를 전문적으로 리뷰하여 품질을 보장한다.
**auto-review 패턴**: GitHub Issue 생성 → 라운드별 검사/수정 → 커밋/푸시 → re-check → 완료 시 Issue close.

## Step 0: Pre-flight Checks

1. **gh CLI**: `which gh` — 없으면 경고 후 Issue 없이 진행 (오프라인 모드)
2. **Git branch**: 현재 브랜치 확인. `main`이면 `review/doc-review-{YYYYMMDD}` 브랜치 생성
3. **Clean working tree**: `git status --porcelain` — 미커밋 있으면 경고
4. **Remote**: `git remote -v` — push 가능 여부

Feature branch가 아니면:

```bash
git checkout -b review/doc-review-$(date +%Y%m%d-%H%M%S)
```

## Step 1: GitHub Issue 생성

```bash
gh issue create \
  --title "Doc Review: $(date +%Y-%m-%d)" \
  --body "## 문서 자동 리뷰

대상: 프로젝트 루트 md 파일 + specs/ 폴더
Branch: $(git branch --show-current)
검사 축: 구조, 일관성, 완성도, 정확성, 가독성, 교차 정합성

상태: 🔄 진행 중"
```

Issue 번호 저장. `gh` 없으면 이 단계 skip.

## Step 2: 대상 파일 수집

```bash
find . -maxdepth 1 -name "*.md" -type f | sort
find ./specs -name "*.md" -type f | sort 2>/dev/null
```

각 파일의 줄 수와 마지막 수정일도 수집.

## Step 3: Round 1 — 전체 리뷰 (6개 축)

각 md 파일을 **반드시 Read로 읽은 후** 아래 6개 축으로 검사.

### 축 1: 구조 & 포맷 (Structure)
- 제목(H1) 존재
- 섹션 번호 순차 (`## 1`, `## 2`, `## 3`...)
- 깨진 마크다운 (코드블록, 테이블)
- 깨진 상대 링크 (`[text](file.md)` → 파일 존재 확인)
- 빈 섹션 (제목만 있고 내용 없음)

### 축 2: 일관성 (Consistency)
- 용어 통일 ("매장" vs "스토어", "플라이" vs "Fly.io")
- 숫자 일관성 (같은 수치가 문서마다 다른 경우)
- 기술 스택 일관성 (`SPEC.md` vs sub spec)
- Phase 번호 or 이름 일관성
- Constitution 원칙과 문서 내용의 충돌

### 축 3: 완성도 (Completeness)
- `SPEC.md`에 언급된 기능이 sub spec에 빠져 있는가
- TODO, TBD, placeholder 마커
- 참조 문서 실제 존재 여부
- 가격 or 비용 빠진 곳
- Success Criteria 측정 가능성

### 축 4: 정확성 (Accuracy)
- 오래된 정보 (날짜, 버전)
- 잘못된 기술 참조
- 계산 오류
- Constitution 위반 문구

### 축 5: 가독성 (Readability)
- 비개발자 이해 가능성
- 과도하게 긴 섹션 (100줄+)
- 약어 미설명 (GBP, CMS, ETL 등)
- 코드 블록 언어 태그

### 축 6: 교차 문서 정합성 (Cross-Document)
- `SPEC.md` ↔ sub specs
- `SPEC.md` ↔ `DATA_SOURCES.md`
- `SPEC.md` ↔ `COMPETITIVE_ANALYSIS.md`
- `SPEC.md` ↔ `GUIDE.md`
- `SPEC.md` ↔ Constitution
- `SPEC.md` 스펙 분해 계획 ↔ `specs/` 실제 파일

### 축 7: 코드 정합성 (Code Alignment)

소스코드가 존재하는 경우 문서와 코드의 정합성을 검사:
- 스펙의 DB 스키마(SQL) ↔ 실제 마이그레이션 or 스키마 파일
- 스펙의 API 엔드포인트 ↔ 실제 라우트 파일 (`pages/api/`, `app/api/`)
- 스펙의 환경 변수 목록 ↔ `.env.example`, `fly.toml`, `Dockerfile`
- 스펙의 기술 스택 ↔ `package.json` dependencies, `requirements.txt`
- 스펙의 디렉토리 구조 ↔ 실제 파일 시스템
- `GUIDE.md`의 명령어 ↔ `package.json` scripts, `Makefile`
- Constitution의 Non-Negotiable Rules ↔ 실제 코드 준수 여부

코드가 아직 없으면 이 축은 skip하고 "코드 미존재, 향후 재검토" 표시.

## Step 4: 발견 사항 분류

| 심각도 | 기준 | 처리 |
|--------|------|------|
| **CRITICAL** | Constitution 위반, 계산 오류, 모순 | 즉시 수정 |
| **HIGH** | 누락, 깨진 링크, 일관성 오류 | 즉시 수정 |
| **MEDIUM** | 용어 불일치, 빈 섹션 | 수정 |
| **LOW** | 스타일, 포맷 | 리포트만 |

## Step 5: 자동 수정 + 커밋

CRITICAL → HIGH → MEDIUM 순서로 수정.

**수정 규칙**:
- `SPEC.md`가 마스터 — 충돌 시 `SPEC.md` 기준
- Constitution이 최상위 — 위반 시 Constitution이 이김
- 기존 의도를 바꾸지 않음 (형식/정확성만)
- 수정 전 반드시 Read

수정 완료 후:

```bash
git add -A
git commit -m "docs: doc-review round 1 — {N} issues fixed

{summary table}

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin $(git branch --show-current)
```

## Step 6: Issue에 라운드 결과 포스팅

```bash
gh issue comment {issue_number} --body "## Round 1 결과

| # | 심각도 | 파일 | 축 | 설명 | 처리 |
|---|--------|------|----|------|------|
| 1 | CRITICAL | ... | ... | ... | ✅ 수정 |
| ... |

수정: {fixed}건 / 미수정(LOW): {skipped}건
커밋: {hash}"
```

## Step 7: Codex 크로스 체크

Claude가 수정한 내용을 Codex에게 독립적으로 검증받는다.

### 7.1 Pre-check

```bash
which codex
```

`codex` CLI가 없으면 이 단계 skip → Step 8로.

### 7.2 Codex Review 실행

```bash
codex review --base main 2>&1
```

- Timeout: 5분
- 전체 stdout 캡처

### 7.3 Codex 결과 파싱

Codex 출력에서 문서 관련 발견 사항을 추출:
- 일관성 문제 (Claude가 놓친 것)
- 문서 ↔ 코드 정합성 (코드가 있는 경우)
- 추가 모순 or 누락

### 7.4 Codex 발견 처리

| Codex 결과 | 처리 |
|-----------|------|
| "LGTM" / 이슈 없음 | Codex sign-off → Step 9 |
| CRITICAL or HIGH 발견 | Claude가 수정 → 커밋 → 다시 Codex 실행 (최대 2회) |
| MEDIUM or LOW 발견 | Issue에 기록, 수정은 선택 |

### 7.5 Issue에 Codex 결과 포스팅

```bash
gh issue comment {issue_number} --body "## Codex Cross-Check

{codex_output_summary}

상태: {LGTM | N건 추가 발견}"
```

> Codex가 추가 이슈를 발견하면 Claude가 수정 → 커밋 → Codex 재실행 (최대 2라운드).
> Codex 크로스 체크는 "다른 눈으로 한번 더 보는 것"이 목적.

## Step 8: Round 2 — Re-check (Claude)

수정된 파일들을 다시 읽고 검사:
- Round 1에서 수정한 것이 새 모순을 만들지 않았는가?
- Codex가 발견한 이슈가 모두 해결되었는가?
- CRITICAL or HIGH가 0개가 될 때까지 반복 (최대 3 라운드)

추가 발견 있으면 → Step 5로 돌아감.

## Step 9: 완료

모든 CRITICAL or HIGH가 0이 되면:

```bash
gh issue comment {issue_number} --body "## Doc Review 완료 ✅

총 라운드: {N}
총 수정: {total_fixes}건
잔여 LOW: {remaining}건

최종 상태: CRITICAL 0 / HIGH 0"

gh issue close {issue_number}
```

출력:

```text
╭─── Doc Review 완료 ─────────────────────────────────────╮
│                                                          │
│  검토 파일: {N}개                                        │
│  총 라운드: {rounds}                                     │
│  총 발견: {total} (C:{c} H:{h} M:{m} L:{l})             │
│  수정 완료: {fixed}개                                    │
│  GitHub Issue: {url} (closed)                            │
│                                                          │
│  파일별 요약:                                            │
│  ├── SPEC.md          {n}건 수정                         │
│  ├── DATA_SOURCES.md  {n}건 수정                         │
│  ├── specs/01-infra/  {n}건 수정                         │
│  └── ...                                                 │
│                                                          │
│  교차 정합성: {pass}/{total} 통과                         │
│                                                          │
│  다음 단계:                                              │
│  - main 머지: git checkout main && git merge {branch}    │
│  - 또는 PR 생성: gh pr create                            │
╰──────────────────────────────────────────────────────────╯
```

## Behavior Rules

- **최대 3 라운드 (Claude) + 2 라운드 (Codex)** — 수렴하지 않으면 잔여 이슈 리포트하고 중단
- Codex 크로스 체크는 Claude 수정 후 실행. `codex` CLI 없으면 skip
- 문서 의도를 바꾸지 않는다
- `SPEC.md` 마스터, Constitution 최상위
