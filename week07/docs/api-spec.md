# API 명세

새 API와 평점 쓰기 API는 `isSuccess / code / message / result`로 응답한다. 기존 공개 조회는 이전 주차의 DTO 형식을 유지한다.

| Method | URL | 인증 | 요청 | 성공 |
| --- | --- | --- | --- | --- |
| POST | /members | 공개 | email, password, nickname | 201, 회원 ID·이메일·닉네임 |
| POST | /auth/login | 공개 | email, password | 200, nickname·accessToken |
| GET | /members/me | Bearer | 없음 | 200, email·nickname·createdAt |
| PATCH | /members/me | Bearer | nickname(2~12자) | 200, 수정된 내 정보 |
| POST | /ratings | Bearer | movieId, score(1~5 정수), comment(선택, 500자 이하) | 201, RatingResponse |
| PATCH | /ratings/{ratingId} | Bearer, 작성자 | score, comment | 200, RatingResponse |
| DELETE | /ratings/{ratingId} | Bearer, 작성자 | 없음 | 200, result: null |
| GET | /members/{memberId}/ratings | 공개 | 없음 | 200, RatingResponse 배열 |
| GET | /members/nickname/{nickname} | 공개 | 없음 | 200, available |
| GET | /members/email/{email} | 공개 | 없음 | 200, available |

RatingResponse 필드는 ratingId, movieId, score, comment, createdAt, updatedAt이다. memberId는 평점 쓰기 URL·요청 DTO에 없고 검증된 토큰의 sub에서 얻는다. Body나 query의 memberId를 추가해도 작성자는 바뀌지 않는다.

```http
Authorization: Bearer {accessToken}
Content-Type: application/json
```

| HTTP | code | 상황 |
| --- | --- | --- |
| 401 | AUTH401_1 | 없는 이메일 또는 틀린 비밀번호. 메시지도 동일 |
| 401 | AUTH401_2 | Authorization 헤더 또는 Bearer 형식 없음 |
| 401 | AUTH401_3 | 토큰 형식·서명·필수 claim 오류 |
| 401 | AUTH401_4 | 만료 토큰 |
| 404 | MEMBER404_1 | 회원 없음 |
| 409 | MEMBER409_1 | 내 정보 수정 시 타 회원 닉네임과 중복 |
| 404 | RATING404_1 | 평점 없음 |
| 403 | RATING403_1 | 다른 회원이 작성한 평점의 수정·삭제 |
| 409 | RATING409_1 | 같은 회원·영화의 중복 평점 |
| 400 | COMMON4001 | DTO 검증 또는 JSON·경로 타입 오류 |

이전 회원가입 검증·충돌 처리도 유지했다. 인터셉터를 전 경로에 등록하고 공개 경로와 `/error`만 제외했다. OPTIONS는 통과시키고 CORS에서 localhost:5173과 Authorization 헤더를 허용한다.

Access Token에는 sub(memberId 문자열), email, iat, exp만 담는다. 비밀번호나 해시는 담지 않는다. JJWT가 서명과 만료를 검증하고 최대 60초의 clock skew를 허용한다. 만료 시각과 양의 정수 sub가 없는 토큰도 거절한다. 이 주차에서는 토큰 재발급·로그아웃·강제 폐기를 구현하지 않는다.
