from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import time
import unittest

try:
    from datahub_actions.event.event_envelope import EventEnvelope
    from datahub_actions.pipeline.pipeline_context import PipelineContext

    from dcl_notifications.datahub_action import ComplianceFormAssignmentAction

    ACTIONS_AVAILABLE = True
except ModuleNotFoundError:
    ACTIONS_AVAILABLE = False


FORM_URN = "urn:li:form:compliance"
ENTITY_URN = "urn:li:container:test"
OWNERSHIP_TYPE_URN = "urn:li:ownershipType:bcp"


class FakeEvent:
    def as_json(self):
        return json.dumps(
            {
                "entityUrn": ENTITY_URN,
                "changeType": "UPSERT",
                "aspectName": "forms",
                "aspect": {
                    "contentType": "application/json",
                    "value": json.dumps(
                        {
                            "incompleteForms": [{"urn": FORM_URN}],
                            "completedForms": [],
                        }
                    ),
                },
                "previousAspectValue": None,
                "created": {"time": 1234},
            }
        )


class Graph:
    def get_untyped_aspect(self, entity_urn, aspect_name, aspect_type_name):
        return {
            "owners": [
                {
                    "owner": "urn:li:corpuser:bcp",
                    "typeUrn": OWNERSHIP_TYPE_URN,
                }
            ]
        }


@unittest.skipUnless(
    ACTIONS_AVAILABLE, "acryl-datahub-actions is an optional POC extra"
)
class DataHubActionCompatibilityTest(unittest.TestCase):
    def test_adapter_runs_with_actions_framework_event_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            work_directory = Path(directory)
            action = ComplianceFormAssignmentAction.create(
                {
                    "forms": [
                        {
                            "urn": FORM_URN,
                            "review_date": (
                                date.today() + timedelta(days=14)
                            ).isoformat(),
                        }
                    ],
                    "business_contact_ownership_type_urn": OWNERSHIP_TYPE_URN,
                    "principal_emails": {"urn:li:corpuser:bcp": "bcp@example.test"},
                    "dsg_emails": ["dsg@example.test"],
                    "sender": "sender@example.test",
                    "outbox_directory": str(work_directory / "outbox"),
                    "review_schedule_path": str(work_directory / "schedule.json"),
                    "review_poll_seconds": 0.01,
                },
                PipelineContext("test-pipeline", Graph()),
            )

            try:
                action.act(
                    EventEnvelope(
                        event_type="MetadataChangeLogEvent_v1",
                        event=FakeEvent(),
                        meta={},
                    )
                )
                deadline = time.monotonic() + 1
                while (
                    len(list((work_directory / "outbox").glob("*.eml"))) < 2
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
            finally:
                action.close()

            self.assertEqual(2, len(list((work_directory / "outbox").glob("*.eml"))))
            schedule = json.loads(
                (work_directory / "schedule.json").read_text(encoding="utf-8")
            )
            self.assertEqual(ENTITY_URN, schedule[0]["entityUrn"])
            self.assertEqual(FORM_URN, schedule[0]["formUrn"])


if __name__ == "__main__":
    unittest.main()
