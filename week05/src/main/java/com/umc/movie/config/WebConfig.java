package com.umc.movie.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    private final boolean enabled;
    public WebConfig(@Value("${app.cors-enabled:true}") boolean enabled) { this.enabled = enabled; }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        if (enabled) {
            registry.addMapping("/**")
                    .allowedOrigins("http://localhost:5173")
                    .allowedMethods("GET", "POST", "PATCH", "DELETE")
                    .allowedHeaders("*");
        }
    }
}
