import argparse
import json
from datetime import date
from pathlib import Path

from dcl_notifications.assignment_service import FormAssignmentNotificationService
from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.recipients import StaticBusinessContactRecipientResolver
from dcl_notifications.review_schedule import (
    JsonReviewSchedule,
    ReviewReminderWorker,
    ScheduledReview,
)


FORM_URN = "urn:li:form:dcl.tour.native.privacy-attestation.v1"
ENTITY_URN = "urn:li:container:328308bacafdd7dac732214f6e3eaf8b0618d00f"


def _assignment_event() -> dict:
    return {
        "entityType": "container",
        "entityUrn": ENTITY_URN,
        "changeType": "UPSERT",
        "aspectName": "forms",
        "aspect": {
            "contentType": "application/json",
            "value": json.dumps(
                {
                    "incompleteForms": [{"urn": FORM_URN}],
                    "completedForms": [],
                    "verifications": [],
                }
            ),
        },
        "previousAspectValue": {
            "contentType": "application/json",
            "value": json.dumps(
                {
                    "incompleteForms": [],
                    "completedForms": [],
                    "verifications": [],
                }
            ),
        },
        "created": {"time": 1787590800000, "actor": "urn:li:corpuser:datahub"},
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the DCL notification POC")
    parser.add_argument("--work-directory", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    outbox = DirectoryEmailOutbox(
        args.work_directory / "outbox", "compliance@example.test"
    )
    recipients = StaticBusinessContactRecipientResolver(
        {ENTITY_URN: ("bcp.assignment@example.test",)}
    )
    assignment_service = FormAssignmentNotificationService(
        {FORM_URN}, recipients, outbox
    )
    assignment_deliveries = assignment_service.handle(_assignment_event())

    schedule = JsonReviewSchedule(args.work_directory / "review-schedule.json")
    worker = ReviewReminderWorker(
        schedule=schedule,
        recipients=recipients,
        dsg_emails=("dsg@example.test",),
        outbox=outbox,
        poll_seconds=60,
    )
    schedule.schedule(ScheduledReview(ENTITY_URN, FORM_URN, date(2026, 9, 8)))
    due_soon, created_soon = worker.run_once(date(2026, 8, 25))
    schedule.schedule(ScheduledReview(ENTITY_URN, FORM_URN, date(2026, 8, 11)))
    overdue, created_overdue = worker.run_once(date(2026, 8, 25))

    assignment_created = sum(assignment_deliveries)
    total_due = len(assignment_deliveries) + due_soon + overdue
    total_created = assignment_created + created_soon + created_overdue
    print(
        f"due={total_due} created={total_created} "
        f"duplicates={total_due - total_created} "
        f"work_directory={args.work_directory}"
    )


if __name__ == "__main__":
    main()
