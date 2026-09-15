import json
import logging

from datahub.metadata.urns import FormUrn, StructuredPropertyUrn, TagUrn
from datahub.utilities.urns.error import InvalidUrnError
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from pydantic import BaseModel, ConfigDict, Field, model_validator

from dcl_form_assignment.datahub import DataHubAssignments
from dcl_form_assignment.events import added_forms, added_owners, added_table_tags
from dcl_form_assignment.service import AssignmentService


logger = logging.getLogger(__name__)


class AssignmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tag_to_form: dict[str, str] = Field(default_factory=dict)
    minimum_metadata_form: str | None = None
    form_to_property: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rules(self):
        if not (
            self.tag_to_form or self.minimum_metadata_form or self.form_to_property
        ):
            raise ValueError("Configure at least one assignment or property rule")
        try:
            for tag, form in self.tag_to_form.items():
                TagUrn.from_string(tag)
                FormUrn.from_string(form)
            if self.minimum_metadata_form is not None:
                FormUrn.from_string(self.minimum_metadata_form)
            for form, prop in self.form_to_property.items():
                FormUrn.from_string(form)
                StructuredPropertyUrn.from_string(prop)
        except InvalidUrnError as error:
            raise ValueError(str(error)) from error
        return self


class FormAssignmentAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext):
        config = AssignmentConfig.model_validate(config_dict)
        if ctx.graph is None:
            raise ValueError("The Action requires a DataHub connection")
        datahub = DataHubAssignments(ctx.graph.graph)
        datahub.validate_mapping(config.tag_to_form)
        forms = set(config.form_to_property)
        if config.minimum_metadata_form:
            forms.add(config.minimum_metadata_form)
        datahub.validate_forms(forms)
        datahub.validate_properties(set(config.form_to_property.values()))
        return cls(
            AssignmentService(
                config.tag_to_form,
                datahub,
                config.minimum_metadata_form,
                config.form_to_property,
            )
        )

    def __init__(self, service: AssignmentService):
        self.service = service

    def act(self, event: EventEnvelope) -> None:
        if event.event_type != "MetadataChangeLogEvent_v1":
            return
        value = json.loads(event.event.as_json())
        aspect = value.get("aspectName")
        if aspect == "globalTags" and self.service.mapping:
            for addition in added_table_tags(value):
                logger.info(
                    "Tag assignment outcome=%s entity=%s",
                    self.service.handle(addition),
                    addition.entity_urn,
                )
        elif aspect == "ownership" and self.service.minimum_metadata_form:
            addition = added_owners(value)
            if addition:
                logger.info(
                    "Owner assignment outcome=%s entity=%s",
                    self.service.handle_owner(addition),
                    addition.entity_urn,
                )
        elif aspect == "forms" and self.service.form_to_property:
            for addition in added_forms(value):
                logger.info(
                    "Property initialization outcome=%s entity=%s",
                    self.service.handle_form(addition),
                    addition.entity_urn,
                )

    def close(self) -> None:
        pass
