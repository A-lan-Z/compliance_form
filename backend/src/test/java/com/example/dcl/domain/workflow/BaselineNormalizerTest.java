package com.example.dcl.domain.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.dcl.application.error.InvalidBaselineValueException;
import com.example.dcl.domain.form.FormDefinition;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BaselineNormalizerTest {
    private final FormDefinition form = new FormDefinition(
            "dcl.edw.database.fixture",
            1,
            "Fixture",
            List.of("TEST_CLASS_A", "TEST_CLASS_B"),
            Map.of("TEST_CLASS_A", "TEST_ACTION_A", "TEST_CLASS_B", "TEST_ACTION_B"),
            "a".repeat(64));
    private final BaselineNormalizer normalizer = new BaselineNormalizer();

    @Test
    void initializesValidAndNullClassesWithoutWarnings() {
        BaselineNormalization valid = normalizer.normalize(values("TEST_CLASS_B", "TEST_ACTION_B"), form);
        BaselineNormalization empty = normalizer.normalize(values(null, null), form);

        assertThat(valid.initialDraft().disposalClass()).isEqualTo("TEST_CLASS_B");
        assertThat(valid.initialDraft().disposalAction(form)).isEqualTo("TEST_ACTION_B");
        assertThat(valid.warnings()).isEmpty();
        assertThat(empty.initialDraft().disposalClass()).isNull();
        assertThat(empty.initialDraft().disposalAction(form)).isNull();
        assertThat(empty.warnings()).isEmpty();
    }

    @Test
    void preservesUnsupportedRawClassAndStartsAnEmptyDraftWithWarning() {
        BaselineNormalization result = normalizer.normalize(values("OLD_CLASS", "Old action"), form);

        assertThat(result.rawValues()).containsEntry("disposalClass", "OLD_CLASS");
        assertThat(result.initialDraft().disposalClass()).isNull();
        assertThat(result.initialDraft().disposalAction(form)).isNull();
        assertThat(result.warnings()).extracting(WorkflowWarning::code)
                .containsExactly("UNSUPPORTED_BASELINE_DISPOSAL_CLASS");
    }

    @Test
    void exposesCanonicalActionAndWarnsWhenBaselineActionDoesNotMatch() {
        BaselineNormalization result = normalizer.normalize(values("TEST_CLASS_A", "Wrong action"), form);

        assertThat(result.initialDraft().disposalClass()).isEqualTo("TEST_CLASS_A");
        assertThat(result.initialDraft().disposalAction(form)).isEqualTo("TEST_ACTION_A");
        assertThat(result.warnings()).extracting(WorkflowWarning::code)
                .containsExactly("BASELINE_DISPOSAL_ACTION_MISMATCH");
    }

    @Test
    void rejectsMalformedAdapterValues() {
        assertThatThrownBy(() -> normalizer.normalize(values(12, "TEST_ACTION_A"), form))
                .isInstanceOf(InvalidBaselineValueException.class)
                .hasMessageContaining("disposalClass");
        assertThatThrownBy(() -> normalizer.normalize(values("TEST_CLASS_A", 12), form))
                .isInstanceOf(InvalidBaselineValueException.class)
                .hasMessageContaining("disposalAction");
    }

    private Map<String, Object> values(Object disposalClass, Object disposalAction) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("disposalClass", disposalClass);
        values.put("disposalAction", disposalAction);
        return values;
    }
}
