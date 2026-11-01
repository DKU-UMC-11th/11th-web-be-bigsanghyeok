package com.umc.study.repository;

import com.umc.study.entity.Book;
import java.util.List;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BookRepository extends JpaRepository<Book, Long> {
    @EntityGraph(attributePaths = "category")
    List<Book> findAllByOrderByBookIdDesc();
}
