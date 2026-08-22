package com.example.dcl.application;

import com.example.dcl.application.error.InvalidFieldValueException;
import com.example.dcl.application.error.ReadOnlyFieldException;
import com.example.dcl.application.error.UnknownFieldException;
import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.DraftValues;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public final class DraftRequestParser {

    public DraftValues parse(Map<String, Object> values, FormDefinition definition) {
        if (values.containsKey("disposalAction")) {
            throw new ReadOnlyFieldException("values.disposalAction");
        }
        values.keySet().stream()
                .filter(key -> !"disposalClass".equals(key))
                .findFirst()
                .ifPresent(key -> {
                    throw new UnknownFieldException("values." + key);
                });
        if (!values.containsKey("disposalClass")) {
            throw new InvalidFieldValueException("values.disposalClass", "This field must be present");
        }
        Object value = values.get("disposalClass");
        if (value != null && !(value instanceof String)) {
            throw new InvalidFieldValueException("values.disposalClass", "Must be a string or null");
        }
        return DraftValues.validated((String) value, definition);
    }
}
