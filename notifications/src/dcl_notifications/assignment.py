import json
from dataclasses import dataclass


@dataclass(frozen=True)
class FormAssignment:
    entity_urn: str
    form_urn: str
    occurred_at_ms: int


def _assigned_form_urns(generic_aspect: dict | None) -> set[str]:
    if generic_aspect is None:
        return set()
    forms = json.loads(generic_aspect["value"])
    return {
        association["urn"]
        for name in ("incompleteForms", "completedForms")
        for association in forms.get(name, [])
    }


def detect_form_assignments(event: dict) -> tuple[FormAssignment, ...]:
    if event.get("changeType") != "UPSERT" or event.get("aspectName") != "forms":
        return ()

    current = _assigned_form_urns(event["aspect"])
    previous = _assigned_form_urns(event.get("previousAspectValue"))

    return tuple(
        FormAssignment(event["entityUrn"], form_urn, event["created"]["time"])
        for form_urn in sorted(current - previous)
    )
