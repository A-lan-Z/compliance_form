package com.example.dcl.application.error;

public final class WorkflowVersionConflictException extends DclException {
    public WorkflowVersionConflictException(long currentVersion) {
        super(
                409,
                "WORKFLOW_VERSION_CONFLICT",
                "Workflow version conflict",
                "This draft changed elsewhere. Reload before saving.",
                java.util.List.of(),
                currentVersion);
    }
}
