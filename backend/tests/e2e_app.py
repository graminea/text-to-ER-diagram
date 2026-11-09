"""Browser test entry point with a credential-free provider transport."""

import json

from app.entrypoints.http import create_app
from app.generations.adapters.agents import AgentGenerator
from app.llm_provider import LLMGenerator
from app.settings import Settings
from tests.support import response


def complete(**request):
    if request["response_format"]["json_schema"]["name"] == "er_review":
        instructions = request["messages"][0]["content"]
        finding = (
            "Cada pedido pertence a um cliente."
            if "limites mínimo e máximo" in instructions
            else "Cliente e Pedido aparecem nos requisitos."
        )
        return response(json.dumps({"findings": [finding]}))
    return response()


direct = LLMGenerator(Settings(model="openai/test", api_key="test-only"), complete)
app = create_app(
    generator=direct, agent_generator=AgentGenerator(direct),
)
