from dcl_form_assignment.datahub import DataHubAssignments
from dcl_form_assignment.events import FormAddition, OwnerAddition, TagAddition


class AssignmentService:
    def __init__(
        self,
        mapping: dict[str, str],
        datahub: DataHubAssignments,
        minimum_metadata_form: str | None = None,
        form_to_property: dict[str, str] | None = None,
    ):
        self.mapping = mapping
        self.datahub = datahub
        self.minimum_metadata_form = minimum_metadata_form
        self.form_to_property = form_to_property or {}

    def handle(self, addition: TagAddition) -> str:
        form = self.mapping.get(addition.tag_urn)
        if form is None:
            return "unmapped-tag"
        if not self.datahub.is_table(addition.entity_urn):
            return "not-table"
        if not self.datahub.has_tag(addition.entity_urn, addition.tag_urn):
            return "tag-absent"
        return self.assign_missing(addition.entity_urn, form)

    def assign_missing(self, entity: str, form: str) -> str:
        if self.datahub.has_form(entity, form):
            return "already-assigned"
        self.datahub.assign(entity, form)
        return "assigned"

    def handle_owner(self, addition: OwnerAddition) -> str:
        if self.minimum_metadata_form is None:
            return "disabled"
        if not self.datahub.is_active(addition.entity_urn):
            return "inactive"
        if not self.datahub.has_owner(addition.entity_urn, addition.owner_urns):
            return "owner-absent"
        return self.assign_missing(addition.entity_urn, self.minimum_metadata_form)

    def handle_form(self, addition: FormAddition) -> str:
        prop = self.form_to_property.get(addition.form_urn)
        if prop is None:
            return "unmapped-form"
        if not self.datahub.is_active(addition.entity_urn):
            return "inactive"
        if not self.datahub.has_form(addition.entity_urn, addition.form_urn):
            return "form-absent"
        return self.datahub.initialize_property(addition.entity_urn, prop)
