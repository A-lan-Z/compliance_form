import unittest

from dcl_notifications.recipients import DataHubOwnershipRecipientResolver


class Graph:
    def __init__(self, ownership):
        self.ownership = ownership
        self.requested_urn = None

    def get_untyped_aspect(self, entity_urn, aspect_name, aspect_type_name):
        self.requested_urn = entity_urn
        return self.ownership


class DataHubOwnershipRecipientResolverTest(unittest.TestCase):
    def test_selects_current_typed_owners_and_maps_their_emails(self):
        graph = Graph(
            {
                "owners": [
                    {
                        "owner": "urn:li:corpuser:alice",
                        "typeUrn": "urn:li:ownershipType:bcp",
                    },
                    {
                        "owner": "urn:li:corpuser:bob",
                        "typeUrn": "urn:li:ownershipType:technical",
                    },
                ]
            }
        )
        resolver = DataHubOwnershipRecipientResolver(
            graph,
            "urn:li:ownershipType:bcp",
            {"urn:li:corpuser:alice": "alice@example.test"},
        )

        recipients = resolver("urn:li:container:test")

        self.assertEqual(("alice@example.test",), recipients)
        self.assertEqual("urn:li:container:test", graph.requested_urn)

    def test_missing_ownership_has_no_recipients(self):
        resolver = DataHubOwnershipRecipientResolver(
            Graph(None), "urn:li:ownershipType:bcp", {}
        )

        self.assertEqual((), resolver("urn:li:container:test"))


if __name__ == "__main__":
    unittest.main()
