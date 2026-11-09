"""Required tests never select a paid provider from a developer's environment."""

import pytest


@pytest.fixture(autouse=True)
def default_offline(monkeypatch):
    monkeypatch.setenv("MODE", "mock")
