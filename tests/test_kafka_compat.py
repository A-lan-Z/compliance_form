import copy
from io import BytesIO
import json
import unittest
from unittest.mock import Mock, patch

from avro.errors import AvroTypeException
from confluent_kafka import TopicPartition
from datahub.metadata.schema_classes import MetadataChangeLogClass
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.source.kafka.kafka_event_source import (
    KafkaEventSource,
    KafkaEventSourceConfig,
)
from datahub_actions.source.event_source_registry import event_source_registry
from fastavro import parse_schema, schemaless_reader, schemaless_writer

from dcl_form_assignment.kafka_compat import (
    EXPECTED_AUDIT_STAMP,
    LEGACY_AUDIT_STAMP,
    LegacyAuditStampKafkaEventSource,
    normalize_legacy_audit_stamps,
)

ENTITY = "urn:li:dataset:(urn:li:dataPlatform:postgres,dcl.poc.table,DEV)"


def avro_message(audit_name):
    schema = MetadataChangeLogClass.RECORD_SCHEMA.to_json()

    def rename(value):
        if isinstance(value, dict):
            value = {key: rename(child) for key, child in value.items()}
            if value.get("type") == "record" and value.get("name") in {
                "AuditStamp",
                EXPECTED_AUDIT_STAMP,
            }:
                namespace, name = audit_name.rsplit(".", 1)
                value.update(namespace=namespace, name=name)
            return value
        if isinstance(value, list):
            return [rename(child) for child in value]
        return audit_name if value == EXPECTED_AUDIT_STAMP else value

    schema = parse_schema(rename(copy.deepcopy(schema)))
    data = {
        "entityType": "dataset",
        "entityUrn": ENTITY,
        "aspectName": "globalTags",
        "changeType": "UPSERT",
        "aspect": {
            "contentType": "application/json",
            "value": b'{"tags":[{"tag":"urn:li:tag:dcl.poc.requires-compliance"}]}',
        },
        "created": {
            "time": 1234,
            "actor": "urn:li:corpuser:__datahub_system",
            "impersonator": None,
            "message": None,
        },
    }
    buffer = BytesIO()
    schemaless_writer(buffer, schema, data)
    buffer.seek(0)
    decoded = schemaless_reader(buffer, schema, return_record_name=True)
    msg = Mock()
    msg.value.return_value = decoded
    msg.topic.return_value = "MetadataChangeLog_Versioned_v1"
    msg.partition.return_value = 0
    msg.offset.return_value = 50
    msg.error.return_value = None
    return msg


def source_instance(cls):
    source = object.__new__(cls)
    source.source_config = KafkaEventSourceConfig(
        topic_routes={"mcl": "MetadataChangeLog_Versioned_v1"},
        async_commit_enabled=False,
    )
    source.consumer = Mock()
    source._skip_mcl_entirely = False
    source._early_mcl_criteria_list = []
    source._pipeline_name = "compatibility-test"
    return source


class KafkaCompatibilityTest(unittest.TestCase):
    def test_real_avro_named_union_fails_upstream_and_passes_compatibility_source(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        before = copy.deepcopy(msg.value())
        with self.assertRaises(AvroTypeException):
            list(source_instance(KafkaEventSource).handle_mcl(msg))
        with self.assertLogs("dcl_form_assignment.kafka_compat", level="INFO") as logs:
            envelopes = list(
                source_instance(LegacyAuditStampKafkaEventSource).handle_mcl(msg)
            )
        self.assertEqual(1, len(envelopes))
        payload = json.loads(envelopes[0].event.as_json())
        self.assertEqual(ENTITY, payload["entityUrn"])
        self.assertEqual(1234, payload["created"]["time"])
        self.assertEqual(
            "urn:li:corpuser:__datahub_system", payload["created"]["actor"]
        )
        self.assertEqual(
            {"tags": [{"tag": "urn:li:tag:dcl.poc.requires-compliance"}]},
            json.loads(payload["aspect"]["value"]),
        )
        self.assertEqual(before, msg.value())
        self.assertIn("offset=50", logs.output[0])
        self.assertEqual(
            {"kafka": {"topic": msg.topic(), "partition": 0, "offset": 50}},
            envelopes[0].meta,
        )

    def test_current_records_have_identical_payload_to_upstream(self):
        msg = avro_message(EXPECTED_AUDIT_STAMP)
        expected = list(source_instance(KafkaEventSource).handle_mcl(msg))[0]
        actual = list(
            source_instance(LegacyAuditStampKafkaEventSource).handle_mcl(msg)
        )[0]
        self.assertEqual(expected.event.as_json(), actual.event.as_json())
        self.assertEqual(expected.meta, actual.meta)

    def test_unknown_namespace_still_fails(self):
        msg = avro_message("com.example.incompatible.AuditStamp")
        with self.assertRaises(AvroTypeException):
            list(source_instance(LegacyAuditStampKafkaEventSource).handle_mcl(msg))

    def test_invalid_legacy_record_is_not_accepted(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        msg.value()["created"] = (LEGACY_AUDIT_STAMP, "invalid-record-payload")
        with self.assertRaises(AvroTypeException):
            list(source_instance(LegacyAuditStampKafkaEventSource).handle_mcl(msg))

    def test_nested_records_translate_only_the_known_union_label(self):
        data = {
            "records": [
                (LEGACY_AUDIT_STAMP, {"time": 1, "actor": "urn:li:corpuser:test"}),
                ("com.example.OtherRecord", {"value": LEGACY_AUDIT_STAMP}),
            ],
            "payload": b"opaque aspect contents",
            "description": LEGACY_AUDIT_STAMP,
        }
        before = copy.deepcopy(data)
        actual, count = normalize_legacy_audit_stamps(data)
        self.assertEqual(1, count)
        self.assertEqual(EXPECTED_AUDIT_STAMP, actual["records"][0][0])
        self.assertEqual(before["records"][1], actual["records"][1])
        self.assertEqual(before["payload"], actual["payload"])
        self.assertEqual(before["description"], actual["description"])
        self.assertEqual(before, data)

    def test_source_is_loadable_from_yaml_type(self):
        source = event_source_registry.get(
            "dcl_form_assignment.kafka_compat:LegacyAuditStampKafkaEventSource"
        )
        self.assertIs(LegacyAuditStampKafkaEventSource, source)

    def test_offset_commit_still_uses_successful_event_offset_plus_one(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        event = list(source_instance(LegacyAuditStampKafkaEventSource).handle_mcl(msg))[
            0
        ]
        source = source_instance(LegacyAuditStampKafkaEventSource)
        source.consumer.commit.return_value = [TopicPartition(msg.topic(), 0, 51)]
        source.ack(event)
        call = source.consumer.commit.call_args.kwargs
        self.assertFalse(call["asynchronous"])
        self.assertEqual(
            [(msg.topic(), 0, 51)],
            [(p.topic, p.partition, p.offset) for p in call["offsets"]],
        )

    def test_source_creation_preserves_consumer_and_registry_settings(self):
        config = {
            "async_commit_enabled": False,
            "connection": {
                "bootstrap": "test-broker:29092",
                "schema_registry_url": "http://test-registry:8081",
                "schema_registry_config": {"timeout": 30},
                "consumer_config": {
                    "auto.offset.reset": "earliest",
                    "client.id": "compliance-compat-test",
                },
            },
            "topic_routes": {"mcl": "company-mcl"},
        }
        before = copy.deepcopy(config)
        module = "datahub_actions.plugin.source.kafka.kafka_event_source"
        with (
            patch(module + ".SchemaRegistryClient") as registry,
            patch(module + ".AvroDeserializer") as decoder,
            patch(module + ".confluent_kafka.DeserializingConsumer") as consumer,
            self.assertLogs("dcl_form_assignment.kafka_compat", level="INFO") as logs,
        ):
            source = LegacyAuditStampKafkaEventSource.create(
                config, PipelineContext(pipeline_name="compatibility-test", graph=None)
            )
        self.assertIsInstance(source, LegacyAuditStampKafkaEventSource)
        self.assertEqual(before, config)
        self.assertEqual({"mcl": "company-mcl"}, source.source_config.topic_routes)
        registry.assert_called_once_with(
            {"timeout": 30, "url": "http://test-registry:8081"}
        )
        decoder.assert_called_once_with(
            schema_registry_client=registry.return_value, return_record_name=True
        )
        actual = consumer.call_args.args[0]
        self.assertEqual("compatibility-test", actual["group.id"])
        self.assertEqual("test-broker:29092", actual["bootstrap.servers"])
        self.assertEqual("earliest", actual["auto.offset.reset"])
        self.assertEqual("compliance-compat-test", actual["client.id"])
        self.assertFalse(actual["enable.auto.commit"])
        self.assertIn("pipeline=compatibility-test", logs.output[0])

    def test_wrapper_does_not_change_the_standard_source(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        wrapped = source_instance(LegacyAuditStampKafkaEventSource)
        self.assertEqual(1, len(list(wrapped.handle_mcl(msg))))
        with self.assertRaises(AvroTypeException):
            list(source_instance(KafkaEventSource).handle_mcl(msg))

    def test_failed_conversion_logs_position_without_acknowledging_or_payload(self):
        msg = avro_message("com.example.incompatible.AuditStamp")
        source = source_instance(LegacyAuditStampKafkaEventSource)
        with (
            self.assertLogs("dcl_form_assignment.kafka_compat", level="ERROR") as logs,
            self.assertRaises(AvroTypeException),
        ):
            list(source.handle_mcl(msg))
        self.assertIn("topic=MetadataChangeLog_Versioned_v1", logs.output[0])
        self.assertIn("partition=0 offset=50", logs.output[0])
        self.assertIn("error_type=AvroTypeException", logs.output[0])
        self.assertNotIn(ENTITY, logs.output[0])
        self.assertNotIn("urn:li:corpuser", logs.output[0])
        source.consumer.commit.assert_not_called()
        source.consumer.store_offsets.assert_not_called()

    def test_deferred_acknowledgment_keeps_upstream_offset_storage(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        source = source_instance(LegacyAuditStampKafkaEventSource)
        source.source_config.async_commit_enabled = True
        event = list(source.handle_mcl(msg))[0]
        expected = source_instance(KafkaEventSource)
        expected.source_config.async_commit_enabled = True
        expected.ack(event, processed=False)
        source.ack(event, processed=False)
        self.assertEqual(expected.consumer.method_calls, source.consumer.method_calls)

    def test_inherited_consumer_dispatch_normalizes_timeseries_mcl(self):
        msg = avro_message(LEGACY_AUDIT_STAMP)
        msg.topic.return_value = "MetadataChangeLog_Timeseries_v1"
        source = source_instance(LegacyAuditStampKafkaEventSource)
        source.source_config.topic_routes = {
            "mcl_timeseries": "MetadataChangeLog_Timeseries_v1"
        }
        source._observe_message = Mock()
        source.consumer.poll.return_value = msg
        events = source.events()
        try:
            event = next(events)
        finally:
            events.close()
        self.assertEqual(msg.topic(), event.meta["kafka"]["topic"])
        self.assertEqual(ENTITY, json.loads(event.event.as_json())["entityUrn"])
        source.consumer.subscribe.assert_called_once_with([msg.topic()])
        source._observe_message.assert_called_once_with(msg)
