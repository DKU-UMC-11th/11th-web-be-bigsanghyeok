-- 1주차 ERD 확장: 회원 1이 지역 1에서 완료한 미션을 최근 완료순으로 최대 10개 조회한다.
-- 화면에는 미션명, 가게명, 지역명, 완료 시각, 해당 미션에서 획득한 포인트를 표시한다.
-- 이 쿼리는 도서 대여 DB가 아니라 week01 ERD 구조의 리워드 DB에서 실행한다.
SELECT
    m.title AS mission_title,
    s.name AS store_name,
    rg.name AS region_name,
    mm.completed_at,
    mm.awarded_points
FROM member_mission AS mm
INNER JOIN mission AS m
    ON m.id = mm.mission_id
INNER JOIN store AS s
    ON s.id = m.store_id
INNER JOIN region AS rg
    ON rg.id = s.region_id
WHERE mm.member_id = 1
  AND rg.id = 1
  AND mm.status = 'COMPLETED'
ORDER BY mm.completed_at DESC, mm.id DESC
LIMIT 10;

-- 기준 테이블은 member_mission이며, mission → store → region을 JOIN하여 화면에 필요한 이름을 조회한다.
-- WHERE는 회원 1, 지역 1, 완료 상태를 선택하며, 과거 내역이므로 가게나 미션의 현재 활성 상태로 제외하지 않는다.
-- 완료 시각 내림차순으로 최대 10개를 반환하고, 완료 시각이 같으면 수행 내역 ID 내림차순으로 순서를 고정한다.
