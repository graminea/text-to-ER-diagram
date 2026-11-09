"""Focused module boundaries, exercised by the ordinary offline pytest command."""

import ast
import sys
from importlib.util import resolve_name
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
SOURCES = {
    "app." + ".".join(path.relative_to(APP).with_suffix("").parts).removesuffix(".__init__"):
    path for path in APP.rglob("*.py")
}
# The root initializer's name is app, rather than app.__init__.
SOURCES["app"] = SOURCES.pop("app.__init__")

# Application edges are exact: legacy facades cannot bypass the same boundaries.
ALLOWED = {
    "app.er.models": set(),
    "app.er.validation": {"app.er.models"},
    "app.generations.models": {"app.er.models"},
    "app.generations.ports": {"app.generations.models"},
    "app.generations.service": {
        "app.er.models", "app.er.validation", "app.generations.models", "app.generations.ports",
    },
    "app.generations.adapters.sqlite": {"app.generations.models"},
    "app.generations.adapters.prompts": set(),
    "app.generations.adapters.agents": {
        "app.er.models", "app.generations.adapters.llm", "app.generations.adapters.prompts",
        "app.generations.models", "app.generations.ports",
    },
    "app.generations.adapters.llm": {
        "app.er.models", "app.generations.ports", "app.generations.adapters.prompts",
        "app.settings",
    },
    "app.settings": set(),
    "app.providers": {
        "app.generations.ports", "app.settings",
        "app.generations.adapters.agents", "app.generations.adapters.llm",
    },
    "app.bootstrap": {
        "app.generations.service", "app.generations.ports", "app.generations.adapters.sqlite",
        "app.providers", "app.settings",
    },
    "app.entrypoints.http": {
        "app.bootstrap", "app.er.models", "app.er.validation", "app.generations.models",
        "app.generations.ports", "app.settings",
    },
    "app.main": {"app.entrypoints.http"},
    "app.domain": {"app.er.models"},
    "app.validation": {"app.er.validation"},
    "app.generation": {
        "app.generations.models", "app.generations.ports", "app.generations.service",
    },
    "app.provider_contract": {"app.generations.ports"},
    "app.persistence": {"app.generations.adapters.sqlite"},
    "app.prompts": {"app.generations.adapters.prompts"},
    "app.llm_provider": {"app.generations.adapters.llm"},
}
EXTERNAL = {
    "app.er.models": {"pydantic"},
    "app.generations.models": {"pydantic"},
    "app.generations.service": {"pydantic"},
    "app.generations.adapters.llm": {"litellm"},
    "app.entrypoints.http": {"fastapi"},
}
CORE = {
    "app.er.models", "app.er.validation", "app.generations.models",
    "app.generations.ports", "app.generations.service",
}
CORE_IO = {"http", "urllib", "sqlite3", "socket", "ssl"}


def dependencies(source: str, module: str, *, package: bool = False) -> list[tuple[int, str]]:
    """Read imports without importing/executing the app, including nested imports."""
    result = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            result.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parent = module if package else module.rpartition(".")[0]
                base = resolve_name("." * node.level + base, parent)
            for alias in node.names:
                candidate = f"{base}.{alias.name}"
                result.append((node.lineno, candidate if candidate in SOURCES else base))
        elif isinstance(node, ast.Call):
            # Known dynamic import forms; computed names fail closed for review.
            function = ast.unparse(node.func)
            if function in {"importlib.import_module", "import_module", "__import__"}:
                name = node.args[0] if node.args else None
                target = (
                    name.value if isinstance(name, ast.Constant) and isinstance(name.value, str)
                    else "<computed import>"
                )
                result.append((node.lineno, target))
    return result


def violations(module: str, imports: list[tuple[int, str]]) -> list[str]:
    errors = []
    for line, target in imports:
        root = target.split(".")[0]
        if target == "app" or target.startswith("app."):
            allowed = target in ALLOWED.get(module, set())
        else:
            allowed = root in sys.stdlib_module_names | EXTERNAL.get(module, set())
            if module in CORE and root in CORE_IO:
                allowed = False
        if not allowed:
            errors.append(f"{module}:{line} must not import {target}")
    return errors


def test_module_boundaries() -> None:
    errors = []
    for module, path in SOURCES.items():
        # Initializers must remain empty of app/third-party imports. New implementation
        # modules require an explicit policy, even if they currently have no imports.
        if path.name != "__init__.py" and module not in ALLOWED:
            errors.append(f"{module}: add an explicit boundary policy")
        imports = dependencies(path.read_text(encoding="utf-8"), module,
                               package=path.name == "__init__.py")
        errors.extend(violations(module, imports))
    assert not errors, "\n".join(errors)


def test_application_imports_are_acyclic() -> None:
    graph = {
        module: [target for _, target in dependencies(
            path.read_text(encoding="utf-8"), module, package=path.name == "__init__.py"
        ) if target in SOURCES]
        for module, path in SOURCES.items()
    }
    complete: set[str] = set()

    def visit(module: str, trail: tuple[str, ...]) -> None:
        assert module not in trail, "Import cycle: " + " -> ".join((*trail, module))
        if module in complete:
            return
        for target in graph[module]:
            visit(target, (*trail, module))
        complete.add(module)

    for module in graph:
        visit(module, ())


@pytest.mark.parametrize("source", [
    "import fastapi",
    "from starlette.requests import Request",
    "from http import HTTPStatus",
    "import sqlite3",
    "from app.persistence import GenerationRepository",
    "from app import persistence",
    "from .adapters.sqlite import GenerationRepository",
    "def generate():\n    from app.generations.adapters.llm import LLMGenerator",
    "from app.llm_provider import LLMGenerator",
    "importlib.import_module('litellm')",
    "__import__('httpx')",
    "import_module(provider_name)",
])
def test_checker_rejects_service_boundary_regressions(source: str) -> None:
    assert violations("app.generations.service", dependencies(source, "app.generations.service"))


def test_checker_resolves_relative_and_package_imports() -> None:
    assert dependencies("from .models import Generation", "app.generations.service") == [
        (1, "app.generations.models"),
    ]
    assert dependencies("from . import models", "app.generations", package=True) == [
        (1, "app.generations.models"),
    ]
    assert not violations("app.generations.service", [(1, "app.generations.models")])
