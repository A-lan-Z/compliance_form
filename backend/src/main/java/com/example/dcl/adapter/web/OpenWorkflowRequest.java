package com.example.dcl.adapter.web;

import jakarta.validation.constraints.NotBlank;

public record OpenWorkflowRequest(
        @NotBlank String assetUrn,
        @NotBlank String formKey) {
}
