"""Shared fixtures for the standalone build tooling tests."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests needing test services")
    config.addinivalue_line("markers", "e2e: end-to-end tests")


@pytest.fixture
def fake_project(tmp_path):
    """A fake project layout: <root>/backend and <root>/standalone/build."""
    root = tmp_path / "project"
    (root / "backend").mkdir(parents=True)
    (root / "standalone" / "build").mkdir(parents=True)
    (root / "standalone" / "requirements.txt").write_text("aiosqlite\n")
    return root


@pytest.fixture
def relocate(monkeypatch, fake_project):
    """Make a build module believe it lives in <fake_project>/standalone/build."""

    def _relocate(module, filename):
        fake_file = fake_project / "standalone" / "build" / filename
        monkeypatch.setattr(module, "__file__", str(fake_file))
        return fake_file

    return _relocate
