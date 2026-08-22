package com.example.dcl.application;

import com.example.dcl.application.error.AccessDeniedException;
import com.example.dcl.application.error.DclException;
import com.example.dcl.application.error.DependencyUnavailableException;
import com.example.dcl.application.error.InvalidWorkflowStateException;
import com.example.dcl.application.error.WorkflowNotFoundException;
import com.example.dcl.application.error.WorkflowVersionConflictException;
import com.example.dcl.application.port.AuditEventRepository;
import com.example.dcl.application.port.DraftSeed;
import com.example.dcl.application.port.DraftSeedReader;
import com.example.dcl.application.port.EditAuthorizationService;
import com.example.dcl.application.port.WorkflowRepository;
import com.example.dcl.domain.form.FixtureFormRegistry;
import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.AuditEvent;
import com.example.dcl.domain.workflow.BaselineNormalization;
import com.example.dcl.domain.workflow.BaselineNormalizer;
import com.example.dcl.domain.workflow.DraftValues;
import com.example.dcl.domain.workflow.PublicationStatus;
import com.example.dcl.domain.workflow.ReviewStatus;
import com.example.dcl.domain.workflow.Workflow;
import java.time.Clock;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class WorkflowService {
    private final FixtureFormRegistry formRegistry;
    private final EditAuthorizationService authorizationService;
    private final DraftSeedReader draftSeedReader;
    private final WorkflowRepository workflowRepository;
    private final AuditEventRepository auditEventRepository;
    private final BaselineNormalizer baselineNormalizer;
    private final DraftRequestParser draftRequestParser;
    private final WorkflowCreationTransaction creationTransaction;
    private final Clock clock;

    public WorkflowService(
            FixtureFormRegistry formRegistry,
            EditAuthorizationService authorizationService,
            DraftSeedReader draftSeedReader,
            WorkflowRepository workflowRepository,
            AuditEventRepository auditEventRepository,
            BaselineNormalizer baselineNormalizer,
            DraftRequestParser draftRequestParser,
            WorkflowCreationTransaction creationTransaction,
            Clock clock) {
        this.formRegistry = formRegistry;
        this.authorizationService = authorizationService;
        this.draftSeedReader = draftSeedReader;
        this.workflowRepository = workflowRepository;
        this.auditEventRepository = auditEventRepository;
        this.baselineNormalizer = baselineNormalizer;
        this.draftRequestParser = draftRequestParser;
        this.creationTransaction = creationTransaction;
        this.clock = clock;
    }

    public WorkflowResult open(String actorId, String assetUrn, String formKey, String requestId) {
        requireOpenAssetAccess(actorId, assetUrn);
        FormDefinition form = formRegistry.active(formKey);
        requireOpenAccess(actorId, assetUrn, formKey);
        var existing = workflowRepository.findByAssetAndForm(assetUrn, formKey);
        if (existing.isPresent()) {
            return result(existing.get(), false);
        }

        DraftSeed seed;
        try {
            seed = draftSeedReader.loadDraftSeed(actorId, assetUrn, form);
        } catch (DclException exception) {
            throw exception;
        } catch (RuntimeException exception) {
            throw new DependencyUnavailableException();
        }
        if (!seed.authorizedPrincipals().contains(actorId)) {
            throw new AccessDeniedException();
        }
        BaselineNormalization baseline = baselineNormalizer.normalize(seed.managedValues(), form);
        return creationTransaction.createOrGet(actorId, requestId, form, seed, baseline);
    }

    public WorkflowResult get(String actorId, UUID workflowId) {
        Workflow workflow = accessibleWorkflow(actorId, workflowId);
        return result(workflow, false);
    }

    @Transactional
    public WorkflowResult saveDraft(
            String actorId,
            UUID workflowId,
            long expectedVersion,
            Map<String, Object> values,
            String requestId) {
        Workflow current = accessibleWorkflow(actorId, workflowId);
        requireDraftState(current);
        if (current.lockVersion() != expectedVersion) {
            throw new WorkflowVersionConflictException(current.lockVersion());
        }
        FormDefinition form = pinnedForm(current);
        DraftValues requested = draftRequestParser.parse(values, form);
        if (requested.equals(current.draftValues())) {
            return result(current, false);
        }

        Instant now = clock.instant();
        int updated = workflowRepository.updateDraft(
                workflowId, expectedVersion, requested.disposalClass(), actorId, now);
        if (updated == 0) {
            Workflow latest = workflowRepository.findById(workflowId)
                    .orElseThrow(WorkflowNotFoundException::new);
            requireDraftState(latest);
            throw new WorkflowVersionConflictException(latest.lockVersion());
        }

        long nextVersion = expectedVersion + 1;
        auditEventRepository.insert(new AuditEvent(
                UUID.randomUUID(),
                workflowId,
                nextVersion,
                "DRAFT_SAVED",
                actorId,
                "USER",
                now,
                requestId,
                nextVersion,
                saveDetails(current, requested, form, nextVersion)));

        Workflow saved = workflowRepository.findById(workflowId)
                .orElseThrow(WorkflowNotFoundException::new);
        return result(saved, false);
    }

    private Workflow accessibleWorkflow(String actorId, UUID workflowId) {
        Workflow workflow = workflowRepository.findById(workflowId)
                .orElseThrow(WorkflowNotFoundException::new);
        if (!authorizationService.canEdit(actorId, workflow.assetUrn(), workflow.formKey())) {
            throw new WorkflowNotFoundException();
        }
        return workflow;
    }

    private void requireOpenAssetAccess(String actorId, String assetUrn) {
        if (!authorizationService.canAccessAsset(actorId, assetUrn)) {
            throw new AccessDeniedException();
        }
    }

    private void requireOpenAccess(String actorId, String assetUrn, String formKey) {
        if (!authorizationService.canEdit(actorId, assetUrn, formKey)) {
            throw new AccessDeniedException();
        }
    }

    private void requireDraftState(Workflow workflow) {
        if (workflow.reviewStatus() != ReviewStatus.DRAFT
                || workflow.publicationStatus() != PublicationStatus.NOT_STARTED) {
            throw new InvalidWorkflowStateException();
        }
    }

    private FormDefinition pinnedForm(Workflow workflow) {
        return formRegistry.pinned(
                workflow.formKey(), workflow.formRevision(), workflow.formDefinitionSha256());
    }

    private WorkflowResult result(Workflow workflow, boolean created) {
        FormDefinition form = pinnedForm(workflow);
        List<com.example.dcl.domain.workflow.WorkflowWarning> warnings =
                baselineNormalizer.normalize(workflow.baselineValues(), form).warnings();
        return new WorkflowResult(workflow, form, warnings, created);
    }

    private Map<String, Object> saveDetails(
            Workflow current, DraftValues requested, FormDefinition form, long nextVersion) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("priorWorkflowVersion", current.lockVersion());
        details.put("newWorkflowVersion", nextVersion);
        details.put("changedFields", List.of("disposalClass"));
        details.put("previousEditableValues", current.draftValues().asMap());
        details.put("newEditableValues", requested.asMap());
        details.put("previousDerivedAction", current.draftValues().disposalAction(form));
        details.put("newDerivedAction", requested.disposalAction(form));
        details.put("formRevision", form.revision());
        details.put("formDefinitionSha256", form.definitionSha256());
        return details;
    }
}
