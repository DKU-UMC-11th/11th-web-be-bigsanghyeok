# 2주차 미션 기록 — 온라인 도서 대여 조회와 1주차 ERD 확장

## 실행 확인

제공된 `01_schema.sql`과 `02_seed.sql`을 수정 없이 MySQL에서 실행한 뒤 공통 SELECT 3개를 조회했다. 기존 서비스 DB와 분리된 임시 로컬 MySQL 서버를 사용했으며, 검증을 마친 뒤 종료했다. 확장 쿼리는 1주차 리워드 ERD를 재현한 별도 DB와 별도로 작성한 검증 데이터를 사용했다.

`results/*.png`는 **실제 mysql CLI 출력을 HTML 보고서로 표시하고 브라우저에서 캡처한 이미지**다. Workbench 실행 화면은 아니며, 원본 출력도 TSV 및 로그로 함께 제공한다.

- 실행 환경: MySQL 26.7.0
- 실행 시각: 2026-09-29T18:23:23.553370+09:00
- 원본 실행 로그: [00_setup.txt](results/00_setup.txt)
- 검증 결과·원본 파일 해시: [verification.json](results/verification.json)

![테이블 생성 및 더미 데이터 실행 확인](results/00_setup.png)

## ERD와 JOIN 경로

![기준 ERD와 JOIN 경로](results/library-erd-join-paths.png)

파랑은 미션 1, 초록은 미션 2, 보라는 미션 3에서 사용하는 관계를 나타낸다. 보라색 users–book_like 관계는 좋아요 소유자의 의미를 보여주며 실제 미션 3 SQL은 users를 JOIN하지 않는다. 관계선의 1은 정확히 하나, 0..N은 0개 이상이다.

공통 관계는 users 1:N rental, book 1:N rental, category 1:N book, book N:M tag(book_tag), users N:M book(book_like), users 1:N notification이다. 연결 테이블의 복합 PK가 같은 책·태그 및 같은 사용자·책의 중복 연결을 방지한다.

## 조회 정책

- 특정 사용자: `user_id = 1`(민서). 특정 책: `book_id = 1`(달빛 도서관).
- 최신순: book에는 등록 시각이 없으므로 **book_id가 클수록 최근 등록된 책**이라고 가정한다. 실제 등록 시각순이 필요한 시스템에서는 created_at 같은 컬럼을 별도로 설계해야 한다.
- 미반납: `returned_at IS NULL`. 반납 예정일이 지났더라도 아직 반납하지 않았으면 포함한다.
- 미션 3: 태그당 한 행. 좋아요는 1/0으로 표시한다. 태그가 없으면 NULL 태그 행 하나를, 책 자체가 없으면 0행을 반환한다.
- `LIMIT 10`은 최대 10개이므로 조건에 맞는 행이 1개뿐이면 1개만 나온다.

## 미션 1 · 대여 가능한 문학 도서

**요구사항:** 문학 카테고리의 대여 가능한 도서를 최신순으로 최대 10개 조회하고, 책 제목·설명·카테고리 이름을 표시한다.

파일: [03_mission1.sql](03_mission1.sql)

```sql
SELECT
    b.title AS book_title,
    b.description,
    c.name AS category_name
FROM book AS b
INNER JOIN category AS c
    ON c.category_id = b.category_id
WHERE c.name = '문학'
  AND b.is_available = TRUE
ORDER BY b.book_id DESC
LIMIT 10;
```

기준 테이블은 book이며, category 1:N book 관계를 따라 분류 이름을 얻기 위해 JOIN한다. WHERE는 문학이면서 대여 가능한 책만 남긴다. book_id 내림차순으로 정렬하고 최대 10권을 반환한다.

**JOIN 경로:** `book → category`

![미션 1 · 대여 가능한 문학 도서 실행 결과](results/03_mission1.png)

**한 문장 검증:** 달빛 도서관 1권만 조회되어 문학·대여 가능 조건과 일치합니다.

원본 결과: [03_mission1.tsv](results/03_mission1.tsv)

## 미션 2 · 사용자의 미반납 도서

**요구사항:** 사용자 1이 아직 반납하지 않은 책을 반납 예정일이 빠른 순으로 조회하고, 책 제목·대여일·반납 예정일을 표시한다.

파일: [04_mission2.sql](04_mission2.sql)

```sql
SELECT
    b.title AS book_title,
    r.rented_at,
    r.due_at
FROM rental AS r
INNER JOIN book AS b
    ON b.book_id = r.book_id
WHERE r.user_id = 1
  AND r.returned_at IS NULL
ORDER BY r.due_at ASC, r.rental_id ASC;
```

기준 테이블은 rental이며, book 1:N rental 관계를 따라 책 제목을 얻기 위해 JOIN한다. 사용자 ID는 rental에 있으므로 users JOIN 없이 특정 사용자와 미반납 조건을 검사한다. 반납 예정일 오름차순이며, 예정일이 같으면 rental_id 오름차순으로 순서를 고정하고 전체 목록을 반환한다.

**JOIN 경로:** `rental → book`

![미션 2 · 사용자의 미반납 도서 실행 결과](results/04_mission2.png)

**한 문장 검증:** 민서가 미반납한 겨울의 편지 1건과 대여일·반납 예정일이 조회되어 요구사항과 일치합니다.

원본 결과: [04_mission2.tsv](results/04_mission2.tsv)

## 미션 3 · 책의 태그와 좋아요 여부

**요구사항:** 책 1의 태그 목록과 사용자 1의 좋아요 여부를 조회한다.

파일: [05_mission3.sql](05_mission3.sql)

```sql
SELECT
    b.title AS book_title,
    t.name AS tag_name,
    CASE WHEN bl.user_id IS NULL THEN 0 ELSE 1 END AS is_liked
FROM book AS b
LEFT JOIN book_tag AS bt
    ON bt.book_id = b.book_id
LEFT JOIN tag AS t
    ON t.tag_id = bt.tag_id
LEFT JOIN book_like AS bl
    ON bl.book_id = b.book_id
   AND bl.user_id = 1
WHERE b.book_id = 1
ORDER BY t.tag_id ASC;
```

기준 테이블은 book이며, book N:M tag 관계를 book_tag로 연결하고 book_like로 특정 사용자의 좋아요를 확인한다. WHERE는 책을 선택하고 사용자 조건은 LEFT JOIN의 ON에 두어 좋아요가 없어도 책이 조회되게 한다. 태그 ID 오름차순으로 전체 태그를 보여주며, is_liked의 1은 좋아요, 0은 좋아요하지 않음을 뜻한다.

**JOIN 경로:** `book → book_tag → tag / book → book_like`

![미션 3 · 책의 태그와 좋아요 여부 실행 결과](results/05_mission3.png)

**한 문장 검증:** 달빛 도서관의 소설·추천 태그 2개와 민서의 좋아요 여부 1이 각 행에 조회되어 요구사항과 일치합니다.

원본 결과: [05_mission3.tsv](results/05_mission3.tsv)

## 확장 · 지역별 완료 미션 내역

**요구사항:** 회원 1이 지역 1에서 완료한 미션을 최근 완료순으로 최대 10개 조회하고, 미션명·가게명·지역명·완료 시각·미션 획득 포인트를 표시한다.

파일: [06_extension.sql](06_extension.sql)

```sql
SELECT
    m.title AS mission_title,
    s.name AS store_name,
    rg.name AS region_name,
    mm.completed_at,
    mm.awarded_points
FROM member_mission AS mm
INNER JOIN mission AS m
    ON m.id = mm.mission_id
INNER JOIN store AS s
    ON s.id = m.store_id
INNER JOIN region AS rg
    ON rg.id = s.region_id
WHERE mm.member_id = 1
  AND rg.id = 1
  AND mm.status = 'COMPLETED'
ORDER BY mm.completed_at DESC, mm.id DESC
LIMIT 10;
```

기준 테이블은 member_mission이며, mission → store → region을 JOIN하여 화면에 필요한 이름을 조회한다. WHERE는 회원 1, 지역 1, 완료 상태를 선택하며, 과거 내역이므로 가게나 미션의 현재 활성 상태로 제외하지 않는다. 완료 시각 내림차순으로 최대 10개를 반환하고, 완료 시각이 같으면 수행 내역 ID 내림차순으로 순서를 고정한다.

**JOIN 경로:** `member_mission → mission → store → region`

![확장 ERD JOIN 경로](results/extension-erd-join-path.png)

위 그림은 조회에 사용하는 1주차 테이블과 주요 컬럼만 표시했다. [1주차 전체 ERD](../week01/erd/reward-service-erd.png) 및 [컬럼 정의](../week01/erd/schema.md)와 동일한 관계다. 확장 결과는 공통 도서 더미 데이터가 아닌 별도 검증 데이터에서 실행했다.

`awarded_points`는 해당 미션의 보상이며 지역 10회 보너스나 전체 잔액이 아니다. 이미 완료한 과거 내역이므로 가게나 미션의 현재 활성 상태를 추가 필터로 사용하지 않는다.

![확장 · 지역별 완료 미션 내역 실행 결과](results/06_extension.png)

**한 문장 검증:** 회원 1의 안암동 완료 미션 2건만 최근 완료순으로 조회되고, 진행 중·다른 회원·다른 지역의 행은 제외되어 요구사항과 일치합니다.

원본 결과: [06_extension.tsv](results/06_extension.tsv)

## 질문과 답변

### 어떤 요구사항에서 어떤 테이블을 기준으로 시작했나요?

| 요구사항 | 기준 테이블 | 선택 이유 |
|---|---|---|
| 문학·대여 가능 도서 | book | 조회할 대상과 대여 가능 상태가 책에 있다. |
| 특정 사용자의 미반납 목록 | rental | 사용자·미반납 여부·대여일·반납 예정일이 대여 내역에 있다. |
| 특정 책의 태그·좋아요 | book | 태그나 좋아요가 없어도 책은 결과에 남겨야 한다. |
| 특정 회원의 지역별 완료 미션 | member_mission | 회원별 완료 상태·완료 시각·확정 포인트가 수행 내역에 있다. |

### JOIN이 필요한 이유를 ERD의 관계로 설명할 수 있나요?

미션 1은 book.category_id가 category.category_id를 참조하는 N:1 관계를 이용해 분류 이름을 가져온다. 미션 2는 rental.book_id가 book.book_id를 참조하는 N:1 관계를 이용해 제목을 가져오며, 사용자 ID는 rental에 있으므로 users를 추가로 JOIN하지 않는다.

미션 3은 책과 태그의 N:M 관계를 book_tag를 거쳐 조회하고, 사용자와 책의 N:M 관계를 book_like에서 확인한다. 사용자 조건을 ON에 적용하면 복합 PK(user_id, book_id)에 의해 좋아요 행은 최대 1개만 연결되므로 태그 행이 불필요하게 늘어나지 않는다. 태그 2개 때문에 같은 책이 2행 나오는 것은 의도한 결과다.

확장 쿼리는 member_mission → mission → store → region의 N:1 경로를 따라 화면에 필요한 이름을 가져온다. 각 수행 내역이 미션·가게·지역 하나씩에 연결되므로 JOIN 후에도 수행 내역당 한 행을 유지한다.

### 더미 데이터 결과가 예상과 달랐을 때 어떤 조건 또는 관계를 먼저 확인했나요?

이번 실제 실행에서는 예상 결과와 불일치한 사례는 없었다. 대신 다음 경계 사례를 공통 데이터를 수정하지 않는 SELECT로 추가 확인했다.

| 확인 사례 | 실제 결과 | 우선 확인할 조건·관계 |
|---|---|---|
| 태그·좋아요가 없는 책 2 | 겨울의 편지 / NULL / 0 | INNER JOIN으로 책을 제거하지 않았는지 확인한다. |
| 책 1을 좋아요하지 않은 사용자 2 | 소설·추천 각각 is_liked=0 | 사용자 조건이 WHERE가 아닌 LEFT JOIN의 ON에 있는지 확인한다. |
| 존재하지 않는 책 999 | 0행 | WHERE에 전달한 책 ID와 실제 원본 행을 확인한다. |
| 이미 반납한 사용자 2의 대여 | 0행 | `returned_at IS NULL`인지 확인한다. `= NULL`을 쓰지 않는다. |

미션 1의 겨울의 편지는 문학이지만 is_available=FALSE여서 제외되고, 우주를 읽는 법은 대여 가능하지만 과학이어서 제외된다. 미션 2의 겨울의 편지는 반납 예정일이 지났지만 returned_at이 NULL이므로 계속 포함되는 것이 맞다. 결과 행이 과도하게 늘어나면 JOIN의 PK–FK 연결과 N:M 연결 테이블을 먼저 확인한다.

## 검증 범위와 한계

- 원본 스키마·더미 데이터 파일의 해시는 실행 전후 동일하다. 공통 실습 및 추가 확인은 SELECT만 사용했으며 공통 테이블 행 수도 동일하다.
- 공통 미션 1·2는 결과가 1행이어서 정렬 순서를 여러 행에서 관찰할 수 없다. 미션 1의 10개 제한도 경계 데이터로 검증하지 않았으며 SQL의 ORDER BY·LIMIT과 실행 성공을 확인한 범위다.
- 확장은 두 완료 시각의 내림차순 및 진행 중·다른 회원·다른 지역 제외를 확인했다. 동률 정렬과 10개 제한의 경계 사례는 별도로 실행하지 않았다.
- validation/extension_schema.sql은 1주차의 컬럼·PK·FK·UNIQUE를 재현한 조회 검증용 DDL이다. 운영용 CHECK·인증·포인트 지급 로직 구현물이 아니다.

## 실행 순서와 제출 파일

공통 실습은 새로 만든 빈 MySQL 실습 DB를 선택한 후 `01_schema.sql → 02_seed.sql → 03_mission1.sql → 04_mission2.sql → 05_mission3.sql` 순서로 실행한다. 06_extension.sql은 도서 DB에서 실행하지 않는다. 별도 빈 리워드 실습 DB에서 `validation/extension_schema.sql → validation/extension_seed.sql → 06_extension.sql` 순서로 실행한다.

| 제출 항목 | 파일 |
|---|---|
| 스키마·더미 데이터 | 01_schema.sql, 02_seed.sql |
| 공통 조회 3개 | 03_mission1.sql, 04_mission2.sql, 05_mission3.sql |
| 1주차 확장 조회 | 06_extension.sql |
| 미션 기록·설명·질문 답변 | README.md(현재 문서) |
| 실행 확인 캡처 | results/00_setup.png |
| 조회 결과 캡처 4개 | results/03_mission1.png, 04_mission2.png, 05_mission3.png, 06_extension.png |
| JOIN 경로가 표시된 ERD | results/library-erd-join-paths.png, results/extension-erd-join-path.png |
| 원본 실행 증거 | results/00_setup.txt, results/*.tsv, results/verification.json |

자동 검증을 재현하려면 Python으로 `validation/verify_mysql.py`를 실행한다. 설치된 MySQL 바이너리 경로가 다르면 MYSQL_BIN 환경변수로 지정할 수 있다. 이 스크립트는 새로운 임시 서버를 생성·검증·종료하며 기존 MySQL 서비스에 연결하지 않는다. 보고서와 ERD 생성은 Pillow가 설치된 Python으로 `validation/build_report.py`를 실행한다. 브라우저 캡처 PNG는 결과 HTML에서 별도로 캡처한 파일이므로 재실행 결과가 바뀌면 다시 캡처해야 한다.

