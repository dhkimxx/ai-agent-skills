---
name: naver-land-scouter
description: "네이버 부동산 데이터 탐색과 분석을 위한 스킬. 지도 기반 단지 탐색, 단지 심층 분석, 매물 비교, 투자 지표 산출, 학군/교통 요약 리포트 생성에 사용한다. Keywords: 네이버 부동산, 매물 찾기, 시세 분석, 단지 정보, 부동산 임장 보고서, naver land, complex, article, price, school, transportation"
---

# Naver Land Scouter

## 목표
- 네이버 부동산 API 관측 결과를 기반으로 매물/단지 데이터를 수집·요약한다.
- 하이브리드 마크다운 형식으로 사람이 읽기 쉬운 보고서와 시스템 연동 JSON을 동시에 제공한다.

## 필수 규칙
1. 모든 가격은 **만원 단위 정수**로 처리한다.
2. `directions` 필터는 `S:SW:SE` 형태의 콜론 구분 문자열로 전송한다.
3. 면적 입력의 `평`은 `1평 = 3.3058㎡`로 변환해 API를 호출한다.
4. 응답 필드가 누락되거나 변형될 수 있으므로 방어적으로 처리한다.
5. 지도 탐색 시 `cortars` → `single-markers` 순서로 호출한다.
6. 401/403/429가 나오면 쿠키/헤더를 주입해 재시도한다.
7. 기본 동작은 `bootstrap-mode=auto`이며, 먼저 공개 페이지를 방문해 익명 세션을 만든 뒤 API를 호출한다.

## 빠른 시작
```bash
cd skills/naver-land-scouter

# 기본 권장: 자동 익명 세션 부트스트랩
uv run --project . python -m scripts.cli \
  --bootstrap-mode auto \
  discover \
  --center-lat 37.269736 \
  --center-lon 127.075797 \
  --zoom 17 \
  --left-lon 127.0689305 \
  --right-lon 127.0826635 \
  --top-lat 37.2731041 \
  --bottom-lat 37.2663677 \
  --real-estate-type APT:ABYG:JGC:PRE

# 매물 리스트
uv run --project . python -m scripts.cli listings \
  --complex-no 11084 \
  --real-estate-type APT:ABYG:JGC:PRE \
  --trade-type A1 \
  --price-max "10억" \
  --area-min "30평" \
  --area-max "40평"

# 단지 리포트
uv run --project . python -m scripts.cli complex \
  --complex-no 11084 \
  --trade-type A1 \
  --year 5 \
  --transport-zoom 17 \
  --bbox 127.0689 127.0827 37.2731 37.2663

# 매물 비교
uv run --project . python -m scripts.cli compare \
  --article-no 2613227531 \
  --article-no 2613227532

# 투자 지표
uv run --project . python -m scripts.cli invest \
  --article-no 2613227531

# 지도 탐색
uv run --project . python -m scripts.cli discover \
  --center-lat 37.269736 \
  --center-lon 127.075797 \
  --zoom 17 \
  --left-lon 127.0689305 \
  --right-lon 127.0826635 \
  --top-lat 37.2731041 \
  --bottom-lat 37.2663677 \
  --real-estate-type APT:ABYG:JGC:PRE

# 헤더/쿠키 주입 (403/429 대응)
uv run --project . python -m scripts.cli \
  --cookie "NID_SES=..." \
  --cookie "NID_AUT=..." \
  --complex-no 11084 \
  --real-estate-type APT:ABYG:JGC:PRE \
  --header "Referer:https://new.land.naver.com/" \
  --header "User-Agent:Mozilla/5.0 ..." \
  listings

# 환경 변수 주입 (JSON 또는 세미콜론 구분)
export NAVER_LAND_HEADERS='{"Referer":"https://new.land.naver.com/","User-Agent":"Mozilla/5.0 ..."}'
export NAVER_LAND_COOKIES='NID_SES=...; NID_AUT=...'
uv run --project . python -m scripts.cli listings \
  --complex-no 11084 \
  --real-estate-type APT:ABYG:JGC:PRE

# 브라우저 부트스트랩 강제 (Playwright 설치 시)
uv run --project . python -m scripts.cli \
  --bootstrap-mode browser \
  discover \
  --center-lat 37.269736 \
  --center-lon 127.075797 \
  --zoom 17 \
  --left-lon 127.0689305 \
  --right-lon 127.0826635 \
  --top-lat 37.2731041 \
  --bottom-lat 37.2663677 \
  --real-estate-type APT:ABYG:JGC:PRE
```

## 세션 전략
- `auto`: 기본값. `httpx`로 공개 페이지를 먼저 방문해 익명 쿠키를 만들고, 403/429가 계속되면 Playwright 브라우저 부트스트랩으로 승격한다.
- `auto`: 기본값. `httpx`로 공개 페이지를 먼저 방문해 익명 쿠키를 만들고, 401/403/429가 발생하면 Playwright 브라우저 부트스트랩으로 승격한다.
- `http`: 공개 페이지 방문만 수행한다.
- `browser`: 처음부터 헤드리스 Chromium으로 쿠키를 만든다.
- `none`: 세션 부트스트랩을 하지 않는다.
- `articles/*` 계열은 브라우저가 보내는 익명 `Authorization: Bearer ...` 헤더가 필요할 수 있다. `auto`/`browser` 모드는 이 헤더를 브라우저 요청에서 캡처해 재사용한다.
- 브라우저 부트스트랩을 실제로 쓰려면 1회 `uv run playwright install chromium`이 필요할 수 있다.

## 하이브리드 출력 계약
- 상단: 요약 텍스트 + 비교 표(매물/단지/투자 기준)
- 하단: `<details>` 내부의 JSON 코드 블록
- 가격은 사람이 읽기 쉬운 단위(예: 10억 5천)로 표기한다.
- JSON 내부 값은 만원 단위 정수로 유지한다.

## 참고 문서
- [api_endpoints.md](references/api_endpoints.md)
- [param_dictionary.md](references/param_dictionary.md)
- [ops_policies.md](references/ops_policies.md)
- [workflows.md](references/workflows.md)
