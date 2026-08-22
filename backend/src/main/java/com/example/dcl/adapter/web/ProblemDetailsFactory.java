package com.example.dcl.adapter.web;

import com.example.dcl.application.error.DclException;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;

@Component
public final class ProblemDetailsFactory {

    public ProblemDetail from(DclException exception, HttpServletRequest request) {
        return create(
                exception.status(),
                exception.code(),
                exception.title(),
                exception.getMessage(),
                request,
                exception.fieldErrors(),
                exception.currentVersion());
    }

    public ProblemDetail create(
            int status,
            String code,
            String title,
            String detail,
            HttpServletRequest request,
            List<?> fieldErrors,
            Long currentVersion) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.valueOf(status), detail);
        problem.setTitle(title);
        problem.setProperty("code", code);
        problem.setProperty("requestId", RequestIdFilter.requestId(request));
        if (fieldErrors != null && !fieldErrors.isEmpty()) {
            problem.setProperty("fieldErrors", fieldErrors);
        }
        if (currentVersion != null) {
            problem.setProperty("currentVersion", currentVersion);
        }
        return problem;
    }
}
