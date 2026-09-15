import json
from dataclasses import dataclass

from datahub.metadata.urns import FormUrn, TagUrn, Urn

from dcl_form_assignment.entities import (
    FORM_ENTITY_TYPES,
    OWNER_ENTITY_TYPES,
    entity_type,
)


@dataclass(frozen=True)
class TagAddition:
    entity_urn: str
    tag_urn: str


@dataclass(frozen=True)
class OwnerAddition:
    entity_urn: str
    owner_urns: frozenset[str]


@dataclass(frozen=True)
class FormAddition:
    entity_urn: str
    form_urn: str


def aspect_value(aspect):
    return json.loads(aspect["value"]) if aspect is not None else None


def relevant_entity(event, aspect, types):
    if event.get("aspectName") != aspect or event.get("changeType") not in {
        "UPSERT",
        "CREATE",
    }:
        return None
    entity = event["entityUrn"]
    return entity if entity_type(entity) in types else None


def added_table_tags(event: dict) -> tuple[TagAddition, ...]:
    entity = relevant_entity(event, "globalTags", {"dataset"})
    if entity is None:
        return ()

    def tags(aspect):
        value = aspect_value(aspect)
        result = {item["tag"] for item in value["tags"]} if value is not None else set()
        for tag in result:
            TagUrn.from_string(tag)
        return result

    return tuple(
        TagAddition(entity, tag)
        for tag in sorted(
            tags(event["aspect"]) - tags(event.get("previousAspectValue"))
        )
    )


def added_owners(event: dict) -> OwnerAddition | None:
    entity = relevant_entity(event, "ownership", OWNER_ENTITY_TYPES)
    if entity is None:
        return None

    def owners(aspect):
        value = aspect_value(aspect)
        result = (
            {item["owner"] for item in value["owners"]} if value is not None else set()
        )
        for owner in result:
            if Urn.from_string(owner).entity_type not in {"corpuser", "corpGroup"}:
                raise ValueError("Owner must be a user or group URN")
        return result

    additions = owners(event["aspect"]) - owners(event.get("previousAspectValue"))
    return OwnerAddition(entity, frozenset(additions)) if additions else None


def added_forms(event: dict) -> tuple[FormAddition, ...]:
    entity = relevant_entity(event, "forms", FORM_ENTITY_TYPES)
    if entity is None:
        return ()

    def forms(aspect):
        value = aspect_value(aspect)
        if value is None:
            return set()
        result = {
            item["urn"]
            for item in (*value["incompleteForms"], *value["completedForms"])
        }
        for form in result:
            FormUrn.from_string(form)
        return result

    return tuple(
        FormAddition(entity, form)
        for form in sorted(
            forms(event["aspect"]) - forms(event.get("previousAspectValue"))
        )
    )
