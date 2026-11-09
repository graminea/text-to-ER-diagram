import json
from types import SimpleNamespace

EXAMPLE_REQUIREMENTS = (
    "Um cliente pode fazer vários pedidos. Cada pedido pertence a exatamente um cliente."
)


def example_schema() -> dict:
    return {
        "entities": [
            {
                "name": name,
                "attributes": [{"name": "id", "data_type": "integer", "is_identifier": True}],
            }
            for name in ("Cliente", "Pedido")
        ],
        "relationships": [
            {
                "name": "realiza",
                "participants": [
                    {
                        "entity": "Cliente", "role": "comprador",
                        "min_cardinality": 0, "max_cardinality": "N",
                    },
                    {
                        "entity": "Pedido", "role": "compra",
                        "min_cardinality": 1, "max_cardinality": 1,
                    },
                ],
            },
        ],
        "assumptions": [],
        "ambiguities": [],
    }


class FixtureGenerator:
    name = "test-fixture"

    def generate(self, requirements: str) -> dict:
        return example_schema()


def response(content=None, finish="stop", refusal=None, usage=True):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish,
                message=SimpleNamespace(
                    content=content if content is not None else json.dumps(example_schema()),
                    refusal=refusal,
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=80) if usage else None,
    )
