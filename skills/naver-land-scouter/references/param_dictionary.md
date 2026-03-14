# 파라미터 사전 (관측 기반)

## ID 계열
- `complexNo`: 단지 ID
- `articleNo`: 매물 ID
- `realtorId`: 중개사 ID
- `cortarNo`: 행정구역 코드
- `dongNo`: 동 ID
- `areaNo`: 평형 ID
- `pyeongTypeNumber`: 평형 번호

## 지도/영역
- `zoom`: 지도 줌 레벨
- `centerLat`, `centerLon`: 지도 중심 좌표
- `leftLon`, `rightLon`, `topLat`, `bottomLat`: 지도 영역 박스(BBox)

## 필터
- `realEstateType`: 주택 유형 필터 (관측값: `APT:ABYG:JGC:PRE`)
- `tradeType`: 거래 유형 필터 (관측값: 공백 또는 `A1`)
- `priceType`: 가격 기준 (관측값: `RETAIL`)
- `page`: 페이지 번호
- `order`: 정렬 기준 (관측값: `rank`, `recent`)
- `type`: 응답 유형 (관측값: `list`, `chart`, `table`, `summary`)
- `year`: 기간 범위 (관측값: `5`)
- `priceMin`, `priceMax`: 매매가 범위
- `rentPriceMin`, `rentPriceMax`: 임대가 범위
- `areaMin`, `areaMax`: 면적 범위
- `oldBuildYears`, `recentlyBuildYears`: 노후/신축 필터
- `minHouseHoldCount`, `maxHouseHoldCount`: 세대수 범위
- `directions`: 방향 필터

## 플래그/옵션
- `showArticle`: 매물 표시 플래그
- `sameAddressGroup`: 동일주소 묶기
- `priceChartChange`: 시세 차트 변화량 표시 옵션
- `initial`: 초기 로딩 플래그
- `isPresale`: 분양 포함 여부

## 정규화/변환 가이드
- 금액/면적 등 단위는 실제 네이버 요청값 관측을 통해 확정한다.
- 자연어 입력(예: "10억 이하")은 파라미터 빌더에서 일관된 숫자 단위로 변환한다.
- `tradeType`, `realEstateType`, `priceType`은 표준 값만 사용하며 불필요한 기본값 전송을 최소화한다.
