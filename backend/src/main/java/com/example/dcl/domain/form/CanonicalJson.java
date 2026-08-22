package com.example.dcl.domain.form;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.stream.StreamSupport;
import org.springframework.stereotype.Component;

@Component
public final class CanonicalJson {
    private final ObjectMapper objectMapper;

    public CanonicalJson(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public byte[] bytes(Object value) {
        try {
            return objectMapper.writeValueAsBytes(sort(objectMapper.valueToTree(value)));
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Value cannot be represented as canonical JSON", exception);
        }
    }

    public String string(Object value) {
        return new String(bytes(value), StandardCharsets.UTF_8);
    }

    public String sha256(Object value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes(value)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private JsonNode sort(JsonNode node) {
        if (node.isObject()) {
            ObjectNode sorted = JsonNodeFactory.instance.objectNode();
            StreamSupport.stream(((Iterable<String>) node::fieldNames).spliterator(), false)
                    .sorted()
                    .forEach(name -> sorted.set(name, sort(node.get(name))));
            return sorted;
        }
        if (node.isArray()) {
            ArrayNode ordered = JsonNodeFactory.instance.arrayNode();
            node.forEach(item -> ordered.add(sort(item)));
            return ordered;
        }
        return node;
    }
}
