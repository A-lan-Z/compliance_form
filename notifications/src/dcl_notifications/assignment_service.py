from collections.abc import Callable, Iterable

from dcl_notifications.assignment import FormAssignment, detect_form_assignments
from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.model import EmailNotification


class FormAssignmentNotificationService:
    def __init__(
        self,
        allowed_form_urns: set[str],
        recipients: Callable[[str], tuple[str, ...]],
        outbox: DirectoryEmailOutbox,
    ) -> None:
        self._allowed_form_urns = allowed_form_urns
        self._recipients = recipients
        self._outbox = outbox

    def handle(self, event: dict) -> tuple[bool, ...]:
        return self.handle_assignments(detect_form_assignments(event))

    def handle_assignments(
        self, assignments: Iterable[FormAssignment]
    ) -> tuple[bool, ...]:
        deliveries = []
        for assignment in assignments:
            if assignment.form_urn not in self._allowed_form_urns:
                continue
            recipients = self._recipients(assignment.entity_urn)
            if not recipients:
                continue
            notification = EmailNotification(
                idempotency_key=(
                    f"form-assigned:{assignment.entity_urn}:{assignment.form_urn}:"
                    f"{assignment.occurred_at_ms}"
                ),
                kind="form-assigned",
                entity_urn=assignment.entity_urn,
                form_urn=assignment.form_urn,
                recipients=recipients,
                subject="Compliance form assigned",
                body=(
                    "A compliance form has been assigned to an entity for which you are "
                    "a current Business Contact.\n\n"
                    f"Entity: {assignment.entity_urn}\n"
                    f"Form: {assignment.form_urn}\n"
                ),
            )
            deliveries.append(self._outbox.deliver(notification))
        return tuple(deliveries)
