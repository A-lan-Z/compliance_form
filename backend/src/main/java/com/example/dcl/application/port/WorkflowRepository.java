package com.example.dcl.application.port;

import com.example.dcl.domain.workflow.Workflow;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public interface WorkflowRepository {
    Optional<Workflow> findByAssetAndForm(String assetUrn, String formKey);

    Optional<Workflow> findById(UUID workflowId);

    boolean insertIfAbsent(Workflow workflow);

    int updateDraft(
            UUID workflowId,
            long expectedVersion,
            String disposalClass,
            String updatedBy,
            Instant updatedAt);
}
