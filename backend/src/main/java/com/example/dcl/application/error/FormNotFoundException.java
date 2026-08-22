package com.example.dcl.application.error;

public final class FormNotFoundException extends DclException {
    public FormNotFoundException() {
        super(404, "FORM_NOT_FOUND", "Form not found", "The requested fixture form was not found.");
    }
}
