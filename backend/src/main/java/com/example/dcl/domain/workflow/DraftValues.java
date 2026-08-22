package com.example.dcl.domain.workflow;

import com.example.dcl.application.error.InvalidFieldValueException;
import com.example.dcl.domain.form.FormDefinition;
import java.util.LinkedHashMap;
import java.util.Map;

public record DraftValues(String disposalClass) {

    public static DraftValues validated(String disposalClass, FormDefinition definition) {
        if (!definition.permits(disposalClass)) {
            throw new InvalidFieldValueException("values.disposalClass", "Unsupported disposal class");
        }
        return new DraftValues(disposalClass);
    }

    public String disposalAction(FormDefinition definition) {
        return definition.deriveDisposalAction(disposalClass);
    }

    public Map<String, Object> asMap() {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("disposalClass", disposalClass);
        return values;
    }
}
