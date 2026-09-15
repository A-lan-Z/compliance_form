import argparse
import json
from urllib.parse import urlparse
from uuid import uuid4

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig
from datahub.metadata import schema_classes as s
from datahub.metadata.urns import DatasetUrn

from dcl_form_assignment.entities import FORM_ENTITY_TYPES


MINIMUM_FORM = "urn:li:form:dcl.poc.minimum-metadata.v1"
STATUS_PROPERTY = "urn:li:structuredProperty:dcl.poc.population-status"

TAG = "urn:li:tag:dcl.poc.requires-compliance"
FORM = "urn:li:form:dcl.poc.table-compliance.v1"
PROPERTY = "urn:li:structuredProperty:dcl.poc.table-classification"


def mutation(graph, name, input_type, values, selection=""):
    result = graph.execute_graphql(
        "mutation($input: "
        + input_type
        + "!) { "
        + name
        + "(input: $input) "
        + selection
        + " }",
        {"input": values},
    )[name]
    if not result:
        raise RuntimeError(f"{name} returned no success")
    return result


def emit(graph, entity, aspect):
    graph.emit_mcp(MetadataChangeProposalWrapper(entityUrn=entity, aspect=aspect))


def seed_definitions(graph, tag=TAG, form=FORM, prop=PROPERTY):
    if graph.get_aspect(tag, s.TagPropertiesClass) is None:
        emit(
            graph,
            tag,
            s.TagPropertiesClass(
                name=tag.removeprefix("urn:li:tag:"),
                description="Synthetic POC: this table requires a compliance form.",
            ),
        )
    if graph.get_aspect(prop, s.StructuredPropertyDefinitionClass) is None:
        mutation(
            graph,
            "createStructuredProperty",
            "CreateStructuredPropertyInput",
            {
                "id": prop.removeprefix("urn:li:structuredProperty:"),
                "qualifiedName": prop.removeprefix("urn:li:structuredProperty:"),
                "displayName": "POC information classification",
                "description": "Synthetic local POC property.",
                "valueType": "urn:li:dataType:datahub.string",
                "cardinality": "SINGLE",
                "entityTypes": ["urn:li:entityType:datahub.dataset"],
                "allowedValues": [
                    {"stringValue": "Internal"},
                    {"stringValue": "Confidential"},
                ],
            },
            "{ urn }",
        )
    if graph.get_aspect(form, s.FormInfoClass) is None:
        mutation(
            graph,
            "createForm",
            "CreateFormInput",
            {
                "id": form.removeprefix("urn:li:form:"),
                "type": "COMPLETION",
                "name": "POC table compliance",
                "description": "Synthetic local form for the tag-to-form assignment POC.",
                "actors": {"owners": True},
                "prompts": [
                    {
                        "id": form + ".classification",
                        "title": "Classify this table",
                        "type": "STRUCTURED_PROPERTY",
                        "required": True,
                        "structuredPropertyParams": {"urn": prop},
                    }
                ],
            },
            "{ urn }",
        )


def seed_automation_definitions(graph, form=MINIMUM_FORM, prop=STATUS_PROPERTY):
    if graph.get_aspect(prop, s.StructuredPropertyDefinitionClass) is None:
        mutation(
            graph,
            "createStructuredProperty",
            "CreateStructuredPropertyInput",
            {
                "id": prop.removeprefix("urn:li:structuredProperty:"),
                "qualifiedName": prop.removeprefix("urn:li:structuredProperty:"),
                "displayName": "Population status",
                "valueType": "urn:li:dataType:datahub.string",
                "cardinality": "SINGLE",
                "entityTypes": [
                    "urn:li:entityType:datahub." + name
                    for name in sorted(FORM_ENTITY_TYPES)
                ],
                "allowedValues": [
                    {"stringValue": "Awaiting population"},
                    {"stringValue": "Completed"},
                ],
            },
            "{ urn }",
        )
    description_property = prop + ".description"
    if (
        graph.get_aspect(description_property, s.StructuredPropertyDefinitionClass)
        is None
    ):
        mutation(
            graph,
            "createStructuredProperty",
            "CreateStructuredPropertyInput",
            {
                "id": description_property.removeprefix("urn:li:structuredProperty:"),
                "qualifiedName": description_property.removeprefix(
                    "urn:li:structuredProperty:"
                ),
                "displayName": "Metadata description",
                "valueType": "urn:li:dataType:datahub.string",
                "cardinality": "SINGLE",
                "entityTypes": [
                    "urn:li:entityType:datahub." + name
                    for name in sorted(FORM_ENTITY_TYPES)
                ],
            },
            "{ urn }",
        )
    if graph.get_aspect(form, s.FormInfoClass) is None:
        mutation(
            graph,
            "createForm",
            "CreateFormInput",
            {
                "id": form.removeprefix("urn:li:form:"),
                "name": "Minimum Metadata",
                "description": "Local demonstration form.",
                "type": "COMPLETION",
                "actors": {"owners": True},
                "prompts": [
                    {
                        "id": form + ".description",
                        "title": "Provide a description",
                        "type": "STRUCTURED_PROPERTY",
                        "structuredPropertyParams": {"urn": description_property},
                        "required": True,
                    }
                ],
            },
            "{ urn }",
        )


def seed_table(graph, entity, subtype="Table"):
    emit(
        graph,
        entity,
        s.DatasetPropertiesClass(
            name="POC customer table",
            description="Synthetic metadata only; no real data is ingested.",
        ),
    )
    emit(graph, entity, s.SubTypesClass(typeNames=[subtype]))
    emit(graph, entity, s.StatusClass(removed=False))


def main():
    parser = argparse.ArgumentParser(description="Local tag-to-form demo.")
    parser.add_argument("command", choices=["setup", "tag", "status"])
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    parser.add_argument("--entity")
    args = parser.parse_args()
    if urlparse(args.server).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("The synthetic demo is restricted to a local DataHub server")
    if args.command != "setup" and not args.entity:
        parser.error("--entity is required for tag and status")
    entity = args.entity or str(
        DatasetUrn("postgres", "dcl.poc.table." + uuid4().hex, "DEV")
    )
    urn = DatasetUrn.from_string(entity)
    if not urn.name.startswith("dcl.poc.table."):
        parser.error("Use a synthetic dcl.poc.table.* dataset")
    graph = DataHubGraph(DatahubClientConfig(server=args.server))
    try:
        if args.command == "setup":
            seed_definitions(graph)
            seed_automation_definitions(graph)
            seed_table(graph, entity)
            print(json.dumps({"entity": entity, "tag": TAG, "form": FORM}, indent=2))
        elif args.command == "tag":
            mutation(
                graph,
                "addTag",
                "TagAssociationInput",
                {"tagUrn": TAG, "resourceUrn": entity},
            )
            print("Tag added. The running Action will assign the form.")
        else:
            forms = graph.get_aspect(entity, s.FormsClass)
            print(json.dumps(forms.to_obj() if forms else {}, indent=2))
    finally:
        graph.close()


if __name__ == "__main__":
    main()
