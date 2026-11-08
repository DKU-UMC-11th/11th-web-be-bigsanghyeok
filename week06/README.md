# 6주차 — 입력한 데이터를 저장하기

[워크북](https://app.notion.com/p/6-9271d799147b83f59b52017406fc0760)의 실습 1~3과 필수 Standard Mission을 Spring Boot 3.5.0 / Java 21로 수행했다. `week05`를 보존하고 `week06`에 확장 버전을 구성했다. 선택 Challenge와 CodeRabbit 리뷰는 수행하지 않는다.

## 제출 자료

- [API 명세](docs/api-spec.md)
- [실습 인증](docs/practice-evidence.md)
- [필수 미션 기록·확인 포인트·트러블슈팅](docs/mission-record.md)
- [핵심 키워드 6개·학습 후기](docs/learning-notes.md)
- [실제 MySQL HTTP 결과](results/http-results.json), [검증 요약](results/verification.json)
- [Postman Collection](postman/week06.postman_collection.json)

핵심 코드: [DTO](src/main/java/com/umc/movie/dto), [MemberService](src/main/java/com/umc/movie/service/MemberService.java), [RatingService](src/main/java/com/umc/movie/service/RatingService.java), [Controller](src/main/java/com/umc/movie/controller), [PasswordConfig](src/main/java/com/umc/movie/config/PasswordConfig.java), [Rating](src/main/java/com/umc/movie/entity/Rating.java).

## 일반 실행

`week06`에서 실행한다. 로컬 MySQL에 별도 실습용 DB를 만들고 `sql/01_schema.sql`, `sql/02_seed.sql`을 순서대로 적용한다. 기존 데이터가 있는 DB에 다시 적용하지 않는다. 스키마는 5주차와 같으며 Favorite은 테이블만 유지한다.

```powershell
$env:DB_URL = 'jdbc:mysql://localhost:3306/umc_movie'
$env:DB_USER = '본인_DB_사용자'
$env:DB_PASSWORD = '본인_DB_비밀번호'
.\gradlew.bat bootRun
```

기본 주소는 `http://localhost:8080`, CORS 허용 출처는 `http://localhost:5173`이다. 실제 비밀번호는 환경 변수로만 제공하고 `.env.example`에는 예시 값만 둔다. Spring Boot는 `.env`를 자동으로 읽지 않는다.

## 실제 MySQL 검증

```powershell
.\gradlew.bat build --no-daemon
python validation\verify_mysql.py
```

설치된 MySQL 실행 파일을 사용해 임시 서버와 DB를 만들고, 기존 사용자 DB에는 접속하지 않는다. `MYSQL_BIN`으로 MySQL bin 폴더를, `JAVA_HOME`으로 JDK를 지정할 수 있다. 포트 18086이 사용 중이면 요청 전에 중단한다.

Postman 인증용 서버를 유지하려면 `python validation/verify_mysql.py --serve`를 실행한다. 종료는 `Set-Content .validation-runtime/stop stop`으로 한다. Spring Boot와 임시 MySQL 프로세스가 함께 종료된다.

Gradle 빌드는 성공했고 실제 HTTP **41개** 검증을 통과했다. JUnit 대신 실 DB·HTTP 통합 검증을 수행한다. DB에서 읽은 회원가입 해시는 `validation/VerifyPasswordHash.java`에서 BCryptPasswordEncoder.matches로 확인했다. 같은 테스트 비밀번호로 가입해도 두 해시가 다름을 확인했다. 새 회원의 응답 DTO에 password가 없고, 중복 평점은 추가 저장되지 않으며, 타인 요청 뒤 원본 평점이 유지되고, DELETE는 204와 0바이트 Body를 반환했다.

## 구현 범위와 동작

- 회원가입 요청 DTO에서 이메일, 닉네임 2~12자, 비밀번호 조합·최소 길이를 검증한다. DB email 컬럼 길이 및 bcrypt의 UTF-8 72바이트 한계도 오류로 처리한다.
- `spring-security-crypto`만 추가했으며 로그인 자동 설정을 켜는 starter-security는 사용하지 않았다.
- 저장 전 중복·회원 존재 여부를 확인하고 DB UNIQUE/FK 제약도 유지했다. 사전 체크가 DB 제약을 대신하지 않는다.
- 평점 수정·삭제는 평점을 먼저 조회하고 memberId가 소유자와 일치하는지 검사한다. 아직 로그인 전 주차이므로 memberId 자체의 사용자 신원은 인증하지 않는다.
- 신규 쓰기 API의 JSON 성공·실패는 공통 ApiResponse 형식이다. DELETE의 성공은 204이므로 JSON이 없다. 워크북 예시대로 5주차 GET 성공 응답은 기존 DTO/배열 형식을 유지했다.
- 소수 별점이 정수로 잘려 저장되는 문제를 실제로 재현하고, Jackson의 `accept-float-as-int`를 꺼서 400으로 수정했다. 수정 전후 원본 결과는 `results/troubleshooting`에 보관했다.
