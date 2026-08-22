package com.example.dcl.adapter.persistence;

import com.example.dcl.application.port.WorkflowRepository;
import com.example.dcl.domain.form.CanonicalJson;
import com.example.dcl.domain.workflow.AssetSnapshot;
import com.example.dcl.domain.workflow.DraftValues;
import com.example.dcl.domain.workflow.PublicationStatus;
import com.example.dcl.domain.workflow.ReviewStatus;
import com.example.dcl.domain.workflow.Workflow;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class JdbcWorkflowRepository implements WorkflowRepository {
    private static final String COLUMNS = """
            id, asset_urn, asset_snapshot, form_key, form_revision, form_definition_sha256,
            review_status, publication_status, baseline_values, baseline_captured_at,
            baseline_sha256, draft_values, lock_version, created_by, updated_by, created_at, updated_at
            """;

    private final NamedParameterJdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final CanonicalJson canonicalJson;
    private final RowMapper<Workflow> rowMapper = this::mapWorkflow;

    public JdbcWorkflowRepository(
            NamedParameterJdbcTemplate jdbc, ObjectMapper objectMapper, CanonicalJson canonicalJson) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.canonicalJson = canonicalJson;
    }

    @Override
    public Optional<Workflow> findByAssetAndForm(String assetUrn, String formKey) {
        return jdbc.query(
                        "SELECT " + COLUMNS + " FROM dcl_workflow WHERE asset_urn = :assetUrn AND form_key = :formKey",
                        Map.of("assetUrn", assetUrn, "formKey", formKey),
                        rowMapper)
                .stream()
                .findFirst();
    }

    @Override
    public Optional<Workflow> findById(UUID workflowId) {
        return jdbc.query(
                        "SELECT " + COLUMNS + " FROM dcl_workflow WHERE id = :id",
                        Map.of("id", workflowId),
                        rowMapper)
                .stream()
                .findFirst();
    }

    @Override
    public boolean insertIfAbsent(Workflow workflow) {
        String sql = """
                INSERT INTO dcl_workflow (
                    id, asset_urn, asset_snapshot, form_key, form_revision, form_definition_sha256,
                    review_status, publication_status, baseline_values, baseline_captured_at,
                    baseline_sha256, draft_values, lock_version, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :assetUrn, CAST(:assetSnapshot AS jsonb), :formKey, :formRevision, :formDefinitionSha256,
                    :reviewStatus, :publicationStatus, CAST(:baselineValues AS jsonb), :baselineCapturedAt,
                    :baselineSha256, CAST(:draftValues AS jsonb), :lockVersion, :createdBy, :updatedBy,
                    :createdAt, :updatedAt
                ) ON CONFLICT (asset_urn, form_key) DO NOTHING
                """;
        MapSqlParameterSource parameters = new MapSqlParameterSource()
                .addValue("id", workflow.id())
                .addValue("assetUrn", workflow.assetUrn())
                .addValue("assetSnapshot", canonicalJson.string(workflow.assetSnapshot()))
                .addValue("formKey", workflow.formKey())
                .addValue("formRevision", workflow.formRevision())
                .addValue("formDefinitionSha256", workflow.formDefinitionSha256())
                .addValue("reviewStatus", workflow.reviewStatus().name())
                .addValue("publicationStatus", workflow.publicationStatus().name())
                .addValue("baselineValues", canonicalJson.string(workflow.baselineValues()))
                .addValue("baselineCapturedAt", utc(workflow.baselineCapturedAt()))
                .addValue("baselineSha256", workflow.baselineSha256())
                .addValue("draftValues", canonicalJson.string(workflow.draftValues().asMap()))
                .addValue("lockVersion", workflow.lockVersion())
                .addValue("createdBy", workflow.createdBy())
                .addValue("updatedBy", workflow.updatedBy())
                .addValue("createdAt", utc(workflow.createdAt()))
                .addValue("updatedAt", utc(workflow.updatedAt()));
        return jdbc.update(sql, parameters) == 1;
    }

    @Override
    public int updateDraft(
            UUID workflowId,
            long expectedVersion,
            String disposalClass,
            String updatedBy,
            Instant updatedAt) {
        Map<String, Object> draft = new LinkedHashMap<>();
        draft.put("disposalClass", disposalClass);
        return jdbc.update(
                """
                UPDATE dcl_workflow
                   SET draft_values = CAST(:draftValues AS jsonb),
                       lock_version = lock_version + 1,
                       updated_by = :updatedBy,
                       updated_at = :updatedAt
                 WHERE id = :id
                   AND lock_version = :expectedVersion
                   AND review_status = 'DRAFT' AND publication_status = 'NOT_STARTED'
                """,
                new MapSqlParameterSource()
                        .addValue("draftValues", canonicalJson.string(draft))
                        .addValue("updatedBy", updatedBy)
                        .addValue("updatedAt", utc(updatedAt))
                        .addValue("id", workflowId)
                        .addValue("expectedVersion", expectedVersion));
    }

    private Workflow mapWorkflow(ResultSet resultSet, int rowNumber) throws SQLException {
        Map<String, Object> baseline = readMap(resultSet.getString("baseline_values"));
        Map<String, Object> draft = readMap(resultSet.getString("draft_values"));
        return new Workflow(
                resultSet.getObject("id", UUID.class),
                resultSet.getString("asset_urn"),
                readAsset(resultSet.getString("asset_snapshot")),
                resultSet.getString("form_key"),
                resultSet.getInt("form_revision"),
                resultSet.getString("form_definition_sha256"),
                ReviewStatus.valueOf(resultSet.getString("review_status")),
                PublicationStatus.valueOf(resultSet.getString("publication_status")),
                baseline,
                resultSet.getObject("baseline_captured_at", OffsetDateTime.class).toInstant(),
                resultSet.getString("baseline_sha256"),
                new DraftValues((String) draft.get("disposalClass")),
                resultSet.getLong("lock_version"),
                resultSet.getString("created_by"),
                resultSet.getString("updated_by"),
                resultSet.getObject("created_at", OffsetDateTime.class).toInstant(),
                resultSet.getObject("updated_at", OffsetDateTime.class).toInstant());
    }

    private AssetSnapshot readAsset(String json) throws SQLException {
        try {
            return objectMapper.readValue(json, AssetSnapshot.class);
        } catch (JsonProcessingException exception) {
            throw new SQLException("Persisted asset snapshot is invalid", exception);
        }
    }

    private Map<String, Object> readMap(String json) throws SQLException {
        try {
            return objectMapper.readValue(json, new TypeReference<LinkedHashMap<String, Object>>() {});
        } catch (JsonProcessingException exception) {
            throw new SQLException("Persisted workflow JSON is invalid", exception);
        }
    }

    private OffsetDateTime utc(Instant instant) {
        return OffsetDateTime.ofInstant(instant, ZoneOffset.UTC);
    }
}
