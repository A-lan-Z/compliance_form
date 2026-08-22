package com.example.dcl.application.port;

public interface EditAuthorizationService {
    boolean canAccessAsset(String principalId, String assetUrn);

    boolean canEdit(String principalId, String assetUrn, String formKey);
}
