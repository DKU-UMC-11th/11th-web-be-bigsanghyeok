-- 미션 1: 문학 카테고리에서 대여 가능한 책을 최신순으로 최대 10권 조회한다.
-- 등록일 컬럼이 없으므로 book_id가 클수록 최근 등록된 책이라고 가정한다.
SELECT
    b.title AS book_title,
    b.description,
    c.name AS category_name
FROM book AS b
INNER JOIN category AS c
    ON c.category_id = b.category_id
WHERE c.name = '문학'
  AND b.is_available = TRUE
ORDER BY b.book_id DESC
LIMIT 10;

-- 기준 테이블은 book이며, category 1:N book 관계를 따라 분류 이름을 얻기 위해 JOIN한다.
-- WHERE는 문학이면서 대여 가능한 책만 남긴다.
-- book_id 내림차순으로 정렬하고 최대 10권을 반환한다.
