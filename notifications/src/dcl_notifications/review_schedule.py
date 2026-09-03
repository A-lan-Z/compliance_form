from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from threading import Event, Thread

from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.reminders import ReviewRecord, evaluate_review_reminders


@dataclass(frozen=True)
class ScheduledReview:
    entity_urn: str
    form_urn: str
    review_date: date


class JsonReviewSchedule:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def schedule(self, review: ScheduledReview) -> None:
        reviews = [
            existing
            for existing in self.read()
            if (existing.entity_urn, existing.form_urn)
            != (review.entity_urn, review.form_urn)
        ]
        reviews.append(review)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                [
                    {
                        "entityUrn": scheduled.entity_urn,
                        "formUrn": scheduled.form_urn,
                        "reviewDate": scheduled.review_date.isoformat(),
                    }
                    for scheduled in reviews
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def read(self) -> tuple[ScheduledReview, ...]:
        if not self._path.exists():
            return ()
        values = json.loads(self._path.read_text(encoding="utf-8"))
        return tuple(
            ScheduledReview(
                value["entityUrn"],
                value["formUrn"],
                date.fromisoformat(value["reviewDate"]),
            )
            for value in values
        )


class ReviewReminderWorker:
    def __init__(
        self,
        schedule: JsonReviewSchedule,
        recipients: Callable[[str], tuple[str, ...]],
        dsg_emails: Sequence[str],
        outbox: DirectoryEmailOutbox,
        poll_seconds: float,
    ) -> None:
        self._schedule = schedule
        self._recipients = recipients
        self._dsg_emails = tuple(dsg_emails)
        self._outbox = outbox
        self._poll_seconds = poll_seconds
        self._stopped = Event()
        self._thread = Thread(
            target=self._run,
            name="dcl-review-reminders",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._stopped.set()
        self._thread.join()

    def run_once(self, as_of: date) -> tuple[int, int]:
        due = 0
        created = 0
        for scheduled in self._schedule.read():
            record = ReviewRecord(
                entity_urn=scheduled.entity_urn,
                form_urn=scheduled.form_urn,
                review_date=scheduled.review_date,
                business_contact_emails=self._recipients(scheduled.entity_urn),
            )
            for notification in evaluate_review_reminders(
                record, as_of, self._dsg_emails
            ):
                due += 1
                if self._outbox.deliver(notification):
                    created += 1
        return due, created

    def _run(self) -> None:
        while not self._stopped.is_set():
            self.run_once(date.today())
            self._stopped.wait(self._poll_seconds)
