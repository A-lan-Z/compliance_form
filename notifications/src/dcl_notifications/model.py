from dataclasses import dataclass


@dataclass(frozen=True)
class EmailNotification:
    idempotency_key: str
    kind: str
    entity_urn: str
    form_urn: str
    recipients: tuple[str, ...]
    subject: str
    body: str
