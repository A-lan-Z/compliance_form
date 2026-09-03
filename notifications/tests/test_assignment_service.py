import json
from pathlib import Path
import tempfile
import unittest

from dcl_notifications.assignment_service import FormAssignmentNotificationService
from dcl_notifications.email_outbox import DirectoryEmailOutbox
from dcl_notifications.recipients import StaticBusinessContactRecipientResolver


FORM_URN = "urn:li:form:compliance"
ENTITY_URN = "urn:li:container:test"


def event(form_urn=FORM_URN, timestamp=1234):
    return {
        "entityUrn": ENTITY_URN,
        "changeType": "UPSERT",
        "aspectName": "forms",
        "aspect": {
            "contentType": "application/json",
            "value": json.dumps(
                {
                    "incompleteForms": [{"urn": form_urn}],
                    "completedForms": [],
                }
            ),
        },
        "previousAspectValue": None,
        "created": {"time": timestamp},
    }


class AssignmentNotificationServiceTest(unittest.TestCase):
    def test_allowed_assignment_is_delivered_once(self):
        with tempfile.TemporaryDirectory() as directory:
            service = FormAssignmentNotificationService(
                {FORM_URN},
                StaticBusinessContactRecipientResolver(
                    {ENTITY_URN: ("bcp@example.test",)}
                ),
                DirectoryEmailOutbox(directory, "sender@example.test"),
            )

            first = service.handle(event())
            replay = service.handle(event())

            self.assertTrue(first[0])
            self.assertFalse(replay[0])
            self.assertEqual(1, len(list(Path(directory).glob("*.eml"))))

    def test_later_reassignment_has_a_distinct_key(self):
        with tempfile.TemporaryDirectory() as directory:
            service = FormAssignmentNotificationService(
                {FORM_URN},
                StaticBusinessContactRecipientResolver(
                    {ENTITY_URN: ("bcp@example.test",)}
                ),
                DirectoryEmailOutbox(directory, "sender@example.test"),
            )

            service.handle(event(timestamp=1234))
            service.handle(event(timestamp=5678))

            self.assertEqual(2, len(list(Path(directory).glob("*.eml"))))

    def test_unallowed_form_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            service = FormAssignmentNotificationService(
                {FORM_URN},
                StaticBusinessContactRecipientResolver(
                    {ENTITY_URN: ("bcp@example.test",)}
                ),
                DirectoryEmailOutbox(directory, "sender@example.test"),
            )

            deliveries = service.handle(event(form_urn="urn:li:form:other"))

            self.assertEqual((), deliveries)


if __name__ == "__main__":
    unittest.main()
