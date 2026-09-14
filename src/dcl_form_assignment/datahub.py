from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.schema_classes import (
    FormInfoClass,
    FormsClass,
    GlobalTagsClass,
    StatusClass,
    SubTypesClass,
    TagPropertiesClass,
)


_ASSIGN = """
mutation AssignComplianceForm($input: BatchAssignFormInput!) {
  batchAssignForm(input: $input)
}
"""


class DataHubAssignments:
    def __init__(self, graph: DataHubGraph):
        self.graph = graph

    def validate_mapping(self, mapping: dict[str, str]) -> None:
        for tag in mapping:
            if self.graph.get_aspect(tag, TagPropertiesClass) is None:
                raise ValueError(f"Configured tag does not exist: {tag}")
        for form in set(mapping.values()):
            if self.graph.get_aspect(form, FormInfoClass) is None:
                raise ValueError(f"Configured form does not exist: {form}")

    def is_table(self, entity: str) -> bool:
        status = self.graph.get_aspect(entity, StatusClass)
        if status and status.removed:
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
        # Some server paths can skip an assignment yet return true.
        if not self.has_form(entity, form):
            raise RuntimeError("DataHub assignment was not present on read-back")
