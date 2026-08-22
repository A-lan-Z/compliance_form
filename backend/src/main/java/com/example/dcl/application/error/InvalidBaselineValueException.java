package com.example.dcl.application.error;

public final class InvalidBaselineValueException extends DclException {
    public InvalidBaselineValueException(String detail) {
        super(422, "INVALID_BASELINE_VALUE", "Invalid baseline value", detail);
    }
}
