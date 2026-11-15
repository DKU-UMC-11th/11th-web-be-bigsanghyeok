# Week 07 — 로그인한 사용자를 구분하기

Spring Boot(Java 21)로 실습 1~6과 필수 미션을 구현했다. JWT 로그인, 내 정보 조회·수정, 인증된 사용자의 평점 등록·수정·삭제를 제공한다.

## 실행

1. MySQL에 `umc_movie` 데이터베이스를 만들고 `sql/01_schema.sql`, `sql/02_seed.sql`을 순서대로 실행한다.
2. `.env.example`의 항목을 실행 환경변수에 설정한다. Spring Boot는 `.env`를 자동으로 읽지 않는다. DB 비밀번호와 JWT 키는 저장소에 커밋하지 않는다.
3. `JWT_SECRET`에는 무작위로 만든 32바이트 이상의 문자열을 넣는다. PowerShell 예시:

```powershell
$env:DB_URL = 'jdbc:mysql://localhost:3306/umc_movie'
$env:DB_USER = 'root'
$env:DB_PASSWORD = '본인의 DB 비밀번호'
$env:JWT_SECRET = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
$env:JWT_ACCESS_EXPIRATION = '3600'
.\gradlew.bat bootRun
```

매번 새 키를 만들면 이전에 발급한 토큰은 검증되지 않는다. 직접 실행할 때는 생성한 키를 로컬 실행 환경에서 유지한다. 기본 API 주소는 `http://localhost:8080`이다.

기존 seed 회원의 비밀번호는 5·6주차 조회용 더미 값이다. 로그인 실습은 `POST /members`로 새로 가입한 회원을 사용한다.

## 구현

| 실습 | 구현 내용 |
| --- | --- |
| 1 | bcrypt `matches()`로 비밀번호 비교 후 JWT 발급. 없는 이메일과 틀린 비밀번호는 동일한 401 |
| 2 | HandlerInterceptor에서 Authorization 헤더·서명·만료 검증, request attribute에 memberId 저장 |
| 3 | GET /members/me. 비밀번호를 제외한 DTO 응답, 토큰 누락·변조 차단 |
| 4 | PATCH /members/me. 본인 닉네임 유지 허용, 타 회원 닉네임 중복 409 |
| 5 | POST /ratings, PATCH·DELETE /ratings/{ratingId}. 작성자는 토큰으로만 결정 |
| 6 | 인증 실패 401, 소유권 위반 403, 존재하지 않는 대상 404 분리 |

회원가입·중복 확인·회원별 평점 목록은 공개 API로 유지했다. 평점 삭제는 `200 / COMMON200 / result: null`이다. 선택 미션과 CodeRabbit 리뷰는 제외했다.

## 검증 및 제출 파일

```powershell
.\gradlew.bat --no-daemon build
python validation\verify_mysql.py
# Postman 캡처용으로 서버를 유지할 때
python validation\verify_mysql.py --serve
# 종료 신호 (다른 터미널에서)
Set-Content .validation-runtime\stop stop
```

검증 스크립트는 설치된 MySQL 실행 파일을 사용해 임시 데이터 디렉터리와 무작위 DB 포트를 만든다. 기존 DB에 쓰지 않는다. API 검증 포트는 기본 18087이며 이미 사용 중이면 중단한다. `MYSQL_BIN`, `JAVA_HOME`, `SERVER_PORT`를 환경에 맞게 조정할 수 있다. JWT 키는 매 실행 시 무작위로 생성하며 저장하지 않는다. 캡처에 나온 토큰은 임시 서버 종료 후 재사용할 수 없다.

- `docs/core-code.md`, `.txt`: Notion에 복사할 핵심 코드 텍스트
- `docs/practice-evidence.md`: 실습별 인증 설명
- `docs/mission-record.md`: 필수 미션 과정과 9단계 실행 결과
- `docs/learning-notes.md`: 핵심 키워드와 학습 후기
- `postman/week07.postman_collection.json`: 실행 순서와 토큰 저장 스크립트가 포함된 요청 모음
- `results/http-results.json`, `verification.json`: 실제 HTTP·MySQL 검증 결과
- `results/practice/`: 실습 인증 PNG
- `results/required-mission/`: 필수 제출 PNG 4장
- `results/week07-submission.zip`: 코드·문서·인증 파일 묶음
