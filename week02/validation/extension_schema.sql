-- 별도 확장 검증 DB 전용: week01 컬럼 및 키를 재현한 fixture. 운영용 CHECK/로직은 생략.
CREATE TABLE `member` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `nickname` VARCHAR(50) NOT NULL,
    `email` VARCHAR(255),
    `phone` VARCHAR(20),
    `gender` VARCHAR(20) NOT NULL,
    `birth_date` DATE NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `address_detail` VARCHAR(255),
    `profile_image_url` VARCHAR(500),
    `status` VARCHAR(20) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    `withdrawn_at` DATETIME,
    PRIMARY KEY (`id`)
);

CREATE TABLE `social_account` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `member_id` BIGINT NOT NULL,
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`),
    `provider` VARCHAR(20) NOT NULL,
    `provider_user_id` VARCHAR(255) NOT NULL,
    `created_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE `food_category` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    UNIQUE (`name`),
    PRIMARY KEY (`id`)
);

CREATE TABLE `member_food_category` (
    `member_id` BIGINT NOT NULL,
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`),
    `food_category_id` BIGINT NOT NULL,
    FOREIGN KEY (`food_category_id`) REFERENCES `food_category` (`id`),
    PRIMARY KEY (`member_id`, `food_category_id`)
);

CREATE TABLE `terms` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL,
    `version` VARCHAR(30) NOT NULL,
    `title` VARCHAR(100) NOT NULL,
    `content` TEXT NOT NULL,
    `is_required` BOOLEAN NOT NULL,
    `effective_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE(code, version)
);

CREATE TABLE `member_agreement` (
    `member_id` BIGINT NOT NULL,
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`),
    `terms_id` BIGINT NOT NULL,
    FOREIGN KEY (`terms_id`) REFERENCES `terms` (`id`),
    `agreed` BOOLEAN NOT NULL,
    `agreed_at` DATETIME,
    `revoked_at` DATETIME,
    PRIMARY KEY (`member_id`, `terms_id`)
);

CREATE TABLE `region` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `code` VARCHAR(30) NOT NULL,
    UNIQUE (`code`),
    `name` VARCHAR(100) NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `store` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `region_id` BIGINT NOT NULL,
    FOREIGN KEY (`region_id`) REFERENCES `region` (`id`),
    `food_category_id` BIGINT NOT NULL,
    FOREIGN KEY (`food_category_id`) REFERENCES `food_category` (`id`),
    `name` VARCHAR(100) NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `phone` VARCHAR(20),
    `image_url` VARCHAR(500),
    `status` VARCHAR(20) NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `mission` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `store_id` BIGINT NOT NULL,
    FOREIGN KEY (`store_id`) REFERENCES `store` (`id`),
    `title` VARCHAR(100) NOT NULL,
    `description` TEXT NOT NULL,
    `min_spend` DECIMAL(12,0) NOT NULL,
    `reward_type` VARCHAR(20) NOT NULL,
    `reward_value` DECIMAL(12,2) NOT NULL,
    `starts_at` DATETIME NOT NULL,
    `ends_at` DATETIME NOT NULL,
    `status` VARCHAR(20) NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `member_mission` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `member_id` BIGINT NOT NULL,
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`),
    `mission_id` BIGINT NOT NULL,
    FOREIGN KEY (`mission_id`) REFERENCES `mission` (`id`),
    `status` VARCHAR(20) NOT NULL,
    `accepted_at` DATETIME NOT NULL,
    `completed_at` DATETIME,
    `verification_code_hash` VARCHAR(255),
    `code_expires_at` DATETIME,
    `paid_amount` DECIMAL(12,0),
    `awarded_points` INT,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE(member_id, mission_id)
);

CREATE TABLE `region_reward` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `member_id` BIGINT NOT NULL,
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`),
    `region_id` BIGINT NOT NULL,
    FOREIGN KEY (`region_id`) REFERENCES `region` (`id`),
    `cycle_no` INT NOT NULL,
    `points` INT NOT NULL,
    `awarded_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE(member_id, region_id, cycle_no)
);

CREATE TABLE `review` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `member_mission_id` BIGINT NOT NULL,
    UNIQUE (`member_mission_id`),
    FOREIGN KEY (`member_mission_id`) REFERENCES `member_mission` (`id`),
    `rating` DECIMAL(2,1) NOT NULL,
    `content` TEXT,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `review_image` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `review_id` BIGINT NOT NULL,
    FOREIGN KEY (`review_id`) REFERENCES `review` (`id`),
    `image_url` VARCHAR(500) NOT NULL,
    `sort_order` SMALLINT NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE(review_id, sort_order)
);
