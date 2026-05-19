---
name: go-gorm-persistence
description: Use when working on Go backend persistence code that uses GORM, including entity-first modeling, reusable GORM scopes, repository/service boundaries, preloads, pagination helpers, transactions, migrations, MySQL/MariaDB/PostgreSQL behavior, tests, file metadata cleanup, and worker locking.
---

# Go GORM Persistence

이 Skill은 Go 백엔드에서 GORM 기반 persistence 코드를 설계하거나 수정할 때 사용한다. 특정 프로젝트의 도메인 지식이 아니라, 실제 운영 코드에서 반복적으로 문제를 줄였던 GORM 사용 관례를 정리한 것이다.

## 핵심 흐름

1. 기본은 Entity 중심으로 시작한다. 먼저 엔터티의 PK, FK, nullable 관계, cascade 정책, unique/index 제약을 읽고 쿼리 모양을 결정한다.
2. 현재 코드베이스의 레이어 구조를 확인한다. 보통 HTTP/controller는 입출력, service는 비즈니스 규칙과 트랜잭션 경계, repository는 DB query를 맡는다.
3. 기존 repository 생성 방식, DB 주입 방식, 테스트 DB helper, migration 방식부터 읽는다.
4. 관계 조회가 많은 코드라면 재사용 가능한 GORM scope 함수가 이미 있는지 확인한다. 없다면 흩어진 `Preload`/`Joins`/필터를 repository 구현체 안의 scope로 모은다.
5. 새 테이블/컬럼은 entity tag, AutoMigrate 대상 목록, 수동 migration, 테스트 fixture를 함께 갱신한다.
6. MySQL/MariaDB/PostgreSQL/SQLite 차이가 있는 기능은 실제 운영 DB와 같은 계열의 testcontainers 기반 단위 테스트를 우선 고려한다. JSON 함수, row lock, UUID 타입, regex 정렬, `SKIP LOCKED`는 SQLite 대체 검증만으로 충분한지 확인한다.

## 엔터티 설계

- 공통 PK/타임스탬프 모델이 있으면 재사용한다. UUID PK는 `BeforeCreate` hook으로 생성하면 fixture와 운영 코드의 중복을 줄일 수 있다.
- UUID FK는 명시적인 타입과 index를 붙인다. 필수 관계는 `not null`, 선택 관계는 pointer FK를 사용한다.
- 관계는 `foreignKey:...;references:...`를 명시한다. 삭제 정책이 중요한 관계는 `constraint:OnDelete:CASCADE` 또는 `OnDelete:SET NULL`까지 tag에 드러낸다.
- 단순 JSON/list 저장은 `serializer:json` 또는 `gorm.io/datatypes` 같은 GORM 제공 기능을 먼저 검토한다. DB별 타입 제어, 검증, 쿼리 헬퍼가 필요하면 `driver.Valuer`, `sql.Scanner`, `GormDataType`, `GormDBDataType` 구현을 사용한다.
- FK 값을 바꿀 때 이미 로드된 association struct가 있으면 빈 struct나 nil로 비워 stale association 저장을 피한다.

## Repository 패턴

- repository는 DB query에 집중한다. request parsing, 권한 판단, 외부 API 호출, queue publish는 service/controller로 올린다.
- service 계층이 의존할 repository interface와 GORM 구현체를 분리한다. 구현체는 global DB getter를 직접 호출하기보다 `*gorm.DB`를 생성자로 주입받고, repository I/O method는 `context.Context`를 받아 `WithContext(ctx)`로 전파한다.
- `Create`/`Save` 후 응답에 관계 데이터가 필요하면 바로 저장된 struct를 반환하지 말고 `FindByID`로 재조회해 preload된 상태를 반환한다.
- 기본 조회와 관계 포함 조회를 분리한다. 예: `FindByID`는 최소 row만, `FindDetailByID`는 `Scopes(WithXxxDetailRelations)`로 필요한 관계를 명시한다.
- 관계 로딩은 repository 구현체 안에서 재사용 가능한 GORM scope 함수로 모은다. scope는 `func(db *gorm.DB) *gorm.DB` 형태로 만들고, 여러 repository/domain의 scope가 서로 합성해 쓸 수 있게 작게 유지한다.
- 관계 로딩 scope 이름은 `WithXxxRelations`를 사용하되, list/detail/export처럼 조회 목적이 다르면 `WithXxxListRelations`, `WithXxxDetailRelations`, `WithXxxExportRelations`로 나눈다.
- `db.Scopes(WithTeamDetailRelations)`처럼 썼을 때 query composition 의도가 잘 드러난다.
- nested preload는 callback 안에서 다른 scope를 호출해 합성한다.

```go
package persistence

import "gorm.io/gorm"

func WithTeamDetailRelations(db *gorm.DB) *gorm.DB {
	return db.
		Preload("Settings").
		Preload("Members", func(db *gorm.DB) *gorm.DB {
			return db.Where("status = ?", "ACTIVE").Order("created_at asc")
		})
}

func WithTeamListRelations(db *gorm.DB) *gorm.DB {
	return db.Preload("Settings")
}
```

- update method는 의도를 나눈다. 전체 엔터티 갱신은 zero value 저장 여부를 명시하고, 단일 필드/상태 변경은 `Model(...).Where(...).Update(...)`처럼 좁게 작성한다.

```go
type TeamRepository interface {
	FindByID(ctx context.Context, id uuid.UUID) (*entity.Team, error)
	FindDetailByID(ctx context.Context, id uuid.UUID) (*entity.Team, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status entity.TeamStatus) error
}

type TeamRepositoryImpl struct {
	db *gorm.DB
}

func NewTeamRepository(db *gorm.DB) *TeamRepositoryImpl {
	return &TeamRepositoryImpl{db: db}
}

func (r *TeamRepositoryImpl) FindByID(ctx context.Context, id uuid.UUID) (*entity.Team, error) {
	var team entity.Team
	if err := r.db.WithContext(ctx).First(&team, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &team, nil
}

func (r *TeamRepositoryImpl) FindDetailByID(ctx context.Context, id uuid.UUID) (*entity.Team, error) {
	var team entity.Team
	if err := r.db.WithContext(ctx).Scopes(WithTeamDetailRelations).First(&team, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &team, nil
}

func (r *TeamRepositoryImpl) UpdateStatus(ctx context.Context, id uuid.UUID, status entity.TeamStatus) error {
	return r.db.WithContext(ctx).Model(&entity.Team{}).Where("id = ?", id).Update("status", status).Error
}
```

- Join이 들어간 쿼리는 컬럼명을 테이블명까지 붙여 ambiguous column 문제를 피한다.
- pagination 보일러플레이트는 공통 helper로 뺀다. 각 repository는 filter가 적용된 base query를 만들고, 공통 helper가 `Count`와 `Offset`/`Limit` 적용을 맡게 한다.
- count query에는 `Order`, `Offset`, `Limit`, relation preload를 섞지 않는다. fetch query에만 relation scope와 정렬을 붙이면 SQL이 예측 가능해진다.
- many-side join으로 row가 중복될 수 있으면 base query에서 primary key `Distinct` 또는 subquery 기준을 먼저 잡는다.
- DB 특화 필터나 정렬은 helper로 분리한다.
- `Save`는 zero value까지 저장한다. 일부 컬럼만 바꿀 때는 `Model(...).Where(...).Updates(map[string]any{...})` 또는 `Update`를 선호한다.

```go
package pagination

import "gorm.io/gorm"

type Request struct {
	Page int
	Size int
}

type Page[T any] struct {
	Items []T
	Total int64
	Page  int
	Size  int
}

func Normalize(req Request) Request {
	if req.Page < 1 {
		req.Page = 1
	}
	if req.Size <= 0 {
		req.Size = 20
	}
	if req.Size > 100 {
		req.Size = 100
	}
	return req
}

func FindPage[T any](base *gorm.DB, req Request, fetchScopes ...func(*gorm.DB) *gorm.DB) (Page[T], error) {
	req = Normalize(req)

	var total int64
	if err := base.Session(&gorm.Session{}).Count(&total).Error; err != nil {
		return Page[T]{}, err
	}

	var items []T
	err := base.
		Session(&gorm.Session{}).
		Scopes(fetchScopes...).
		Offset((req.Page - 1) * req.Size).
		Limit(req.Size).
		Find(&items).
		Error
	if err != nil {
		return Page[T]{}, err
	}

	return Page[T]{Items: items, Total: total, Page: req.Page, Size: req.Size}, nil
}
```

```go
func (r *TeamRepositoryImpl) Search(ctx context.Context, filter TeamFilter, page pagination.Request) (pagination.Page[entity.Team], error) {
	base := r.db.
		WithContext(ctx).
		Model(&entity.Team{}).
		Scopes(WithTeamFilter(filter))

	return pagination.FindPage[entity.Team](
		base,
		page,
		WithTeamListRelations,
		WithTeamDefaultOrder,
	)
}
```

## 트랜잭션 경계

- 여러 aggregate를 함께 바꾸거나 검증 후 쓰기가 필요한 작업은 service에서 `db.Transaction(func(tx *gorm.DB) error { ... })`로 묶는다.
- 트랜잭션 내부에서 repository를 호출해야 하면 tx 전용 method를 늘리기보다 `tx`로 같은 repository 구현체를 새로 만든다. 예: `teamRepo := NewTeamRepository(tx)`.
- 트랜잭션 안에서 원래 repository 인스턴스의 `r.db`를 쓰면 같은 tx를 벗어난다. 이 실수가 가장 흔하다.
- 단일 repository 내부에서 관련 row 정리가 완결되는 삭제 작업은 repository가 transaction을 소유해도 된다. 단, 여러 repository와 도메인 검증이 엮이면 service가 경계를 소유한다.
- DB commit 전에는 DB row만 다룬다. queue publish, object storage 삭제, 외부 API 호출 같은 rollback 불가능한 side effect는 commit 이후에 수행한다.
- worker/scheduler 같은 경쟁 소비나 리소스 할당 로직이 있으면 row lock과 상태 조건부 update를 검토한다. `FOR UPDATE`, `SKIP LOCKED`, `WHERE status IN (...)` 조합이 자주 쓰인다.
- 동시 upsert/claim 로직에서 deadlock 또는 lock wait timeout 가능성이 있으면 좁은 범위의 retry가 필요한지 검토한다.

## 외부 Side Effect

- DB transaction은 rollback 가능한 DB row 변경에 집중한다. object storage, queue, 외부 API 같은 side effect는 commit 이후로 분리하는 편이 안전하다.
- 외부 리소스 cleanup 대상은 DB row 변경 전에 식별해 두고, 실제 cleanup은 commit 이후 처리한다.
- soft hide, hard delete, cascade delete 중 어떤 정책인지 먼저 확인하고 조회 조건과 외부 cleanup 범위를 맞춘다.

## 마이그레이션

- AutoMigrate는 새 테이블/컬럼 추가에는 편하지만 drop, rename, 데이터 변환, FK 재작성에는 충분하지 않다.
- 새 엔터티를 추가하면 AutoMigrate 대상 목록의 의존 순서를 확인한다. 참조 대상 테이블이 먼저 생성되어야 한다.
- 운영 데이터가 있는 컬럼 rename/type 변경/그룹 재구성은 SQL 또는 Go migration을 별도로 둔다.
- Go migration은 `db.Transaction` 안에서 실행한다. 기존 스키마를 읽어야 하면 현재 entity struct 대신 local struct 또는 `tx.Table("...")`를 사용해 schema drift와 충돌을 피한다.
- 재실행 가능성을 고려한다. duplicate column/index, FK 존재 여부, 이미 migrate된 row를 어떻게 처리할지 명시한다.
- 운영 DB 전용 문법을 쓰면 테스트도 같은 DB 계열로 맞춘다. MySQL/MariaDB의 JSON 함수, UUID column, `SET FOREIGN_KEY_CHECKS`, lock 문법은 SQLite와 다르다.

## 테스트 전략

- repository 테스트는 운영 DB와 같은 계열의 testcontainers를 우선 사용한다. 테스트 helper로 컨테이너 시작, 임시 DB 생성, AutoMigrate 또는 migration 적용, cleanup까지 캡슐화한다.
- SQLite in-memory는 빠르지만 lock, JSON, UUID, regex, FK 동작이 다를 수 있다. GORM tag/hook만 보는 아주 좁은 테스트가 아니라면 testcontainers 기반 DB 테스트를 우선 고려한다.
- 상태 전이 repository는 `RowsAffected == 0`, `ErrRecordNotFound`, 동시성 경로를 함께 검증한다.

## 자주 빠지는 함정

- `Find`는 row가 없어도 에러를 내지 않는다. 단건 필수 조회는 `First` 또는 `Take`를 쓴다.
- `Preload`는 상위 query의 filter/order를 자동 상속하지 않는다. 관계마다 callback으로 필요한 조건을 지정한다.
- `Save` 전에 로드된 association struct를 그대로 두면 FK 변경 의도와 다른 관계 저장이 발생할 수 있다.
- `Count` query에 preload/order/join이 과하게 섞이면 느리거나 잘못된 SQL이 나온다.
- 트랜잭션 안에서 외부 side effect를 수행하면 rollback 불가능한 불일치가 생긴다.
- raw SQL을 쓸 때는 DB 방언과 identifier quoting을 현재 프로젝트 기준에 맞춘다.
