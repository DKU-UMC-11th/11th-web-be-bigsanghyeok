package com.umc.study.repository;

import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
@RequiredArgsConstructor
public class BookRepository {
    private final JdbcTemplate jdbcTemplate;

    public List<Map<String, Object>> findAll() {
        return jdbcTemplate.queryForList("SELECT * FROM book ORDER BY book_id");
    }

    public List<Map<String, Object>> findByCategoryId(Long categoryId) {
        String sql = "SELECT * FROM book WHERE category_id = ? ORDER BY book_id";
        return jdbcTemplate.queryForList(sql, categoryId);
    }

    public void save(Map<String, Object> body) {
        // AUTO_INCREMENT인 book_id를 생략하고, 입력값은 ?에 바인딩한다.
        String sql = """
                INSERT INTO book (category_id, title, description, is_available)
                VALUES (?, ?, ?, true)
                """;
        jdbcTemplate.update(sql, body.get("categoryId"), body.get("title"), body.get("description"));
    }
}
