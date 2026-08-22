package com.example.dcl.application.error;

import java.util.List;

public final class UnknownFieldException extends DclException {
    public UnknownFieldException(String field) {
        super(
                422,
                "UNKNOWN_FIELD",
                "Unknown field",
                "The request contains an unknown field.",
                List.of(new FieldErrorDetail(field, "UNKNOWN_FIELD", "Unknown field")),
                null);
    }
}
