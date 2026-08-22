package com.example.dcl.domain.form;

import com.example.dcl.application.error.FormNotFoundException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
public final class FixtureFormRegistry {
    public static final String FORM_KEY = "dcl.edw.database.fixture";
    private static final String RESOURCE = "fixtures/dcl-edw-database-fixture-v1.json";

    private final FormDefinition definition;

    public FixtureFormRegistry(ObjectMapper objectMapper, CanonicalJson canonicalJson) {
        try {
            JsonNode root = objectMapper.readTree(new ClassPathResource(RESOURCE).getInputStream());
            validate(root);
            List<String> allowed = new ArrayList<>();
            root.path("fields").get(0).path("allowedValues").forEach(value -> allowed.add(value.textValue()));
            Map<String, String> mapping = new LinkedHashMap<>();
            root.path("disposalActionByClass").fields()
                    .forEachRemaining(entry -> mapping.put(entry.getKey(), entry.getValue().textValue()));
            this.definition = new FormDefinition(
                    root.path("formKey").textValue(),
                    root.path("revision").intValue(),
                    root.path("displayName").textValue(),
                    allowed,
                    mapping,
                    canonicalJson.sha256(root));
        } catch (IOException exception) {
            throw new IllegalStateException("Fixture form definition cannot be loaded", exception);
        }
    }

    public FormDefinition active(String formKey) {
        if (!definition.key().equals(formKey)) {
            throw new FormNotFoundException();
        }
        return definition;
    }

    public FormDefinition pinned(String formKey, int revision, String digest) {
        if (!definition.key().equals(formKey)
                || definition.revision() != revision
                || !definition.definitionSha256().equals(digest)) {
            throw new IllegalStateException("Pinned fixture form revision is unavailable or changed");
        }
        return definition;
    }

    public FormDefinition fixtureDefinition() {
        return definition;
    }

    static void validate(JsonNode root) {
        List<String> errors = new ArrayList<>();
        if (!root.isObject()) {
            throw new IllegalStateException("Invalid fixture form definition: root must be an object");
        }
        if (!root.path("fixtureOnly").asBoolean(false)) {
            errors.add("fixtureOnly must be true");
        }
        if (!FORM_KEY.equals(root.path("formKey").textValue())) {
            errors.add("formKey must identify the approved fixture");
        }
        JsonNode revision = root.path("revision");
        if (!revision.isIntegralNumber() || !revision.canConvertToInt() || revision.intValue() != 1) {
            errors.add("revision must be 1");
        }
        if (!"DCL EDW Database Compliance — Fixture".equals(root.path("displayName").textValue())) {
            errors.add("displayName must identify fixture data");
        }
        JsonNode fields = root.path("fields");
        if (!fields.isArray() || fields.size() != 2) {
            errors.add("exactly two fixture fields are required");
        } else {
            Set<String> keys = new LinkedHashSet<>();
            fields.forEach(field -> keys.add(field.path("key").textValue()));
            if (!keys.equals(Set.of("disposalClass", "disposalAction"))) {
                errors.add("fixture field keys are invalid or duplicated");
            }
            JsonNode classField = fields.get(0);
            JsonNode actionField = fields.get(1);
            if (!"disposalClass".equals(classField.path("key").textValue())
                    || !classField.path("editable").asBoolean(false)) {
                errors.add("disposalClass must be the editable field");
            }
            List<String> allowed = new ArrayList<>();
            classField.path("allowedValues").forEach(value -> allowed.add(value.textValue()));
            if (!allowed.equals(List.of("TEST_CLASS_A", "TEST_CLASS_B"))) {
                errors.add("allowed values must be the approved non-production fixtures");
            }
            if (!"disposalAction".equals(actionField.path("key").textValue())
                    || actionField.path("editable").asBoolean(true)
                    || !"disposalClass".equals(actionField.path("derivedFrom").textValue())) {
                errors.add("disposalAction must be read-only and derived from disposalClass");
            }
        }
        Map<String, String> expectedMapping = Map.of(
                "TEST_CLASS_A", "TEST_ACTION_A",
                "TEST_CLASS_B", "TEST_ACTION_B");
        JsonNode mappingNode = root.path("disposalActionByClass");
        Map<String, String> actualMapping = new LinkedHashMap<>();
        if (mappingNode.isObject()) {
            mappingNode.fields().forEachRemaining(
                    entry -> actualMapping.put(entry.getKey(), entry.getValue().textValue()));
        }
        if (!actualMapping.equals(expectedMapping)) {
            errors.add("every allowed fixture class must have its approved fixture action");
        }
        if (!errors.isEmpty()) {
            throw new IllegalStateException("Invalid fixture form definition: " + String.join("; ", errors));
        }
    }
}
