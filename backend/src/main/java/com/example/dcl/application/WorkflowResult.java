package com.example.dcl.application;

import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.Workflow;
import com.example.dcl.domain.workflow.WorkflowWarning;
import java.util.List;

public record WorkflowResult(Workflow workflow, FormDefinition form, List<WorkflowWarning> warnings, boolean created) {
    public WorkflowResult {
        warnings = List.copyOf(warnings);
    }
}
