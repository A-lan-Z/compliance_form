package com.example.dcl.domain.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class WorkflowDomainTest {

    @Test
    void draftEqualityProvidesSemanticNoOpComparison() {
        assertThat(new DraftValues("TEST_CLASS_A"))
                .isEqualTo(new DraftValues("TEST_CLASS_A"))
                .isNotEqualTo(new DraftValues("TEST_CLASS_B"));
        assertThat(new DraftValues(null)).isEqualTo(new DraftValues(null));
    }

    @Test
    void enforcesPositiveVersionsAndPreApprovalPublicationInvariant() {
        assertThatThrownBy(() -> workflow(0, ReviewStatus.DRAFT, PublicationStatus.NOT_STARTED))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> workflow(1, ReviewStatus.DRAFT, PublicationStatus.PENDING))
                .isInstanceOf(IllegalArgumentException.class);

        assertThat(workflow(1, ReviewStatus.DRAFT, PublicationStatus.NOT_STARTED).reviewStatus())
                .isEqualTo(ReviewStatus.DRAFT);
    }

    private Workflow workflow(long version, ReviewStatus review, PublicationStatus publication) {
        Instant now = Instant.parse("2026-08-21T00:00:00Z");
        return new Workflow(
                UUID.fromString("00000000-0000-0000-0000-000000000001"),
                "urn:test:fixture",
                new AssetSnapshot("urn:test:fixture", "Fixture", "TEST", List.of("Fixture")),
                "fixture.form",
                1,
                "a".repeat(64),
                review,
                publication,
                Map.of("disposalClass", "TEST_CLASS_A", "disposalAction", "TEST_ACTION_A"),
                now,
                "b".repeat(64),
                new DraftValues("TEST_CLASS_A"),
                version,
                "bcp.alice",
                "bcp.alice",
                now,
                now);
    }
}
