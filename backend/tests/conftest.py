"""
Top-level test configuration.

- Registers the custom markers used by the test suite.
- When the QA environment provides a Postgres URL (AQAA_PG_URL), it is mapped onto the
  PG_DSN setting that bracket.config reads. This has to happen before `bracket.config` is
  imported, which is why it lives at module level in the top-most conftest.
"""

import os

import pytest


def _normalise_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


AQAA_PG_URL = os.getenv("AQAA_PG_URL")

if AQAA_PG_URL:
    os.environ["PG_DSN"] = _normalise_pg_url(AQAA_PG_URL)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: integration test against real services")
    config.addinivalue_line("markers", "e2e: end-to-end test")
