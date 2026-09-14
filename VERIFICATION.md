# Verification

Verified 14 September 2026 after promoting the Action to the repository root and pinning the
runtime to 1.6.0.16. No company endpoint or real data source was used.

## Release checks

| Check | Result |
| --- | --- |
| Complete `scripts/verify.sh` gate | 18 tests passed; Ruff lint and format passed; wheel built; dependencies valid |
| Fresh isolated wheel installation | Dependency resolution passed; CLI and Actions both 1.6.0.16 |
| Import outside the checkout | Action imported from the fresh environment's site-packages |
| Installed wheel unit tests | All 18 passed with no source PYTHONPATH |
| CLI and demo entry point | `datahub version` and `dcl-tag-form-demo --help` passed |
| Real Kafka/GMS workflow using the installed wheel | All 10 scenarios passed |

The core Action modules, YAML configuration, and unit test assertions are unchanged from the
previous source-only version check. The live harness now resolves the repository root and installed
CLI correctly and accepts local GMS/Kafka port arguments.

## Versions

- Python 3.11.15.
- `acryl-datahub` and `acryl-datahub-actions`: 1.6.0.16.
- GMS: official `acryldata/datahub-gms:v1.3.0`, reported commit
  `94885944cfc8067dcfb34072c90824d6100cfba7`.
- Kafka: `confluentinc/cp-kafka:8.0.0` in an isolated local test stack.
- GMS port 18083; Kafka port 19093; schema registry served by the local GMS.

[Version, image, source, and tested-wheel hashes](evidence/gms13-cli16-versions.json).

## Live scenarios

The test used the installed wheel and the checked-in harness:

```bash
python tests/live_tag_assignment.py --gms-port 18083 --kafka-port 19093
```

1. Native tag mutation produces a Kafka event and assigns the form, preserving another form.
2. Replay of the captured native event preserves assignment and prompt state.
3. Tag removal preserves assigned forms.
4. Tag re-addition preserves assignments.
5. Views, missing subtype, and containers are excluded.
6. Unrelated tags do not restore a manually removed form.
7. Ingestion-origin tag addition assigns the form.
8. Native form completion and answers survive retagging.
9. Restart with the same consumer identity preserves completed work.
10. A stale captured addition does not assign after the tag is removed.

[Live result manifest](evidence/gms13-cli16-live-results.json). Both test worker instances were
stopped by the harness. Synthetic metadata was retained for inspection.

An earlier same-day browser test of the unchanged Action source also passed on the matching
1.3.0 frontend: adding a tag showed Awaiting Documentation; saving Internal as an owner showed
Documented; GMS readback confirmed the completed prompt and stored Structured Property. That
browser check was separate from the installed-wheel live run above.

## Limits

Unit tests fake GMS for error paths. Live tests use actual GMS, Kafka, and the Actions worker, but
the local GMS has authentication disabled. Company authentication, authorization, Kafka ACLs,
custom GMS patches, production workloads, outage recovery, high availability, and simultaneous
independent writers remain unverified. Column-tag exclusion is covered at the unit event boundary.
The transitive Authlib deprecation warning did not affect these results.
