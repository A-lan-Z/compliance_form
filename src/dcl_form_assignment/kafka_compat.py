"""Kafka source for the legacy AuditStamp namespace in GMS startup records."""

import logging
from typing import Any, Iterable

from datahub.metadata.schema_classes import AuditStampClass
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.source.kafka.kafka_event_source import KafkaEventSource

logger = logging.getLogger(__name__)

LEGACY_AUDIT_STAMP = "com.linkedin.common.AuditStamp"
EXPECTED_AUDIT_STAMP = AuditStampClass.RECORD_SCHEMA.fullname


def normalize_legacy_audit_stamps(value: Any) -> tuple[Any, int]:
    """Copy decoded Avro values, translating only the known AuditStamp union name."""
    if isinstance(value, dict):
        result = {}
        count = 0
        for key, child in value.items():
            result[key], changed = normalize_legacy_audit_stamps(child)
            count += changed
        return result, count
    if isinstance(value, (list, tuple)):
        children = [normalize_legacy_audit_stamps(child) for child in value]
        result = [child for child, _ in children]
        count = sum(changed for _, changed in children)
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and value[0] == LEGACY_AUDIT_STAMP
            and isinstance(value[1], dict)
        ):
            result[0] = EXPECTED_AUDIT_STAMP
            count += 1
        return (tuple(result) if isinstance(value, tuple) else result), count
    return value, 0


class _NormalizedMessage:
    def __init__(self, message: Any, value: Any):
        self._message = message
        self._value = value

    def value(self) -> Any:
        return self._value

    def __getattr__(self, name: str) -> Any:
        return getattr(self._message, name)


class LegacyAuditStampKafkaEventSource(KafkaEventSource):
    """Keep the upstream consumer and acknowledgments; adapt MCLs before SDK parsing."""

    @classmethod
    def create(
        cls, config_dict: dict, ctx: PipelineContext
    ) -> "LegacyAuditStampKafkaEventSource":
        source = super().create(config_dict, ctx)
        logger.info(
            "Legacy AuditStamp compatibility source enabled pipeline=%s",
            ctx.pipeline_name,
        )
        return source

    def handle_mcl(self, msg: Any) -> Iterable[EventEnvelope]:
        try:
            value, count = normalize_legacy_audit_stamps(msg.value())
            message = _NormalizedMessage(msg, value) if count else msg
            for event in super().handle_mcl(message):
                if count:
                    logger.info(
                        "Normalized legacy AuditStamp namespace topic=%s partition=%s "
                        "offset=%s count=%s",
                        msg.topic(),
                        msg.partition(),
                        msg.offset(),
                        count,
                    )
                yield event
        except Exception as error:
            logger.error(
                "MCL conversion failed topic=%s partition=%s offset=%s error_type=%s",
                msg.topic(),
                msg.partition(),
                msg.offset(),
                type(error).__name__,
            )
            raise
