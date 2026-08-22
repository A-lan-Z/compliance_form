package com.example.dcl.domain.workflow;

import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

public record AuditEvent(
        UUID id,
        UUID workflowId,
        long sequence,
        String eventType,
        String actorId,
        String actorType,
        Instant occurredAt,
        String requestId,
        long workflowVersion,
        Map<String, Object> details) {

    public AuditEvent {
        details = Collections.unmodifiableMap(new LinkedHashMap<>(details));
    }
}
