package com.example.dcl.domain.workflow;

import java.util.List;

public record AssetSnapshot(String urn, String displayName, String entityType, List<String> subTypes) {
    public AssetSnapshot {
        subTypes = List.copyOf(subTypes);
    }
}
