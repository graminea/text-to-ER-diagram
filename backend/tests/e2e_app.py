"""Browser test entry point with a credential-free provider transport."""

from app.entrypoints.http import create_app
from app.llm_provider import LLMGenerator
from app.settings import Settings
from tests.support import response


def complete(**_):
    return response()


app = create_app(
    generator=LLMGenerator(Settings(model="openai/test", api_key="test-only"), complete),
)
