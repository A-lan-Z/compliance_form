package com.example.dcl.adapter.fixture;

import com.example.dcl.application.port.EditAuthorizationService;
import com.example.dcl.domain.form.FixtureFormRegistry;
import org.springframework.stereotype.Component;

@Component
public final class FixtureEditAuthorizationService implements EditAuthorizationService {
    public static final String AUTHORIZED_PRINCIPAL = "bcp.alice";
    public static final String ASSET_URN = "urn:li:container:00000000000000000000000000000001";

    @Override
    public boolean canAccessAsset(String principalId, String assetUrn) {
        return AUTHORIZED_PRINCIPAL.equals(principalId) && ASSET_URN.equals(assetUrn);
    }

    @Override
    public boolean canEdit(String principalId, String assetUrn, String formKey) {
        return AUTHORIZED_PRINCIPAL.equals(principalId)
                && ASSET_URN.equals(assetUrn)
                && FixtureFormRegistry.FORM_KEY.equals(formKey);
    }
}
