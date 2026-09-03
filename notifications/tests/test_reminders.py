from datetime import date
import unittest

from dcl_notifications.reminders import ReviewRecord, evaluate_review_reminders


class ReviewReminderTest(unittest.TestCase):
    def setUp(self):
        self.as_of = date(2026, 8, 25)

    def record(self, review_date):
        return ReviewRecord(
            entity_urn="urn:li:container:test",
            form_urn="urn:li:form:compliance",
            review_date=review_date,
            business_contact_emails=("bcp@example.test",),
        )

    def test_fourteen_days_before_notifies_bcp_and_dsg(self):
        notifications = evaluate_review_reminders(
            self.record(date(2026, 9, 8)), self.as_of, ("dsg@example.test",)
        )

        self.assertEqual("review-due-soon", notifications[0].kind)
        self.assertEqual(
            ("bcp@example.test", "dsg@example.test"),
            notifications[0].recipients,
        )

    def test_fourteen_days_after_current_date_is_overdue(self):
        notifications = evaluate_review_reminders(
            self.record(date(2026, 8, 11)), self.as_of, ("dsg@example.test",)
        )

        self.assertEqual("review-overdue", notifications[0].kind)

    def test_advanced_review_date_does_not_match_old_overdue_cycle(self):
        notifications = evaluate_review_reminders(
            self.record(date(2027, 8, 11)), self.as_of, ("dsg@example.test",)
        )

        self.assertEqual((), notifications)

    def test_non_boundary_day_does_not_notify(self):
        notifications = evaluate_review_reminders(
            self.record(date(2026, 9, 7)), self.as_of, ("dsg@example.test",)
        )

        self.assertEqual((), notifications)


if __name__ == "__main__":
    unittest.main()
