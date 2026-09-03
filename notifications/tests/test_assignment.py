import json
import unittest

from dcl_notifications.assignment import detect_form_assignments


FORM_A = "urn:li:form:a"
FORM_B = "urn:li:form:b"


def generic_aspect(incomplete=(), completed=()):
    return {
        "contentType": "application/json",
        "value": json.dumps(
            {
                "incompleteForms": [{"urn": urn} for urn in incomplete],
                "completedForms": [{"urn": urn} for urn in completed],
                "verifications": [],
            }
        ),
    }


def event(current, previous=None, aspect_name="forms", change_type="UPSERT"):
    return {
        "entityUrn": "urn:li:container:test",
        "changeType": change_type,
        "aspectName": aspect_name,
        "aspect": current,
        "previousAspectValue": previous,
        "created": {"time": 1234, "actor": "urn:li:corpuser:test"},
    }


class FormAssignmentDetectorTest(unittest.TestCase):
    def test_detects_new_assignment_on_first_forms_aspect(self):
        assignments = detect_form_assignments(event(generic_aspect((FORM_A,))))

        self.assertEqual(1, len(assignments))
        self.assertEqual(FORM_A, assignments[0].form_urn)
        self.assertEqual(1234, assignments[0].occurred_at_ms)

    def test_detects_only_new_form_when_an_existing_form_remains(self):
        assignments = detect_form_assignments(
            event(
                generic_aspect((FORM_A, FORM_B)),
                generic_aspect((FORM_A,)),
            )
        )

        self.assertEqual([FORM_B], [assignment.form_urn for assignment in assignments])

    def test_completion_move_is_not_a_new_assignment(self):
        assignments = detect_form_assignments(
            event(
                generic_aspect(completed=(FORM_A,)),
                generic_aspect(incomplete=(FORM_A,)),
            )
        )

        self.assertEqual((), assignments)

    def test_removal_is_not_an_assignment(self):
        assignments = detect_form_assignments(
            event(generic_aspect(), generic_aspect((FORM_A,)))
        )

        self.assertEqual((), assignments)

    def test_unrelated_event_is_ignored(self):
        self.assertEqual(
            (),
            detect_form_assignments(event(generic_aspect(), aspect_name="ownership")),
        )


if __name__ == "__main__":
    unittest.main()
