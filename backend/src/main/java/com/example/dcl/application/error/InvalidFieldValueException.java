package com.example.dcl.application.error;

import java.util.List;

public final class InvalidFieldValueException extends DclException {
    public InvalidFieldValueException(String field, String message) {
        super(
                422,
                "INVALID_FIELD_VALUE",
                "Invalid field value",
                "One or more field values are invalid.",
                List.of(new FieldErrorDetail(field, "INVALID_FIELD_VALUE", message)),
                null);
    }
}
