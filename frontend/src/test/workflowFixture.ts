import type { WorkflowView } from "../api/workflows";

export function workflowFixture(): WorkflowView {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    asset: {
      urn: "urn:li:container:00000000000000000000000000000001",
      displayName: "Fixture EDW Database",
      entityType: "CONTAINER",
      subTypes: ["Database"],
    },
    form: {
      key: "dcl.edw.database.fixture",
      displayName: "DCL EDW Database Compliance — Fixture",
      revision: 1,
      definitionSha256:
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    status: {
      review: "DRAFT",
      publication: "NOT_STARTED",
    },
    version: 1,
    fields: {
      disposalClass: {
        value: "TEST_CLASS_A",
        editable: true,
        allowedValues: ["TEST_CLASS_A", "TEST_CLASS_B"],
      },
      disposalAction: {
        value: "TEST_ACTION_A",
        editable: false,
        derivedFrom: "disposalClass",
        previewByDisposalClass: {
          TEST_CLASS_A: "TEST_ACTION_A",
          TEST_CLASS_B: "TEST_ACTION_B",
        },
      },
    },
    baseline: {
      capturedAt: "2026-08-21T01:02:03Z",
      sha256:
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    },
    warnings: [],
    permissions: {
      canEdit: true,
    },
  };
}
