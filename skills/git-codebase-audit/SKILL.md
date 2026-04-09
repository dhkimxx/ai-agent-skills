---
name: git-codebase-audit
description: "Git 이력만으로 새로운 코드베이스의 구조와 위험 구역을 빠르게 진단하는 스킬. git log, git shortlog, churn, bug hotspot, bus factor, hotfix, revert, rollback, 코드베이스 분석, Git 이력 분석."
argument-hint: "[repo-path] [분석 범위 또는 질문]"
---

# Git Codebase Audit

## 목적

- 코드 파일을 열기 전에 Git 이력으로 탐색 우선순위를 정한다.
- 변경 빈도, 버그 집중도, 기여자 편중, 활동 추세, 긴급 대응 신호를 한 번에 훑는다.
- 어디부터 읽어야 하는지와 어떤 파일을 조심해야 하는지를 빠르게 판단한다.

## 언제 사용하나

- 새로운 저장소를 처음 분석할 때
- 코드 리뷰 전에 위험 구역을 좁혀야 할 때
- 유지보수 공백, 버스 팩터, 배포 안정성을 빠르게 점검할 때

## 컨텍스트 절약 규칙

- 코드 검색이나 파일 열람보다 먼저 이 스킬의 Git 분석을 실행한다.
- 결과 해석 기준이 더 필요할 때만 `references/risk-signals.md`를 읽는다.
- 스크립트 출력에서 겹치는 위험 파일을 찾은 뒤에만 실제 코드로 내려간다.

## 필수 실행 순서

1. 현재 경로가 Git 저장소인지 확인한다.
2. 기본적으로 `scripts/analyze_git_history.py`를 실행한다.
3. `변경 빈도 상위 파일`과 `버그 커밋 상위 파일`의 겹침을 먼저 본다.
4. 상위 기여자 편중과 최근 활동 공백을 확인한다.
5. 월별 커밋 추세와 `revert`/`hotfix` 신호를 보고 배포 안정성을 추정한다.
6. 이 결과를 바탕으로 읽을 파일 순서를 정한다.

## 빠른 시작

기본 실행:

```bash
python3 skills/git-codebase-audit/scripts/analyze_git_history.py --repo .
```

기간을 명시해 더 넓게 보기:

```bash
python3 skills/git-codebase-audit/scripts/analyze_git_history.py \
  --repo . \
  --since "1 year ago" \
  --activity-since "24 months ago" \
  --recent-activity-since "6 months ago" \
  --limit 20
```

## 원문 명령을 그대로 써야 할 때

스크립트 대신 원문 흐름이 필요하면 아래 다섯 가지를 순서대로 실행한다.

```bash
git log --format=format: --name-only --since="1 year ago" | sort | uniq -c | sort -nr | head -20
git shortlog -sn --no-merges
git log -i -E --grep="fix|bug|broken" --name-only --format='' | sort | uniq -c | sort -nr | head -20
git log --format='%ad' --date=format:'%Y-%m' | sort | uniq -c
git log --oneline --since="1 year ago" | grep -iE 'revert|hotfix|emergency|rollback'
```

## 출력 계약

최종 응답에는 아래 항목이 반드시 들어가야 한다.

1. 어떤 기간을 기준으로 분석했는지
2. 최근 변경 빈도 상위 파일
3. 버그 관련 커밋 상위 파일
4. 두 목록이 겹치는 고위험 파일
5. 기여자 분포, 상위 기여자 집중도, 최근 활동 공백
6. 월별 커밋 추세
7. `revert`/`hotfix`/`rollback` 관련 신호
8. 결과를 왜곡할 수 있는 주의사항

## 해석 규칙

- 변경 빈도와 버그 커밋이 동시에 높은 파일을 최우선 위험 파일로 본다.
- 상위 1명이 비병합 커밋의 60% 이상이면 버스 팩터 위험으로 본다.
- 상위 기여자가 최근 6개월 동안 활동하지 않았다면 유지보수 공백 가능성을 경고한다.
- 긴급 대응 커밋이 잦다면 테스트, 릴리스, 롤백 절차 문제를 의심한다.

자세한 해석 기준과 왜곡 요인은 `references/risk-signals.md`를 읽는다.
