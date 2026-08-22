package com.example.dcl.domain.workflow;

import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

public record Workflow(
        UUID id,
        String assetUrn,
        AssetSnapshot assetSnapshot,
        String formKey,
        int formRevision,
        String formDefinitionSha256,
        ReviewStatus reviewStatus,
        PublicationStatus publicationStatus,
        Map<String, Object> baselineValues,
        Instant baselineCapturedAt,
        String baselineSha256,
        DraftValues draftValues,
        long lockVersion,
        String createdBy,
        String updatedBy,
        Instant createdAt,
        Instant updatedAt) {

    public Workflow {
        baselineValues = Collections.unmodifiableMap(new LinkedHashMap<>(baselineValues));
        if (formRevision < 1 || lockVersion < 1) {
            throw new IllegalArgumentException("Workflow revision and version must be positive");
        }
        if (reviewStatus != ReviewStatus.APPROVED && publicationStatus != PublicationStatus.NOT_STARTED) {
            throw new IllegalArgumentException("Publication cannot start before approval");
        }
    }
}
