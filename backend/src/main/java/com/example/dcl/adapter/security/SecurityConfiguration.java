package com.example.dcl.adapter.security;

import com.example.dcl.adapter.web.ProblemDetailsFactory;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import java.util.List;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;

@Configuration
public class SecurityConfiguration {

    @Bean
    SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            ObjectProvider<LocalFixedPrincipalFilter> localPrincipal,
            ProblemDetailsFactory problems,
            ObjectMapper objectMapper) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .httpBasic(basic -> basic.disable())
                .formLogin(form -> form.disable())
                .logout(logout -> logout.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers("/actuator/health/**").permitAll()
                        .requestMatchers("/api/**").authenticated()
                        .anyRequest().permitAll())
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, exception) -> {
                            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                            response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
                            objectMapper.writeValue(
                                    response.getOutputStream(),
                                    problems.create(
                                            401,
                                            "ACCESS_DENIED",
                                            "Authentication required",
                                            "Authentication is required to access this resource.",
                                            request,
                                            List.of(),
                                            null));
                        })
                        .accessDeniedHandler((request, response, exception) -> {
                            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                            response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
                            objectMapper.writeValue(
                                    response.getOutputStream(),
                                    problems.create(
                                            403,
                                            "ACCESS_DENIED",
                                            "Access denied",
                                            "You are not authorized to access this resource.",
                                            request,
                                            List.of(),
                                            null));
                        }));
        LocalFixedPrincipalFilter filter = localPrincipal.getIfAvailable();
        if (filter != null) {
            http.addFilterBefore(filter, AnonymousAuthenticationFilter.class);
        }
        return http.build();
    }

    @Bean
    @Profile("local")
    FilterRegistrationBean<LocalFixedPrincipalFilter> disableLocalPrincipalServletRegistration(
            ObjectProvider<LocalFixedPrincipalFilter> localPrincipal) {
        FilterRegistrationBean<LocalFixedPrincipalFilter> registration = new FilterRegistrationBean<>();
        LocalFixedPrincipalFilter filter = localPrincipal.getIfAvailable();
        if (filter != null) {
            registration.setFilter(filter);
        }
        registration.setEnabled(false);
        return registration;
    }
}
