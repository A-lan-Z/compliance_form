package com.example.dcl.domain.form;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record FormDefinition(
        String key,
        int revision,
        String displayName,
        List<String> allowedDisposalClasses,
        Map<String, String> disposalActionByClass,
        String definitionSha256) {

    public FormDefinition {
        allowedDisposalClasses = List.copyOf(allowedDisposalClasses);
        disposalActionByClass = Map.copyOf(new LinkedHashMap<>(disposalActionByClass));
    }

    public String deriveDisposalAction(String disposalClass) {
        if (disposalClass == null) {
            return null;
        }
        String action = disposalActionByClass.get(disposalClass);
        if (action == null) {
            throw new IllegalArgumentException("Unsupported disposal class: " + disposalClass);
        }
        return action;
    }

    public boolean permits(String disposalClass) {
        return disposalClass == null || disposalActionByClass.containsKey(disposalClass);
    }
}
