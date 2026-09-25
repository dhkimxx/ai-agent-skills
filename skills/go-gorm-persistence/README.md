# go-gorm-persistence

> Go 백엔드의 GORM persistence 코드를 설계·수정할 때 따르는 관례 모음.
> 특정 프로젝트 지식이 아니라, 운영 코드에서 반복적으로 문제를 줄인 규칙입니다.

- **설치**: `npx skills add dhkimxx/ai-agent-skills --skill go-gorm-persistence`

## 언제 쓰나

- GORM 기반 repository/service 코드를 새로 쓰거나 고칠 때
- entity 관계·preload·트랜잭션 경계를 정리할 때
- migration과 테스트 픽스처를 함께 갱신할 때

## 핵심 흐름

1. **Entity 먼저** — PK/FK, nullable, cascade, unique/index 제약을 읽고 쿼리 모양을 정한다
2. **레이어 확인** — controller(입출력) / service(규칙·트랜잭션) / repository(쿼리) 경계를 지킨다
3. **Scope 재사용** — 흩어진 `Preload`/`Joins`/필터를 repository 안 scope로 모은다
4. **함께 갱신** — 새 테이블·컬럼은 entity tag · AutoMigrate 목록 · migration · fixture를 한 번에 바꾼다
5. **DB 계열 테스트** — MySQL/MariaDB/PostgreSQL 차이(JSON 함수, row lock, `SKIP LOCKED` 등)는
   같은 계열 DB(testcontainers)로 검증한다

## 대표 규칙

- repository는 쿼리에 집중 — request 파싱·권한·외부 호출은 service/controller로 올린다
- repository method는 `context.Context`를 받아 `WithContext(ctx)`로 전파한다
- 저장 직후 관계 데이터가 필요하면 재조회(`FindByID`)로 preload된 상태를 반환한다
- 기본 조회와 관계 포함 조회를 분리한다(`FindByID` / `FindDetailByID`)

## 구성 파일

| 파일 | 역할 |
|---|---|
| `SKILL.md` | 전체 규칙 — 엔터티 설계 · repository 패턴 · 트랜잭션 · 마이그레이션 · 테스트 |
