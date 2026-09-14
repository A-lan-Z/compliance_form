from dcl_form_assignment.datahub import DataHubAssignments
from dcl_form_assignment.events import TagAddition


class AssignmentService:
    def __init__(self, mapping: dict[str, str], datahub: DataHubAssignments):
        self.mapping = mapping
        self.datahub = datahub

    def handle(self, addition: TagAddition) -> str:
        form = self.mapping.get(addition.tag_urn)
        if form is None:
            return "unmapped-tag"
        if not self.datahub.is_table(addition.entity_urn):
            return "not-table"
        if not self.datahub.has_tag(addition.entity_urn, addition.tag_urn):
            return "tag-absent"
        if self.datahub.has_form(addition.entity_urn, form):
            return "already-assigned"
        self.datahub.assign(addition.entity_urn, form)
        return "assigned"
