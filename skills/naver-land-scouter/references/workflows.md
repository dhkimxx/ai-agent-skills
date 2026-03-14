# 워크플로우 요약

## 지도 기반 탐색 플로우
1. 중심 좌표로 `cortars` 호출 → `cortarNo` 확보
2. `single-markers/2.0` 호출 → 단지 마커 목록 확보
3. 필요 시 `regions/locations`로 위치 보강

## 단지 심층 분석 플로우
1. `complexes/{complexNo}?initial=Y` 호출
2. `complexes/overview/{complexNo}` 호출
3. `complexes/{complexNo}/additions` 호출
4. 필요 시 `buildings/list` → `buildings/pyeongtype`로 평형 보강

## 매물 탐색/상세 플로우
1. `articles/complex/{complexNo}`로 리스트 수집
2. `articles/{articleNo}`로 상세 수집
3. 상세 응답에 `complexNo` 누락 시 리스트 응답과 조인

## 시세/실거래 플로우
1. `complexes/{complexNo}/prices`로 시세 요약/차트/테이블 수집
2. `complexes/{complexNo}/prices/real`로 실거래 테이블 수집
3. `tradeType`, `areaNo` 기준을 명확히 고정

## 학군/교통 플로우
- 학군: `complexes/{complexNo}/schools`
- 교통/편의: `regions/neighborhoods?type=BUS` (bbox 기반)

## 중개사 플로우
- `realtors/{realtorId}`로 상세
- `articles?realtorId=...`로 매물 리스트
- 지도 마커는 `realtors/detailed-clusters` 사용
