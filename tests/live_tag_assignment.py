import argparse
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from confluent_kafka import (
    ConsumerGroupTopicPartitions,
    DeserializingConsumer,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from datahub.configuration.config_loader import load_config_file
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig
from datahub.metadata import schema_classes as s
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.api.action_graph import AcrylDataHubGraph
import yaml

from dcl_form_assignment.action import FormAssignmentAction
from dcl_form_assignment.demo import (
    emit,
    mutation,
    seed_automation_definitions,
    seed_definitions,
    seed_table,
)
from dcl_form_assignment.entities import OWNER_ENTITY_TYPES


parser = argparse.ArgumentParser(description="Local Kafka/GMS integration tests.")
parser.add_argument("--gms-port", type=int, default=8080)
parser.add_argument("--kafka-port", type=int, default=9092)
args = parser.parse_args()
GMS_URL = f"http://127.0.0.1:{args.gms_port}"
KAFKA_BOOTSTRAP = f"127.0.0.1:{args.kafka_port}"
SCHEMA_REGISTRY_URL = GMS_URL + "/schema-registry/api/"
ROOT = Path(__file__).resolve().parents[1]
ID = "dcl.poc.live." + uuid4().hex
RUN = Path(tempfile.mkdtemp(prefix="dcl-form-rules-live-"))
TABLE = f"urn:li:dataset:(urn:li:dataPlatform:postgres,{ID},DEV)"
VIEW = f"urn:li:dataset:(urn:li:dataPlatform:postgres,{ID}.view,DEV)"
UNKNOWN = f"urn:li:dataset:(urn:li:dataPlatform:postgres,{ID}.unknown,DEV)"
CONTAINER = "urn:li:container:" + ID
TAG = "urn:li:tag:" + ID
UNRELATED = TAG + ".unrelated"
FORM = "urn:li:form:" + ID
OTHER = FORM + ".other"
PROPERTY = "urn:li:structuredProperty:" + ID
MINIMUM = FORM + ".minimum"
POPULATION = PROPERTY + ".population"
OWNER = "urn:li:corpuser:" + ID
OWNER_GROUP = "urn:li:corpGroup:" + ID
GROUP = ID.replace(".", "-")
TOPIC = "MetadataChangeLog_Versioned_v1"
graph = DataHubGraph(DatahubClientConfig(server=GMS_URL))
admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP})
observer = DeserializingConsumer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP + "-observer",
        "enable.auto.commit": False,
        "value.deserializer": AvroDeserializer(
            SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})
        ),
    }
)
partitions = sorted(admin.list_topics(TOPIC, timeout=10).topics[TOPIC].partitions)
observer.assign(
    [
        TopicPartition(
            TOPIC,
            p,
            observer.get_watermark_offsets(TopicPartition(TOPIC, p), timeout=10)[1],
        )
        for p in partitions
    ]
)
process = None
log = None
results = []


def wait_for(description, predicate, timeout=45):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError("Timed out: " + description)


def observe(urn, aspect="globalTags"):
    until = time.monotonic() + 45
    while time.monotonic() < until:
        message = observer.poll(1)
        if message is None:
            continue
        assert not message.error(), message.error()
        event = message.value()
        if event.get("entityUrn") == urn and event.get("aspectName") == aspect:
            return message, event
    raise AssertionError("No native event for " + urn)


def acknowledged(message):
    def committed():
        offsets = (
            admin.list_consumer_group_offsets([ConsumerGroupTopicPartitions(GROUP)])[
                GROUP
            ]
            .result(10)
            .topic_partitions
        )
        return any(
            p.topic == TOPIC
            and p.partition == message.partition()
            and p.offset > message.offset()
            for p in offsets
        )

    wait_for("Action acknowledgement", committed)


def start():
    global process, log
    log = (RUN / ("action-" + str(len(results)) + ".log")).open("w")
    process = subprocess.Popen(
        [
            str(Path(sys.executable).with_name("datahub")),
            "actions",
            "-c",
            str(RUN / "action.yaml"),
        ],
        cwd=RUN,
        env={**os.environ, "DATAHUB_TELEMETRY_ENABLED": "false"},
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    def ready():
        assert process.poll() is None, "Action exited; inspect " + str(RUN)
        group = admin.describe_consumer_groups([GROUP])[GROUP].result(10)
        return any(m.assignment.topic_partitions for m in group.members)

    wait_for("Action subscribed", ready)


def stop():
    global process, log
    if process is not None:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(10)
        process = None
        log.close()
        wait_for(
            "consumer released",
            lambda: (
                not admin.describe_consumer_groups([GROUP])[GROUP].result(10).members
            ),
        )


def forms(entity=TABLE):
    value = graph.get_aspect(entity, s.FormsClass)
    return value.to_obj() if value else {}


def has_form(entity, form, complete=False):
    value = forms(entity)
    items = value.get("completedForms", [])
    if not complete:
        items += value.get("incompleteForms", [])
    return any(item["urn"] == form for item in items)


def tag(entity=TABLE, tag_urn=TAG, remove=False):
    mutation(
        graph,
        "removeTag" if remove else "addTag",
        "TagAssociationInput",
        {
            "resourceUrn": entity,
            "tagUrn": tag_urn,
        },
    )
    message, event = observe(entity)
    acknowledged(message)
    return event


def record(name):
    results.append({"case": name, "result": "PASS"})
    print(json.dumps(results[-1]), flush=True)


try:
    seed_automation_definitions(graph, MINIMUM, POPULATION)
    emit(graph, OWNER, s.CorpUserInfoClass(active=True, displayName=ID))
    emit(
        graph,
        OWNER_GROUP,
        s.CorpGroupInfoClass(displayName=ID, members=[], admins=[], groups=[]),
    )
    seed_definitions(graph, TAG, FORM, PROPERTY)
    seed_definitions(graph, UNRELATED, OTHER, PROPERTY)
    seed_table(graph, TABLE)
    seed_table(graph, VIEW, "View")
    emit(graph, UNKNOWN, s.DatasetPropertiesClass(name="Synthetic unknown subtype"))
    emit(graph, CONTAINER, s.ContainerPropertiesClass(name="Synthetic container"))
    mutation(
        graph,
        "batchAssignForm",
        "BatchAssignFormInput",
        {"formUrn": OTHER, "entityUrns": [TABLE]},
    )
    unrelated_before = copy.deepcopy(forms()["incompleteForms"])
    config = load_config_file(ROOT / "config/tag-form-action.yaml")
    config["name"] = GROUP
    config["action"]["config"]["tag_to_form"] = {TAG: FORM}
    config["action"]["config"]["minimum_metadata_form"] = MINIMUM
    config["action"]["config"]["form_to_property"] = {MINIMUM: POPULATION}
    config["datahub"] = {"server": GMS_URL}
    config["source"]["config"]["connection"] = {
        "bootstrap": KAFKA_BOOTSTRAP,
        "consumer_config": {
            "auto.offset.reset": "earliest",
            "auto.commit.interval.ms": 100,
        },
        "schema_registry_url": SCHEMA_REGISTRY_URL,
    }
    (RUN / "action.yaml").write_text(yaml.safe_dump(config))
    start()
    first_event = tag()
    for aspect_name in ("aspect", "previousAspectValue"):
        aspect = first_event.get(aspect_name)
        if aspect is not None:
            aspect["value"] = aspect["value"].decode("utf-8")
    assert has_form(TABLE, FORM)
    assert (
        next(a for a in forms()["incompleteForms"] if a["urn"] == OTHER)
        == unrelated_before[0]
    )
    record("Native UI/API tag addition assigns form and preserves unrelated form")

    before = copy.deepcopy(forms())
    action = FormAssignmentAction.create(
        {"tag_to_form": {TAG: FORM}},
        PipelineContext("replay", AcrylDataHubGraph(graph)),
    )
    action.act(
        EventEnvelope.from_json(
            json.dumps(
                {"event_type": "MetadataChangeLogEvent_v1", "event": first_event}
            )
        )
    )
    assert forms() == before
    record("Replay of captured native event preserves assignment and prompt state")

    tag(remove=True)
    assert forms() == before
    record("Tag removal preserves assigned forms")
    tag()
    assert forms() == before
    record("Tag re-addition does not reset existing assignments")

    tag(VIEW)
    assert not has_form(VIEW, FORM)
    tag(UNKNOWN)
    assert not has_form(UNKNOWN, FORM)
    tag(CONTAINER)
    assert not has_form(CONTAINER, FORM)
    record("Views, missing subtype and containers are excluded")

    mutation(
        graph,
        "batchRemoveForm",
        "BatchRemoveFormInput",
        {"formUrn": FORM, "entityUrns": [TABLE]},
    )
    tag(tag_urn=UNRELATED)
    assert not has_form(TABLE, FORM)
    record("Unrelated tag does not restore a manually removed form")

    tag(remove=True)
    emit(graph, TABLE, s.GlobalTagsClass(tags=[s.TagAssociationClass(tag=TAG)]))
    message, _ = observe(TABLE)
    acknowledged(message)
    assert has_form(TABLE, FORM)
    record("Ingestion-origin tag addition also assigns the form")

    result = graph.execute_graphql(
        """mutation($urn:String!, $input:SubmitFormPromptInput!) {
        submitFormPrompt(urn:$urn,input:$input)
    }""",
        {
            "urn": TABLE,
            "input": {
                "formUrn": FORM,
                "promptId": FORM + ".classification",
                "type": "STRUCTURED_PROPERTY",
                "structuredPropertyParams": {
                    "structuredPropertyUrn": PROPERTY,
                    "values": [{"stringValue": "Internal"}],
                },
            },
        },
    )
    assert result["submitFormPrompt"]
    wait_for("native form completion", lambda: has_form(TABLE, FORM, complete=True))
    before = copy.deepcopy(forms())
    tag(remove=True)
    tag()
    assert forms() == before
    record("Native completed form and answers survive retagging")

    stop()
    start()
    before = copy.deepcopy(forms())
    tag(remove=True)
    tag()
    assert forms() == before
    record("Restart with same consumer identity preserves completed work")

    stop()
    mutation(
        graph,
        "batchRemoveForm",
        "BatchRemoveFormInput",
        {"formUrn": FORM, "entityUrns": [TABLE]},
    )
    mutation(
        graph, "removeTag", "TagAssociationInput", {"resourceUrn": TABLE, "tagUrn": TAG}
    )
    action.act(
        EventEnvelope.from_json(
            json.dumps(
                {"event_type": "MetadataChangeLogEvent_v1", "event": first_event}
            )
        )
    )
    assert not has_form(TABLE, FORM)
    record("Stale captured addition after removal does not assign")

    def property_values(entity, prop=POPULATION):
        aspect = graph.get_aspect(entity, s.StructuredPropertiesClass)
        return (
            next(
                (item.values for item in aspect.properties if item.propertyUrn == prop),
                [],
            )
            if aspect
            else []
        )

    def replay(native, target=None):
        value = copy.deepcopy(native)
        for key in ("aspect", "previousAspectValue"):
            if value.get(key) and isinstance(value[key]["value"], bytes):
                value[key]["value"] = value[key]["value"].decode()
        (target or rules_action).act(
            EventEnvelope.from_json(
                json.dumps({"event_type": "MetadataChangeLogEvent_v1", "event": value})
            )
        )

    def set_status(entity, values, prop=POPULATION):
        aspect = graph.get_aspect(
            entity, s.StructuredPropertiesClass
        ) or s.StructuredPropertiesClass(properties=[])
        aspect.properties = [p for p in aspect.properties if p.propertyUrn != prop]
        if values is not None:
            aspect.properties.append(
                s.StructuredPropertyValueAssignmentClass(
                    propertyUrn=prop, values=values
                )
            )
        emit(graph, entity, aspect)

    rules_action = FormAssignmentAction.create(
        {"minimum_metadata_form": MINIMUM, "form_to_property": {MINIMUM: POPULATION}},
        PipelineContext("rules-replay", AcrylDataHubGraph(graph)),
    )
    start()
    assets = {
        "dataset": f"urn:li:dataset:(urn:li:dataPlatform:postgres,{ID}.owned,DEV)",
        "dataJob": f"urn:li:dataJob:(urn:li:dataFlow:(airflow,{ID},PROD),{ID})",
        "dataFlow": f"urn:li:dataFlow:(airflow,{ID},PROD)",
        "chart": f"urn:li:chart:(looker,{ID})",
        "dashboard": f"urn:li:dashboard:(looker,{ID})",
        "corpuser": OWNER,
        "corpGroup": OWNER_GROUP,
        "domain": "urn:li:domain:" + ID,
        "container": "urn:li:container:" + ID + ".owned",
        "glossaryTerm": "urn:li:glossaryTerm:" + ID,
        "glossaryNode": "urn:li:glossaryNode:" + ID,
        "mlModel": f"urn:li:mlModel:(urn:li:dataPlatform:mlflow,{ID},PROD)",
        "mlModelGroup": f"urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,{ID},PROD)",
        "mlFeatureTable": f"urn:li:mlFeatureTable:(urn:li:dataPlatform:feast,{ID})",
        "mlFeature": f"urn:li:mlFeature:(urn:li:dataPlatform:feast,{ID})",
        "mlPrimaryKey": f"urn:li:mlPrimaryKey:(urn:li:dataPlatform:feast,{ID})",
        "schemaField": f"urn:li:schemaField:({TABLE},column)",
        "dataProduct": "urn:li:dataProduct:" + ID,
        "application": "urn:li:application:" + ID,
    }
    owner_events = {}
    form_events = {}
    for kind, entity in assets.items():
        if kind == "domain":
            emit(graph, entity, s.DomainPropertiesClass(name=ID))
        elif kind != "dataset":
            emit(graph, entity, s.StatusClass(removed=False))
        if kind in OWNER_ENTITY_TYPES:
            emit(
                graph,
                entity,
                s.OwnershipClass(owners=[s.OwnerClass(owner=OWNER, type="DATAOWNER")]),
            )
            message, native = observe(entity, "ownership")
            acknowledged(message)
            owner_events[entity] = native
        else:
            mutation(
                graph,
                "batchAssignForm",
                "BatchAssignFormInput",
                {"formUrn": MINIMUM, "entityUrns": [entity]},
            )
        wait_for("Minimum Metadata form on " + kind, lambda: has_form(entity, MINIMUM))
        message, native = observe(entity, "forms")
        acknowledged(message)
        form_events[entity] = native
        wait_for(
            "Population status on " + kind,
            lambda: property_values(entity) == ["Awaiting population"],
        )
        record("Form assignment and population status on " + kind)

    owned = assets["dataset"]
    set_status(owned, ["Completed"])
    before = copy.deepcopy(forms(owned))
    replay(owner_events[owned])
    replay(form_events[owned])
    assert forms(owned) == before
    assert property_values(owned) == ["Completed"]
    record("Captured owner and form replay preserve form state and populated status")

    emit(
        graph,
        owned,
        s.OwnershipClass(
            owners=[
                s.OwnerClass(owner=OWNER, type="DATAOWNER"),
                s.OwnerClass(owner=OWNER_GROUP, type="DATAOWNER"),
            ]
        ),
    )
    message, _ = observe(owned, "ownership")
    acknowledged(message)
    assert forms(owned) == before
    record("Additional group owner does not duplicate or reset the form")

    mutation(
        graph,
        "batchAssignForm",
        "BatchAssignFormInput",
        {"formUrn": MINIMUM, "entityUrns": [TABLE]},
    )
    message, _ = observe(TABLE, "forms")
    acknowledged(message)
    wait_for(
        "Manual form status", lambda: property_values(TABLE) == ["Awaiting population"]
    )
    assert property_values(TABLE, PROPERTY) == ["Internal"]
    record(
        "Manual form assignment initializes status and preserves unrelated properties"
    )

    mutation(
        graph,
        "batchRemoveForm",
        "BatchRemoveFormInput",
        {"formUrn": MINIMUM, "entityUrns": [TABLE]},
    )
    set_status(TABLE, ["Completed"])
    mutation(
        graph,
        "batchAssignForm",
        "BatchAssignFormInput",
        {"formUrn": MINIMUM, "entityUrns": [TABLE]},
    )
    wait_for("Manual reattachment", lambda: has_form(TABLE, MINIMUM))
    for _ in range(2):
        message, _ = observe(TABLE, "forms")
        acknowledged(message)
    assert property_values(TABLE) == ["Completed"]
    record("Reattachment preserves an existing status value")

    stop()
    set_status(owned, [])
    replay(form_events[owned])
    assert property_values(owned) == ["Awaiting population"]
    record("Explicit empty property assignment is initialized")

    blank_property = POPULATION + ".blank"
    definition = copy.deepcopy(
        graph.get_aspect(POPULATION, s.StructuredPropertyDefinitionClass)
    )
    definition.qualifiedName = blank_property.removeprefix("urn:li:structuredProperty:")
    definition.allowedValues = None
    emit(graph, blank_property, definition)
    blank_action = FormAssignmentAction.create(
        {"form_to_property": {MINIMUM: blank_property}},
        PipelineContext("blank-value", AcrylDataHubGraph(graph)),
    )
    for values in ([""], ["   "]):
        set_status(owned, values, blank_property)
        replay(form_events[owned], blank_action)
        assert property_values(owned, blank_property) == ["Awaiting population"]
    record("Blank strings in an unrestricted status property are initialized")

    set_status(owned, None)
    previous = graph.get_aspect(owned, s.FormsClass)
    completed = copy.deepcopy(previous)
    completed.completedForms = [
        f for f in completed.incompleteForms if f.urn == MINIMUM
    ]
    completed.incompleteForms = [
        f for f in completed.incompleteForms if f.urn != MINIMUM
    ]
    emit(graph, owned, completed)
    start()
    message, _ = observe(owned, "forms")
    acknowledged(message)
    wait_for("Form completed", lambda: has_form(owned, MINIMUM, complete=True))
    stop()
    assert property_values(owned) == []
    record("Form completion does not initialize or reset status")

    mutation(
        graph,
        "batchRemoveForm",
        "BatchRemoveFormInput",
        {"formUrn": MINIMUM, "entityUrns": [owned]},
    )
    emit(graph, owned, s.OwnershipClass(owners=[]))
    replay(owner_events[owned])
    replay(form_events[owned])
    assert not has_form(owned, MINIMUM)
    assert property_values(owned) == []
    record("Stale owner and form events are skipped after removal")

    set_status(TABLE, ["Completed"])
    before = copy.deepcopy(forms(TABLE))
    start()
    emit(
        graph,
        TABLE,
        s.OwnershipClass(owners=[s.OwnerClass(owner=OWNER, type="DATAOWNER")]),
    )
    message, _ = observe(TABLE, "ownership")
    acknowledged(message)
    assert forms(TABLE) == before
    assert property_values(TABLE) == ["Completed"]
    record("Worker restart preserves assigned forms and populated status")

finally:
    stop()
    observer.close()
    graph.close()
    (RUN / "results.json").write_text(
        json.dumps(
            {
                "run": ID,
                "entity": TABLE,
                "tag": TAG,
                "form": FORM,
                "results": results,
            },
            indent=2,
        )
    )
    print("Evidence: " + str(RUN), flush=True)
