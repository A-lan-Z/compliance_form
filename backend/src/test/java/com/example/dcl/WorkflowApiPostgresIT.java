package com.example.dcl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.matchesPattern;
import static org.hamcrest.Matchers.nullValue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.dcl.adapter.fixture.FixtureDraftSeedAdapter;
import com.example.dcl.adapter.fixture.FixtureEditAuthorizationService;
import com.example.dcl.application.WorkflowResult;
import com.example.dcl.application.WorkflowService;
import com.example.dcl.application.port.DraftSeedReader;
import com.example.dcl.domain.form.FixtureFormRegistry;
import com.example.dcl.domain.form.FormDefinition;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.lang.reflect.Method;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers
@SpringBootTest(webEnvironment = WebEnvironment.MOCK)
@AutoConfigureMockMvc
class WorkflowApiPostgresIT {
    private static final String ALICE = FixtureEditAuthorizationService.AUTHORIZED_PRINCIPAL;
    private static final String ASSET_URN = FixtureEditAuthorizationService.ASSET_URN;
    private static final String FORM_KEY = FixtureFormRegistry.FORM_KEY;
    private static final String OPEN_BODY =
            """
            {
              "assetUrn": "urn:li:container:00000000000000000000000000000001",
              "formKey": "dcl.edw.database.fixture"
            }
            """;

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:17.10-alpine3.24");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        properties.add("spring.datasource.username", POSTGRES::getUsername);
        properties.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private FixtureFormRegistry formRegistry;

    @Autowired
    private ApplicationContext applicationContext;

    @MockitoSpyBean
    private FixtureDraftSeedAdapter seedAdapter;

    @BeforeEach
    void resetDatabaseAndAdapter() {
        dropFailureConstraints();
        jdbc.update("DELETE FROM dcl_audit_event");
        jdbc.update("DELETE FROM dcl_workflow");
        reset(seedAdapter);
        seedAdapter.resetInvocationCount();
    }

    @Test
    void appliesMigrationToEmptyPostgresAndEnforcesStorageConstraints() throws Exception {
        assertThat(jdbc.queryForObject(
                        "SELECT count(*) FROM flyway_schema_history WHERE success", Long.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT count(*) FROM information_schema.tables WHERE table_name IN ('dcl_workflow', 'dcl_audit_event')",
                        Long.class))
                .isEqualTo(2);
        assertThat(jdbc.queryForObject(
                        "SELECT data_type FROM information_schema.columns WHERE table_name = 'dcl_workflow' AND column_name = 'baseline_captured_at'",
                        String.class))
                .isEqualTo("timestamp with time zone");

        UUID workflowId = id(open(ALICE, "migration-open"));
        assertThatThrownBy(() -> jdbc.update(
                        """
                        INSERT INTO dcl_workflow (
                            id, asset_urn, asset_snapshot, form_key, form_revision,
                            form_definition_sha256, review_status, publication_status,
                            baseline_values, baseline_captured_at, baseline_sha256, draft_values,
                            lock_version, created_by, updated_by, created_at, updated_at
                        )
                        SELECT ?, asset_urn, asset_snapshot, form_key, form_revision,
                               form_definition_sha256, review_status, publication_status,
                               baseline_values, baseline_captured_at, baseline_sha256, draft_values,
                               lock_version, created_by, updated_by, created_at, updated_at
                          FROM dcl_workflow
                         WHERE id = ?
                        """,
                        UUID.randomUUID(),
                        workflowId))
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isEqualTo(1);

        mockMvc.perform(get("/actuator/health/readiness"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void openReopenAndGetReturnThePinnedFixtureWithoutReseeding() throws Exception {
        FormDefinition definition = formRegistry.fixtureDefinition();

        MvcResult created = mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user(ALICE))
                        .header("X-Request-ID", "open-create-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andExpect(status().isCreated())
                .andExpect(header().string("X-Request-ID", "open-create-1"))
                .andExpect(header().string("Location", matchesPattern("/api/v1/workflows/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.asset.urn").value(ASSET_URN))
                .andExpect(jsonPath("$.asset.displayName").value("Fixture EDW Database"))
                .andExpect(jsonPath("$.asset.entityType").value("CONTAINER"))
                .andExpect(jsonPath("$.asset.subTypes[0]").value("Database"))
                .andExpect(jsonPath("$.form.key").value(FORM_KEY))
                .andExpect(jsonPath("$.form.revision").value(1))
                .andExpect(jsonPath("$.form.displayName").value("DCL EDW Database Compliance — Fixture"))
                .andExpect(jsonPath("$.form.definitionSha256").value(definition.definitionSha256()))
                .andExpect(jsonPath("$.status.review").value("DRAFT"))
                .andExpect(jsonPath("$.status.publication").value("NOT_STARTED"))
                .andExpect(jsonPath("$.version").value(1))
                .andExpect(jsonPath("$.fields.disposalClass.value").value("TEST_CLASS_A"))
                .andExpect(jsonPath("$.fields.disposalClass.editable").value(true))
                .andExpect(jsonPath("$.fields.disposalClass.allowedValues[0]").value("TEST_CLASS_A"))
                .andExpect(jsonPath("$.fields.disposalClass.allowedValues[1]").value("TEST_CLASS_B"))
                .andExpect(jsonPath("$.fields.disposalAction.value").value("TEST_ACTION_A"))
                .andExpect(jsonPath("$.fields.disposalAction.editable").value(false))
                .andExpect(jsonPath("$.fields.disposalAction.derivedFrom").value("disposalClass"))
                .andExpect(jsonPath("$.baseline.capturedAt").value(matchesPattern(".*Z")))
                .andExpect(jsonPath("$.baseline.sha256")
                        .value("0e4c0b4a3ebfc238a905eabe8ef9483cada523f72b9ec8eb6340748733159a7a"))
                .andExpect(jsonPath("$.warnings").isEmpty())
                .andExpect(jsonPath("$.permissions.canEdit").value(true))
                .andReturn();

        UUID workflowId = id(created);
        MvcResult reopened = mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user(ALICE))
                        .header("X-Request-ID", "open-existing-2")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(workflowId.toString()))
                .andExpect(jsonPath("$.version").value(1))
                .andReturn();
        assertThat(id(reopened)).isEqualTo(workflowId);

        mockMvc.perform(get("/api/v1/workflows/{id}", workflowId).with(user(ALICE)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(workflowId.toString()))
                .andExpect(jsonPath("$.fields.disposalAction.value").value("TEST_ACTION_A"));

        assertThat(seedAdapter.invocationCount()).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT sequence FROM dcl_audit_event WHERE workflow_id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT workflow_version FROM dcl_audit_event WHERE workflow_id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT actor_id FROM dcl_audit_event WHERE workflow_id = ?", String.class, workflowId))
                .isEqualTo(ALICE);
        assertThat(jdbc.queryForObject(
                        "SELECT request_id FROM dcl_audit_event WHERE workflow_id = ?", String.class, workflowId))
                .isEqualTo("open-create-1");
        JsonNode details = auditDetails(workflowId, "WORKFLOW_CREATED");
        assertThat(details.path("assetUrn").asText()).isEqualTo(ASSET_URN);
        assertThat(details.path("assetSnapshot").path("displayName").asText())
                .isEqualTo("Fixture EDW Database");
        assertThat(details.path("formKey").asText()).isEqualTo(FORM_KEY);
        assertThat(details.path("formRevision").asInt()).isEqualTo(1);
        assertThat(details.path("formDefinitionSha256").asText())
                .isEqualTo(definition.definitionSha256());
        assertThat(details.path("baselineCapturedAt").asText()).isNotBlank();
        assertThat(details.path("baselineSha256").asText())
                .isEqualTo("0e4c0b4a3ebfc238a905eabe8ef9483cada523f72b9ec8eb6340748733159a7a");
        assertThat(details.path("initialEditableValues").path("disposalClass").asText())
                .isEqualTo("TEST_CLASS_A");
        assertThat(details.path("derivedAction").asText()).isEqualTo("TEST_ACTION_A");
        assertThat(details.path("warnings").isArray()).isTrue();
        assertThat(details.path("warnings").isEmpty()).isTrue();
        assertThat(details.toString()).doesNotContainIgnoringCase("password", "authorization", "token");

        assertThat(applicationContext.getBeansOfType(DraftSeedReader.class))
                .hasSize(1)
                .allSatisfy((name, reader) -> assertThat(reader).isInstanceOf(FixtureDraftSeedAdapter.class));
        assertThat(List.of(DraftSeedReader.class.getDeclaredMethods()))
                .extracting(Method::getName)
                .containsExactly("loadDraftSeed");
    }

    @Test
    void materialNoOpNullAndStaleSavesPreserveDerivationAndAuditSemantics() throws Exception {
        UUID workflowId = id(open(ALICE, "save-open"));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .header("X-Request-ID", "save-b")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "TEST_CLASS_B")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(2))
                .andExpect(jsonPath("$.fields.disposalClass.value").value("TEST_CLASS_B"))
                .andExpect(jsonPath("$.fields.disposalAction.value").value("TEST_ACTION_B"));

        JsonNode stored = objectMapper.readTree(
                jdbc.queryForObject("SELECT draft_values::text FROM dcl_workflow WHERE id = ?", String.class, workflowId));
        assertThat(stored.size()).isEqualTo(1);
        assertThat(stored.path("disposalClass").asText()).isEqualTo("TEST_CLASS_B");
        assertThat(stored.has("disposalAction")).isFalse();
        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(2);

        mockMvc.perform(get("/api/v1/workflows/{id}", workflowId).with(user(ALICE)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.fields.disposalClass.value").value("TEST_CLASS_B"))
                .andExpect(jsonPath("$.fields.disposalAction.value").value("TEST_ACTION_B"));

        JsonNode saveDetails = auditDetails(workflowId, "DRAFT_SAVED");
        assertThat(jdbc.queryForObject(
                        "SELECT actor_id FROM dcl_audit_event WHERE workflow_id = ? AND event_type = 'DRAFT_SAVED'",
                        String.class,
                        workflowId))
                .isEqualTo(ALICE);
        assertThat(jdbc.queryForObject(
                        "SELECT request_id FROM dcl_audit_event WHERE workflow_id = ? AND event_type = 'DRAFT_SAVED'",
                        String.class,
                        workflowId))
                .isEqualTo("save-b");
        assertThat(saveDetails.path("priorWorkflowVersion").asLong()).isEqualTo(1);
        assertThat(saveDetails.path("newWorkflowVersion").asLong()).isEqualTo(2);
        assertThat(saveDetails.path("changedFields").get(0).asText()).isEqualTo("disposalClass");
        assertThat(saveDetails.path("previousEditableValues").path("disposalClass").asText())
                .isEqualTo("TEST_CLASS_A");
        assertThat(saveDetails.path("newEditableValues").path("disposalClass").asText())
                .isEqualTo("TEST_CLASS_B");
        assertThat(saveDetails.path("previousDerivedAction").asText()).isEqualTo("TEST_ACTION_A");
        assertThat(saveDetails.path("newDerivedAction").asText()).isEqualTo("TEST_ACTION_B");
        assertThat(saveDetails.path("formRevision").asInt()).isEqualTo(1);
        assertThat(saveDetails.path("formDefinitionSha256").asText())
                .isEqualTo(formRegistry.fixtureDefinition().definitionSha256());
        assertThat(jdbc.queryForList(
                        "SELECT sequence FROM dcl_audit_event WHERE workflow_id = ? ORDER BY sequence", Long.class, workflowId))
                .containsExactly(1L, 2L);

        OffsetDateTime updatedAt = jdbc.queryForObject(
                "SELECT updated_at FROM dcl_workflow WHERE id = ?", OffsetDateTime.class, workflowId);
        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(2, "TEST_CLASS_B")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(2));
        assertThat(jdbc.queryForObject(
                        "SELECT updated_at FROM dcl_workflow WHERE id = ?", OffsetDateTime.class, workflowId))
                .isEqualTo(updatedAt);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(2);

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(2, null)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(3))
                .andExpect(jsonPath("$.fields.disposalClass.value").value(nullValue()))
                .andExpect(jsonPath("$.fields.disposalAction.value").value(nullValue()));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .header("X-Request-ID", "stale-save")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(2, "TEST_CLASS_A")))
                .andExpect(status().isConflict())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.code").value("WORKFLOW_VERSION_CONFLICT"))
                .andExpect(jsonPath("$.currentVersion").value(3))
                .andExpect(jsonPath("$.requestId").value("stale-save"));
        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(3);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(3);
        assertThat(seedAdapter.invocationCount()).isEqualTo(1);
    }

    @Test
    void rejectsReadOnlyUnknownAndInvalidInputsWithoutMutation() throws Exception {
        UUID workflowId = id(open(ALICE, "reject-open"));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .header("X-Request-ID", "reject-action")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"expectedVersion":1,"values":{"disposalClass":"TEST_CLASS_B","disposalAction":"OVERRIDE"}}
                                """))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.status").value(422))
                .andExpect(jsonPath("$.code").value("READ_ONLY_FIELD"))
                .andExpect(jsonPath("$.requestId").value("reject-action"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("values.disposalAction"));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "UNKNOWN_CLASS")))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("INVALID_FIELD_VALUE"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("values.disposalClass"));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"expectedVersion":1,"values":{"disposalClass":"TEST_CLASS_A","other":"x"}}
                                """))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("UNKNOWN_FIELD"));

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"expectedVersion":1,"values":{},"actor":"bcp.alice"}
                                """))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("UNKNOWN_FIELD"));

        mockMvc.perform(get("/api/v1/workflows/not-a-uuid").with(user(ALICE)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("WORKFLOW_NOT_FOUND"));
        mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "assetUrn": "urn:li:container:00000000000000000000000000000001",
                                  "formKey": "missing.fixture.form"
                                }
                                """))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("FORM_NOT_FOUND"));

        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
    }

    @Test
    void authenticationAndAuthorizationFailClosedWithoutActorSelectionOrEnumeration() throws Exception {
        mockMvc.perform(post("/api/v1/workflows/open")
                        .header("X-Request-ID", "anonymous-open")
                        .header("Authorization", "Bearer forged-local-token")
                        .header("X-Principal", ALICE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andExpect(status().isUnauthorized())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(header().string("X-Request-ID", "anonymous-open"))
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"))
                .andExpect(jsonPath("$.requestId").value("anonymous-open"));

        mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user("bcp.mallory"))
                        .header("X-Principal", ALICE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"));
        assertThat(seedAdapter.invocationCount()).isZero();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isZero();

        UUID workflowId = id(open(ALICE, "auth-open"));
        mockMvc.perform(get("/api/v1/workflows/{id}", workflowId).with(user("bcp.mallory")))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("WORKFLOW_NOT_FOUND"));
        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user("bcp.mallory"))
                        .header("X-Principal", ALICE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "TEST_CLASS_B")))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("WORKFLOW_NOT_FOUND"));
        mockMvc.perform(get("/api/v1/workflows/{id}", UUID.randomUUID()).with(user(ALICE)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("WORKFLOW_NOT_FOUND"));

        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(1);
    }

    @Test
    void adapterFailureReturns503WithoutRowsAndExistingWorkflowNeedsNoAdapter() throws Exception {
        doThrow(new RuntimeException("sensitive-adapter-test-marker"))
                .when(seedAdapter)
                .loadDraftSeed(anyString(), anyString(), any(FormDefinition.class));

        mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user(ALICE))
                        .header("X-Request-ID", "adapter-down")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("DEPENDENCY_UNAVAILABLE"))
                .andExpect(jsonPath("$.requestId").value("adapter-down"))
                .andExpect(content().string(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("sensitive-adapter-test-marker"))));
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isZero();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isZero();

        reset(seedAdapter);
        seedAdapter.resetInvocationCount();
        UUID workflowId = id(open(ALICE, "adapter-existing-open"));
        doThrow(new RuntimeException("adapter unavailable"))
                .when(seedAdapter)
                .loadDraftSeed(anyString(), anyString(), any(FormDefinition.class));

        mockMvc.perform(get("/api/v1/workflows/{id}", workflowId).with(user(ALICE)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(1));
        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "TEST_CLASS_B")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(2));
        verify(seedAdapter, times(1)).loadDraftSeed(anyString(), anyString(), any(FormDefinition.class));
    }

    @Test
    @Timeout(60)
    void concurrentFirstOpenReturnsOneCreatedOneExistingAndOneDatabaseWorkflow() throws Exception {
        AtomicInteger requestSequence = new AtomicInteger();
        List<MvcResult> results = concurrently(
                () -> open(ALICE, "concurrent-open-" + requestSequence.incrementAndGet()));

        assertThat(results.stream()
                        .map(result -> result.getResponse().getStatus())
                        .sorted()
                        .toList())
                .containsExactly(200, 201);
        assertThat(results).extracting(this::id).containsOnly(id(results.get(0)));
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT count(*) FROM dcl_audit_event WHERE event_type = 'WORKFLOW_CREATED'", Long.class))
                .isEqualTo(1);
        assertThat(seedAdapter.invocationCount()).isBetween(1, 2);
    }

    @Test
    @Timeout(60)
    void concurrentSameVersionSavesProduceOneSuccessOneConflictAndOneEvent() throws Exception {
        UUID workflowId = id(open(ALICE, "concurrent-save-open"));
        AtomicInteger requestSequence = new AtomicInteger();
        List<MvcResult> results = concurrently(() -> mockMvc.perform(
                        put("/api/v1/workflows/{id}/draft", workflowId)
                                .with(user(ALICE))
                                .header("X-Request-ID", "concurrent-save-" + requestSequence.incrementAndGet())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(saveBody(1, "TEST_CLASS_B")))
                .andReturn());

        assertThat(results.stream()
                        .map(result -> result.getResponse().getStatus())
                        .sorted()
                        .toList())
                .containsExactly(200, 409);
        MvcResult conflict = results.stream()
                .filter(result -> result.getResponse().getStatus() == 409)
                .findFirst()
                .orElseThrow();
        assertThat(objectMapper.readTree(conflict.getResponse().getContentAsString())
                        .path("currentVersion")
                        .asLong())
                .isEqualTo(2);
        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(2);
        assertThat(jdbc.queryForObject(
                        "SELECT count(*) FROM dcl_audit_event WHERE event_type = 'DRAFT_SAVED'", Long.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(2);
    }

    @Test
    void creationAuditFailureRollsBackTheWorkflowInsert() throws Exception {
        jdbc.execute(
                "ALTER TABLE dcl_audit_event ADD CONSTRAINT test_reject_workflow_created CHECK (event_type <> 'WORKFLOW_CREATED')");
        try {
            mockMvc.perform(post("/api/v1/workflows/open")
                            .with(user(ALICE))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(OPEN_BODY))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.code").value("INTERNAL_ERROR"))
                    .andExpect(content().string(org.hamcrest.Matchers.not(
                            org.hamcrest.Matchers.containsString("test_reject_workflow_created"))));
        } finally {
            jdbc.execute("ALTER TABLE dcl_audit_event DROP CONSTRAINT IF EXISTS test_reject_workflow_created");
        }

        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_workflow", Long.class)).isZero();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isZero();
    }

    @Test
    void auditInsertFailureRollsBackTheWorkflowUpdate() throws Exception {
        UUID workflowId = id(open(ALICE, "audit-failure-open"));
        jdbc.execute(
                "ALTER TABLE dcl_audit_event ADD CONSTRAINT test_reject_draft_saved CHECK (event_type <> 'DRAFT_SAVED')");
        try {
            mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                            .with(user(ALICE))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(saveBody(1, "TEST_CLASS_B")))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.code").value("INTERNAL_ERROR"))
                    .andExpect(content().string(org.hamcrest.Matchers.not(
                            org.hamcrest.Matchers.containsString("test_reject_draft_saved"))));
        } finally {
            jdbc.execute("ALTER TABLE dcl_audit_event DROP CONSTRAINT IF EXISTS test_reject_draft_saved");
        }

        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(objectMapper.readTree(
                                jdbc.queryForObject(
                                        "SELECT draft_values::text FROM dcl_workflow WHERE id = ?",
                                        String.class,
                                        workflowId))
                        .path("disposalClass")
                        .asText())
                .isEqualTo("TEST_CLASS_A");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
    }

    @Test
    void workflowUpdateFailureCreatesNoAuditEvent() throws Exception {
        UUID workflowId = id(open(ALICE, "update-failure-open"));
        jdbc.execute(
                """
                ALTER TABLE dcl_workflow
                ADD CONSTRAINT test_reject_class_b
                CHECK ((draft_values ->> 'disposalClass') IS DISTINCT FROM 'TEST_CLASS_B')
                """);
        try {
            mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                            .with(user(ALICE))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(saveBody(1, "TEST_CLASS_B")))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.code").value("INTERNAL_ERROR"));
        } finally {
            jdbc.execute("ALTER TABLE dcl_workflow DROP CONSTRAINT IF EXISTS test_reject_class_b");
        }

        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject(
                        "SELECT count(*) FROM dcl_audit_event WHERE event_type = 'DRAFT_SAVED'", Long.class))
                .isZero();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
    }

    @Test
    void reservedWorkflowStateCannotBeSaved() throws Exception {
        UUID workflowId = id(open(ALICE, "state-open"));
        jdbc.update("UPDATE dcl_workflow SET review_status = 'SUBMITTED' WHERE id = ?", workflowId);

        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "TEST_CLASS_B")))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_WORKFLOW_STATE"));

        assertThat(jdbc.queryForObject(
                        "SELECT lock_version FROM dcl_workflow WHERE id = ?", Long.class, workflowId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM dcl_audit_event", Long.class)).isEqualTo(1);
    }

    @Test
    void persistedDraftSurvivesAFreshApplicationContextWithoutReseeding() throws Exception {
        UUID workflowId = id(open(ALICE, "restart-open"));
        mockMvc.perform(put("/api/v1/workflows/{id}/draft", workflowId)
                        .with(user(ALICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(saveBody(1, "TEST_CLASS_B")))
                .andExpect(status().isOk());

        try (ConfigurableApplicationContext restarted = new SpringApplicationBuilder(DclApplication.class).run(
                "--spring.datasource.url=" + POSTGRES.getJdbcUrl(),
                "--spring.datasource.username=" + POSTGRES.getUsername(),
                "--spring.datasource.password=" + POSTGRES.getPassword(),
                "--server.port=0",
                "--management.server.port=0",
                "--spring.main.banner-mode=off")) {
            WorkflowResult persisted = restarted.getBean(WorkflowService.class).get(ALICE, workflowId);
            assertThat(persisted.workflow().lockVersion()).isEqualTo(2);
            assertThat(persisted.workflow().draftValues().disposalClass()).isEqualTo("TEST_CLASS_B");
            assertThat(persisted.workflow().draftValues().disposalAction(persisted.form()))
                    .isEqualTo("TEST_ACTION_B");
            assertThat(restarted.getBean(FixtureDraftSeedAdapter.class).invocationCount()).isZero();
        }
    }

    private MvcResult open(String principal, String requestId) throws Exception {
        return mockMvc.perform(post("/api/v1/workflows/open")
                        .with(user(principal))
                        .header("X-Request-ID", requestId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OPEN_BODY))
                .andReturn();
    }

    private UUID id(MvcResult result) {
        try {
            return UUID.fromString(objectMapper.readTree(result.getResponse().getContentAsString())
                    .path("id")
                    .asText());
        } catch (Exception exception) {
            throw new IllegalArgumentException("Response does not contain a workflow ID", exception);
        }
    }

    private String saveBody(long expectedVersion, String disposalClass) {
        String encodedClass = disposalClass == null ? "null" : "\"" + disposalClass + "\"";
        return "{\"expectedVersion\":" + expectedVersion
                + ",\"values\":{\"disposalClass\":" + encodedClass + "}}";
    }

    private JsonNode auditDetails(UUID workflowId, String eventType) throws Exception {
        String json = jdbc.queryForObject(
                "SELECT details::text FROM dcl_audit_event WHERE workflow_id = ? AND event_type = ? ORDER BY sequence LIMIT 1",
                String.class,
                workflowId,
                eventType);
        return objectMapper.readTree(json);
    }

    private <T> List<T> concurrently(Callable<T> task) throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        Callable<T> gated = () -> {
            ready.countDown();
            if (!start.await(10, TimeUnit.SECONDS)) {
                throw new IllegalStateException("Concurrent test did not start in time");
            }
            return task.call();
        };
        try {
            Future<T> first = executor.submit(gated);
            Future<T> second = executor.submit(gated);
            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            return List.of(first.get(30, TimeUnit.SECONDS), second.get(30, TimeUnit.SECONDS));
        } finally {
            executor.shutdownNow();
        }
    }

    private void dropFailureConstraints() {
        jdbc.execute("ALTER TABLE dcl_audit_event DROP CONSTRAINT IF EXISTS test_reject_draft_saved");
        jdbc.execute("ALTER TABLE dcl_audit_event DROP CONSTRAINT IF EXISTS test_reject_workflow_created");
        jdbc.execute("ALTER TABLE dcl_workflow DROP CONSTRAINT IF EXISTS test_reject_class_b");
    }
}
