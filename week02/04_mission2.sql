-- 미션 2: 사용자 1(민서)이 아직 반납하지 않은 책을 반납 예정일이 빠른 순으로 조회한다.
-- 다른 사용자를 조회하려면 아래 r.user_id = 1의 값을 변경한다.
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

-- 기준 테이블은 rental이며, book 1:N rental 관계를 따라 책 제목을 얻기 위해 JOIN한다.
-- 사용자 ID는 rental에 있으므로 users JOIN 없이 특정 사용자와 미반납 조건을 검사한다.
-- 반납 예정일 오름차순이며, 예정일이 같으면 rental_id 오름차순으로 순서를 고정하고 전체 목록을 반환한다.
