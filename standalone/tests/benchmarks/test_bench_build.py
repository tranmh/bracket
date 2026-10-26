"""Benchmarks for the standalone build scripts (standalone/build/*.py).

The scripts derive every path from the module's ``__file__``; the benchmarks
point that at a project tree under tmp_path so nothing outside it is touched.
Only the file-system parts run here: pip and PyInstaller are never invoked.
"""
import importlib.util
from pathlib import Path

import pytest

BUILD_DIR = Path(__file__).resolve().parents[2] / "build"


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "aqaa_bench_build_" + name, str(BUILD_DIR / (name + ".py"))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_project(tmp_path, monkeypatch, module, name):
    project_root = tmp_path / "project"
    (project_root / "standalone" / "build").mkdir(parents=True)
    (project_root / "backend").mkdir()
    monkeypatch.setattr(
        module, "__file__", str(project_root / "standalone" / "build" / (name + ".py"))
    )
    monkeypatch.setattr(module, "print", lambda *a, **k: None, raising=False)
    return project_root


@pytest.mark.parametrize("stale_files", [0, 100, 1000])
def test_bench_build_frontend_static(benchmark, tmp_path, monkeypatch, stale_files):
    frontend = _load("frontend")
    project_root = _fake_project(tmp_path, monkeypatch, frontend, "frontend")
    output_dir = project_root / "standalone" / "dist" / "frontend"
    output_dir.mkdir(parents=True)
    for i in range(stale_files):
        (output_dir / ("stale_%d.js" % i)).write_text("x" * 64)

    result = benchmark(frontend.build_frontend_static)

    assert result is True
    assert (output_dir / "index.html").exists()


@pytest.mark.parametrize("entry", ["main.py", "run.py", "start.py", None])
def test_bench_find_main_file(benchmark, tmp_path, monkeypatch, entry):
    backend = _load("backend")
    project_root = _fake_project(tmp_path, monkeypatch, backend, "backend")
    if entry is not None:
        (project_root / "backend" / entry).write_text("app = None\n")

    result = benchmark(backend.find_main_file)

    if entry is None:
        assert result is None
    else:
        assert result.name == entry


def test_bench_create_enhanced_main_file(benchmark, tmp_path, monkeypatch):
    backend = _load("backend")
    project_root = _fake_project(tmp_path, monkeypatch, backend, "backend")

    result = benchmark(backend.create_enhanced_main_file)

    assert result == project_root / "backend" / "main.py"
    assert result.stat().st_size > 0
