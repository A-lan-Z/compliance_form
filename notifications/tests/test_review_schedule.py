from datetime import date
from pathlib import Path
import tempfile
import unittest

from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.recipients import StaticBusinessContactRecipientResolver
from dcl_notifications.review_schedule import (
    JsonReviewSchedule,
    ReviewReminderWorker,
    ScheduledReview,
)


FORM_URN = "urn:li:form:compliance"
ENTITY_URN = "urn:li:container:test"


class JsonReviewScheduleTest(unittest.TestCase):
    def test_schedule_is_persisted_and_a_new_date_replaces_the_old_date(self):
        with tempfile.TemporaryDirectory() as directory:
            schedule = JsonReviewSchedule(Path(directory) / "schedule.json")

            schedule.schedule(ScheduledReview(ENTITY_URN, FORM_URN, date(2026, 9, 8)))
            schedule.schedule(ScheduledReview(ENTITY_URN, FORM_URN, date(2027, 9, 8)))

            self.assertEqual(
                (ScheduledReview(ENTITY_URN, FORM_URN, date(2027, 9, 8)),),
                schedule.read(),
            )

    def test_worker_resolves_current_contacts_and_writes_one_due_email(self):
        with tempfile.TemporaryDirectory() as directory:
            schedule = JsonReviewSchedule(Path(directory) / "schedule.json")
            schedule.schedule(ScheduledReview(ENTITY_URN, FORM_URN, date(2026, 9, 8)))
            worker = ReviewReminderWorker(
                schedule=schedule,
                recipients=StaticBusinessContactRecipientResolver(
                    {ENTITY_URN: ("bcp@example.test",)}
                ),
                dsg_emails=("dsg@example.test",),
                outbox=DirectoryEmailOutbox(
                    Path(directory) / "outbox", "sender@example.test"
                ),
                poll_seconds=60,
            )

            first = worker.run_once(date(2026, 8, 25))
            replay = worker.run_once(date(2026, 8, 25))

            self.assertEqual((1, 1), first)
            self.assertEqual((1, 0), replay)
            message = next((Path(directory) / "outbox").glob("*.eml")).read_text()
            self.assertIn("To: bcp@example.test, dsg@example.test", message)
            self.assertIn("X-DCL-Notification-Kind: review-due-soon", message)


if __name__ == "__main__":
    unittest.main()
