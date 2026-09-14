import json
from dataclasses import dataclass

from datahub.metadata.urns import DatasetUrn, TagUrn


@dataclass(frozen=True)
class TagAddition:
    entity_urn: str
    tag_urn: str


def added_table_tags(event: dict) -> tuple[TagAddition, ...]:
    """Inspect entity tags only; table subtype is checked against current GMS state."""
    if event.get("aspectName") != "globalTags" or event.get("changeType") not in {
        "UPSERT",
        "CREATE",
    }:
        return ()
    entity = event["entityUrn"]
    if not entity.startswith("urn:li:dataset:"):
        return ()
    DatasetUrn.from_string(entity)

    def tags(aspect):
        if aspect is None:
            return set()
        value = json.loads(aspect["value"])
        result = {item["tag"] for item in value["tags"]}
        for tag in result:
            TagUrn.from_string(tag)
        return result

    current = tags(event["aspect"])
    previous = tags(event.get("previousAspectValue"))
    return tuple(TagAddition(entity, tag) for tag in sorted(current - previous))
