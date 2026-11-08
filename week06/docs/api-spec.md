# 6주차 API 명세

일반 서버 `http://localhost:8080`, 격리 인증 서버 `http://localhost:18086`. Body가 있는 요청의 Content-Type은 application/json이다. 인증·JWT는 7주차 범위이며 현재는 경로 memberId로 소유자를 비교한다.

| 기능 | Method / URL | Body | 성공 |
|---|---|---|---|
| 회원가입 | POST /members | email, password, nickname | 201, 회원 DTO |
| 평점 등록 | POST /members/{memberId}/ratings | movieId, score, comment(선택) | 201, ratingId |
| 평점 수정 | PATCH /members/{memberId}/ratings/{ratingId} | score, comment(선택) | 200, result null |
| 평점 삭제 | DELETE /members/{memberId}/ratings/{ratingId} | 없음 | 204, Body 없음 |
| 회원별 평점 조회 | GET /members/{memberId}/ratings | 없음 | 200, RatingResponse 배열 |
| 닉네임 중복 체크 | GET /members/nickname/{nickname} | 없음 | 200, available boolean |
| 이메일 중복 체크 | GET /members/email/{email} | 없음 | 200, available boolean |

## 입력 규칙

- email: 비어 있지 않은 이메일 형식, DB 컬럼에 맞춰 254자 이하.
- nickname: 비어 있지 않으며 2~12자.
- password: 영문 대·소문자, 숫자, !@#$%^&* 중 특수문자를 포함한 8자 이상. bcrypt 처리를 위해 UTF-8 72바이트 이하. 응답에는 포함하지 않는다.
- movieId: 필수 양의 정수. TMDB ID이며 로컬 영화 테이블 FK가 아니다.
- score: 필수 정수 1~5. 소수는 변환하지 않고 400으로 거부한다.
- comment: 선택, null 허용, 최대 500자. PATCH에서 생략하면 null로 수정된다. PATCH는 score가 필수인 워크북 계약을 따른다.

## 요청·응답 예시

```http
POST /members
Content-Type: application/json
```

```json
{"email":"capture06@example.com","password":"Movie123!","nickname":"인증회원06"}
```

```json
{"isSuccess":true,"code":"COMMON201","message":"회원가입에 성공했습니다.","result":{"memberId":5,"email":"capture06@example.com","nickname":"인증회원06"}}
```

평점 등록 Body는 `{"movieId":550,"score":4,"comment":"등록 인증"}`, 수정 Body는 `{"score":5,"comment":"수정 인증"}`이다. 등록 응답의 result는 저장된 ratingId이며, 실제 발급 ID를 이후 요청 경로에 사용한다. 위 memberId는 격리 검증 데이터 기준 예시다.

```json
{"isSuccess":false,"code":"COMMON4092","message":"이미 이 영화에 평점을 남기셨습니다.","result":null}
```

## 실패 응답

| 상황 | HTTP | code |
|---|---|---|
| DTO 검증 실패·잘못된 JSON·숫자 타입 불일치 | 400 | COMMON4001 |
| bcrypt 72바이트 초과 | 400 | COMMON400 |
| 중복 이메일·닉네임·평점의 사전 확인 | 409 | COMMON4092 |
| DB 무결성 제약 위반 | 409 | COMMON4091 |
| 다른 회원 평점의 수정·삭제 | 403 | COMMON403 |
| 없는 회원·평점 | 404 | COMMON404 |

실패는 isSuccess=false, code, message, result=null의 같은 구조다. Validation 오류가 여러 개이면 첫 오류 메시지를 제공한다. 삭제한 평점을 다시 수정·삭제하면 404가 된다.
