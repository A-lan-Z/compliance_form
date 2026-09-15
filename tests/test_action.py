import copy
import json
from pathlib import Path
import unittest

from datahub.configuration.config_loader import load_config_file
from datahub.metadata import schema_classes as s
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.pipeline.pipeline import create_action
from datahub_actions.pipeline.pipeline_config import PipelineConfig

from dcl_form_assignment.action import AssignmentConfig, FormAssignmentAction
from dcl_form_assignment.datahub import DataHubAssignments
from dcl_form_assignment.demo import MINIMUM_FORM, STATUS_PROPERTY
from dcl_form_assignment.entities import FORM_ENTITY_TYPES
from dcl_form_assignment.events import added_table_tags


ENTITY = "urn:li:dataset:(urn:li:dataPlatform:postgres,dcl.poc.table,DEV)"
TAG = "urn:li:tag:dcl.poc.requires-compliance"
FORM = "urn:li:form:dcl.poc.table-compliance.v1"
OTHER = "urn:li:form:other"


def event(tags=(TAG,), previous=(), **overrides):
    def aspect(values):
        return {
            "contentType": "application/json",
            "value": json.dumps({"tags": [{"tag": tag} for tag in values]}),
        }

    value = {
        "entityType": "dataset",
        "entityUrn": ENTITY,
        "aspectName": "globalTags",
        "changeType": "UPSERT",
        "aspect": aspect(tags),
        "previousAspectValue": aspect(previous),
        "created": {"time": 1234, "actor": "urn:li:corpuser:__datahub_system"},
    }
    value.update(overrides)
    return value


def envelope(value):
    return EventEnvelope.from_json(
        json.dumps(
            {
                "event_type": "MetadataChangeLogEvent_v1",
                "event": value,
                "meta": {},
            }
        )
    )


class Graph:
    def __init__(self):
        self.aspects = {
            (TAG, s.TagPropertiesClass): s.TagPropertiesClass(name="POC tag"),
            (FORM, s.FormInfoClass): object(),
            (MINIMUM_FORM, s.FormInfoClass): object(),
            (
                STATUS_PROPERTY,
                s.StructuredPropertyDefinitionClass,
            ): s.StructuredPropertyDefinitionClass(
                qualifiedName="status",
                valueType="urn:li:dataType:datahub.string",
                entityTypes=[
                    "urn:li:entityType:datahub." + name for name in FORM_ENTITY_TYPES
                ],
                allowedValues=[
                    s.PropertyValueClass(value="Awaiting population"),
                    s.PropertyValueClass(value="Completed"),
                ],
            ),
            (ENTITY, s.SubTypesClass): s.SubTypesClass(typeNames=["Table"]),
            (ENTITY, s.GlobalTagsClass): s.GlobalTagsClass(
                tags=[s.TagAssociationClass(tag=TAG)]
            ),
            (ENTITY, s.FormsClass): s.FormsClass(incompleteForms=[], completedForms=[]),
        }
        self.calls = []
        self.error = None
        self.result = True
        self.persist = True
        self.entity_exists = True
        self.emits = []
        self.before_emit = None

    def exists(self, urn):
        if self.error:
            raise self.error
        return self.entity_exists

    def emit_mcp(self, mcp, async_flag=None):
        if self.error:
            raise self.error
        self.emits.append(mcp)
        if self.before_emit:
            self.before_emit()
        if self.persist:
            value = json.loads(mcp.aspect.value)[0]["value"]
            current = self.aspects.get(
                (mcp.entityUrn, s.StructuredPropertiesClass),
                s.StructuredPropertiesClass(properties=[]),
            )
            current.properties = [
                item
                for item in current.properties
                if item.propertyUrn != value["propertyUrn"]
            ]
            current.properties.append(
                s.StructuredPropertyValueAssignmentClass.from_obj(value)
            )
            self.aspects[(mcp.entityUrn, s.StructuredPropertiesClass)] = current

    def get_aspect(self, urn, aspect):
        if self.error:
            raise self.error
        return self.aspects.get((urn, aspect))

    def execute_graphql(self, query, variables):
        self.calls.append((query, variables))
        if self.error:
            raise self.error
        if self.persist:
            form = variables["input"]["formUrn"]
            entity = variables["input"]["entityUrns"][0]
            forms = self.aspects.setdefault(
                (entity, s.FormsClass),
                s.FormsClass(incompleteForms=[], completedForms=[]),
            )
            forms.incompleteForms.append(s.FormAssociationClass(urn=form))
        return {"batchAssignForm": self.result}


class TagEventTest(unittest.TestCase):
    def test_detects_new_tags_in_native_serialized_event(self):
        value = event(tags=(TAG, "urn:li:tag:old"), previous=("urn:li:tag:old",))
        native = json.loads(envelope(value).event.as_json())
        additions = added_table_tags(native)
        self.assertEqual(
            [(ENTITY, TAG)], [(a.entity_urn, a.tag_urn) for a in additions]
        )

    def test_initial_tag_aspect_is_an_addition(self):
        self.assertEqual(1, len(added_table_tags(event(previousAspectValue=None))))

    def test_removal_and_unchanged_tags_are_ignored(self):
        self.assertEqual((), added_table_tags(event(tags=(), previous=(TAG,))))
        self.assertEqual((), added_table_tags(event(previous=(TAG,))))

    def test_other_aspects_and_entities_are_ignored(self):
        for overrides in [
            {"aspectName": "editableSchemaMetadata"},
            {"aspectName": "schemaMetadata"},
            {"aspectName": "forms"},
            {"entityUrn": "urn:li:container:example"},
            {"changeType": "DELETE"},
        ]:
            with self.subTest(overrides=overrides):
                self.assertEqual((), added_table_tags(event(**overrides)))

    def test_malformed_relevant_event_fails_visibly(self):
        with self.assertRaises(json.JSONDecodeError):
            added_table_tags(event(aspect={"value": "not json"}))
        with self.assertRaises(KeyError):
            added_table_tags(event(aspect={"value": "{}"}))


class ActionTest(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()
        self.action = FormAssignmentAction.create(
            {"tag_to_form": {TAG: FORM}},
            PipelineContext("test", AcrylDataHubGraph(self.graph)),
        )

    def test_assigns_and_replay_does_not_write_again(self):
        self.action.act(envelope(event()))
        self.action.act(envelope(event()))
        self.assertEqual(1, len(self.graph.calls))
        self.assertEqual(
            {"input": {"formUrn": FORM, "entityUrns": [ENTITY]}}, self.graph.calls[0][1]
        )
        self.assertIn("batchAssignForm", self.graph.calls[0][0])

    def test_preserves_existing_completed_form_and_prompt_progress(self):
        forms = s.FormsClass(
            incompleteForms=[],
            completedForms=[
                s.FormAssociationClass(
                    urn=FORM,
                    completedPrompts=[
                        s.FormPromptAssociationClass(
                            id="classification",
                            lastModified=s.AuditStampClass(
                                time=1234, actor="urn:li:corpuser:test"
                            ),
                        )
                    ],
                )
            ],
        )
        self.graph.aspects[(ENTITY, s.FormsClass)] = forms
        before = copy.deepcopy(forms.to_obj())
        self.action.act(envelope(event()))
        self.assertEqual([], self.graph.calls)
        self.assertEqual(before, forms.to_obj())

    def test_already_incomplete_form_is_not_reset(self):
        self.graph.aspects[(ENTITY, s.FormsClass)].incompleteForms = [
            s.FormAssociationClass(urn=FORM)
        ]
        self.action.act(envelope(event()))
        self.assertEqual([], self.graph.calls)

    def test_skips_views_unknown_subtypes_and_removed_tables(self):
        for names in [["View"], [], ["Table", "View"]]:
            with self.subTest(names=names):
                self.graph.aspects[(ENTITY, s.SubTypesClass)] = s.SubTypesClass(
                    typeNames=names
                )
                self.action.act(envelope(event()))
                self.assertEqual([], self.graph.calls)
        self.graph.aspects[(ENTITY, s.SubTypesClass)] = s.SubTypesClass(
            typeNames=["Table"]
        )
        self.graph.aspects[(ENTITY, s.StatusClass)] = s.StatusClass(removed=True)
        self.action.act(envelope(event()))
        self.assertEqual([], self.graph.calls)

    def test_stale_addition_does_not_assign_after_tag_removal(self):
        self.graph.aspects[(ENTITY, s.GlobalTagsClass)] = s.GlobalTagsClass(tags=[])
        self.action.act(envelope(event()))
        self.assertEqual([], self.graph.calls)

    def test_unmapped_tag_does_not_read_or_write_datahub(self):
        self.graph.error = RuntimeError("must not read")
        self.action.act(envelope(event(tags=("urn:li:tag:unrelated",))))
        self.assertEqual([], self.graph.calls)

    def test_two_tags_mapping_to_same_form_assign_once(self):
        second = "urn:li:tag:second"
        self.graph.aspects[(second, s.TagPropertiesClass)] = s.TagPropertiesClass(
            name="second"
        )
        self.graph.aspects[(ENTITY, s.GlobalTagsClass)].tags.append(
            s.TagAssociationClass(tag=second)
        )
        action = FormAssignmentAction.create(
            {"tag_to_form": {TAG: FORM, second: FORM}},
            PipelineContext("test", AcrylDataHubGraph(self.graph)),
        )
        action.act(envelope(event(tags=(TAG, second))))
        self.assertEqual(1, len(self.graph.calls))

    def test_read_failure_is_not_acknowledged_as_success(self):
        self.graph.error = RuntimeError("GMS unavailable")
        with self.assertRaisesRegex(RuntimeError, "GMS unavailable"):
            self.action.act(envelope(event()))

    def test_assignment_failure_and_missing_readback_fail(self):
        self.graph.result = False
        self.graph.persist = False
        with self.assertRaisesRegex(RuntimeError, "did not accept"):
            self.action.act(envelope(event()))
        self.graph.result = True
        with self.assertRaisesRegex(RuntimeError, "read-back"):
            self.action.act(envelope(event()))

    def test_write_exception_propagates(self):
        def fail(*args):
            raise PermissionError("assignment forbidden")

        self.graph.execute_graphql = fail
        with self.assertRaises(PermissionError):
            self.action.act(envelope(event()))

    def test_missing_form_or_tag_prevents_startup(self):
        for key in [(TAG, s.TagPropertiesClass), (FORM, s.FormInfoClass)]:
            with self.subTest(key=key):
                graph = Graph()
                del graph.aspects[key]
                with self.assertRaisesRegex(ValueError, "does not exist"):
                    DataHubAssignments(graph).validate_mapping({TAG: FORM})

    def test_invalid_or_obsolete_configuration_is_rejected(self):
        for config in [
            {"tag_to_form": {}},
            {"tag_to_form": {"invalid": FORM}},
            {"tag_to_form": {TAG: "urn:li:tag:wrong"}},
            {"tag_to_form": {TAG: FORM}, "delivery": {"type": "smtp"}},
        ]:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    AssignmentConfig.model_validate(config)

    def test_checked_in_yaml_loads_real_action_plugin(self):
        path = Path(__file__).resolve().parents[1] / "config/tag-form-action.yaml"
        config = PipelineConfig.model_validate(load_config_file(path))
        self.assertEqual("THROW", config.options.failure_mode.value)
        self.assertEqual(
            "earliest",
            config.source.config["connection"]["consumer_config"]["auto.offset.reset"],
        )
        action = create_action(
            config.action, PipelineContext("test", AcrylDataHubGraph(self.graph))
        )
        action.act(envelope(event()))
        self.assertEqual(1, len(self.graph.calls))
        action.close()
