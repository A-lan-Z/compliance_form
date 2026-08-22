package com.example.dcl.application.error;

public final class AccessDeniedException extends DclException {
    public AccessDeniedException() {
        super(403, "ACCESS_DENIED", "Access denied", "You are not authorized for this fixture asset and form.");
    }
}
