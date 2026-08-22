package com.example.dcl.application.error;

public final class InvalidWorkflowStateException extends DclException {
    public InvalidWorkflowStateException() {
        super(
                409,
                "INVALID_WORKFLOW_STATE",
                "Invalid workflow state",
                "Only a draft with publication not started can be edited.");
    }
}
