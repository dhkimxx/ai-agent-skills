# 운영 정책 및 주의사항

## 약관/정책 준수
- 서비스 이용약관 및 데이터 이용 정책을 사전에 확인한다.
- robots.txt 및 접근 제한 정책을 준수한다.
- 로그인/유료/제한 구역 데이터는 수집하지 않는다.

## 요청 헤더 정책
- User-Agent: 실제 브라우저 환경과 유사한 값으로 일관 유지
- Accept: `application/json, text/plain, */*`
- Accept-Language: `ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7`
- Referer: `https://new.land.naver.com/` 또는 실제 탐색 페이지 URL
- Origin: `https://new.land.naver.com`
- Accept-Encoding: `gzip, deflate, br`

## 세션/쿠키
- 로그인 없이 접근 가능한 범위만 수집한다.
- 세션 쿠키가 필요하면 Playwright로 세션을 생성하고 재사용한다.
- 쿠키는 보안적으로 저장하고 장기 보관을 피한다.

## 속도 제한/재시도
- 기본 요청 속도: 초당 1~3건 이내 권장
- 병렬 수집 시 동시 요청 수 제한(예: 3~5)
- 429/403/5xx 또는 `net::ERR_ABORTED` 발생 시 지수 백오프 + 지터 적용
- 동일 요청 반복 실패 시 일정 시간 대기 후 스킵

## 캐싱/중복 제거
- 동일 파라미터 요청은 로컬 캐시를 사용해 중복 호출을 줄인다.
- 지도 기반 API 캐시 키: `zoom`, `bbox`, `cortarNo`
- 매물 상세(`articleNo`)와 단지 상세(`complexNo`)도 캐시 키로 관리한다.

## 데이터 정합성
- `complexNo`, `articleNo`, `realtorId`, `cortarNo`, `dongNo`, `areaNo` 관계를 유지한다.
- 단지별 평형(`areaNo`)은 `buildings/pyeongtype`으로 보강한다.
- `articles/{articleNo}` 응답에 `complexNo`가 비어 있을 수 있어 목록 응답과 조인한다.
- 시세/실거래는 `tradeType`, `areaNo` 기준을 명확히 기록한다.

## 개인정보/민감정보
- 중개사 전화번호 등 PII는 저장 최소화, 필요 시 마스킹 처리한다.
- 수집 목적에 불필요한 PII는 저장하지 않는다.
- 로그에 개인식별정보를 그대로 남기지 않는다.

## 로그 권장 포맷
- 요청: `timestamp`, `endpoint`, `params`, `status`, `latency`, `retryCount`
- 오류: `endpoint`, `status`, `errorType`, `message`, `responseSnippet`
- 데이터: `entityId`, `entityType`, `fetchedAt`
