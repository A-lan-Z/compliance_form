from dataclasses import dataclass
from datetime import date, timedelta
from collections.abc import Iterable

from dcl_notifications.model import EmailNotification


@dataclass(frozen=True)
class ReviewRecord:
    entity_urn: str
    form_urn: str
    review_date: date
    business_contact_emails: tuple[str, ...]


def evaluate_review_reminders(
    record: ReviewRecord,
    as_of: date,
    dsg_emails: Iterable[str],
) -> tuple[EmailNotification, ...]:
    recipients = tuple(sorted({*record.business_contact_emails, *dsg_emails}))
    if not recipients:
        return ()

    if record.review_date == as_of + timedelta(days=14):
        kind = "review-due-soon"
        subject = "Compliance review due in two weeks"
        introduction = "The compliance review date is fourteen days away."
    elif record.review_date == as_of - timedelta(days=14):
        kind = "review-overdue"
        subject = "Compliance review date passed two weeks ago"
        introduction = (
            "The current compliance review date passed fourteen days ago and has not "
            "been advanced."
        )
    else:
        return ()

    return (
        EmailNotification(
            idempotency_key=(
                f"{kind}:{record.entity_urn}:{record.form_urn}:"
                f"{record.review_date.isoformat()}"
            ),
            kind=kind,
            entity_urn=record.entity_urn,
            form_urn=record.form_urn,
            recipients=recipients,
            subject=subject,
            body=(
                f"{introduction}\n\n"
                f"Entity: {record.entity_urn}\n"
                f"Form: {record.form_urn}\n"
                f"Review Date: {record.review_date.isoformat()}\n"
            ),
        ),
    )
