package com.example.dcl.adapter.fixture;

import com.example.dcl.application.error.AssetNotFoundException;
import com.example.dcl.application.port.DraftSeed;
import com.example.dcl.application.port.DraftSeedReader;
import com.example.dcl.domain.form.FormDefinition;
import com.example.dcl.domain.workflow.AssetSnapshot;
import java.time.Clock;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;

@Component
public final class FixtureDraftSeedAdapter implements DraftSeedReader {
    private final Clock clock;
    private final AtomicInteger invocationCount = new AtomicInteger();

    public FixtureDraftSeedAdapter(Clock clock) {
        this.clock = clock;
    }

    @Override
    public DraftSeed loadDraftSeed(String principalId, String assetUrn, FormDefinition formDefinition) {
        invocationCount.incrementAndGet();
        if (!FixtureEditAuthorizationService.ASSET_URN.equals(assetUrn)) {
            throw new AssetNotFoundException();
        }
        Map<String, Object> managedValues = new LinkedHashMap<>();
        managedValues.put("disposalClass", "TEST_CLASS_A");
        managedValues.put("disposalAction", "TEST_ACTION_A");
        return new DraftSeed(
                new AssetSnapshot(
                        assetUrn,
                        "Fixture EDW Database",
                        "CONTAINER",
                        List.of("Database")),
                managedValues,
                Set.of(FixtureEditAuthorizationService.AUTHORIZED_PRINCIPAL),
                clock.instant());
    }

    public int invocationCount() {
        return invocationCount.get();
    }

    public void resetInvocationCount() {
        invocationCount.set(0);
    }
}
