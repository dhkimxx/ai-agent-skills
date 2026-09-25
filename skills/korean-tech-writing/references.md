# 레퍼런스 — 한국어 기술문서 작성

이 스킬 규칙의 근거 자료 (2026-09 조사). 각 항목에 **무엇을 가져왔는지**를 함께 적었다.

## 1. 용어·표기 표준

| 자료 | 성격 | 이 스킬에 반영된 것 | 위치 |
|---|---|---|---|
| **TTA 정보통신용어사전** | ICT 용어의 표준 한국어 표기 | 한글 표기가 갈릴 때 **1차 기준** | terms.tta.or.kr |
| **국립국어원 다듬은 말** | 어려운 외래어·한자어의 쉬운 우리말 대안(수만 항목) | "쉬운 말 먼저, 정식 용어 병기" 원칙 | korean.go.kr → 개선 → 다듬은 말 |
| **국립국어원 온라인가나다** | 맞춤법·띄어쓰기 판단 | 애매할 때 확인용 | korean.go.kr |

## 2. 문체·표기 스타일 가이드

| 자료 | 성격 | 이 스킬에 반영된 것 | 위치 |
|---|---|---|---|
| **Mozilla 한국어 지역화 가이드** | 가장 구체적인 한국어 규칙 | 상표 원문 유지 · 개발 용어 관용 표기(버그/벌레) · 조사 병기 지양 · 수동태·번역체 회피 · 마침표=완전문장 | mozilla-l10n.github.io/styleguides/ko/ |
| **KDE 한국어 가이드** | 번역 문체 | 영어 어순 1:1 직역 지양 | community.kde.org/KDE_Localization/ko/styleguide |
| **WordPress.com 한국어 가이드** | 표기 세부 | 제품·기능 이름의 대소문자 유지, 약어 규칙 | translate.wordpress.com → Korean style guide |
| **Google Developer Documentation Style Guide** | 영문 기술문서 표준 | 2인칭("you") · 현재 시제 · 조건 먼저 · 번역 친화 문장 | developers.google.com/style |
| **Microsoft Writing Style Guide** | 평이한 언어 | "간단히/쉽게" 금지, 편견 없는 표현 | learn.microsoft.com/style-guide |

## 3. 구조·방법론

| 자료 | 성격 | 이 스킬에 반영된 것 | 위치 |
|---|---|---|---|
| **Diátaxis** | 문서 유형 표준 | 4유형(튜토리얼·하우투·레퍼런스·설명) 분리, **유형 혼합 금지** | diataxis.fr |
| **Google Technical Writing One/Two** | 실습형 교육 과정 | 용어 일관성 · 모호한 대명사 제거 · 구체 동사 · 목록·표 규칙(도입 문장·병렬·동사 시작) · 지식의 저주 | developers.google.com/tech-writing |
| **The Good Docs Project** | 문서 템플릿 모음 | 유형 분류 교차 확인, 참고 링크는 하단에 모으기 | thegooddocsproject.dev |
| **Docs for Developers** | 작성 프로세스 | 6단계(요구사항 → 독자 → 개요 → 초안 → 리뷰 → 발행) | 도서(한빛) |
| **인포그랩 테크니컬 라이팅 10원칙** | 실무 원칙 | "초보자 대상이면 초보자를 리뷰어로" | insight.infograb.net |

## 4. 도구 (선택)

| 도구 | 용도 | 비고 |
|---|---|---|
| `hanlint` | 한국어 산문 린터(prose linter) — 번역투·이중 피동·명사 나열 검사 | PyPI·npm, 프리셋 `docs`/`blog` |
| `textlint` | 자연어 린트 프레임워크(+프리셋) | npm. 일본어 기술문서 프리셋이 참고 사례 |
| `Vale` | 영문 산문 린터(Google·Microsoft 스타일 내장) | 영문 문서를 함께 쓸 때 |

글리프 검사(폰트 커버리지 대조)는 프로젝트마다 도구가 다르므로 프로젝트 문서에 적는다.

## 5. 규칙 → 출처 매핑 (추적용)

| 이 스킬의 규칙 | 출처 |
|---|---|
| 첫 등장 `한글(English)` 병기 | Mozilla · Google Technical Writing |
| 쉬운 말 먼저, 정식 용어 병기 | 국립국어원 다듬은 말 |
| 용어 일관성(같은 개념에 같은 단어) | Google Technical Writing · Mozilla |
| 능동태 · 현재 시제 · 2인칭 | Google Style Guide |
| 조건 먼저 → 지시 나중 | Google Style Guide |
| 모호한 대명사 제거(명사 반복) | Google Technical Writing |
| 구체 동사 | Google Technical Writing |
| 목록·표 규칙(도입 문장·병렬·동사 시작) | Google Technical Writing · Good Docs |
| 문서 유형 6종(4유형 + 교재·브리프) | Diátaxis + 실무 확장 |
| 문제 → 해결 순서 | Diátaxis · Docs for Developers |
| 작성 6단계 · 초보자 리뷰어 | Docs for Developers · 인포그랩 |
| 금지 표현("쉽게/간단히/그냥") | Microsoft Style Guide |
| 상표·제품명 원문 유지 · 관용 표기 | Mozilla · WordPress |
| 조사 병기 지양(`은(는)`) | Mozilla |
| 마침표 = 완전문장, 없으면 명사구 | Mozilla |
| 글리프 함정(`Σ`·`−`·`①`·`✅`) | 자체 점검에서 추가(폰트 실측) |
