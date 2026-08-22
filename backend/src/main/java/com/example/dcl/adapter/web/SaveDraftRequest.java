package com.example.dcl.adapter.web;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.Map;

public record SaveDraftRequest(
        @NotNull @Positive Long expectedVersion,
        @NotNull Map<String, Object> values) {
}
