package com.example.dcl.application.port;

import com.example.dcl.domain.workflow.AssetSnapshot;
import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

public record DraftSeed(
        AssetSnapshot asset,
        Map<String, Object> managedValues,
        Set<String> authorizedPrincipals,
        Instant retrievedAt) {

    public DraftSeed {
        managedValues = Collections.unmodifiableMap(new LinkedHashMap<>(managedValues));
        authorizedPrincipals = Set.copyOf(authorizedPrincipals);
    }
}
