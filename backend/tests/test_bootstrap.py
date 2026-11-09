"""Reusable startup works without importing an HTTP entry point or SDK."""

import subprocess
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import build_application
from app.entrypoints.http import create_app
from app.generation import GenerationRequest
from app.llm_provider import LLMGenerator
from app.provider_contract import RuntimeMetadata
from app.settings import Settings
from tests.support import EXAMPLE_REQUIREMENTS, FixtureGenerator


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
from tests.support import EXAMPLE_REQUIREMENTS, FixtureGenerator
application = build_application(Path(sys.argv[1]), FixtureGenerator())
assert not Path(sys.argv[1]).exists()
with application.lifespan() as running:
    result = running.service.generate(GenerationRequest(requirements=EXAMPLE_REQUIREMENTS))
    assert running.service.get(result.id) == result
    assert running.service.list_recent() == [result]
with build_application(Path(sys.argv[1]), FixtureGenerator()).lifespan() as restarted:
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
    application = build_application(generator=FixtureGenerator())
    assert not db.exists()
    with pytest.raises(RuntimeError, match="caller failed"), application.lifespan():
        result = application.service.generate(GenerationRequest(requirements=EXAMPLE_REQUIREMENTS))
        raise RuntimeError("caller failed")
    with application.lifespan():
        assert application.service.get(result.id) == result


def test_injected_generator_ignores_environment_and_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    for settings in (None, Settings(model="unused", api_key="private-key")):
        application = build_application(tmp_path / "injected.db", FixtureGenerator(), settings)
        assert application.runtime_metadata == RuntimeMetadata("test-fixture", "custom")
        with application.lifespan():
            assert application.service.generate(
                GenerationRequest(requirements=EXAMPLE_REQUIREMENTS)
            ).provider == "test-fixture"


def test_health_uses_explicit_metadata_without_inspecting_settings(tmp_path: Path) -> None:
    class CustomGenerator(FixtureGenerator):
        @property
        def settings(self):
            raise AssertionError("HTTP must not inspect provider configuration")

    generator = CustomGenerator()
    for metadata in (None, RuntimeMetadata("custom", "llm", "custom/model")):
        with TestClient(create_app(
            tmp_path / "custom.db", generator, runtime_metadata=metadata,
        )) as client:
            expected = metadata or RuntimeMetadata(generator.name, "custom")
            assert client.get("/api/health").json() == {
                "status": "ok", "provider": expected.provider,
                "mode": expected.mode, "model": expected.model,
            }


def test_injected_llm_health(tmp_path: Path) -> None:
    generator = LLMGenerator(
        Settings(model="openai/test", api_key="private-key"), Mock()
    )
    application = build_application(tmp_path / "llm.db", generator)
    assert application.runtime_metadata == RuntimeMetadata("litellm", "llm", "openai/test")
    with TestClient(create_app(tmp_path / "llm.db", generator)) as client:
        response = client.get("/api/health")
        assert response.json() == {
            "status": "ok", "provider": "litellm", "mode": "llm", "model": "openai/test",
        }
        assert "private-key" not in response.text


def test_asgi_entry_point_and_legacy_factory(monkeypatch) -> None:
    completion = Mock()
    monkeypatch.setattr("app.llm_provider.load_completion", lambda: completion)
    monkeypatch.delenv("MODE", raising=False)
    for name in ("TIMEOUT", "MAX_TOKENS", "OUTPUT_MODE", "API_BASE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODEL", "openai/test")
    monkeypatch.setenv("API_KEY", "test-only")
    entry_point = import_module("app.main")
    assert callable(entry_point.app)
    assert entry_point.create_app is create_app
    completion.assert_not_called()


def test_selected_provider_declares_metadata(tmp_path: Path, monkeypatch) -> None:
    class CustomGenerator(FixtureGenerator):
        runtime_metadata = RuntimeMetadata("custom", "llm", "custom/model")

    monkeypatch.setattr(
        "app.bootstrap.create_generators", lambda settings: (CustomGenerator(), FixtureGenerator())
    )
    settings = Settings(model="openai/test", api_key="test-only")
    application = build_application(tmp_path / "selected.db", settings=settings)
    assert application.runtime_metadata == RuntimeMetadata("custom", "llm", "custom/model")
    override = RuntimeMetadata("override", "custom")
    overridden = build_application(
        tmp_path / "override.db", settings=settings, runtime_metadata=override,
    )
    assert overridden.runtime_metadata == override


def test_configured_llm_is_assembled_without_live_calls(tmp_path: Path, monkeypatch) -> None:
    completion = Mock()
    monkeypatch.setattr("app.llm_provider.load_completion", lambda: completion)
    application = build_application(
        tmp_path / "configured.db",
        settings=Settings(model="openai/test", api_key="private-key"),
    )
    assert application.runtime_metadata == RuntimeMetadata("litellm", "llm", "openai/test")
    assert "private-key" not in repr(application.runtime_metadata)
    completion.assert_not_called()
