import copy
import json
import unittest

from datahub.metadata import schema_classes as s
from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.pipeline.pipeline_context import PipelineContext

from dcl_form_assignment.action import AssignmentConfig, FormAssignmentAction
from dcl_form_assignment.datahub import AWAITING_POPULATION, DataHubAssignments
from dcl_form_assignment.demo import MINIMUM_FORM, STATUS_PROPERTY
from dcl_form_assignment.entities import FORM_ENTITY_TYPES, OWNER_ENTITY_TYPES
from dcl_form_assignment.events import added_forms, added_owners
from test_action import ENTITY, FORM, Graph, envelope, event


OWNER = "urn:li:corpuser:owner"
GROUP = "urn:li:corpGroup:owners"
ENTITIES = {
    "dataset": ENTITY,
    "dataJob": "urn:li:dataJob:(urn:li:dataFlow:(airflow,pipeline,PROD),job)",
    "dataFlow": "urn:li:dataFlow:(airflow,pipeline,PROD)",
    "chart": "urn:li:chart:(looker,chart)",
    "dashboard": "urn:li:dashboard:(looker,dashboard)",
    "corpuser": OWNER,
    "corpGroup": GROUP,
    "domain": "urn:li:domain:example",
    "container": "urn:li:container:example",
    "glossaryTerm": "urn:li:glossaryTerm:example",
    "glossaryNode": "urn:li:glossaryNode:example",
    "mlModel": "urn:li:mlModel:(urn:li:dataPlatform:mlflow,model,PROD)",
    "mlModelGroup": "urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,group,PROD)",
    "mlFeatureTable": "urn:li:mlFeatureTable:(urn:li:dataPlatform:feast,table)",
    "mlFeature": "urn:li:mlFeature:(urn:li:dataPlatform:feast,feature)",
    "mlPrimaryKey": "urn:li:mlPrimaryKey:(urn:li:dataPlatform:feast,key)",
    "schemaField": f"urn:li:schemaField:({ENTITY},column)",
    "dataProduct": "urn:li:dataProduct:example",
    "application": "urn:li:application:example",
}


def change(aspect, current, previous=None, entity=ENTITY, **overrides):
    return event(
        aspectName=aspect,
        entityUrn=entity,
        aspect={"contentType": "application/json", "value": json.dumps(current)},
        previousAspectValue={
            "contentType": "application/json",
            "value": json.dumps(previous),
        }
        if previous is not None
        else None,
        **overrides,
    )


def ownership(*owners):
    return {"owners": [{"owner": owner, "type": "DATAOWNER"} for owner in owners]}


def forms(incomplete=(), completed=()):
    return {
        "incompleteForms": [{"urn": urn} for urn in incomplete],
        "completedForms": [{"urn": urn} for urn in completed],
    }


class EventRulesTest(unittest.TestCase):
    def test_initial_and_later_owner_additions(self):
        for before in (None, ownership(), ownership(GROUP)):
            result = added_owners(change("ownership", ownership(OWNER, GROUP), before))
            self.assertIn(OWNER, result.owner_urns)

    def test_owner_removal_and_type_changes_do_not_trigger(self):
        self.assertIsNone(
            added_owners(change("ownership", ownership(), ownership(OWNER)))
        )
        value = ownership(OWNER)
        value["owners"][0]["type"] = "TECHNICAL_OWNER"
        self.assertIsNone(added_owners(change("ownership", value, ownership(OWNER))))

    def test_user_and_group_owners_across_supported_types(self):
        self.assertEqual(FORM_ENTITY_TYPES, set(ENTITIES))
        for kind, entity in ENTITIES.items():
            with self.subTest(kind=kind):
                result = added_owners(
                    change("ownership", ownership(OWNER, GROUP), entity=entity)
                )
                if kind in OWNER_ENTITY_TYPES:
                    self.assertEqual(frozenset((OWNER, GROUP)), result.owner_urns)
                else:
                    self.assertIsNone(result)

    def test_new_forms_across_supported_types(self):
        for entity in ENTITIES.values():
            with self.subTest(entity=entity):
                self.assertEqual(
                    MINIMUM_FORM,
                    added_forms(change("forms", forms((MINIMUM_FORM,)), entity=entity))[
                        0
                    ].form_urn,
                )

    def test_completion_progress_and_removal_do_not_trigger(self):
        previous = forms((MINIMUM_FORM,))
        progressed = copy.deepcopy(previous)
        progressed["incompleteForms"][0]["completedPrompts"] = [{"id": "description"}]
        for current in (
            previous,
            progressed,
            forms(completed=(MINIMUM_FORM,)),
            forms(),
        ):
            self.assertEqual((), added_forms(change("forms", current, previous)))

    def test_reattachment_is_a_new_event(self):
        self.assertEqual(
            1, len(added_forms(change("forms", forms((MINIMUM_FORM,)), forms())))
        )

    def test_unrelated_and_delete_events_do_not_trigger(self):
        for aspect in ("structuredProperties", "status", "formInfo"):
            value = change(aspect, {})
            self.assertIsNone(added_owners(value))
            self.assertEqual((), added_forms(value))
        value = change("forms", forms((MINIMUM_FORM,)), changeType="DELETE")
        self.assertEqual((), added_forms(value))

    def test_malformed_relevant_events_fail(self):
        for value, decode in (
            (change("forms", {}), added_forms),
            (change("ownership", {}), added_owners),
        ):
            with self.assertRaises(KeyError):
                decode(value)
        with self.assertRaises(ValueError):
            added_owners(change("ownership", ownership("urn:li:tag:invalid-owner")))


class NewRuleTest(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()
        self.action = FormAssignmentAction.create(
            {
                "minimum_metadata_form": MINIMUM_FORM,
                "form_to_property": {MINIMUM_FORM: STATUS_PROPERTY},
            },
            PipelineContext("rules", AcrylDataHubGraph(self.graph)),
        )
        self.graph.aspects[(ENTITY, s.OwnershipClass)] = s.OwnershipClass(
            owners=[s.OwnerClass(owner=OWNER, type="DATAOWNER")]
        )

    def attach(self, entity=ENTITY, form=MINIMUM_FORM):
        self.graph.aspects[(entity, s.FormsClass)] = s.FormsClass(
            incompleteForms=[s.FormAssociationClass(urn=form)], completedForms=[]
        )

    def property(self, values, entity=ENTITY, prop=STATUS_PROPERTY):
        self.graph.aspects[(entity, s.StructuredPropertiesClass)] = (
            s.StructuredPropertiesClass(
                properties=[
                    s.StructuredPropertyValueAssignmentClass(
                        propertyUrn=prop, values=values
                    )
                ]
            )
        )

    def test_owner_assigns_once_and_preserves_form_progress(self):
        value = envelope(change("ownership", ownership(OWNER)))
        self.action.act(value)
        state = copy.deepcopy(self.graph.aspects[(ENTITY, s.FormsClass)].to_obj())
        self.action.act(value)
        self.assertEqual(1, len(self.graph.calls))
        self.assertEqual(state, self.graph.aspects[(ENTITY, s.FormsClass)].to_obj())

    def test_owner_rule_covers_views_and_entities_without_status(self):
        for entity in (ENTITY, ENTITIES["domain"], ENTITIES["container"]):
            self.graph.aspects[(entity, s.OwnershipClass)] = self.graph.aspects[
                (ENTITY, s.OwnershipClass)
            ]
            self.graph.aspects[(ENTITY, s.SubTypesClass)] = s.SubTypesClass(
                typeNames=["View"]
            )
            self.action.act(
                envelope(change("ownership", ownership(OWNER), entity=entity))
            )
            self.assertTrue(self.action.service.datahub.has_form(entity, MINIMUM_FORM))

    def test_removed_or_deleted_entities_are_skipped(self):
        self.attach()
        self.graph.aspects[(ENTITY, s.StatusClass)] = s.StatusClass(removed=True)
        for aspect, current in (
            ("ownership", ownership(OWNER)),
            ("forms", forms((MINIMUM_FORM,))),
        ):
            self.action.act(envelope(change(aspect, current)))
        self.graph.entity_exists = False
        self.action.act(envelope(change("ownership", ownership(OWNER))))
        self.assertEqual([], self.graph.calls)
        self.assertEqual([], self.graph.emits)

    def test_stale_owner_addition_is_skipped(self):
        self.graph.aspects[(ENTITY, s.OwnershipClass)].owners = []
        self.action.act(envelope(change("ownership", ownership(OWNER))))
        self.assertEqual([], self.graph.calls)

    def test_missing_property_is_initialized_and_replay_is_skipped(self):
        self.attach()
        value = envelope(change("forms", forms((MINIMUM_FORM,))))
        self.action.act(value)
        self.action.act(value)
        self.assertEqual(1, len(self.graph.emits))
        self.assertEqual(
            [AWAITING_POPULATION],
            self.graph.aspects[(ENTITY, s.StructuredPropertiesClass)]
            .properties[0]
            .values,
        )

    def test_empty_assignment_is_initialized(self):
        self.attach()
        for values in ([], [""], ["   "]):
            self.property(values)
            self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))
            self.assertEqual(
                [AWAITING_POPULATION],
                self.graph.aspects[(ENTITY, s.StructuredPropertiesClass)]
                .properties[0]
                .values,
            )
        self.assertEqual(3, len(self.graph.emits))

    def test_existing_values_are_preserved_even_after_reattachment(self):
        self.attach()
        for values in (["Completed"], ["Awaiting population"], ["", "Completed"]):
            self.property(values)
            self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)), forms())))
            self.assertEqual(
                values,
                self.graph.aspects[(ENTITY, s.StructuredPropertiesClass)]
                .properties[0]
                .values,
            )
        self.assertEqual([], self.graph.emits)

    def test_unrelated_property_edit_is_preserved_by_patch(self):
        self.attach()
        other = "urn:li:structuredProperty:other"
        self.graph.before_emit = lambda: self.property(
            ["Concurrent change"], prop=other
        )
        self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))
        actual = {
            p.propertyUrn: p.values
            for p in self.graph.aspects[
                (ENTITY, s.StructuredPropertiesClass)
            ].properties
        }
        self.assertEqual(["Concurrent change"], actual[other])
        self.assertEqual([AWAITING_POPULATION], actual[STATUS_PROPERTY])

    def test_status_rule_covers_every_form_entity_type(self):
        for entity in ENTITIES.values():
            with self.subTest(entity=entity):
                self.attach(entity)
                self.action.act(
                    envelope(change("forms", forms((MINIMUM_FORM,)), entity=entity))
                )
                self.assertTrue(
                    self.graph.aspects[(entity, s.StructuredPropertiesClass)].properties
                )

    def test_property_scope_mismatch_fails(self):
        self.attach()
        self.action.service.datahub.property_types[STATUS_PROPERTY] = set()
        with self.assertRaisesRegex(ValueError, "not enabled"):
            self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))
        self.assertEqual([], self.graph.emits)

    def test_stale_or_unmapped_form_does_not_write(self):
        self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))
        self.attach(form=FORM)
        self.action.act(envelope(change("forms", forms((FORM,)))))
        self.assertEqual([], self.graph.emits)

    def test_property_write_and_read_failures_propagate(self):
        self.attach()
        self.graph.persist = False
        with self.assertRaisesRegex(RuntimeError, "read-back"):
            self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))
        self.graph.error = PermissionError("denied")
        with self.assertRaises(PermissionError):
            self.action.act(envelope(change("ownership", ownership(OWNER))))

    def test_property_write_exception_propagates(self):
        self.attach()

        def fail(*args, **kwargs):
            raise PermissionError("denied")

        self.graph.emit_mcp = fail
        with self.assertRaises(PermissionError):
            self.action.act(envelope(change("forms", forms((MINIMUM_FORM,)))))

    def test_property_event_does_not_create_a_loop(self):
        self.graph.error = RuntimeError("must not read")
        self.action.act(envelope(change("structuredProperties", {})))

    def test_disabled_rules_do_not_decode_unrelated_payloads(self):
        action = FormAssignmentAction.create(
            {"minimum_metadata_form": MINIMUM_FORM},
            PipelineContext("owner", AcrylDataHubGraph(self.graph)),
        )
        action.act(envelope(change("globalTags", {})))
        action.act(envelope(change("forms", {})))


class ConfigurationTest(unittest.TestCase):
    def test_each_rule_can_be_configured_independently(self):
        for value in (
            {"minimum_metadata_form": MINIMUM_FORM},
            {"form_to_property": {MINIMUM_FORM: STATUS_PROPERTY}},
        ):
            self.assertIsNotNone(AssignmentConfig.model_validate(value))

    def test_invalid_rules_fail_startup(self):
        for value in (
            {},
            {"minimum_metadata_form": "bad"},
            {"form_to_property": {MINIMUM_FORM: "urn:li:tag:wrong"}},
        ):
            with self.assertRaises(ValueError):
                AssignmentConfig.model_validate(value)

    def test_missing_definitions_fail(self):
        graph = Graph()
        adapter = DataHubAssignments(graph)
        with self.assertRaises(ValueError):
            adapter.validate_forms({"urn:li:form:missing"})
        with self.assertRaises(ValueError):
            adapter.validate_properties({"urn:li:structuredProperty:missing"})

    def test_invalid_property_definition_fails(self):
        for field, value in (
            ("valueType", "urn:li:dataType:datahub.number"),
            ("allowedValues", [s.PropertyValueClass(value="Completed")]),
        ):
            graph = Graph()
            setattr(
                graph.aspects[(STATUS_PROPERTY, s.StructuredPropertyDefinitionClass)],
                field,
                value,
            )
            with self.assertRaises(ValueError):
                DataHubAssignments(graph).validate_properties({STATUS_PROPERTY})
