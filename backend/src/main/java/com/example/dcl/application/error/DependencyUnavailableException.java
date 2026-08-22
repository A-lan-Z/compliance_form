package com.example.dcl.application.error;

public final class DependencyUnavailableException extends DclException {
    public DependencyUnavailableException() {
        super(503, "DEPENDENCY_UNAVAILABLE", "Dependency unavailable", "The fixture seed dependency is unavailable.");
    }
}
