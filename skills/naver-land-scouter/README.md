# naver-land-scouter

> 네이버 부동산 데이터를 탐색·분석해 리포트까지 만드는 스킬.
> 단지 탐색, 매물 비교, 시세·학군·교통 요약에 사용합니다.

- **설치**: `npx skills add dhkimxx/ai-agent-skills --skill naver-land-scouter`
- **요구 사항**: Node.js(npx), `uv`(Python 스크립트 실행)

## 언제 쓰나

- "예시역 주변 3억대 아파트"처럼 위치와 조건을 함께 다룰 때
- 여러 역세권을 한 번에 스캔해 하나의 JSON으로 합칠 때
- 현재 호가가 최근 실거래 대비 비싼지 빠르게 판단할 때

## 명령 선택 가이드

| 하고 싶은 것 | 명령 |
|---|---|
| 위치+조건을 한 번에 | `workflow` |
| 위치만 확정 | `search` |
| 한 지점 중심으로 탐색 | `discover` |
| 여러 지점 원시 결과 합치기 | `scan` |
| 특정 단지 매물 보기 | `listings` |

## 기본 원칙

1. 에이전트 후속 처리용 결과는 `--format json --output-file <path>`로 저장한다
2. 위치가 문자열이면 기본 진입점은 `workflow` — 위치 해석만 확인할 때 `search`를 먼저 쓴다
3. "역 주변" 판단은 이름이 아니라 `distanceMeters` 또는 `lat`·`lon` 기준으로 한다
4. 결과가 0건이면 추측하지 말고 `filterStats`를 먼저 확인한다
5. 세대수·준공년도·주차대수 같은 메타데이터가 필요할 때만 `--enrich complex-summary`를 켠다
6. `401/403/429`가 나와도 바로 실패로 끝내지 않고 세션 전략(기본 `auto`)을 확인한다

## 구성 파일

| 파일 | 역할 |
|---|---|
| `SKILL.md` | 에이전트 지침 |
| `scripts/cli.py` | CLI 진입점(workflow/search/discover/scan/listings) |
| `scripts/naver_land_client.py` · `naver_land_repository.py` | API 클라이언트·저장소 |
| `references/api_endpoints.md` `param_dictionary.md` `workflows.md` `ops_policies.md` | API·파라미터·워크플로·운영 정책 |
| `pyproject.toml` · `uv.lock` | 의존성(uv) |
