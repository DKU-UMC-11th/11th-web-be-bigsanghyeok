# 4주차 필수 미션 — ORM 도서 API

[워크북](https://app.notion.com/p/4-ORM-API-9b81d799147b83c3ab8401cfe072f73f)의 **(필수)** 부분만 구현했다. Spring Boot 3.5.0 / Java 21 / Spring Data JPA / MySQL을 사용한다. 기존 `week03` Raw SQL 코드는 유지하며, 이번 주차의 실행 프로젝트와 제출물은 모두 `week04`에 둔다. 제목 검색, 중복 도서 등록 방지 등 선택 미션은 포함하지 않는다.

## 핵심 코드

- Entity: [Book](src/main/java/com/umc/study/entity/Book.java), [Category](src/main/java/com/umc/study/entity/Category.java)
- DTO: [CreateBookRequest](src/main/java/com/umc/study/dto/CreateBookRequest.java), [BookResponse](src/main/java/com/umc/study/dto/BookResponse.java)
- Repository: [BookRepository](src/main/java/com/umc/study/repository/BookRepository.java), [CategoryRepository](src/main/java/com/umc/study/repository/CategoryRepository.java)
- Service: [BookService](src/main/java/com/umc/study/service/BookService.java)
- Controller: [BookController](src/main/java/com/umc/study/controller/BookController.java), [ApiExceptionHandler](src/main/java/com/umc/study/controller/ApiExceptionHandler.java)

`Book.category`는 `@ManyToOne(fetch = LAZY)`와 `category_id` FK로 매핑했다. 조회 메서드는 카테고리도 함께 가져오고, 트랜잭션 안에서 응답 DTO로 변환한다. `ddl-auto: validate`와 `open-in-view: false`를 사용하므로 기존 테이블을 자동 생성·변경하지 않는다.

## API

| 요청 | 결과 |
|---|---|
| `GET /books` | `200`, 도서 ID 내림차순의 전체 도서 목록 |
| `POST /books` | `201`, 저장된 도서의 응답 DTO |
| 제목 누락·공백·100자 초과, categoryId 누락 | `400`, 필드별 검증 오류 |
| 숫자로 변환할 수 없는 categoryId | `400` |
| 존재하지 않는 categoryId | `404`, `존재하지 않는 카테고리입니다.` |

요청 예시:

```json
{
  "categoryId": 1,
  "title": "클린 코드",
  "description": "ORM으로 등록한 도서"
}
```

`description`은 생략하거나 null로 보낼 수 있다. 응답은 `bookId`, `title`, `description`, `categoryName`, `isAvailable` 다섯 필드만 포함한다. 도서 등록 시 대여 가능 여부의 기본값은 true이며 목록에는 대여 불가능한 도서도 포함한다.

## 실행

`week04` 폴더에서 실행한다. 기존 MySQL에 `week02/01_schema.sql` 및 `week02/02_seed.sql`의 테이블과 데이터가 준비되어 있어야 한다. 이미 준비된 DB에 해당 SQL을 다시 실행하지 않는다.

```powershell
$env:DB_URL = 'jdbc:mysql://127.0.0.1:3306/study?serverTimezone=Asia/Seoul&characterEncoding=UTF-8'
$env:DB_USER = '본인_DB_사용자'
$env:DB_PW = '본인_DB_비밀번호'
.\gradlew.bat bootRun
```

기본 API 주소는 `http://localhost:8080`이다. 환경 변수 `SERVER_PORT`로 포트를 변경할 수 있다. `.env.example`은 변수 목록의 예시이며 Spring Boot가 `.env`를 자동으로 읽는 것은 아니다. 실제 비밀번호가 포함된 파일을 Git에 올리지 않는다.

## 검증 및 Postman 제출물

```powershell
.\gradlew.bat build --no-daemon
python validation\verify_mysql.py
```

[통합 검증 스크립트](validation/verify_mysql.py)는 설치된 MySQL 실행 파일을 사용해 임시 MySQL 서버와 데이터베이스를 생성하고, 변경하지 않은 week02 SQL을 가져온다. 기존 사용자 DB에는 접속하지 않으며 테스트 포트가 사용 중이면 요청 전 중단한다. `MYSQL_BIN` 환경 변수로 MySQL 실행 파일 디렉터리를 지정할 수 있다. Java는 `JAVA_HOME` 또는 PATH에서 찾는다.

실제 검증 결과는 [verification.json](results/verification.json)과 [http-results.json](results/http-results.json)에 있다. Gradle 빌드는 성공했으며, JUnit 테스트 대신 위 스크립트로 **13개 실제 HTTP 요청과 MySQL 저장 결과**를 검증했다. 정상 등록, 등록 후 최신순 재조회, 설명 생략, 제목 100자 허용·101자 거부, 제목 오타·누락·공백, categoryId 누락·null·잘못된 형식, 존재하지 않는 카테고리를 확인했다. 실패 요청 이후 도서 수가 증가하지 않았으며 원본 SQL 파일의 해시도 동일했다.

[Postman Collection](postman/week04.postman_collection.json)에는 검증 요청, 상태 코드 테스트, 실제 HTTP 응답 예시가 들어 있다. 일반 실행 서버에서는 `baseUrl`을 `http://localhost:8080`으로 바꾼다. 격리 검증 서버를 Postman에서 호출하려면 다음처럼 실행한다.

```powershell
python validation\verify_mysql.py --serve
```

격리 검증의 기본 주소는 `http://localhost:18084`이다. 종료할 때 `week04/.validation-runtime/stop` 파일을 생성한다. 서버 종료 시 Spring Boot와 임시 MySQL 프로세스를 함께 정리한다.

Postman 화면 인증:

- [GET 성공 — 200 및 응답 DTO](results/postman-get-books.png)
- [POST 성공 — 요청 Body·201·응답 DTO](results/postman-create-book.png)
- [잘못된 제목 — 요청 Body·400·필드 오류](results/postman-invalid-title.png)
- [없는 카테고리 — 요청 Body·404·오류 메시지](results/postman-missing-category.png)

위 PNG는 Postman 웹과 Desktop Agent로 실제 API를 호출한 화면 캡처다. 별도의 자동 HTTP 검증 결과를 Postman 화면으로 꾸미지 않는다.

## 3주차 Raw SQL과 비교

1. 3주차에는 Repository에서 SELECT·INSERT SQL과 물음표 파라미터 순서를 직접 관리했지만, 4주차에는 JPA 엔티티와 `JpaRepository` 메서드가 조회·저장을 담당한다.
2. 3주차의 Map 응답은 DB의 snake_case 컬럼명을 그대로 노출했지만, 4주차에는 응답 DTO로 필요한 다섯 필드만 camelCase로 반환하고 카테고리 이름을 포함한다.
3. 3주차에는 `titel` 같은 오타가 DB의 NOT NULL 오류와 500으로 이어졌지만, 4주차에는 요청 DTO와 `@Valid`가 누락·빈 제목·길이 초과를 Service 실행 전에 400으로 거부한다.
4. 4주차는 등록 전에 카테고리를 조회하므로 없는 카테고리를 FK 오류까지 보내지 않고 404로 응답하며, 도서 등록과 DTO 변환은 하나의 트랜잭션에서 처리한다.

**실행 결과 검증:** 실제 MySQL에서 전체 도서가 최신순의 지정 DTO로 조회되고 정상 등록은 201, 잘못된 입력은 400, 없는 카테고리는 404로 응답하여 필수 요구사항과 일치함을 확인했다.

## 진행 과정 및 트러블슈팅

1. 워크북의 필수 구현·제출 기준을 확인하고 이슈 #4 및 `week4/4-mission` 브랜치를 생성했다.
2. 기존 Gradle Wrapper를 재사용하고 JPA·Validation 의존성을 추가했다. book/category 테이블의 이름·PK·FK·컬럼 제약을 확인하여 엔티티로 옮겼다.
3. Repository → Service → Controller 흐름을 구현하고 요청·응답 DTO 및 오류 처리를 분리했다.
4. 최초 DB 연결 검증에서 강제 지정한 TINYINT 매핑이 JDBC에서 BIT로 보고된 Boolean 메타데이터와 맞지 않아 시작에 실패했다. 강제 JDBC 타입 지정을 제거하고 기본 Boolean 매핑으로 기존 스키마의 `validate` 검증을 통과했다. DB 스키마는 변경하지 않았다.
5. 수정 후 빌드를 완료하고 실제 MySQL 통합 검증 13개를 통과했다. 성공·오류 요청을 Postman에서도 직접 실행하여 결과를 캡처했다.

CodeRabbit 리뷰는 사용자 요청에 따라 생략한다.
