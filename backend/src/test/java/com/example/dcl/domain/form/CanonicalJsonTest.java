package com.example.dcl.domain.form;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CanonicalJsonTest {
    private final CanonicalJson canonicalJson = new CanonicalJson(new ObjectMapper().findAndRegisterModules());

    @Test
    void sortsObjectKeysRecursivelyAndPreservesArrayOrder() {
        Map<String, Object> nested = new LinkedHashMap<>();
        nested.put("z", 1);
        nested.put("y", 2);
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("items", List.of(nested));
        input.put("b", 2);
        input.put("a", 1);

        assertThat(canonicalJson.string(input))
                .isEqualTo("{\"a\":1,\"b\":2,\"items\":[{\"y\":2,\"z\":1}]}");
        assertThat(canonicalJson.sha256(input))
                .isEqualTo("45c01fb9260ee0502fb77e3dd04cff9cbecbbb368988a72f9d92057700da2f1c");
    }

    @Test
    void producesTheFixedFixtureBaselineDigest() {
        Map<String, Object> baseline = new LinkedHashMap<>();
        baseline.put("disposalClass", "TEST_CLASS_A");
        baseline.put("disposalAction", "TEST_ACTION_A");

        assertThat(canonicalJson.sha256(baseline))
                .isEqualTo("0e4c0b4a3ebfc238a905eabe8ef9483cada523f72b9ec8eb6340748733159a7a");
    }
}
