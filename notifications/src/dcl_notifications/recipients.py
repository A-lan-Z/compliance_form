from dataclasses import dataclass


@dataclass(frozen=True)
class StaticBusinessContactRecipientResolver:
    recipients_by_entity: dict[str, tuple[str, ...]]

    def __call__(self, entity_urn: str) -> tuple[str, ...]:
        return self.recipients_by_entity.get(entity_urn, ())


class DataHubOwnershipRecipientResolver:
    def __init__(
        self,
        graph: object,
        ownership_type_urn: str,
        principal_emails: dict[str, str],
    ) -> None:
        self._graph = graph
        self._ownership_type_urn = ownership_type_urn
        self._principal_emails = principal_emails

    def __call__(self, entity_urn: str) -> tuple[str, ...]:
        ownership = self._graph.get_untyped_aspect(
            entity_urn,
            "ownership",
            "com.linkedin.common.Ownership",
        )
        if ownership is None:
            return ()
        return tuple(
            sorted(
                {
                    self._principal_emails[owner["owner"]]
                    for owner in ownership["owners"]
                    if owner["typeUrn"] == self._ownership_type_urn
                    and owner["owner"] in self._principal_emails
                }
            )
        )
