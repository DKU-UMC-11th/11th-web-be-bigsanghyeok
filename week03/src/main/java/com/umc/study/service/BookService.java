package com.umc.study.service;

import com.umc.study.repository.BookRepository;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class BookService {
    private final BookRepository bookRepository;

    public List<Map<String, Object>> getAllBooks() {
        return bookRepository.findAll();
    }

    public List<Map<String, Object>> getBooksByCategory(Long categoryId) {
        return bookRepository.findByCategoryId(categoryId);
    }

    public void createBook(Map<String, Object> body) {
        bookRepository.save(body);
    }
}
