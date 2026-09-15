from datahub.metadata.urns import Urn


FORM_ENTITY_TYPES = frozenset(
    {
        "dataset",
        "dataJob",
        "dataFlow",
        "chart",
        "dashboard",
        "corpuser",
        "corpGroup",
        "domain",
        "container",
        "glossaryTerm",
        "glossaryNode",
        "mlModel",
        "mlModelGroup",
        "mlFeatureTable",
        "mlFeature",
        "mlPrimaryKey",
        "schemaField",
        "dataProduct",
        "application",
    }
)
OWNER_ENTITY_TYPES = FORM_ENTITY_TYPES - {"corpuser", "schemaField"}


def entity_type(urn: str) -> str:
    return Urn.from_string(urn).entity_type
