package com.example.dcl.domain.form;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

class FixtureFormRegistryTest {

    @Test
    void loadsTheApprovedImmutableFixtureDefinition() {
        ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
        FixtureFormRegistry first = new FixtureFormRegistry(objectMapper, new CanonicalJson(objectMapper));
        FixtureFormRegistry second = new FixtureFormRegistry(objectMapper, new CanonicalJson(objectMapper));

        FormDefinition definition = first.fixtureDefinition();
        assertThat(definition.key()).isEqualTo("dcl.edw.database.fixture");
        assertThat(definition.revision()).isEqualTo(1);
        assertThat(definition.displayName()).contains("Fixture");
        assertThat(definition.allowedDisposalClasses()).containsExactly("TEST_CLASS_A", "TEST_CLASS_B");
        assertThat(definition.disposalActionByClass()).isEqualTo(Map.of(
                "TEST_CLASS_A", "TEST_ACTION_A",
                "TEST_CLASS_B", "TEST_ACTION_B"));
        assertThat(definition.definitionSha256()).matches("[0-9a-f]{64}");
        assertThat(second.fixtureDefinition().definitionSha256()).isEqualTo(definition.definitionSha256());
    }

    @Test
    void derivesOnlyApprovedFixtureActions() {
        ObjectMapper objectMapper = new ObjectMapper();
        FormDefinition definition = new FixtureFormRegistry(objectMapper, new CanonicalJson(objectMapper))
                .fixtureDefinition();

        assertThat(definition.deriveDisposalAction(null)).isNull();
        assertThat(definition.deriveDisposalAction("TEST_CLASS_A")).isEqualTo("TEST_ACTION_A");
        assertThat(definition.deriveDisposalAction("TEST_CLASS_B")).isEqualTo("TEST_ACTION_B");
        assertThat(definition.permits("UNKNOWN")).isFalse();
    }

    @Test
    void rejectsARevisionThatIsNotAnInteger() throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        ObjectNode root = (ObjectNode) objectMapper.readTree(
                new ClassPathResource("fixtures/dcl-edw-database-fixture-v1.json").getInputStream());
        root.put("revision", "1");

        assertThatThrownBy(() -> FixtureFormRegistry.validate(root))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("revision must be 1");
    }
}
