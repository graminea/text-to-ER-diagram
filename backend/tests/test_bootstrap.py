"""Reusable startup works without importing an HTTP entry point or SDK."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_application
from app.generation import GenerationRequest
from app.llm_provider import LLMGenerator
from app.main import app, create_app
from app.offline import DEMO_REQUIREMENTS, MockGenerator
from app.provider_contract import RuntimeMetadata
from app.settings import Settings


def test_non_http_runtime_in_fresh_process(tmp_path: Path) -> None:
    script = """
import sys
class BlockOuterImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'app.main' or fullname.split('.')[0] in {'fastapi', 'litellm'}:
            raise AssertionError('Unexpected outer dependency: ' + fullname)
sys.meta_path.insert(0, BlockOuterImports())
from pathlib import Path
from app.bootstrap import build_application
from app.generation import GenerationRequest
from app.offline import DEMO_REQUIREMENTS
from app.settings import Settings
application = build_application(Path(sys.argv[1]), settings=Settings(mode='mock'))
assert not Path(sys.argv[1]).exists()
with application.lifespan() as running:
    result = running.service.generate(GenerationRequest(requirements=DEMO_REQUIREMENTS))
    assert running.service.get(result.id) == result
    assert running.service.list_recent() == [result]
with build_application(Path(sys.argv[1]), settings=Settings()).lifespan() as restarted:
    assert restarted.service.get(result.id) == result
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "nested" / "history.db")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_environment_path_and_lifecycle_error_propagation(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "environment.db"
    monkeypatch.setenv("DB_PATH", str(db))
    application = build_application(settings=Settings())
    assert not db.exists()
    with pytest.raises(RuntimeError, match="caller failed"), application.lifespan():
        result = application.service.generate(GenerationRequest(requirements=DEMO_REQUIREMENTS))
        raise RuntimeError("caller failed")
    with application.lifespan():
        assert application.service.get(result.id) == result


def test_injected_generator_ignores_environment_and_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MODE", "llm")
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    for settings in (None, Settings(mode="llm", model="unused", api_key="private-key")):
        application = build_application(tmp_path / "injected.db", MockGenerator(), settings)
        assert application.runtime_metadata == RuntimeMetadata("mock-fixture-v1", "mock")
        with application.lifespan():
            assert application.service.generate(
                GenerationRequest(requirements=DEMO_REQUIREMENTS)
            ).provider == "mock-fixture-v1"


def test_health_uses_explicit_metadata_without_inspecting_settings(tmp_path: Path) -> None:
    class CustomGenerator(MockGenerator):
        @property
        def settings(self):
            raise AssertionError("HTTP must not inspect provider configuration")

    generator = CustomGenerator()
    for metadata in (None, RuntimeMetadata("custom", "llm", "custom/model")):
        with TestClient(create_app(
            tmp_path / "custom.db", generator, runtime_metadata=metadata,
        )) as client:
            expected = metadata or RuntimeMetadata(generator.name, "mock")
            assert client.get("/api/health").json() == {
                "status": "ok", "provider": expected.provider,
                "mode": expected.mode, "model": expected.model,
            }


def test_injected_llm_health(tmp_path: Path) -> None:
    generator = LLMGenerator(
        Settings(mode="llm", model="openai/test", api_key="private-key"), Mock()
    )
    application = build_application(tmp_path / "llm.db", generator)
    assert application.runtime_metadata == RuntimeMetadata("litellm", "llm", "openai/test")
    with TestClient(create_app(tmp_path / "llm.db", generator)) as client:
        response = client.get("/api/health")
        assert response.json() == {
            "status": "ok", "provider": "litellm", "mode": "llm", "model": "openai/test",
        }
        assert "private-key" not in response.text
    assert callable(app)  # Preserve app.main:app for ASGI servers.


def test_selected_provider_declares_metadata(tmp_path: Path, monkeypatch) -> None:
    class CustomGenerator(MockGenerator):
        runtime_metadata = RuntimeMetadata("custom", "llm", "custom/model")

    monkeypatch.setattr("app.bootstrap.create_generator", lambda settings: CustomGenerator())
    application = build_application(tmp_path / "selected.db", settings=Settings())
    assert application.runtime_metadata == RuntimeMetadata("custom", "llm", "custom/model")
    override = RuntimeMetadata("override", "mock")
    overridden = build_application(
        tmp_path / "override.db", settings=Settings(), runtime_metadata=override,
    )
    assert overridden.runtime_metadata == override


def test_configured_llm_is_assembled_without_live_calls(tmp_path: Path, monkeypatch) -> None:
    completion = Mock()
    monkeypatch.setattr("app.llm_provider.load_completion", lambda: completion)
    application = build_application(
        tmp_path / "configured.db",
        settings=Settings(mode="llm", model="openai/test", api_key="private-key"),
    )
    assert application.runtime_metadata == RuntimeMetadata("litellm", "llm", "openai/test")
    assert "private-key" not in repr(application.runtime_metadata)
    completion.assert_not_called()
