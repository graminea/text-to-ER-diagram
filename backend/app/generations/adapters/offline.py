"""Removable demonstration fixture; not used by real LLM generation."""

from app.er.models import Attribute, ConceptualSchema, Entity, Participation, Relationship

DEMO_REQUIREMENTS = (
    "Um cliente pode fazer vários pedidos. Cada pedido pertence a exatamente um cliente."
)


class MockGenerator:
    name = "mock-fixture-v1"

    def generate(self, requirements: str) -> object:
        # Deliberately a fixture, not a language understanding implementation.
        schema = ConceptualSchema(
            entities=[
                Entity(
                    name=name,
                    attributes=[Attribute(name="id", data_type="integer", is_identifier=True)],
                )
                for name in ["Cliente", "Pedido"]
            ],
            relationships=[
                Relationship(
                    name="realiza",
                    participants=[
                        Participation(
                            entity="Cliente",
                            role="comprador",
                            min_cardinality=0,
                            max_cardinality="N",
                        ),
                        Participation(
                            entity="Pedido", role="compra", min_cardinality=1, max_cardinality=1
                        ),
                    ],
                )
            ],
            assumptions=["Mock: atributos id adicionados como identificadores de demonstração."],
            ambiguities=[]
            if requirements.strip() == DEMO_REQUIREMENTS
            else [
                "O mock retorna sempre Cliente/Pedido e não interpreta este texto. "
                "Conecte um provedor real para modelar outros requisitos."
            ],
        )
        return schema.model_dump()
