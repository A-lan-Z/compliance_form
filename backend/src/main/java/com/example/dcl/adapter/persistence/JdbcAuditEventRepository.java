package com.example.dcl.adapter.persistence;

import com.example.dcl.application.port.AuditEventRepository;
import com.example.dcl.domain.form.CanonicalJson;
import com.example.dcl.domain.workflow.AuditEvent;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class JdbcAuditEventRepository implements AuditEventRepository {
    private final NamedParameterJdbcTemplate jdbc;
    private final CanonicalJson canonicalJson;

    public JdbcAuditEventRepository(NamedParameterJdbcTemplate jdbc, CanonicalJson canonicalJson) {
        this.jdbc = jdbc;
        this.canonicalJson = canonicalJson;
    }

    @Override
    public void insert(AuditEvent event) {
        jdbc.update(
                """
                INSERT INTO dcl_audit_event (
                    id, workflow_id, sequence, event_type, actor_id, actor_type,
                    occurred_at, request_id, workflow_version, details
                ) VALUES (
                    :id, :workflowId, :sequence, :eventType, :actorId, :actorType,
                    :occurredAt, :requestId, :workflowVersion, CAST(:details AS jsonb)
                )
                """,
                new MapSqlParameterSource()
                        .addValue("id", event.id())
                        .addValue("workflowId", event.workflowId())
                        .addValue("sequence", event.sequence())
                        .addValue("eventType", event.eventType())
                        .addValue("actorId", event.actorId())
                        .addValue("actorType", event.actorType())
                        .addValue("occurredAt", OffsetDateTime.ofInstant(event.occurredAt(), ZoneOffset.UTC))
                        .addValue("requestId", event.requestId())
                        .addValue("workflowVersion", event.workflowVersion())
                        .addValue("details", canonicalJson.string(event.details())));
    }
}
