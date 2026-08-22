package com.example.dcl.application.error;

import java.util.List;

public class DclException extends RuntimeException {
    private final int status;
    private final String code;
    private final String title;
    private final List<FieldErrorDetail> fieldErrors;
    private final Long currentVersion;

    public DclException(int status, String code, String title, String detail) {
        this(status, code, title, detail, List.of(), null);
    }

    public DclException(
            int status,
            String code,
            String title,
            String detail,
            List<FieldErrorDetail> fieldErrors,
            Long currentVersion) {
        super(detail);
        this.status = status;
        this.code = code;
        this.title = title;
        this.fieldErrors = List.copyOf(fieldErrors);
        this.currentVersion = currentVersion;
    }

    public int status() {
        return status;
    }

    public String code() {
        return code;
    }

    public String title() {
        return title;
    }

    public List<FieldErrorDetail> fieldErrors() {
        return fieldErrors;
    }

    public Long currentVersion() {
        return currentVersion;
    }
}
