package com.example.dcl.domain.workflow;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record BaselineNormalization(
        Map<String, Object> rawValues,
        DraftValues initialDraft,
        List<WorkflowWarning> warnings) {

    public BaselineNormalization {
        rawValues = Collections.unmodifiableMap(new LinkedHashMap<>(rawValues));
        warnings = List.copyOf(warnings);
    }
}
