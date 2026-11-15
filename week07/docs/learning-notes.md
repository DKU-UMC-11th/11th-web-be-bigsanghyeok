# 핵심 키워드

## 인증(Authentication)과 인가(Authorization)

인증은 요청자가 누구인지 확인하는 과정이고 인가는 그 사람이 특정 행동을 할 수 있는지 판단하는 과정이다. 로그인과 JWT 검증은 인증이고, 평점의 작성자와 요청자 ID를 비교하는 것은 인가다. 유효한 토큰을 가져도 남의 평점에는 권한이 없다.

## 해시와 salt, bcrypt

해시는 복호화해서 원래 비밀번호를 얻는 방식이 아니다. bcrypt는 무작위 salt와 비용 인자를 사용해 같은 비밀번호도 다른 해시로 저장한다. salt는 해시 문자열에 포함되므로 matches()는 저장된 해시에서 필요한 값을 읽어 입력 비밀번호를 비교할 수 있다. 회원가입은 encode(), 로그인은 matches()를 사용한다. bcrypt의 72바이트 제한도 입력에서 처리한다.

## JWT (Header / Payload / Signature, Claim)

JWT는 header.payload.signature로 나뉜다. header는 알고리즘을, payload는 sub·email·iat·exp 같은 claim을 담고 signature는 내용 변경을 검출한다. Base64URL 인코딩은 암호화가 아니므로 payload는 누구나 읽을 수 있다. 비밀번호를 넣지 않고 서버 비밀키는 환경변수로 관리한다. 상태를 저장하지 않고 검증하기 쉽지만 만료 전 강제 폐기에는 별도 설계가 필요하다.

## Bearer 인증과 Authorization 헤더

`Authorization: Bearer {token}`은 토큰을 가진 요청자를 인증하는 HTTP 헤더 형식이다. GET·DELETE처럼 바디가 없는 요청에도 동일하게 보낼 수 있다. 토큰을 탈취하면 소지자가 사용할 수 있으므로 전송에는 HTTPS를 사용하고 URL이나 불필요한 로그에 담지 않는다. 이 실습은 로컬 루프백에서만 실행했다.

## HandlerInterceptor / Guard

컨트롤러 앞에서 공통 인증을 수행한다. Spring HandlerInterceptor의 preHandle에서 토큰을 검증하고 request attribute에 memberId를 넣어 컨트롤러가 사용하게 했다. NestJS Guard도 요청을 허용하거나 차단하는 역할을 한다. 소유권처럼 DB와 기능 규칙이 필요한 인가는 서비스에서 처리한다. 브라우저의 OPTIONS 사전 요청에는 토큰이 없으므로 통과시킨다.

## 401 Unauthorized와 403 Forbidden의 차이

401은 요청자를 인증할 수 없는 경우다. 이 구현에서는 로그인 실패, 토큰 누락·변조·만료에 따라 AUTH401_1~4로 구분한다. 403은 인증됐지만 권한이 없는 경우로 남의 평점 수정·삭제 시 RATING403_1을 반환한다. 대상 자체가 없으면 RATING404_1이다. 상태와 code를 함께 보면 프론트에서 재로그인과 권한 안내를 다르게 처리할 수 있다.

# 학습 후기

memberId를 요청에서 받는 대신 검증된 JWT에서 꺼내도록 바꾸면서 사용자를 구분하는 기준이 서버에 있어야 한다는 점을 이해했다. 특히 토큰은 유효한데 남의 평점 수정이 403으로 막히는 과정을 통해 인증과 인가의 차이가 명확해졌다. 공통 인증은 인터셉터, 소유권은 서비스로 나누고 실패 응답을 코드별로 구분하니 원인을 확인하기도 쉬웠다.
