package com.example.dcl.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.dcl.application.error.InvalidFieldValueException;
import com.example.dcl.application.error.ReadOnlyFieldException;
import com.example.dcl.application.error.UnknownFieldException;
import com.example.dcl.domain.form.FormDefinition;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DraftRequestParserTest {
    private final DraftRequestParser parser = new DraftRequestParser();
    private final FormDefinition form = new FormDefinition(
            "fixture", 1, "Fixture", List.of("TEST_CLASS_A", "TEST_CLASS_B"),
            Map.of("TEST_CLASS_A", "TEST_ACTION_A", "TEST_CLASS_B", "TEST_ACTION_B"), "a".repeat(64));

    @Test
    void allowsMappedAndNullClasses() {
        assertThat(parser.parse(Map.of("disposalClass", "TEST_CLASS_B"), form).disposalClass())
                .isEqualTo("TEST_CLASS_B");
        Map<String, Object> nullClass = new LinkedHashMap<>();
        nullClass.put("disposalClass", null);
        assertThat(parser.parse(nullClass, form).disposalClass()).isNull();
    }

    @Test
    void rejectsUnknownClassesAndMissingClass() {
        assertThatThrownBy(() -> parser.parse(Map.of("disposalClass", "UNKNOWN"), form))
                .isInstanceOf(InvalidFieldValueException.class);
        assertThatThrownBy(() -> parser.parse(Map.of(), form))
                .isInstanceOf(InvalidFieldValueException.class);
        assertThatThrownBy(() -> parser.parse(Map.of("disposalClass", 12), form))
                .isInstanceOf(InvalidFieldValueException.class);
    }

    @Test
    void distinguishesReadOnlyActionFromOtherUnknownFields() {
        assertThatThrownBy(() -> parser.parse(Map.of("disposalClass", "TEST_CLASS_A", "disposalAction", "x"), form))
                .isInstanceOf(ReadOnlyFieldException.class);
        assertThatThrownBy(() -> parser.parse(Map.of("disposalClass", "TEST_CLASS_A", "other", "x"), form))
                .isInstanceOf(UnknownFieldException.class);
    }
}
