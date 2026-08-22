package com.example.dcl.adapter.web;

import com.example.dcl.application.error.DclException;
import com.example.dcl.application.error.FieldErrorDetail;
import com.example.dcl.application.error.UnknownFieldException;
import com.example.dcl.application.error.WorkflowNotFoundException;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import java.util.List;
import org.springframework.core.NestedExceptionUtils;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    private final ProblemDetailsFactory problems;

    public ApiExceptionHandler(ProblemDetailsFactory problems) {
        this.problems = problems;
    }

    @ExceptionHandler(DclException.class)
    ResponseEntity<ProblemDetail> handleDcl(DclException exception, HttpServletRequest request) {
        return response(exception.status(), problems.from(exception, request));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ProblemDetail> handleTypeMismatch(
            MethodArgumentTypeMismatchException exception, HttpServletRequest request) {
        WorkflowNotFoundException notFound = new WorkflowNotFoundException();
        return response(notFound.status(), problems.from(notFound, request));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ProblemDetail> handleValidation(
            MethodArgumentNotValidException exception, HttpServletRequest request) {
        List<FieldErrorDetail> fieldErrors = exception.getBindingResult().getFieldErrors().stream()
                .map(this::fieldError)
                .toList();
        ProblemDetail problem = problems.create(
                422,
                "INVALID_FIELD_VALUE",
                "Invalid field value",
                "One or more field values are invalid.",
                request,
                fieldErrors,
                null);
        return response(422, problem);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ProblemDetail> handleUnreadable(
            HttpMessageNotReadableException exception, HttpServletRequest request) {
        Throwable root = NestedExceptionUtils.getMostSpecificCause(exception);
        if (root instanceof UnrecognizedPropertyException unrecognized) {
            UnknownFieldException unknown = new UnknownFieldException(unrecognized.getPropertyName());
            return response(unknown.status(), problems.from(unknown, request));
        }
        ProblemDetail problem = problems.create(
                422,
                "INVALID_FIELD_VALUE",
                "Invalid request",
                "The request body is malformed or has an invalid value.",
                request,
                List.of(),
                null);
        return response(422, problem);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    ResponseEntity<ProblemDetail> handleConstraint(
            ConstraintViolationException exception, HttpServletRequest request) {
        ProblemDetail problem = problems.create(
                422,
                "INVALID_FIELD_VALUE",
                "Invalid field value",
                "One or more field values are invalid.",
                request,
                List.of(),
                null);
        return response(422, problem);
    }

    @ExceptionHandler({DataAccessResourceFailureException.class, CannotCreateTransactionException.class})
    ResponseEntity<ProblemDetail> handleDatabaseUnavailable(
            Exception exception, HttpServletRequest request) {
        ProblemDetail problem = problems.create(
                503,
                "DEPENDENCY_UNAVAILABLE",
                "Dependency unavailable",
                "The workflow database is unavailable.",
                request,
                List.of(),
                null);
        return response(503, problem);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ProblemDetail> handleUnexpected(Exception exception, HttpServletRequest request) {
        ProblemDetail problem = problems.create(
                500,
                "INTERNAL_ERROR",
                "Internal error",
                "The request could not be completed.",
                request,
                List.of(),
                null);
        return response(500, problem);
    }

    private FieldErrorDetail fieldError(FieldError error) {
        return new FieldErrorDetail(
                error.getField(),
                "INVALID_FIELD_VALUE",
                error.getDefaultMessage() == null ? "Invalid value" : error.getDefaultMessage());
    }

    private ResponseEntity<ProblemDetail> response(int status, ProblemDetail problem) {
        return ResponseEntity.status(HttpStatus.valueOf(status))
                .header("Content-Type", "application/problem+json")
                .body(problem);
    }
}
