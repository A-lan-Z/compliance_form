package com.example.dcl.domain.workflow;

import com.example.dcl.application.error.InvalidBaselineValueException;
import com.example.dcl.domain.form.FormDefinition;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Component;

@Component
public final class BaselineNormalizer {

    public BaselineNormalization normalize(Map<String, Object> supplied, FormDefinition definition) {
        Object rawClass = supplied.get("disposalClass");
        Object rawAction = supplied.get("disposalAction");
        if (rawClass != null && !(rawClass instanceof String)) {
            throw new InvalidBaselineValueException("Baseline disposalClass must be a string or null");
        }
        if (rawAction != null && !(rawAction instanceof String)) {
            throw new InvalidBaselineValueException("Baseline disposalAction must be a string or null");
        }

        String disposalClass = (String) rawClass;
        String disposalAction = (String) rawAction;
        List<WorkflowWarning> warnings = new ArrayList<>();
        DraftValues initialDraft;
        if (disposalClass != null && !definition.permits(disposalClass)) {
            initialDraft = new DraftValues(null);
            warnings.add(new WorkflowWarning(
                    "UNSUPPORTED_BASELINE_DISPOSAL_CLASS",
                    "The existing Disposal Class is unsupported; select a fixture value before saving."));
        } else {
            initialDraft = new DraftValues(disposalClass);
            String canonicalAction = initialDraft.disposalAction(definition);
            if (!Objects.equals(disposalAction, canonicalAction)) {
                warnings.add(new WorkflowWarning(
                        "BASELINE_DISPOSAL_ACTION_MISMATCH",
                        "The existing Disposal Action does not match the canonical action for its class."));
            }
        }

        Map<String, Object> raw = new LinkedHashMap<>();
        raw.put("disposalClass", disposalClass);
        raw.put("disposalAction", disposalAction);
        return new BaselineNormalization(raw, initialDraft, warnings);
    }
}
