import json
import logging
from datetime import date

from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext

from dcl_notifications.assignment import detect_form_assignments
from dcl_notifications.assignment_service import FormAssignmentNotificationService
from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.recipients import DataHubOwnershipRecipientResolver
from dcl_notifications.review_schedule import (
    JsonReviewSchedule,
    ReviewReminderWorker,
    ScheduledReview,
)


logger = logging.getLogger(__name__)


class ComplianceFormAssignmentAction(Action):
    @classmethod
    def create(
        cls, config_dict: dict, ctx: PipelineContext
    ) -> "ComplianceFormAssignmentAction":
        review_dates = {
            form["urn"]: date.fromisoformat(form["review_date"])
            for form in config_dict["forms"]
        }
        recipients = DataHubOwnershipRecipientResolver(
            graph=ctx.graph,
            ownership_type_urn=config_dict["business_contact_ownership_type_urn"],
            principal_emails=config_dict["principal_emails"],
        )
        outbox = DirectoryEmailOutbox(
            config_dict["outbox_directory"],
            config_dict["sender"],
        )
        service = FormAssignmentNotificationService(
            set(review_dates), recipients, outbox
        )
        schedule = JsonReviewSchedule(config_dict["review_schedule_path"])
        reminder_worker = ReviewReminderWorker(
            schedule=schedule,
            recipients=recipients,
            dsg_emails=config_dict["dsg_emails"],
            outbox=outbox,
            poll_seconds=float(config_dict["review_poll_seconds"]),
        )
        action = cls(service, review_dates, schedule, reminder_worker)
        reminder_worker.start()
        return action

    def __init__(
        self,
        service: FormAssignmentNotificationService,
        review_dates: dict[str, date],
        schedule: JsonReviewSchedule,
        reminder_worker: ReviewReminderWorker,
    ) -> None:
        self._service = service
        self._review_dates = review_dates
        self._schedule = schedule
        self._reminder_worker = reminder_worker

    def act(self, event: EventEnvelope) -> None:
        event_value = json.loads(event.event.as_json())
        assignments = detect_form_assignments(event_value)
        deliveries = self._service.handle_assignments(assignments)
        for assignment in assignments:
            review_date = self._review_dates.get(assignment.form_urn)
            if review_date is None:
                continue
            self._schedule.schedule(
                ScheduledReview(
                    entity_urn=assignment.entity_urn,
                    form_urn=assignment.form_urn,
                    review_date=review_date,
                )
            )

        if assignments:
            logger.info(
                "Processed compliance Form assignment: detected=%d emails=%d scheduled=%d",
                len(assignments),
                sum(deliveries),
                len(assignments),
            )

    def close(self) -> None:
        self._reminder_worker.close()
