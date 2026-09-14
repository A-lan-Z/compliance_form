import json
import logging

from datahub.metadata.urns import FormUrn, TagUrn
from datahub.utilities.urns.error import InvalidUrnError
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from pydantic import BaseModel, ConfigDict, Field, field_validator

from dcl_form_assignment.datahub import DataHubAssignments
from dcl_form_assignment.events import added_table_tags
from dcl_form_assignment.service import AssignmentService


logger = logging.getLogger(__name__)


class AssignmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tag_to_form: dict[str, str] = Field(min_length=1)

    @field_validator("tag_to_form")
    @classmethod
    def validate_urns(cls, mapping):
        try:
            for tag, form in mapping.items():
                TagUrn.from_string(tag)
                FormUrn.from_string(form)
        except InvalidUrnError as error:
            raise ValueError(str(error)) from error
        return mapping


class TagFormAssignmentAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext):
        config = AssignmentConfig.model_validate(config_dict)
        if ctx.graph is None:
            raise ValueError("The Action requires a DataHub connection")
        datahub = DataHubAssignments(ctx.graph.graph)
        datahub.validate_mapping(config.tag_to_form)
        return cls(AssignmentService(config.tag_to_form, datahub))

    def __init__(self, service: AssignmentService):
        self.service = service

    def act(self, event: EventEnvelope) -> None:
        if event.event_type != "MetadataChangeLogEvent_v1":
            return
        for addition in added_table_tags(json.loads(event.event.as_json())):
            outcome = self.service.handle(addition)
            logger.info(
                "Tag-to-form outcome=%s entity=%s tag=%s",
                outcome,
                addition.entity_urn,
                addition.tag_urn,
            )

    def close(self) -> None:
        pass
