# API 엔드포인트 카탈로그 (요약)

## 기본 규칙
- Base: https://new.land.naver.com
- 모든 데이터 API는 `/api/*` 경로를 사용한다.
- 본 문서는 관측 기반 요약이며, 실제 호출 시 파라미터 값은 네트워크 재관측으로 확정한다.

## 지도/행정구역
- `GET /api/cortars`
  - 목적: 지도 중심 좌표 기준 행정구역 코드(`cortarNo`) 조회
  - 주요 파라미터: `zoom`, `centerLat`, `centerLon`
- `GET /api/complexes/single-markers/2.0`
  - 목적: 지도 영역 내 단지 마커 목록
  - 주요 파라미터: `cortarNo`, `zoom`, `priceType`, `realEstateType`, `leftLon`, `rightLon`, `topLat`, `bottomLat`, `isPresale`

## 단지 정보
- `GET /api/regions/locations`
  - 목적: 단지 위치 정보
  - 주요 파라미터: `type=complex`, `id={complexNo}`
- `GET /api/complexes/overview/{complexNo}`
  - 목적: 단지 개요 요약
- `GET /api/complexes/{complexNo}`
  - 목적: 단지 상세
  - 주요 파라미터: `complexNo`, `initial=Y`, `sameAddressGroup=false`
- `GET /api/complexes/{complexNo}/additions`
  - 목적: 단지 추가 정보
- `GET /api/complexes/{complexNo}/buildings/list`
  - 목적: 단지 동 목록
- `GET /api/complexes/{complexNo}/buildings/pyeongtype`
  - 목적: 동별 평형 목록
  - 주요 파라미터: `dongNo`, `complexNo`
- `GET /api/complexes/{complexNo}/buildings/landprice`
  - 목적: 동별 공시가격
  - 주요 파라미터: `dongNo`, `complexNo`

## 매물
- `GET /api/articles/complex/{complexNo}`
  - 목적: 단지 매물 리스트
  - 주요 파라미터: `realEstateType`, `tradeType`, `priceType`, `page`, `order`, `priceMin`, `priceMax`, `rentPriceMin`, `rentPriceMax`, `areaMin`, `areaMax`, `showArticle`, `sameAddressGroup`, `directions`
- `GET /api/articles/{articleNo}`
  - 목적: 매물 상세

## 시세/실거래
- `GET /api/complexes/{complexNo}/prices`
  - 목적: 시세 차트/테이블/요약
  - 주요 파라미터: `tradeType`, `year`, `type=chart|table|summary`, `areaNo`
- `GET /api/complexes/{complexNo}/prices/real`
  - 목적: 실거래 테이블
  - 주요 파라미터: `tradeType`, `areaNo`, `type=table`

## 학군/교육
- `GET /api/complexes/{complexNo}/schools`
  - 목적: 단지별 배정 학교 정보
- `GET /api/schools`
  - 목적: 지도 학군 마커
  - 주요 파라미터: `zoom`, `leftLon`, `rightLon`, `topLat`, `bottomLat`

## 교통/편의
- `GET /api/regions/neighborhoods?type=BUS`
  - 목적: 주변 버스/지하철 등 편의시설 마커
  - 주요 파라미터: `zoom`, `leftLon`, `rightLon`, `topLat`, `bottomLat`

## 중개사
- `GET /api/realtors/{realtorId}`
  - 목적: 중개사 상세
- `GET /api/articles?realtorId=...`
  - 목적: 중개사 매물 리스트
  - 주요 파라미터: `realtorId`, `page`, `order`, `tradeType`, `realEstateType`, `isFixed`
- `GET /api/realtors/detailed-clusters`
  - 목적: 지도 중개사 마커 클러스터
  - 주요 파라미터: `cortarNo`, `zoom`, `leftLon`, `rightLon`, `topLat`, `bottomLat`

## 분양
- `GET /api/pre-sale/{cortarNo}`
  - 목적: 지역 분양 정보

## 개발계획 레이어
- `GET /api/developmentplan/road/list`
- `GET /api/developmentplan/rail/list`
- `GET /api/developmentplan/station/list`
- `GET /api/developmentplan/jigu/list`
  - 목적: 지도 레이어 기반 개발계획 조회
  - 주요 파라미터: `zoom`, `leftLon`, `rightLon`, `topLat`, `bottomLat`

## 제외(기본 수집 대상 아님)
- `GET /api/property/complex/{complexNo}/tour`
- `GET /api/property/complex/{complexNo}/vr`
- `GET /api/property/complex/{complexNo}/vr/representative`
