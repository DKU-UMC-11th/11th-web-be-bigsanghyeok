# Week 07 핵심 코드

Notion에 아래 코드 블록을 그대로 복사할 수 있다. JWT 비밀키는 환경변수에서 읽는다.

## exception/ApiException.java

```java
package com.umc.movie.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public class ApiException extends RuntimeException {

    private final HttpStatus status; // 응답으로 내보낼 HTTP 상태 코드
    private final String code;       // 응답 바디의 code 필드에 실릴 문자열

    public ApiException(HttpStatus status, String code, String message) {
        super(message); // message는 부모인 RuntimeException이 들고 있어줍니다
        this.status = status;
        this.code = code;
    }
}
```

## util/JwtUtil.java

```java
package com.umc.movie.util;

import com.umc.movie.exception.ApiException;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;

@Component
public class JwtUtil {

    private final SecretKey secretKey;
    private final Duration accessExpiration;

    public JwtUtil(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.access-expiration}") Long accessExpiration
    ) {
        // 문자열 비밀키를 HMAC-SHA 서명용 키 객체로 바꿉니다.
        // 이 키가 있어야만 서명을 만들 수 있고 같은 키로만 검증할 수 있습니다.
        this.secretKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        if (accessExpiration == null || accessExpiration <= 0) {
            throw new IllegalArgumentException("JWT access expiration must be positive seconds");
        }
        this.accessExpiration = Duration.ofSeconds(accessExpiration);
    }

    /**
     * 로그인에 성공한 회원에게 발급할 Access Token을 만듭니다.
     */
    public String createAccessToken(Long memberId, String email) {
        Instant now = Instant.now();

        return Jwts.builder()
                .subject(String.valueOf(memberId)) // 토큰의 주인이 누구인지. 우리는 memberId를 넣습니다
                .claim("email", email)             // 참고용 부가 정보 (없어도 동작합니다)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(accessExpiration))) // 만료 시각이 없으면 영원히 유효한 토큰이 됩니다
                .signWith(secretKey)               // 이 서명 덕분에 내용을 조작하면 검증에서 걸립니다
                .compact();
    }

    /**
     * 토큰을 검증하고 그 안에 담긴 memberId를 꺼냅니다.
     * 서명이 맞지 않거나 만료된 토큰이면 예외를 던지므로 이 메서드가 값을 돌려줬다면
     * "검증까지 통과한 토큰"이라는 뜻입니다.
     */
    public Long getMemberId(String token) {
        try {
            Claims claims = getClaims(token).getPayload();
            String subject = claims.getSubject();
            if (subject == null || !subject.matches("[1-9][0-9]*") || claims.getExpiration() == null) {
                throw new IllegalArgumentException("Missing or invalid required claims");
            }
            return Long.valueOf(subject);
        } catch (ExpiredJwtException e) {
            // 만료는 사용자가 다시 로그인하면 해결되는 상황이라 따로 구분해줍니다
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH401_4",
                    "토큰이 만료되었습니다. 다시 로그인해주세요.");
        } catch (JwtException | IllegalArgumentException e) {
            // 서명 불일치, 형식 오류 등 그 외 모든 실패
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH401_3",
                    "유효하지 않은 토큰입니다.");
        }
    }

    private Jws<Claims> getClaims(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)  // 이 키로 서명을 다시 계산해서 대조합니다
                .clockSkewSeconds(60)   // 서버와 클라이언트 시계가 조금 어긋나도 되도록 60초 여유를 둡니다
                .build()
                .parseSignedClaims(token);
    }
}
```

## interceptor/AuthInterceptor.java

```java
package com.umc.movie.interceptor;

import com.umc.movie.exception.ApiException;
import com.umc.movie.util.JwtUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
@RequiredArgsConstructor
public class AuthInterceptor implements HandlerInterceptor {

    public static final String MEMBER_ID = "memberId"; // 컨트롤러에서 꺼낼 때 쓸 이름
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtUtil jwtUtil;

    /**
     * 컨트롤러가 실행되기 "전"에 호출됩니다.
     * true를 반환하면 요청이 컨트롤러까지 이어지고 예외를 던지면 여기서 끝납니다.
     */
    @Override
    public boolean preHandle(
            HttpServletRequest request,
            HttpServletResponse response,
            Object handler
    ) {
        // 브라우저가 본 요청 전에 보내는 CORS 사전 요청(preflight)에는 토큰이 붙지 않습니다.
        // 여기서 막아버리면 브라우저에서 오는 모든 요청이 실패하므로 그냥 통과시킵니다.
        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            return true;
        }

        String header = request.getHeader(HttpHeaders.AUTHORIZATION);

        // "Bearer {토큰}" 형식이 아니면 아예 토큰을 보내지 않은 것으로 봅니다
        if (header == null || !header.startsWith(BEARER_PREFIX)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH401_2",
                    "로그인이 필요한 요청입니다.");
        }

        // 검증에 실패하면 JwtUtil이 예외를 던지므로 여기까지 왔다면 유효한 토큰입니다
        Long memberId = jwtUtil.getMemberId(header.substring(BEARER_PREFIX.length()));

        // 뒤이어 실행될 컨트롤러가 꺼내 쓸 수 있도록 요청에 담아둡니다
        request.setAttribute(MEMBER_ID, memberId);

        return true;
    }
}
```

## config/WebConfig.java

```java
package com.umc.movie.config;

import com.umc.movie.interceptor.AuthInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;

    // 5주차에서 작성한 CORS 설정입니다. 본인이 설정한 값을 그대로 두세요.
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("http://localhost:5173")
                .allowedMethods("GET", "POST", "PATCH", "DELETE", "OPTIONS")
                .allowedHeaders("*");
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
                // 일단 모든 경로를 잠그고
                .addPathPatterns("/**")
                // 로그인 없이도 써야 하는 경로만 예외로 열어줍니다
                .excludePathPatterns(
                        "/auth/**",              // 로그인
                        "/members",              // 회원가입 (POST /members)
                        "/members/nickname/**",  // 닉네임 중복 체크
                        "/members/email/**",     // 이메일 중복 체크
                        "/members/*/ratings",    // 유저별 평점 조회 (누구나 볼 수 있는 목록)
                        "/error"                 // 스프링이 내부적으로 쓰는 경로
                );
    }
}
```

## dto/ApiResponse.java

```java
package com.umc.movie.dto;

public record ApiResponse<T>(boolean isSuccess, String code, String message, T result) {
    public static <T> ApiResponse<T> created(String message, T result) {
        return new ApiResponse<>(true, "COMMON201", message, result);
    }

    public static <T> ApiResponse<T> ok(String message, T result) {
        return new ApiResponse<>(true, "COMMON200", message, result);
    }

    public static ApiResponse<Void> failure(String code, String message) {
        return new ApiResponse<>(false, code, message, null);
    }
}
```

## dto/LoginRequest.java

```java
package com.umc.movie.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record LoginRequest(

        @NotBlank(message = "이메일을 입력해주세요.")
        @Email(message = "이메일 형식이 올바르지 않습니다.")
        String email,

        // 로그인 단계에서는 비밀번호 규칙(대소문자/숫자/특수문자)까지 검사하지 않습니다.
        // 규칙이 바뀌기 전에 가입한 회원이 로그인조차 못 하게 되기 때문입니다.
        @NotBlank(message = "비밀번호를 입력해주세요.")
        String password
) {
}
```

## dto/LoginResponse.java

```java
package com.umc.movie.dto;

public record LoginResponse(
        String nickname,
        String accessToken
) {
}
```

## dto/MemberInfoResponse.java

```java
package com.umc.movie.dto;

import com.umc.movie.entity.Member;

import java.time.LocalDateTime;

public record MemberInfoResponse(
        String email,
        String nickname,
        LocalDateTime createdAt
) {
    // 엔티티를 그대로 응답하면 password까지 나가버리므로 반드시 DTO로 옮겨 담습니다
    public static MemberInfoResponse from(Member member) {
        return new MemberInfoResponse(
                member.getEmail(),
                member.getNickname(),
                member.getCreatedAt()
        );
    }
}
```

## dto/MemberUpdateRequest.java

```java
package com.umc.movie.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record MemberUpdateRequest(

        @NotBlank(message = "닉네임을 입력해주세요.")
        @Size(min = 2, max = 12, message = "닉네임은 2자 이상 12자 이하여야 합니다.")
        String nickname
) {
}
```

## dto/CreateRatingRequest.java

```java
package com.umc.movie.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

public record CreateRatingRequest(
        @NotNull(message = "영화 ID를 입력해주세요.")
        @Positive(message = "영화 ID는 양수여야 합니다.") Long movieId,
        @NotNull(message = "별점을 입력해주세요.")
        @Min(value = 1, message = "별점은 1점 이상이어야 합니다.")
        @Max(value = 5, message = "별점은 5점 이하여야 합니다.") Integer score,
        @Size(max = 500, message = "후기는 500자 이하로 입력해주세요.") String comment
) {}
```

## dto/UpdateRatingRequest.java

```java
package com.umc.movie.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record UpdateRatingRequest(
        @NotNull(message = "별점을 입력해주세요.")
        @Min(value = 1, message = "별점은 1점 이상이어야 합니다.")
        @Max(value = 5, message = "별점은 5점 이하여야 합니다.") Integer score,
        @Size(max = 500, message = "후기는 500자 이하로 입력해주세요.") String comment
) {}
```

## dto/RatingResponse.java

```java
package com.umc.movie.dto;

import com.umc.movie.entity.Rating;

import java.time.LocalDateTime;

public record RatingResponse(
        Long ratingId,
        Long movieId,
        Integer score,
        String comment,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
    public static RatingResponse from(Rating rating) {
        return new RatingResponse(
                rating.getRatingId(),
                rating.getMovieId(),
                rating.getScore(),
                rating.getComment(),
                rating.getCreatedAt(),
                rating.getUpdatedAt()
        );
    }
}
```

## entity/Member.java

```java
package com.umc.movie.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "member")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Member extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "member_id")
    private Long memberId;

    @Column(nullable = false, unique = true, length = 254)
    private String email;

    @Column(nullable = false, length = 60)
    private String password;

    @Column(nullable = false, unique = true, length = 50)
    private String nickname;

    public Member(String email, String password, String nickname) {
        this.email = email;
        this.password = password;
        this.nickname = nickname;
    }

    public void updateNickname(String nickname) {
        this.nickname = nickname;
    }
}
```

## entity/Rating.java

```java
package com.umc.movie.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "rating", uniqueConstraints = @UniqueConstraint(columnNames = {"member_id", "movie_id"}))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Rating extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "rating_id")
    private Long ratingId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(name = "movie_id", nullable = false)
    private Long movieId;

    @Column(nullable = false, columnDefinition = "TINYINT")
    private Integer score;

    @Column(columnDefinition = "TEXT")
    private String comment;

    @Builder
    public Rating(Member member, Long movieId, Integer score, String comment) {
        this.member = member;
        this.movieId = movieId;
        this.score = score;
        this.comment = comment;
    }

    public void update(Integer score, String comment) {
        this.score = score;
        this.comment = comment;
    }
}
```

## repository/MemberRepository.java

```java
package com.umc.movie.repository;

import com.umc.movie.entity.Member;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface MemberRepository extends JpaRepository<Member, Long> {
    boolean existsByNickname(String nickname);
    boolean existsByEmail(String email);
    Optional<Member> findByEmail(String email);
    boolean existsByNicknameAndMemberIdNot(String nickname, Long memberId);
}
```

## repository/RatingRepository.java

```java
package com.umc.movie.repository;

import com.umc.movie.entity.Rating;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RatingRepository extends JpaRepository<Rating, Long> {
    List<Rating> findByMember_MemberIdOrderByRatingIdDesc(Long memberId);
    boolean existsByMember_MemberIdAndMovieId(Long memberId, Long movieId);
}
```

## service/AuthService.java

```java
package com.umc.movie.service;

import com.umc.movie.dto.LoginRequest;
import com.umc.movie.dto.LoginResponse;
import com.umc.movie.entity.Member;
import com.umc.movie.exception.ApiException;
import com.umc.movie.repository.MemberRepository;
import com.umc.movie.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder; // 6주차 회원가입에서 등록해둔 Bean입니다
    private final JwtUtil jwtUtil;

    @Transactional(readOnly = true)
    public LoginResponse login(LoginRequest request) {
        // 1. 이메일로 회원을 찾습니다.
        //    없어도 "가입되지 않은 이메일"이라고 알려주지 않고 아래와 같은 예외를 던집니다.
        Member member = memberRepository.findByEmail(request.email())
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "AUTH401_1",
                        "이메일 또는 비밀번호가 올바르지 않습니다."));

        // 2. 입력한 비밀번호를 저장된 해시와 비교합니다.
        //    matches()가 저장된 해시에서 salt를 꺼내 같은 방식으로 해시한 뒤 대조해줍니다.
        if (!passwordEncoder.matches(request.password(), member.getPassword())) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH401_1",
                    "이메일 또는 비밀번호가 올바르지 않습니다.");
        }

        // 3. 검증을 통과했으니 토큰을 발급합니다.
        String accessToken = jwtUtil.createAccessToken(member.getMemberId(), member.getEmail());

        return new LoginResponse(member.getNickname(), accessToken);
    }
}
```

## service/MemberService.java

```java
package com.umc.movie.service;

import com.umc.movie.dto.EmailCheckResponse;
import com.umc.movie.dto.MemberInfoResponse;
import com.umc.movie.dto.MemberUpdateRequest;
import com.umc.movie.exception.ApiException;
import com.umc.movie.dto.MemberResponse;
import com.umc.movie.dto.SignUpRequest;
import com.umc.movie.entity.Member;
import com.umc.movie.dto.NicknameCheckResponse;
import com.umc.movie.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.nio.charset.StandardCharsets;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class MemberService {

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;

    @Transactional(readOnly = true)
    public MemberInfoResponse getMyInfo(Long memberId) {
        return MemberInfoResponse.from(findMember(memberId));
    }

    @Transactional
    public MemberInfoResponse updateMyInfo(Long memberId, MemberUpdateRequest request) {
        Member member = findMember(memberId);
        if (memberRepository.existsByNicknameAndMemberIdNot(request.nickname(), memberId)) {
            throw new ApiException(HttpStatus.CONFLICT, "MEMBER409_1", "이미 사용 중인 닉네임입니다.");
        }
        member.updateNickname(request.nickname());
        return MemberInfoResponse.from(member);
    }

    private Member findMember(Long memberId) {
        return memberRepository.findById(memberId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "MEMBER404_1",
                        "해당 회원을 찾을 수 없습니다."));
    }

    @Transactional
    public MemberResponse signUp(SignUpRequest request) {
        if (request.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "비밀번호는 UTF-8 기준 72바이트 이하여야 합니다.");
        }
        if (memberRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("이미 사용 중인 이메일입니다.");
        }
        if (memberRepository.existsByNickname(request.nickname())) {
            throw new IllegalArgumentException("이미 사용 중인 닉네임입니다.");
        }
        Member saved = memberRepository.save(new Member(request.email(),
                passwordEncoder.encode(request.password()), request.nickname()));
        return new MemberResponse(saved.getMemberId(), saved.getEmail(), saved.getNickname());
    }

    @Transactional(readOnly = true)
    public NicknameCheckResponse checkNickname(String nickname) {
        boolean exists = memberRepository.existsByNickname(nickname);
        return new NicknameCheckResponse(!exists);
    }

    @Transactional(readOnly = true)
    public EmailCheckResponse checkEmail(String email) {
        boolean exists = memberRepository.existsByEmail(email);
        return new EmailCheckResponse(!exists);
    }
}
```

## service/RatingService.java

```java
package com.umc.movie.service;

import com.umc.movie.dto.CreateRatingRequest;
import com.umc.movie.dto.RatingResponse;
import com.umc.movie.dto.UpdateRatingRequest;
import com.umc.movie.entity.Member;
import com.umc.movie.entity.Rating;
import com.umc.movie.exception.ApiException;
import com.umc.movie.repository.MemberRepository;
import com.umc.movie.repository.RatingRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class RatingService {

    private final RatingRepository ratingRepository;
    private final MemberRepository memberRepository;

    // 5주차에 만든 조회입니다. 예외만 ApiException으로 바꿨습니다.
    @Transactional(readOnly = true)
    public List<RatingResponse> getRatingsByMember(Long memberId) {
        if (!memberRepository.existsById(memberId)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "MEMBER404_1",
                    "해당 회원을 찾을 수 없습니다.");
        }

        return ratingRepository.findByMember_MemberIdOrderByRatingIdDesc(memberId).stream()
                .map(RatingResponse::from)
                .toList();
    }

    @Transactional
    public RatingResponse create(Long memberId, CreateRatingRequest request) {
        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "MEMBER404_1",
                        "해당 회원을 찾을 수 없습니다."));

        if (ratingRepository.existsByMember_MemberIdAndMovieId(memberId, request.movieId())) {
            throw new ApiException(HttpStatus.CONFLICT, "RATING409_1",
                    "이미 이 영화에 평점을 남기셨습니다.");
        }

        Rating rating = Rating.builder()
                .member(member)
                .movieId(request.movieId())
                .score(request.score())
                .comment(request.comment())
                .build();

        return RatingResponse.from(ratingRepository.save(rating));
    }

    @Transactional
    public RatingResponse update(Long memberId, Long ratingId, UpdateRatingRequest request) {
        Rating rating = findOwnedRating(memberId, ratingId);

        rating.update(request.score(), request.comment());
        // @UpdateTimestamp도 응답 DTO에 최신 값으로 반영되도록 먼저 flush합니다.
        ratingRepository.saveAndFlush(rating);

        return RatingResponse.from(rating);
    }

    @Transactional
    public void delete(Long memberId, Long ratingId) {
        Rating rating = findOwnedRating(memberId, ratingId);

        ratingRepository.delete(rating);
    }

    /**
     * 평점을 찾고 그 평점이 요청자의 것인지까지 확인합니다.
     * 수정과 삭제가 똑같은 검사를 하므로 메서드로 묶었습니다.
     */
    private Rating findOwnedRating(Long memberId, Long ratingId) {
        Rating rating = ratingRepository.findById(ratingId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "RATING404_1",
                        "해당 평점을 찾을 수 없습니다."));

        // 존재는 하지만 내 것이 아니라면 인가 실패입니다
        if (!rating.getMember().getMemberId().equals(memberId)) {
            throw new ApiException(HttpStatus.FORBIDDEN, "RATING403_1",
                    "본인이 작성한 평점만 수정하거나 삭제할 수 있습니다.");
        }

        return rating;
    }
}
```

## controller/AuthController.java

```java
package com.umc.movie.controller;

import com.umc.movie.dto.LoginRequest;
import com.umc.movie.dto.ApiResponse;
import com.umc.movie.dto.LoginResponse;
import com.umc.movie.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<LoginResponse>> login(
            @RequestBody @Valid LoginRequest request
    ) {
        LoginResponse response = authService.login(request);
        return ResponseEntity.ok(ApiResponse.ok("로그인에 성공했습니다.", response));
    }
}
```

## controller/MemberController.java

```java
package com.umc.movie.controller;

import com.umc.movie.dto.EmailCheckResponse;
import com.umc.movie.dto.MemberInfoResponse;
import com.umc.movie.dto.MemberUpdateRequest;
import com.umc.movie.interceptor.AuthInterceptor;
import com.umc.movie.dto.ApiResponse;
import com.umc.movie.dto.MemberResponse;
import com.umc.movie.dto.SignUpRequest;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import com.umc.movie.dto.NicknameCheckResponse;
import com.umc.movie.service.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
@RequestMapping("/members")
public class MemberController {

    private final MemberService memberService;

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<MemberInfoResponse>> getMyInfo(
            @RequestAttribute(AuthInterceptor.MEMBER_ID) Long memberId) {
        return ResponseEntity.ok(ApiResponse.ok("회원 정보를 조회했습니다.", memberService.getMyInfo(memberId)));
    }

    @PatchMapping("/me")
    public ResponseEntity<ApiResponse<MemberInfoResponse>> updateMyInfo(
            @RequestAttribute(AuthInterceptor.MEMBER_ID) Long memberId,
            @Valid @RequestBody MemberUpdateRequest request) {
        return ResponseEntity.ok(ApiResponse.ok("회원 정보를 수정했습니다.", memberService.updateMyInfo(memberId, request)));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<MemberResponse>> signUp(@Valid @RequestBody SignUpRequest request) {
        return ResponseEntity.status(201).body(ApiResponse.created("회원가입에 성공했습니다.", memberService.signUp(request)));
    }

    @GetMapping("/nickname/{nickname}")
    public NicknameCheckResponse checkNickname(@PathVariable("nickname") String nickname) {
        return memberService.checkNickname(nickname);
    }

    @GetMapping("/email/{email}")
    public EmailCheckResponse checkEmail(@PathVariable("email") String email) {
        return memberService.checkEmail(email);
    }
}
```

## controller/RatingController.java

```java
package com.umc.movie.controller;

import com.umc.movie.dto.ApiResponse;
import com.umc.movie.dto.CreateRatingRequest;
import com.umc.movie.dto.RatingResponse;
import com.umc.movie.dto.UpdateRatingRequest;
import com.umc.movie.interceptor.AuthInterceptor;
import com.umc.movie.service.RatingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class RatingController {

    private final RatingService ratingService;

    // 5주차에 만든 유저별 평점 조회입니다. 공개 API라 토큰을 받지 않습니다.
    @GetMapping("/members/{memberId}/ratings")
    public List<RatingResponse> getMemberRatings(@PathVariable Long memberId) {
        return ratingService.getRatingsByMember(memberId);
    }

    // 경로에서 /members/{memberId}가 사라지고 memberId는 인터셉터가 담아둔 값을 씁니다
    @PostMapping("/ratings")
    public ResponseEntity<ApiResponse<RatingResponse>> create(
            @RequestAttribute(AuthInterceptor.MEMBER_ID) Long memberId,
            @RequestBody @Valid CreateRatingRequest request
    ) {
        RatingResponse response = ratingService.create(memberId, request);
        return ResponseEntity.status(201)
                .body(ApiResponse.created("평점을 등록했습니다.", response));
    }

    // 경로에서도 /{memberId}가 사라지고 인터셉터가 담아둔 값을 씁니다
    @PatchMapping("/ratings/{ratingId}")
    public ResponseEntity<ApiResponse<RatingResponse>> update(
            @RequestAttribute(AuthInterceptor.MEMBER_ID) Long memberId,
            @PathVariable Long ratingId,
            @RequestBody @Valid UpdateRatingRequest request
    ) {
        RatingResponse response = ratingService.update(memberId, ratingId, request);
        return ResponseEntity.ok(ApiResponse.ok("평점을 수정했습니다.", response));
    }

    @DeleteMapping("/ratings/{ratingId}")
    public ResponseEntity<ApiResponse<Void>> delete(
            @RequestAttribute(AuthInterceptor.MEMBER_ID) Long memberId,
            @PathVariable Long ratingId
    ) {
        ratingService.delete(memberId, ratingId);
        return ResponseEntity.ok(ApiResponse.ok("평점을 삭제했습니다.", null));
    }
}
```

## controller/GlobalExceptionHandler.java

```java
package com.umc.movie.controller;

import com.umc.movie.dto.ApiResponse;
import com.umc.movie.exception.ApiException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiResponse<Void>> apiException(ApiException exception) {
        return ResponseEntity.status(exception.getStatus())
                .body(ApiResponse.failure(exception.getCode(), exception.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> validation(MethodArgumentNotValidException exception) {
        String message = exception.getBindingResult().getFieldErrors().getFirst().getDefaultMessage();
        return ResponseEntity.badRequest().body(ApiResponse.failure("COMMON4001", message));
    }

    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<ApiResponse<Void>> malformedRequest(Exception exception) {
        return ResponseEntity.badRequest().body(ApiResponse.failure(
                "COMMON4001", "요청 JSON 형식 또는 필드 타입이 올바르지 않습니다."));
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ApiResponse<Void>> dataIntegrity(DataIntegrityViolationException exception) {
        return ResponseEntity.status(409).body(ApiResponse.failure("COMMON4091", "이미 존재하는 데이터입니다."));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> conflict(IllegalArgumentException exception) {
        return ResponseEntity.status(409).body(ApiResponse.failure("COMMON4092", exception.getMessage()));
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<ApiResponse<Void>> responseStatus(ResponseStatusException exception) {
        int status = exception.getStatusCode().value();
        return ResponseEntity.status(status).body(ApiResponse.failure("COMMON" + status, exception.getReason()));
    }
}
```
