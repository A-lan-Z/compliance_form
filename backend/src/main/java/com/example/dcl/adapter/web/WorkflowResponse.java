package com.example.dcl.adapter.web;

import com.example.dcl.application.WorkflowResult;
import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.Workflow;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record WorkflowResponse(
        UUID id,
        AssetResponse asset,
        FormResponse form,
        StatusResponse status,
        long version,
        FieldsResponse fields,
        BaselineResponse baseline,
        List<WarningResponse> warnings,
        PermissionsResponse permissions) {

    public static WorkflowResponse from(WorkflowResult result) {
        Workflow workflow = result.workflow();
        FormDefinition form = result.form();
        String disposalAction = workflow.draftValues().disposalAction(form);
        Map<String, String> preview = new LinkedHashMap<>();
        form.allowedDisposalClasses()
                .forEach(disposalClass -> preview.put(disposalClass, form.deriveDisposalAction(disposalClass)));
        return new WorkflowResponse(
                workflow.id(),
                new AssetResponse(
                        workflow.assetSnapshot().urn(),
                        workflow.assetSnapshot().displayName(),
                        workflow.assetSnapshot().entityType(),
                        workflow.assetSnapshot().subTypes()),
                new FormResponse(form.key(), form.revision(), form.displayName(), form.definitionSha256()),
                new StatusResponse(workflow.reviewStatus().name(), workflow.publicationStatus().name()),
                workflow.lockVersion(),
                new FieldsResponse(
                        new DisposalClassField(
                                workflow.draftValues().disposalClass(), true, form.allowedDisposalClasses()),
                        new DisposalActionField(
                                disposalAction, false, "disposalClass", preview)),
                new BaselineResponse(workflow.baselineCapturedAt(), workflow.baselineSha256()),
                result.warnings().stream()
                        .map(warning -> new WarningResponse(warning.code(), warning.message()))
                        .toList(),
                new PermissionsResponse(true));
    }

    public record AssetResponse(String urn, String displayName, String entityType, List<String> subTypes) {
    }

    public record FormResponse(String key, int revision, String displayName, String definitionSha256) {
    }

    public record StatusResponse(String review, String publication) {
    }

    public record FieldsResponse(DisposalClassField disposalClass, DisposalActionField disposalAction) {
    }

    public record DisposalClassField(String value, boolean editable, List<String> allowedValues) {
    }

    public record DisposalActionField(
            String value,
            boolean editable,
            String derivedFrom,
            Map<String, String> previewByDisposalClass) {
    }

    public record BaselineResponse(Instant capturedAt, String sha256) {
    }

    public record WarningResponse(String code, String message) {
    }

    public record PermissionsResponse(boolean canEdit) {
    }
}
