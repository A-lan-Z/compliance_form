CREATE TABLE dcl_workflow (
    id                      UUID PRIMARY KEY,
    asset_urn               TEXT NOT NULL,
    asset_snapshot          JSONB NOT NULL,
    form_key                TEXT NOT NULL,
    form_revision           INTEGER NOT NULL,
    form_definition_sha256  TEXT NOT NULL,
    review_status           TEXT NOT NULL,
    publication_status      TEXT NOT NULL,
    baseline_values         JSONB NOT NULL,
    baseline_captured_at    TIMESTAMPTZ NOT NULL,
    baseline_sha256         TEXT NOT NULL,
    draft_values            JSONB NOT NULL,
    lock_version            BIGINT NOT NULL DEFAULT 1,
    created_by              TEXT NOT NULL,
    updated_by              TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_dcl_workflow_asset_form UNIQUE (asset_urn, form_key),
    CONSTRAINT ck_dcl_workflow_form_revision CHECK (form_revision > 0),
    CONSTRAINT ck_dcl_workflow_definition_digest CHECK (form_definition_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dcl_workflow_baseline_digest CHECK (baseline_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dcl_workflow_review_status CHECK (
        review_status IN ('DRAFT', 'SUBMITTED', 'REJECTED', 'APPROVED')
    ),
    CONSTRAINT ck_dcl_workflow_publication_status CHECK (
        publication_status IN ('NOT_STARTED', 'PENDING', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED')
    ),
    CONSTRAINT ck_dcl_workflow_publication_requires_approval CHECK (
        review_status = 'APPROVED' OR publication_status = 'NOT_STARTED'
    ),
    CONSTRAINT ck_dcl_workflow_lock_version CHECK (lock_version > 0),
    CONSTRAINT ck_dcl_workflow_asset_snapshot_object CHECK (jsonb_typeof(asset_snapshot) = 'object'),
    CONSTRAINT ck_dcl_workflow_baseline_values_object CHECK (jsonb_typeof(baseline_values) = 'object'),
    CONSTRAINT ck_dcl_workflow_draft_values_object CHECK (jsonb_typeof(draft_values) = 'object'),
    CONSTRAINT ck_dcl_workflow_draft_has_class CHECK (draft_values ? 'disposalClass'),
    CONSTRAINT ck_dcl_workflow_draft_only_class CHECK (
        draft_values - 'disposalClass' = '{}'::jsonb
        AND NOT draft_values ? 'disposalAction'
    )
);

CREATE TABLE dcl_audit_event (
    id                UUID PRIMARY KEY,
    workflow_id       UUID NOT NULL REFERENCES dcl_workflow(id),
    sequence          BIGINT NOT NULL,
    event_type        TEXT NOT NULL,
    actor_id          TEXT NOT NULL,
    actor_type        TEXT NOT NULL,
    occurred_at       TIMESTAMPTZ NOT NULL,
    request_id        TEXT NOT NULL,
    workflow_version  BIGINT NOT NULL,
    details           JSONB NOT NULL,

    CONSTRAINT uq_dcl_audit_event_sequence UNIQUE (workflow_id, sequence),
    CONSTRAINT ck_dcl_audit_event_sequence CHECK (sequence > 0),
    CONSTRAINT ck_dcl_audit_event_workflow_version CHECK (workflow_version > 0),
    CONSTRAINT ck_dcl_audit_event_type CHECK (event_type IN ('WORKFLOW_CREATED', 'DRAFT_SAVED')),
    CONSTRAINT ck_dcl_audit_actor_type CHECK (actor_type IN ('USER', 'SYSTEM')),
    CONSTRAINT ck_dcl_audit_details_object CHECK (jsonb_typeof(details) = 'object'),
    CONSTRAINT ck_dcl_audit_creation_sequence CHECK (
        event_type <> 'WORKFLOW_CREATED' OR sequence = 1
    )
);

CREATE UNIQUE INDEX uq_dcl_audit_workflow_created
    ON dcl_audit_event (workflow_id)
    WHERE event_type = 'WORKFLOW_CREATED';
