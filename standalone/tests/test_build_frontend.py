"""Unit tests for standalone/build/frontend.py (static fallback frontend)."""
from html.parser import HTMLParser
from unittest import mock

import pytest

from standalone.build import frontend


@pytest.fixture
def project(fake_project, relocate):
    relocate(frontend, "frontend.py")
    return fake_project


@pytest.fixture
def output_dir(project):
    return project / "standalone" / "dist" / "frontend"


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        self._in_title = tag == "title"

    def handle_endtag(self, tag):
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class TestCreateProfessionalFrontend:
    def test_creates_index_html(self, output_dir):
        assert frontend.create_professional_frontend() is True

        index = output_dir / "index.html"
        assert index.is_file()
        assert list(output_dir.iterdir()) == [index]

    def test_index_is_utf8_html_document(self, output_dir):
        frontend.create_professional_frontend()

        content = (output_dir / "index.html").read_bytes().decode("utf-8")
        assert content.startswith("<!DOCTYPE html>")
        assert content.rstrip().endswith("</html>")
        assert '<meta charset="UTF-8">' in content
        assert "🏆" in content

    def test_index_points_at_local_backend(self, output_dir):
        frontend.create_professional_frontend()

        parser = _Collector()
        parser.feed((output_dir / "index.html").read_text(encoding="utf-8"))
        assert parser.title == "Bracket Tournament System"
        assert parser.links == ["http://localhost:8400/", "http://localhost:8400/docs"]
        # the script relies on these element ids
        for element_id in ("status", "mainBtn", "apiBtn"):
            assert element_id in parser.ids

    def test_cleans_stale_output(self, output_dir):
        (output_dir / "_next").mkdir(parents=True)
        (output_dir / "_next" / "old.js").write_text("stale")
        (output_dir / "index.html").write_text("old index")

        frontend.create_professional_frontend()

        assert sorted(p.name for p in output_dir.iterdir()) == ["index.html"]
        assert "old index" not in (output_dir / "index.html").read_text(encoding="utf-8")

    def test_creates_missing_parent_dirs(self, project, output_dir):
        assert not (project / "standalone" / "dist").exists()

        frontend.create_professional_frontend()

        assert output_dir.is_dir()

    def test_is_idempotent(self, output_dir):
        frontend.create_professional_frontend()
        first = (output_dir / "index.html").read_bytes()
        frontend.create_professional_frontend()

        assert (output_dir / "index.html").read_bytes() == first


class TestBuildFrontendStatic:
    @pytest.mark.parametrize("result", [True, False])
    def test_delegates_to_professional_frontend(self, monkeypatch, result):
        create = mock.Mock(return_value=result)
        monkeypatch.setattr(frontend, "create_professional_frontend", create)

        assert frontend.build_frontend_static() is result
        create.assert_called_once_with()

    def test_does_not_run_npm(self, project, output_dir, monkeypatch):
        run = mock.Mock(side_effect=AssertionError("npm must not be invoked"))
        popen = mock.Mock(side_effect=AssertionError("npm must not be invoked"))
        monkeypatch.setattr(frontend.subprocess, "run", run)
        monkeypatch.setattr(frontend.subprocess, "Popen", popen)

        assert frontend.build_frontend_static() is True
        assert (output_dir / "index.html").is_file()
        run.assert_not_called()
        popen.assert_not_called()
