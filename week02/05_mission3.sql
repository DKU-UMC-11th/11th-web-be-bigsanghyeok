-- 미션 3: 책 1('달빛 도서관')의 태그 목록과 사용자 1(민서)의 좋아요 여부를 조회한다.
-- 태그당 한 행으로 반환하며, 태그가 없는 책은 tag_name = NULL인 한 행으로 반환한다.
SELECT
    b.title AS book_title,
    t.name AS tag_name,
    CASE WHEN bl.user_id IS NULL THEN 0 ELSE 1 END AS is_liked
FROM book AS b
LEFT JOIN book_tag AS bt
    ON bt.book_id = b.book_id
LEFT JOIN tag AS t
    ON t.tag_id = bt.tag_id
LEFT JOIN book_like AS bl
    ON bl.book_id = b.book_id
   AND bl.user_id = 1
WHERE b.book_id = 1
ORDER BY t.tag_id ASC;

-- 기준 테이블은 book이며, book N:M tag 관계를 book_tag로 연결하고 book_like로 특정 사용자의 좋아요를 확인한다.
-- WHERE는 책을 선택하고 사용자 조건은 LEFT JOIN의 ON에 두어 좋아요가 없어도 책이 조회되게 한다.
-- 태그 ID 오름차순으로 전체 태그를 보여주며, is_liked의 1은 좋아요, 0은 좋아요하지 않음을 뜻한다.
