# 테이블 상세 정의

총 13개 테이블의 논리 설계입니다. `bigint` 단일 PK는 자동 생성하며, 복합 PK는 연결 대상의 키를 사용합니다. 타입은 MySQL 계열 표기이며 실행용 DDL은 아닙니다.

`NULL`은 허용 여부입니다. 상태값, 금액 범위, 완료 조건 및 트랜잭션 규칙은 [설계 설명](README.md)을 함께 참고합니다.

## member — 회원

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 회원 식별자 |
| `name` | `varchar(50)` | — | 불가 | 가입 시 입력하는 이름 |
| `nickname` | `varchar(50)` | — | 불가 | 리뷰 및 마이페이지 표시 이름 |
| `email` | `varchar(255)` | — | 허용 | 연락용 이메일. 소셜 계정 식별키로 사용하지 않음 |
| `phone` | `varchar(20)` | — | 허용 | 선택 연락처 |
| `gender` | `varchar(20)` | — | 불가 | MALE / FEMALE / UNSPECIFIED |
| `birth_date` | `date` | — | 불가 | 생년월일 |
| `address` | `varchar(255)` | — | 불가 | 가입 화면의 주소 |
| `address_detail` | `varchar(255)` | — | 허용 | 상세 주소 |
| `profile_image_url` | `varchar(500)` | — | 허용 | 프로필 이미지 |
| `status` | `varchar(20)` | — | 불가 | ACTIVE / WITHDRAWN |
| `created_at` | `datetime` | — | 불가 | 가입 시각 |
| `updated_at` | `datetime` | — | 불가 | 최종 수정 시각 |
| `withdrawn_at` | `datetime` | — | 허용 | 탈퇴 시각 |

## social_account — 소셜 로그인 연결

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 소셜 계정 연결 식별자 |
| `member_id` | `bigint` | FK | 불가 | member.id |
| `provider` | `varchar(20)` | — | 불가 | KAKAO / NAVER / APPLE / GOOGLE |
| `provider_user_id` | `varchar(255)` | — | 불가 | 소셜 제공자가 발급하는 사용자 식별자 |
| `created_at` | `datetime` | — | 불가 | 연결 시각 |

추가 제약: `UNIQUE(provider, provider_user_id)`.

## food_category — 음식 종류

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 음식 카테고리 식별자 |
| `name` | `varchar(50)` | UK | 불가 | 한식, 일식, 중식, 디저트 등 |

## member_food_category — 회원 음식 선호도

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `member_id` | `bigint` | PK,FK | 불가 | member.id |
| `food_category_id` | `bigint` | PK,FK | 불가 | food_category.id |

## terms — 약관 버전

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 약관 버전 식별자 |
| `code` | `varchar(50)` | — | 불가 | SERVICE / PRIVACY / LOCATION / MARKETING 등 |
| `version` | `varchar(30)` | — | 불가 | 약관 버전 |
| `title` | `varchar(100)` | — | 불가 | 약관 제목 |
| `content` | `text` | — | 불가 | 해당 버전의 약관 내용 |
| `is_required` | `boolean` | — | 불가 | 필수 동의 여부 |
| `effective_at` | `datetime` | — | 불가 | 시행 시각 |

추가 제약: `UNIQUE(code, version)`.

## member_agreement — 회원 약관 동의

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `member_id` | `bigint` | PK,FK | 불가 | member.id |
| `terms_id` | `bigint` | PK,FK | 불가 | terms.id |
| `agreed` | `boolean` | — | 불가 | 해당 버전의 현재 동의 여부 |
| `agreed_at` | `datetime` | — | 허용 | 동의 시각. 동의한 경우 필수 |
| `revoked_at` | `datetime` | — | 허용 | 동의 철회 시각 |

## region — 서비스 지역

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 보상 집계 단위인 지역 식별자 |
| `code` | `varchar(30)` | UK | 불가 | 지역 고유 코드 |
| `name` | `varchar(100)` | — | 불가 | 안암동 등 표시명. 동명 지역 허용 |

## store — 가게

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 가게 식별자 |
| `region_id` | `bigint` | FK | 불가 | region.id |
| `food_category_id` | `bigint` | FK | 불가 | food_category.id. 대표 카테고리 1개 가정 |
| `name` | `varchar(100)` | — | 불가 | 가게명 |
| `address` | `varchar(255)` | — | 불가 | 가게 주소 |
| `description` | `text` | — | 허용 | 가게 소개 |
| `phone` | `varchar(20)` | — | 허용 | 연락처 |
| `image_url` | `varchar(500)` | — | 허용 | 대표 사진 |
| `status` | `varchar(20)` | — | 불가 | OPEN / CLOSED |

## mission — 미션 정의

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 미션 식별자 |
| `store_id` | `bigint` | FK | 불가 | store.id |
| `title` | `varchar(100)` | — | 불가 | 미션 제목 |
| `description` | `text` | — | 불가 | 미션 조건 설명 |
| `min_spend` | `decimal(12,0)` | — | 불가 | 최소 결제 금액. 단순 방문이면 0 |
| `reward_type` | `varchar(20)` | — | 불가 | FIXED / RATE |
| `reward_value` | `decimal(12,2)` | — | 불가 | FIXED이면 포인트, RATE이면 백분율. 5는 5% |
| `starts_at` | `datetime` | — | 불가 | 미션 시작 시각 |
| `ends_at` | `datetime` | — | 불가 | 미션 종료 시각 |
| `status` | `varchar(20)` | — | 불가 | ACTIVE / INACTIVE |

## member_mission — 회원별 수행 내역

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 수행 내역 식별자 |
| `member_id` | `bigint` | FK | 불가 | member.id |
| `mission_id` | `bigint` | FK | 불가 | mission.id |
| `status` | `varchar(20)` | — | 불가 | IN_PROGRESS / PENDING / COMPLETED / CANCELLED / EXPIRED |
| `accepted_at` | `datetime` | — | 불가 | 미션 도전 시각 |
| `completed_at` | `datetime` | — | 허용 | 완료 시각. COMPLETED일 때 필수 |
| `verification_code_hash` | `varchar(255)` | — | 허용 | 성공 요청 시 생성한 인증번호의 해시 |
| `code_expires_at` | `datetime` | — | 허용 | 인증번호 만료 시각 |
| `paid_amount` | `decimal(12,0)` | — | 허용 | 인증한 결제 금액. 완료 시 필수, 단순 방문은 0 |
| `awarded_points` | `int` | — | 허용 | 완료 당시 확정한 미션 보상. 미완료 NULL, 무보상 0 |
| `updated_at` | `datetime` | — | 불가 | 상태 최종 변경 시각 |

추가 제약: `UNIQUE(member_id, mission_id)`.

## region_reward — 지역 10회 달성 보상

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 지역 보상 식별자 |
| `member_id` | `bigint` | FK | 불가 | member.id |
| `region_id` | `bigint` | FK | 불가 | region.id |
| `cycle_no` | `int` | — | 불가 | 1=10회, 2=20회, 3=30회 달성 |
| `points` | `int` | — | 불가 | 지급 포인트. 현재 정책은 1000 고정 |
| `awarded_at` | `datetime` | — | 불가 | 지급 시각 |

추가 제약: `UNIQUE(member_id, region_id, cycle_no)`.

## review — 완료 미션 리뷰

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 리뷰 식별자 |
| `member_mission_id` | `bigint` | FK,UK | 불가 | member_mission.id. 완료 내역당 리뷰 최대 1개 |
| `rating` | `decimal(2,1)` | — | 불가 | 0.5~5.0, 0.5 단위 가정 |
| `content` | `text` | — | 허용 | 텍스트 리뷰. 별점만 등록 가능하다고 가정 |
| `created_at` | `datetime` | — | 불가 | 작성 시각 |
| `updated_at` | `datetime` | — | 불가 | 최종 수정 시각 |

## review_image — 리뷰 사진

| 컬럼 | 타입 | 키 | NULL | 설명 |
|---|---|---|---|---|
| `id` | `bigint` | PK | 불가 | 리뷰 사진 식별자 |
| `review_id` | `bigint` | FK | 불가 | review.id |
| `image_url` | `varchar(500)` | — | 불가 | 사진 URL |
| `sort_order` | `smallint` | — | 불가 | 1~3. 리뷰당 최대 3장 |

추가 제약: `UNIQUE(review_id, sort_order)`.
