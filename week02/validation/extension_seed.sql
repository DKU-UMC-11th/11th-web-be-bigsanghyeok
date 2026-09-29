-- 확장 쿼리 검증을 위해 별도로 작성한 데이터. 공통 02_seed.sql은 변경하지 않는다.
INSERT INTO member (id, name, nickname, gender, birth_date, address, status, created_at, updated_at)
VALUES
    (1, '민서', '민서', 'UNSPECIFIED', '2000-01-01', '서울', 'ACTIVE', '2026-09-01', '2026-09-01'),
    (2, '수현', '수현', 'UNSPECIFIED', '2000-02-01', '서울', 'ACTIVE', '2026-09-01', '2026-09-01');
INSERT INTO food_category (id, name) VALUES (1, '한식'), (2, '카페');
INSERT INTO region (id, code, name) VALUES (1, 'ANAM', '안암동'), (2, 'OTHER', '다른 지역');
INSERT INTO store (id, region_id, food_category_id, name, address, status)
VALUES (1, 1, 1, '안암 식당', '안암동', 'OPEN'),
       (2, 1, 2, '안암 카페', '안암동', 'OPEN'),
       (3, 2, 1, '다른 지역 식당', '다른 지역', 'OPEN');
INSERT INTO mission (id, store_id, title, description, min_spend, reward_type, reward_value, starts_at, ends_at, status)
VALUES
    (1, 1, '한식 식사 미션', '10,000원 이상 식사', 10000, 'FIXED', 500, '2026-09-01', '2026-10-01', 'ACTIVE'),
    (2, 2, '카페 방문 미션', '음료 구매', 4000, 'FIXED', 300, '2026-09-01', '2026-10-01', 'ACTIVE'),
    (3, 1, '진행 중 미션', '진행 상태 제외 확인', 0, 'FIXED', 100, '2026-09-01', '2026-10-01', 'ACTIVE'),
    (4, 1, '다른 회원 미션', '회원 조건 확인', 0, 'FIXED', 100, '2026-09-01', '2026-10-01', 'ACTIVE'),
    (5, 3, '다른 지역 미션', '지역 조건 확인', 0, 'FIXED', 100, '2026-09-01', '2026-10-01', 'ACTIVE');
INSERT INTO member_mission (id, member_id, mission_id, status, accepted_at, completed_at, paid_amount, awarded_points, updated_at)
VALUES
    (1, 1, 1, 'COMPLETED', '2026-09-27 11:00:00', '2026-09-27 12:00:00', 10000, 500, '2026-09-27 12:00:00'),
    (2, 1, 2, 'COMPLETED', '2026-09-28 14:00:00', '2026-09-28 15:00:00', 4000, 300, '2026-09-28 15:00:00'),
    (3, 1, 3, 'IN_PROGRESS', '2026-09-28 16:00:00', NULL, NULL, NULL, '2026-09-28 16:00:00'),
    (4, 2, 4, 'COMPLETED', '2026-09-28 16:00:00', '2026-09-28 17:00:00', 0, 100, '2026-09-28 17:00:00'),
    (5, 1, 5, 'COMPLETED', '2026-09-28 17:00:00', '2026-09-28 18:00:00', 0, 100, '2026-09-28 18:00:00');
