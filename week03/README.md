# 3주차 — 실습과 필수 미션

[워크북](https://app.notion.com/p/3ef1d799147b808d8fb9ecec615536d7)과 [Spring 세팅 가이드](https://app.notion.com/p/9571d799147b8221ad438133e09e9d71)를 기준으로 Spring Boot 한 스택으로 구현했다.

## 구현 범위

| 구분 | 요청 | 성공 응답 |
|---|---|---|
| 실습 1 | `GET /books` | 200, 도서 목록 JSON 배열 |
| 실습 2 | `POST /books` | 200, `도서 등록이 완료되었습니다!` 문자열 |
| 필수 미션 1 | `GET /books/category/{categoryId}` | 200, 해당 카테고리의 도서 JSON 배열 |
| 필수 미션 2 | `POST /rentals` | 201, `{"message":"도서 대여 기록이 생성되었습니다!"}` |

Controller → Service → Repository로 요청을 전달한다. Controller는 경로 변수와 JSON Body를 받고 응답을 반환한다. Service는 Repository를 호출한다. Repository만 `JdbcTemplate`으로 DB에 접근한다. 요청은 `Map<String, Object>`, 조회 결과는 `List<Map<String, Object>>`로 전달하며 DTO와 ORM은 사용하지 않는다.

## 실행 준비

Java 21, MySQL, Gradle Wrapper가 필요하다. Spring Boot 버전은 가이드의 `3.5.0`이며 Gradle은 `9.7.1`이다.

1. **새로 만든 빈 실습 DB**에서 [2주차 스키마](../week02/01_schema.sql), [더미 데이터](../week02/02_seed.sql)를 순서대로 실행한다. 예시 DB 이름은 `study`다.
2. IntelliJ에서 이 `week03` 폴더를 Gradle 프로젝트로 연다. Gradle JVM과 프로젝트 SDK를 Java 21로 선택한다.
3. `StudyApplication` 실행 구성에 다음 환경변수를 설정한다. 본인의 DB 이름과 계정에 맞게 바꾼다.

```text
DB_URL=jdbc:mysql://localhost:3306/study?serverTimezone=Asia/Seoul&characterEncoding=UTF-8
DB_USER=root
DB_PW=본인의_로컬_DB_비밀번호
```

[.env.example](.env.example)은 입력 항목을 보여주는 예시다. Spring Boot가 이 파일을 자동으로 읽지는 않는다. `application.yml`은 `${DB_URL}`, `${DB_USER}`, `${DB_PW}`를 읽으며 HikariCP와 JdbcTemplate은 Spring Boot가 생성한다.

PowerShell에서 실행하려면 환경변수를 설정한 뒤 아래 명령을 실행한다. 기본 서버 포트는 8080이며 필요하면 `SERVER_PORT` 환경변수로 바꿀 수 있다.

```powershell
# week03 폴더에서 실행, JAVA_HOME은 설치한 Java 21 경로로 설정
.\gradlew.bat build
.\gradlew.bat bootRun
```

## 실습 과정과 핵심 코드

### 실습 1 — 전체 도서 조회

[BookController](src/main/java/com/umc/study/controller/BookController.java)의 `@GetMapping`이 요청을 받고, [BookService](src/main/java/com/umc/study/service/BookService.java)를 거쳐 [BookRepository](src/main/java/com/umc/study/repository/BookRepository.java)의 조회 메서드를 호출한다.

```sql
SELECT * FROM book ORDER BY book_id;
```

`queryForList`로 조회하여 DB 컬럼명이 그대로 JSON의 키가 된다. 최초 더미 데이터의 도서 ID 1, 2, 3을 확인했다. `ORDER BY book_id`로 결과 순서를 고정했다.

### 실습 2 — 도서 등록 후 다시 조회

```json
{
  "categoryId": 1,
  "title": "클린 코드",
  "description": "애자일 소프트웨어 장인 정신"
}
```

```sql
INSERT INTO book (category_id, title, description, is_available)
VALUES (?, ?, ?, true);
```

`jdbcTemplate.update(sql, body.get("categoryId"), body.get("title"), body.get("description"))`로 SQL의 물음표 순서에 맞춰 바인딩한다. book_id는 AUTO_INCREMENT이므로 생략한다. 등록 응답은 워크북과 동일한 문자열이다. GET 재조회에서 4번째 도서인 클린 코드와 대여 가능 상태를 확인했다.

### 필수 미션 1 — 카테고리별 조회

`@GetMapping("/category/{categoryId}")`와 `@PathVariable("categoryId") Long categoryId`로 경로 변수를 받는다.

```sql
SELECT * FROM book WHERE category_id = ? ORDER BY book_id;
```

Repository의 `queryForList(sql, categoryId)`에 값을 바인딩한다. 카테고리 1은 도서 1, 2, 4를, 카테고리 2는 도서 3을 반환했다. 대여 불가인 책 2도 카테고리에 속하므로 포함된다. 존재하지 않는 카테고리 999는 빈 배열을 반환한다.

### 필수 미션 2 — 대여 기록 생성

[RentalController](src/main/java/com/umc/study/controller/RentalController.java) → [RentalService](src/main/java/com/umc/study/service/RentalService.java) → [RentalRepository](src/main/java/com/umc/study/repository/RentalRepository.java) 순서로 처리한다.

```json
{
  "userId": 1,
  "bookId": 4
}
```

```sql
INSERT INTO rental (user_id, book_id, rented_at, due_at)
VALUES (?, ?, NOW(), DATE_ADD(NOW(), INTERVAL 7 DAY));
```

`jdbcTemplate.update(sql, body.get("userId"), body.get("bookId"))`로 사용자와 도서 ID를 바인딩한다. rental_id는 AUTO_INCREMENT이며 returned_at은 NULL로 저장된다. 201 응답을 확인하고 MySQL에서 사용자 1·도서 4의 행이 추가됐는지 검사했다. 대여 시각이 DB의 현재 시각과 일치하며 `due_at - rented_at = 604800초`(7일)임을 확인했다.

## 실제 실행 검증

[검증 스크립트](validation/verify_mysql.py)는 기존 MySQL 서비스와 별개로 임시 서버를 만들고, 원본 2주차 SQL을 실행한 뒤 실제 Spring 서버에 HTTP 요청을 보낸다. 실행이 끝나면 Spring과 MySQL 프로세스를 종료한다. `--serve`는 Postman 확인을 위해 서버를 유지하며 Ctrl+C로 종료한다.

```powershell
# 저장소 루트에서, 먼저 week03의 build를 완료
python week03\validation\verify_mysql.py
# Postman에서 확인할 서버를 유지하려면
python week03\validation\verify_mysql.py --serve
```

MySQL 경로가 다르면 `MYSQL_BIN`을 bin 폴더로 지정한다. Java 경로는 `JAVA_HOME`으로 지정한다. `SERVER_PORT`가 사용 중이면 시작 전에 중단하므로 실행 중인 다른 API에 쓰기 요청을 보내지 않는다.

실제 실행에서 **12개 HTTP 사례와 MySQL 저장 검증이 통과**했다. 결과의 시간대는 Asia/Seoul(+09:00)이다.

| 확인 항목 | 실제 결과 |
|---|---|
| 최초 전체 목록 | 200, 도서 3권 |
| 신규 도서 등록·재조회 | 200, 클린 코드 추가·총 4권 |
| 카테고리 1 / 2 / 999 | 200, 각각 도서 ID [1,2,4] / [3] / [] |
| 숫자가 아닌 경로 변수 | 400 |
| 신규 대여 | 201, rental 1행 증가 |
| 대여 시각·예정일 | 현재 시각, 정확히 7일 차이, 미반납(NULL) |
| title 대신 titel 오타 | 500, 제목 NOT NULL 제약으로 삽입 실패·도서 수 동일 |
| 존재하지 않는 사용자 ID | 500, FK 제약으로 삽입 실패·대여 수 동일 |
| SQL 구문처럼 보이는 제목 | 문자열로 저장되고 book 테이블 유지 |

원본 증거:

- [verification.json](results/verification.json): 검증 요약, 실행 시각, 원본 SQL 해시
- [http-results.json](results/http-results.json): 실제 요청 URL·Body·상태 코드·응답
- [rental-db.tsv](results/rental-db.tsv): 실제 저장된 대여 시각과 7일 간격
- [00_setup.tsv](results/00_setup.tsv): 생성된 테이블
- [server.log](results/server.log): Spring/HikariCP 시작과 의도적으로 발생시킨 오류

## Postman 확인과 인증

[Postman Collection](postman/week03.postman_collection.json)을 Import하고 `baseUrl`을 자신의 서버 주소로 설정한다(기본 `http://localhost:8080`). 요청을 위에서부터 순서대로 실행한다. 등록 후 재조회 요청의 테스트가 새 도서 ID를 `createdBookId`에 저장하므로 대여 요청은 방금 등록한 책을 사용한다.

인증 시 카테고리 조회에서는 URL과 200 상태 및 JSON 배열을, 대여 생성에서는 Body와 201 상태 및 JSON 응답을 한 화면에 캡처한다. 도서 등록 실습은 200 상태와 완료 문자열, 등록 후 GET 목록을 함께 확인한다.

Postman 웹과 공식 Desktop Agent로 로컬 서버에 실제 요청을 보내고 아래 화면을 캡처했다. 원본 브라우저 캡처(JPEG)를 내용 변경 없이 PNG로 변환했다. 필수 미션 화면에는 요청 URL·대여 Body·성공 상태 코드·JSON 응답이 보인다.

- [실습 — 전체 도서 조회, 200 OK](results/postman-get-books.png)
- [실습 — 도서 등록, JSON Body와 200 OK](results/postman-post-books.png)
- [필수 미션 — 카테고리별 조회, 200 OK와 JSON](results/postman-category.png)
- [필수 미션 — 대여 생성, JSON Body와 201 Created](results/postman-rental.png)

도서 등록 응답은 워크북 예시대로 완료 문자열이다. JSON 응답은 도서 조회 및 대여 생성 화면에서 확인할 수 있다. 캡처는 `--serve`로 유지한 임시 MySQL과 Spring Boot 서버에서 실행했다. 아래 HTTP 로그는 별도로 수행한 12개 자동 검증 결과이며, Postman 캡처의 요청 실행 기록과는 구분된다.

아래 이미지는 실제 HTTP 로그와 MySQL 조회 결과를 시각화한 **검증 보고서**다. Postman 원본 스크린샷이 아니며, 각 이미지에 출처와 실행 시각을 표시했다.

- [실습 1 — 전체 목록 조회](results/practice-get-books.png)
- [실습 2 — 도서 등록·재조회](results/practice-post-books.png)
- [필수 미션 1 — 카테고리별 조회](results/mission-category.png)
- [필수 미션 2 — 대여 생성·저장 확인](results/mission-rental.png)

이미지는 Pillow가 설치된 Python으로 `validation/build_evidence.py`를 실행하면 원본 로그에서 다시 생성된다. `--serve`로 유지한 서버는 Ctrl+C 또는 `.validation-runtime/stop` 파일 생성으로 종료할 수 있다.

## 생 SQL·No DTO 체험 및 트러블슈팅

1. **오타 실습:** `title` 대신 `titel`을 보냈을 때 Java 컴파일 단계는 통과하지만 `body.get("title")`이 null이 된다. MySQL의 `title NOT NULL` 제약으로 500이 발생했다. 워크북의 오류 체험을 위해 Map 입력에 검증을 추가하지 않았으며, 이 방식에서는 필수 입력 검증과 오류 변환을 별도로 해야 한다.
2. **응답 결합:** GET 결과에 `book_id`, `category_id`, `is_available`가 그대로 나타난다. DB 컬럼 변경은 JSON 응답의 키에도 영향을 준다.
3. **수동 매핑:** INSERT 컬럼·물음표·Java 인자의 순서를 직접 맞췄다. 문자열처럼 보이는 SQL 입력도 값으로 바인딩되어 실행문이 되지 않는 것을 실제로 확인했다.
4. **빌드 의존성:** 처음에는 Gradle 플러그인 캐시만으로 빌드되지 않았다. 의존성을 다운로드한 뒤 Java 21로 빌드를 완료했다.

대여 API의 범위는 워크북에 명시된 대여 기록 INSERT다. 도서 상태 변경, 중복 대여 검사, 대여 한도 같은 정책은 이 미션에서 구현하지 않았다.
