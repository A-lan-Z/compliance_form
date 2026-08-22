package com.example.dcl.application;

import com.example.dcl.application.port.AuditEventRepository;
import com.example.dcl.application.port.DraftSeed;
import com.example.dcl.application.port.WorkflowRepository;
import com.example.dcl.domain.form.CanonicalJson;
import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.AuditEvent;
import com.example.dcl.domain.workflow.BaselineNormalization;
import com.example.dcl.domain.workflow.PublicationStatus;
import com.example.dcl.domain.workflow.ReviewStatus;
import com.example.dcl.domain.workflow.Workflow;
import com.example.dcl.domain.workflow.WorkflowWarning;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class WorkflowCreationTransaction {
    private final WorkflowRepository workflowRepository;
    private final AuditEventRepository auditEventRepository;
    private final CanonicalJson canonicalJson;
    private final Clock clock;

    public WorkflowCreationTransaction(
            WorkflowRepository workflowRepository,
            AuditEventRepository auditEventRepository,
            CanonicalJson canonicalJson,
            Clock clock) {
        this.workflowRepository = workflowRepository;
        this.auditEventRepository = auditEventRepository;
        this.canonicalJson = canonicalJson;
        this.clock = clock;
    }

    @Transactional
    public WorkflowResult createOrGet(
            String actorId,
            String requestId,
            FormDefinition form,
            DraftSeed seed,
            BaselineNormalization baseline) {
        Instant now = clock.instant();
        Workflow candidate = new Workflow(
                UUID.randomUUID(),
                seed.asset().urn(),
                seed.asset(),
                form.key(),
                form.revision(),
                form.definitionSha256(),
                ReviewStatus.DRAFT,
                PublicationStatus.NOT_STARTED,
                baseline.rawValues(),
                seed.retrievedAt(),
                canonicalJson.sha256(baseline.rawValues()),
                baseline.initialDraft(),
                1,
                actorId,
                actorId,
                now,
                now);

        if (!workflowRepository.insertIfAbsent(candidate)) {
            Workflow existing = workflowRepository.findByAssetAndForm(seed.asset().urn(), form.key())
                    .orElseThrow(() -> new IllegalStateException("Concurrent workflow creation did not produce a row"));
            return new WorkflowResult(existing, form, warnings(existing, form), false);
        }

        auditEventRepository.insert(new AuditEvent(
                UUID.randomUUID(),
                candidate.id(),
                1,
                "WORKFLOW_CREATED",
                actorId,
                "USER",
                now,
                requestId,
                1,
                creationDetails(candidate, form, baseline.warnings())));
        return new WorkflowResult(candidate, form, baseline.warnings(), true);
    }

    private List<WorkflowWarning> warnings(Workflow workflow, FormDefinition form) {
        return new com.example.dcl.domain.workflow.BaselineNormalizer()
                .normalize(workflow.baselineValues(), form)
                .warnings();
    }

    private Map<String, Object> creationDetails(
            Workflow workflow, FormDefinition form, List<WorkflowWarning> warnings) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("assetUrn", workflow.assetUrn());
        details.put("assetSnapshot", workflow.assetSnapshot());
        details.put("formKey", form.key());
        details.put("formRevision", form.revision());
        details.put("formDefinitionSha256", form.definitionSha256());
        details.put("baselineCapturedAt", workflow.baselineCapturedAt());
        details.put("baselineSha256", workflow.baselineSha256());
        details.put("initialEditableValues", workflow.draftValues().asMap());
        details.put("derivedAction", workflow.draftValues().disposalAction(form));
        List<Map<String, String>> warningDetails = new ArrayList<>();
        warnings.forEach(warning -> warningDetails.add(Map.of(
                "code", warning.code(),
                "message", warning.message())));
        details.put("warnings", warningDetails);
        return details;
    }
}
