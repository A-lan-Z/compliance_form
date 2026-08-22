package com.example.dcl.application.error;

public final class WorkflowNotFoundException extends DclException {
    public WorkflowNotFoundException() {
        super(404, "WORKFLOW_NOT_FOUND", "Workflow not found", "The requested workflow was not found.");
    }
}
