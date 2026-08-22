package com.example.dcl.application.error;

import java.util.List;

public final class ReadOnlyFieldException extends DclException {
    public ReadOnlyFieldException(String field) {
        super(
                422,
                "READ_ONLY_FIELD",
                "Read-only field",
                "Disposal Action is derived by the server and cannot be supplied.",
                List.of(new FieldErrorDetail(field, "READ_ONLY_FIELD", "This field is read-only")),
                null);
    }
}
