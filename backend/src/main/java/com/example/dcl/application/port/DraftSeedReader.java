package com.example.dcl.application.port;

import com.example.dcl.domain.form.FormDefinition;

@FunctionalInterface
public interface DraftSeedReader {
    DraftSeed loadDraftSeed(String principalId, String assetUrn, FormDefinition formDefinition);
}
