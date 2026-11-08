# 핵심 키워드

## 1. Bean Validation과 @Valid

Bean Validation은 DTO에 @NotBlank, @Email, @Size, @Min/@Max 같은 제약을 선언하는 방식이다. @Valid는 그 제약을 검사하도록 연결하며 자체가 입력 제약은 아니다. Controller의 @Valid @RequestBody 검증 실패는 MethodArgumentNotValidException으로 처리해 Service에 도달하기 전에 400을 반환한다. 형식 검증을 통과해도 회원 존재 여부와 중복 같은 업무 규칙은 Service에서 별도로 확인해야 한다. [Spring MVC Validation](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html)

## 2. class-validator와 ValidationPipe

NestJS에서는 class-validator의 @IsEmail, @IsInt, @Min/@Max 등으로 DTO 제약을 선언하고 ValidationPipe로 실제 요청 검증을 실행한다. transform은 전달 데이터를 DTO 인스턴스로 변환하는 데 사용한다. whitelist는 DTO에 검증 메타데이터가 없는 속성을 걸러내며, forbidNonWhitelisted를 함께 쓰면 허용되지 않은 속성을 오류로 처리한다. 이번 구현은 Spring Boot 한 스택만 선택했지만 DTO 선언과 검증 실행을 구분한다는 원리는 같다. [NestJS Validation](https://docs.nestjs.com/techniques/validation)

## 3. bcrypt와 salt round

bcrypt는 복호화하는 암호화가 아니라 비밀번호 확인을 위한 단방향 해시 함수다. 매번 생성한 salt를 포함하므로 같은 비밀번호도 서로 다른 해시가 나오며, 로그인 검증에는 문자열 동등 비교 대신 PasswordEncoder.matches를 사용한다. cost(salt round)는 계산량을 조절하고 보통 한 단계 증가하면 비용이 약 두 배가 되므로 실제 서버 성능에 맞춰 정한다. 이번에는 기본 cost 10으로 저장한 60자 해시를 DB에서 읽어 matches 성공과 서로 다른 salt를 검증했다. 입력은 UTF-8 기준 72바이트 이하로 제한했다. [Spring Security Password Storage](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html)

## 4. HTTP 201 Created / 204 No Content / 409 Conflict

201은 회원·평점 같은 새 자원을 생성했을 때 사용하고 응답에 생성된 식별자를 제공한다. 204는 요청을 성공적으로 처리했지만 보낼 본문이 없다는 의미라 삭제 성공 응답에 JSON을 넣지 않았다. 409는 중복 이메일·평점처럼 현재 자원 상태와 충돌하는 요청에 사용했다. 입력 형식·범위 오류인 400, 다른 소유자 요청인 403, 자원이 없는 404와 구분했다. [HTTP Semantics RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)

## 5. UNIQUE 제약 조건과 동시성

Service의 exists 검사와 INSERT는 서로 다른 동작이므로 두 요청이 동시에 사전 중복 검사를 통과할 수 있다. 따라서 email·nickname과 (member_id, movie_id)의 UNIQUE 제약을 DB에도 유지해야 한다. 사전 검사는 이해하기 쉬운 메시지를 위한 것이며 최종 무결성은 DB가 보장한다. 실습 2에 따라 DataIntegrityViolationException도 공통 409 형식으로 처리했다. 이번 필수 미션에서는 반복 중복 요청의 저장 행 수를 확인했으며 선택 Challenge의 동시 요청 실험은 수행하지 않았다. [MySQL CREATE TABLE Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table.html)

## 6. @RestControllerAdvice / Exception Filter

Spring의 @RestControllerAdvice와 @ExceptionHandler는 여러 Controller의 예외를 한 곳에서 HTTP 상태와 공통 응답으로 변환한다. NestJS의 Exception Filter도 예외에서 상태·메시지를 읽어 같은 응답 규칙을 적용하는 역할을 한다. 이번에는 DTO 오류·JSON 타입 오류 400, 중복 409, 소유권 403, 없는 자원 404를 공통 ApiResponse로 변환했다. Controller마다 try-catch를 복제하지 않아 오류 형식을 일관되게 유지할 수 있다. [Spring Exception Handling](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html), [NestJS Exception Filters](https://docs.nestjs.com/exception-filters)

# 학습 후기

DTO는 입력 형식과 범위를, Service는 중복·존재 여부·소유권을, DB는 UNIQUE/FK 무결성을 맡는 역할 분리가 중요하다는 점을 확인했다. 특히 Integer 필드만 선언해도 소수 입력이 막히는 것은 아니어서, 실제 요청으로 타입 변환까지 검증해야 했다.

비밀번호는 응답 DTO에서 제외하고 DB에 저장된 bcrypt 해시까지 검증했으며, 204 응답은 공통 JSON 형식의 예외로 본문을 비워야 한다는 점도 확인했다. 다음 주차에는 경로 memberId를 신뢰하는 현재 방식에서 토큰 기반 사용자 확인으로 넘어가는 흐름을 연결해 보고 싶다.
