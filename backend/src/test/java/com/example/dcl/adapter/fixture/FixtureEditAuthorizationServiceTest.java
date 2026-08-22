package com.example.dcl.adapter.fixture;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.dcl.domain.form.FixtureFormRegistry;
import org.junit.jupiter.api.Test;

class FixtureEditAuthorizationServiceTest {
    private final FixtureEditAuthorizationService authorization = new FixtureEditAuthorizationService();

    @Test
    void grantsOnlyAliceForTheExactFixturePair() {
        assertThat(authorization.canAccessAsset(
                        "bcp.alice", FixtureEditAuthorizationService.ASSET_URN))
                .isTrue();
        assertThat(authorization.canAccessAsset(
                        "bcp.mallory", FixtureEditAuthorizationService.ASSET_URN))
                .isFalse();
        assertThat(authorization.canAccessAsset("bcp.alice", "urn:other")).isFalse();
        assertThat(authorization.canEdit(
                        "bcp.alice", FixtureEditAuthorizationService.ASSET_URN, FixtureFormRegistry.FORM_KEY))
                .isTrue();
        assertThat(authorization.canEdit(
                        "bcp.mallory", FixtureEditAuthorizationService.ASSET_URN, FixtureFormRegistry.FORM_KEY))
                .isFalse();
        assertThat(authorization.canEdit("bcp.alice", "urn:other", FixtureFormRegistry.FORM_KEY))
                .isFalse();
        assertThat(authorization.canEdit(
                        "bcp.alice", FixtureEditAuthorizationService.ASSET_URN, "another.form"))
                .isFalse();
    }
}
