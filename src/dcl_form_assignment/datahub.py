import json

from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.schema_classes import (
    FormInfoClass,
    FormsClass,
    GlobalTagsClass,
    GenericAspectClass,
    MetadataChangeProposalClass,
    OwnershipClass,
    StructuredPropertiesClass,
    StructuredPropertyDefinitionClass,
    StructuredPropertyValueAssignmentClass,
    StatusClass,
    SubTypesClass,
    TagPropertiesClass,
)


from dcl_form_assignment.entities import entity_type


AWAITING_POPULATION = "Awaiting population"

_ASSIGN = """
mutation AssignComplianceForm($input: BatchAssignFormInput!) {
  batchAssignForm(input: $input)
}
"""


class DataHubAssignments:
    def __init__(self, graph: DataHubGraph):
        self.graph = graph
        self.property_types: dict[str, set[str]] = {}

    def validate_mapping(self, mapping: dict[str, str]) -> None:
        for tag in mapping:
            if self.graph.get_aspect(tag, TagPropertiesClass) is None:
                raise ValueError(f"Configured tag does not exist: {tag}")
        self.validate_forms(set(mapping.values()))

    def validate_forms(self, forms: set[str]) -> None:
        for form in forms:
            if self.graph.get_aspect(form, FormInfoClass) is None:
                raise ValueError(f"Configured form does not exist: {form}")

    def validate_properties(self, properties: set[str]) -> None:
        for prop in properties:
            definition = self.graph.get_aspect(prop, StructuredPropertyDefinitionClass)
            if definition is None:
                raise ValueError(
                    f"Configured structured property does not exist: {prop}"
                )
            if definition.valueType != "urn:li:dataType:datahub.string":
                raise ValueError(f"Status property must have string values: {prop}")
            if definition.allowedValues is not None and AWAITING_POPULATION not in {
                item.value for item in definition.allowedValues
            }:
                raise ValueError(
                    f"Status property must allow {AWAITING_POPULATION}: {prop}"
                )
            self.property_types[prop] = set(definition.entityTypes)

    def is_active(self, entity: str) -> bool:
        if not self.graph.exists(entity):
            return False
        if entity_type(entity) == "domain":
            return True
        status = self.graph.get_aspect(entity, StatusClass)
        return not (status and status.removed)

    def has_owner(self, entity: str, owners: frozenset[str]) -> bool:
        ownership = self.graph.get_aspect(entity, OwnershipClass)
        return bool(
            ownership and any(item.owner in owners for item in ownership.owners)
        )

    def is_table(self, entity: str) -> bool:
        if not self.is_active(entity):
            return False
        subtypes = self.graph.get_aspect(entity, SubTypesClass)
        return bool(subtypes and subtypes.typeNames == ["Table"])

    def has_tag(self, entity: str, tag: str) -> bool:
        tags = self.graph.get_aspect(entity, GlobalTagsClass)
        return bool(tags and any(item.tag == tag for item in tags.tags))

    def has_form(self, entity: str, form: str) -> bool:
        forms = self.graph.get_aspect(entity, FormsClass)
        return bool(
            forms
            and any(
                item.urn == form
                for item in (*forms.incompleteForms, *forms.completedForms)
            )
        )

    def assign(self, entity: str, form: str) -> None:
        result = self.graph.execute_graphql(
            _ASSIGN, {"input": {"formUrn": form, "entityUrns": [entity]}}
        )
        if result.get("batchAssignForm") is not True:
            raise RuntimeError("DataHub did not accept the form assignment")
        if not self.has_form(entity, form):
            raise RuntimeError("DataHub assignment was not present on read-back")

    def initialize_property(self, entity: str, prop: str) -> str:
        if (
            "urn:li:entityType:datahub." + entity_type(entity)
            not in self.property_types[prop]
        ):
            raise ValueError(
                f"Structured property is not enabled for this entity type: {prop}"
            )
        current = self.graph.get_aspect(entity, StructuredPropertiesClass)
        assignments = current.properties if current else []
        if any(
            item.propertyUrn == prop
            and any(
                not isinstance(value, str) or value.strip() for value in item.values
            )
            for item in assignments
        ):
            return "already-populated"
        path = "/properties/" + prop.replace("~", "~0").replace("/", "~1")
        patch = [
            {
                "op": "add",
                "path": path,
                "value": StructuredPropertyValueAssignmentClass(
                    propertyUrn=prop, values=[AWAITING_POPULATION]
                ).to_obj(),
            }
        ]
        self.graph.emit_mcp(
            MetadataChangeProposalClass(
                entityType=entity_type(entity),
                entityUrn=entity,
                aspectName="structuredProperties",
                changeType="PATCH",
                aspect=GenericAspectClass(
                    value=json.dumps(patch).encode(), contentType="application/json"
                ),
            ),
            async_flag=False,
        )
        updated = self.graph.get_aspect(entity, StructuredPropertiesClass)
        if not updated or not any(
            item.propertyUrn == prop
            and any(
                not isinstance(value, str) or value.strip() for value in item.values
            )
            for item in updated.properties
        ):
            raise RuntimeError(
                "Structured property initialization was not present on read-back"
            )
        return "initialized"
