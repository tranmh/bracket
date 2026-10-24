"""Unit tests for standalone/build/backend.py (PyInstaller build of the backend)."""
import subprocess
import sys
from unittest import mock

import pytest

from standalone.build import backend


@pytest.fixture
def project(fake_project, relocate):
    relocate(backend, "backend.py")
    return fake_project


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# install_all_dependencies
# ---------------------------------------------------------------------------

class TestInstallAllDependencies:
    def test_installs_backend_then_standalone_then_extras(self, project, monkeypatch):
        backend_reqs = project / "backend" / "requirements.txt"
        backend_reqs.write_text("fastapi\n")
        run = mock.Mock(return_value=_completed())
        monkeypatch.setattr(backend.subprocess, "run", run)

        backend.install_all_dependencies()

        calls = [c.args[0] for c in run.call_args_list]
        assert calls == [
            [sys.executable, "-m", "pip", "install", "-r", str(backend_reqs)],
            [sys.executable, "-m", "pip", "install", "-r", str(project / "standalone" / "requirements.txt")],
            [sys.executable, "-m", "pip", "install", "uvicorn[standard]"],
            [sys.executable, "-m", "pip", "install", "gunicorn"],
        ]
        assert all(c.kwargs.get("check") is True for c in run.call_args_list)

    def test_skips_backend_requirements_when_missing(self, project, monkeypatch):
        run = mock.Mock(return_value=_completed())
        monkeypatch.setattr(backend.subprocess, "run", run)

        backend.install_all_dependencies()

        commands = [c.args[0] for c in run.call_args_list]
        assert len(commands) == 3
        assert commands[0][-1] == str(project / "standalone" / "requirements.txt")
        assert not any(str(project / "backend") in " ".join(cmd) for cmd in commands)

    def test_failure_of_optional_extra_is_tolerated(self, project, monkeypatch, capsys):
        def fake_run(cmd, check):
            if cmd[-1] == "uvicorn[standard]":
                raise subprocess.CalledProcessError(1, cmd)
            return _completed()

        run = mock.Mock(side_effect=fake_run)
        monkeypatch.setattr(backend.subprocess, "run", run)

        backend.install_all_dependencies()

        # gunicorn is still attempted after uvicorn[standard] failed
        assert run.call_args_list[-1].args[0][-1] == "gunicorn"
        assert "Failed to install uvicorn[standard]" in capsys.readouterr().out

    def test_failure_of_standalone_requirements_propagates(self, project, monkeypatch):
        def fake_run(cmd, check):
            if "-r" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return _completed()

        run = mock.Mock(side_effect=fake_run)
        monkeypatch.setattr(backend.subprocess, "run", run)

        with pytest.raises(subprocess.CalledProcessError):
            backend.install_all_dependencies()
        # extras are not attempted after a hard failure
        assert run.call_count == 1

    def test_failure_of_backend_requirements_propagates(self, project, monkeypatch):
        (project / "backend" / "requirements.txt").write_text("fastapi\n")
        run = mock.Mock(side_effect=subprocess.CalledProcessError(1, "pip"))
        monkeypatch.setattr(backend.subprocess, "run", run)

        with pytest.raises(subprocess.CalledProcessError):
            backend.install_all_dependencies()
        assert run.call_count == 1


# ---------------------------------------------------------------------------
# find_main_file
# ---------------------------------------------------------------------------

class TestFindMainFile:
    def test_prefers_main_py(self, project):
        for name in ("main.py", "app.py", "server.py"):
            (project / "backend" / name).write_text("")

        assert backend.find_main_file() == project / "backend" / "main.py"

    @pytest.mark.parametrize(
        "present, expected",
        [
            (["app.py", "server.py", "run.py", "start.py"], "app.py"),
            (["server.py", "run.py", "start.py"], "server.py"),
            (["run.py", "start.py"], "run.py"),
            (["start.py"], "start.py"),
        ],
    )
    def test_fallback_order(self, project, present, expected):
        for name in present:
            (project / "backend" / name).write_text("")

        assert backend.find_main_file() == project / "backend" / expected

    def test_returns_none_when_no_candidate(self, project):
        (project / "backend" / "cli.py").write_text("")
        (project / "backend" / "main.txt").write_text("")

        assert backend.find_main_file() is None

    def test_returns_none_when_backend_dir_missing(self, project):
        (project / "backend").rmdir()

        assert backend.find_main_file() is None


# ---------------------------------------------------------------------------
# create_enhanced_main_file and the generated entry point
# ---------------------------------------------------------------------------

@pytest.fixture
def generated_source(project):
    main_file = backend.create_enhanced_main_file()
    return main_file.read_text()


@pytest.fixture
def generated_ns(generated_source, monkeypatch):
    """Execute the generated main.py as a non-__main__ module and return its namespace."""
    monkeypatch.setenv("BRACKET_STANDALONE", "false")
    ns = {"__name__": "generated_main"}
    exec(compile(generated_source, "main.py", "exec"), ns)
    ns["input"] = lambda *a, **k: ""  # never block on the console
    return ns


def _module(name, **attrs):
    mod = type(sys)(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


class _FakeApp:
    def openapi(self):
        return {}


APP_CANDIDATES = [
    "bracket", "bracket.app", "bracket.main", "bracket.server", "bracket.api",
    "bracket.backend", "bracket.core", "bracket.core.app", "bracket.core.main",
    "app", "main", "server", "api",
]


@pytest.fixture
def no_apps(monkeypatch):
    """Make every module the generated find_app() probes unimportable."""
    for name in APP_CANDIDATES:
        monkeypatch.setitem(sys.modules, name, None)
    return monkeypatch


class TestCreateEnhancedMainFile:
    def test_writes_main_py_into_backend_dir(self, project):
        result = backend.create_enhanced_main_file()

        assert result == project / "backend" / "main.py"
        assert result.exists()

    def test_overwrites_existing_main_py(self, project):
        target = project / "backend" / "main.py"
        target.write_text("old content")

        backend.create_enhanced_main_file()

        assert "old content" not in target.read_text()

    def test_generated_file_is_valid_python(self, generated_source):
        compile(generated_source, "main.py", "exec")

    def test_generated_file_sets_standalone_mode_on_import(self, generated_ns):
        import os

        assert os.environ["BRACKET_STANDALONE"] == "true"
        for name in ("check_dependencies", "find_app", "start_server"):
            assert callable(generated_ns[name])

    def test_raises_when_backend_dir_missing(self, project):
        (project / "backend").rmdir()

        with pytest.raises(FileNotFoundError):
            backend.create_enhanced_main_file()

    def test_generated_file_is_windows_console_safe(self, generated_source):
        # aqaa: bug - backend/main.py was explicitly fixed to be
        # "Windows console compatible (no emoji characters)", but the generator
        # still emits emoji, which raise UnicodeEncodeError when stdout is a pipe
        # with a legacy Windows code page (electron/main.js spawns the backend
        # with stdio ['pipe', 'pipe', 'pipe'] and no PYTHONIOENCODING).
        generated_source.encode("cp1252")


class TestGeneratedCheckDependencies:
    MODULES = ["uvicorn", "fastapi", "sqlalchemy", "databases", "aiosqlite"]

    def test_all_available(self, generated_ns, monkeypatch):
        for name in self.MODULES:
            monkeypatch.setitem(sys.modules, name, _module(name))

        assert generated_ns["check_dependencies"]() is True

    @pytest.mark.parametrize("missing", MODULES)
    def test_one_missing(self, generated_ns, monkeypatch, capsys, missing):
        for name in self.MODULES:
            monkeypatch.setitem(sys.modules, name, None if name == missing else _module(name))

        assert generated_ns["check_dependencies"]() is False
        assert f"Missing dependencies: {missing}" in capsys.readouterr().out


class TestGeneratedFindApp:
    def test_finds_app_with_openapi(self, generated_ns, no_apps):
        app = _FakeApp()
        no_apps.setitem(sys.modules, "bracket.app", _module("bracket.app", app=app))

        assert generated_ns["find_app"]() == (app, "bracket.app:app")

    def test_first_match_wins(self, generated_ns, no_apps):
        first, second = _FakeApp(), _FakeApp()
        no_apps.setitem(sys.modules, "bracket.main", _module("bracket.main", app=first))
        no_apps.setitem(sys.modules, "app", _module("app", app=second))

        assert generated_ns["find_app"]() == (first, "bracket.main:app")

    def test_skips_module_without_app_attribute(self, generated_ns, no_apps):
        app = _FakeApp()
        no_apps.setitem(sys.modules, "bracket.app", _module("bracket.app"))
        no_apps.setitem(sys.modules, "server", _module("server", app=app))

        assert generated_ns["find_app"]() == (app, "server:app")

    def test_accepts_app_factory(self, generated_ns, no_apps):
        instance = _FakeApp()
        no_apps.setitem(sys.modules, "bracket.app", _module("bracket.app", create_app=lambda: instance))

        assert generated_ns["find_app"]() == (instance, "bracket.app:create_app")

    def test_ignores_factory_that_raises(self, generated_ns, no_apps):
        def broken():
            raise RuntimeError("boom")

        no_apps.setitem(sys.modules, "bracket.app", _module("bracket.app", app=broken))

        assert generated_ns["find_app"]() == (None, None)

    def test_ignores_non_app_objects(self, generated_ns, no_apps):
        no_apps.setitem(sys.modules, "bracket.app", _module("bracket.app", app="not an app"))

        assert generated_ns["find_app"]() == (None, None)

    def test_returns_none_when_nothing_importable(self, generated_ns, no_apps):
        assert generated_ns["find_app"]() == (None, None)


class TestGeneratedStartServer:
    @pytest.fixture
    def fake_uvicorn(self, monkeypatch):
        uv = _module("uvicorn", run=mock.Mock())
        monkeypatch.setitem(sys.modules, "uvicorn", uv)
        return uv

    def test_runs_uvicorn_on_localhost_8400(self, generated_ns, fake_uvicorn):
        generated_ns["check_dependencies"] = lambda: True
        generated_ns["find_app"] = lambda: (_FakeApp(), "bracket.app:app")

        generated_ns["start_server"]()

        fake_uvicorn.run.assert_called_once()
        args, kwargs = fake_uvicorn.run.call_args
        assert args == ("bracket.app:app",)
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8400
        assert kwargs["reload"] is False

    def test_exits_when_dependencies_missing(self, generated_ns, fake_uvicorn):
        generated_ns["check_dependencies"] = lambda: False

        with pytest.raises(SystemExit) as exc:
            generated_ns["start_server"]()

        assert exc.value.code == 1
        fake_uvicorn.run.assert_not_called()

    def test_exits_when_app_not_found(self, generated_ns, fake_uvicorn):
        generated_ns["check_dependencies"] = lambda: True
        generated_ns["find_app"] = lambda: (None, None)

        with pytest.raises(SystemExit) as exc:
            generated_ns["start_server"]()

        assert exc.value.code == 1
        fake_uvicorn.run.assert_not_called()

    def test_exits_when_uvicorn_fails(self, generated_ns, fake_uvicorn):
        generated_ns["check_dependencies"] = lambda: True
        generated_ns["find_app"] = lambda: (_FakeApp(), "bracket.app:app")
        fake_uvicorn.run.side_effect = OSError("address in use")

        with pytest.raises(SystemExit) as exc:
            generated_ns["start_server"]()

        assert exc.value.code == 1

    def test_exits_when_uvicorn_not_importable(self, generated_ns, monkeypatch):
        monkeypatch.setitem(sys.modules, "uvicorn", None)
        generated_ns["check_dependencies"] = lambda: True

        with pytest.raises(SystemExit) as exc:
            generated_ns["start_server"]()

        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# build_backend_executable
# ---------------------------------------------------------------------------

class TestBuildBackendExecutable:
    @pytest.fixture
    def build_env(self, project, monkeypatch):
        (project / "backend" / "main.py").write_text("print('hi')\n")
        install = mock.Mock()
        monkeypatch.setattr(backend, "install_all_dependencies", install)
        dist = project / "standalone" / "dist"

        def fake_run(cmd, **kwargs):
            (dist / "bracket-backend.exe").write_bytes(b"x" * 1024)
            return _completed(0)

        run = mock.Mock(side_effect=fake_run)
        monkeypatch.setattr(backend.subprocess, "run", run)
        return {"project": project, "install": install, "run": run, "dist": dist}

    def test_success(self, build_env):
        assert backend.build_backend_executable() is True
        build_env["install"].assert_called_once_with()
        assert build_env["dist"].is_dir()

    def test_pyinstaller_invocation(self, build_env):
        project, dist = build_env["project"], build_env["dist"]

        backend.build_backend_executable()

        build_env["run"].assert_called_once()
        cmd = build_env["run"].call_args.args[0]
        kwargs = build_env["run"].call_args.kwargs
        assert cmd[0] == "pyinstaller"
        assert cmd[1] == str(project / "backend" / "main.py")
        for flag in ("--onefile", "--name=bracket-backend", "--console", "--clean",
                     f"--distpath={dist}", f"--workpath={dist / 'build'}", f"--specpath={dist / 'build'}"):
            assert flag in cmd
        assert kwargs["cwd"] == str(project / "backend")
        assert kwargs["env"]["BRACKET_STANDALONE"] == "true"

    def test_hidden_imports_are_passed_as_pairs(self, build_env):
        backend.build_backend_executable()

        cmd = build_env["run"].call_args.args[0]
        hidden = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--hidden-import"]
        for name in ("uvicorn", "fastapi", "aiosqlite", "sqlalchemy.dialects.sqlite.aiosqlite", "databases"):
            assert name in hidden

    def test_env_of_caller_is_not_mutated(self, build_env, monkeypatch):
        monkeypatch.setenv("BRACKET_STANDALONE", "false")

        backend.build_backend_executable()

        import os
        assert os.environ["BRACKET_STANDALONE"] == "false"

    def test_add_data_only_for_existing_dirs(self, build_env):
        backend_dir = build_env["project"] / "backend"
        (backend_dir / "static").mkdir()
        (backend_dir / "migrations").mkdir()

        backend.build_backend_executable()

        cmd = build_env["run"].call_args.args[0]
        add_data = [a for a in cmd if a.startswith("--add-data=")]
        assert add_data == [
            f"--add-data={backend_dir / 'static'};static",
            f"--add-data={backend_dir / 'migrations'};migrations",
        ]

    def test_no_add_data_without_data_dirs(self, build_env):
        backend.build_backend_executable()

        cmd = build_env["run"].call_args.args[0]
        assert not [a for a in cmd if a.startswith("--add-data")]

    def test_pyinstaller_failure_returns_false(self, build_env, capsys):
        build_env["run"].side_effect = None
        build_env["run"].return_value = _completed(1, stdout="out" * 2000, stderr="boom-error")

        assert backend.build_backend_executable() is False
        out = capsys.readouterr().out
        assert "PyInstaller failed" in out
        assert "boom-error" in out

    def test_missing_executable_after_build_returns_false(self, build_env, capsys):
        build_env["run"].side_effect = None
        build_env["run"].return_value = _completed(0)

        assert backend.build_backend_executable() is False
        assert "Executable not found" in capsys.readouterr().out

    def test_creates_main_file_when_none_found(self, build_env):
        main = build_env["project"] / "backend" / "main.py"
        main.unlink()

        assert backend.build_backend_executable() is True

        assert main.exists()
        assert build_env["run"].call_args.args[0][1] == str(main)

    def test_uses_fallback_entry_point(self, build_env):
        backend_dir = build_env["project"] / "backend"
        (backend_dir / "main.py").unlink()
        (backend_dir / "server.py").write_text("")

        backend.build_backend_executable()

        assert build_env["run"].call_args.args[0][1] == str(backend_dir / "server.py")
        assert not (backend_dir / "main.py").exists()

    def test_install_failure_propagates_and_skips_pyinstaller(self, build_env):
        build_env["install"].side_effect = subprocess.CalledProcessError(1, "pip")

        with pytest.raises(subprocess.CalledProcessError):
            backend.build_backend_executable()
        build_env["run"].assert_not_called()

    def test_missing_backend_dir_returns_false(self, build_env):
        # aqaa: suspected bug - the function reports "Could not find or create main
        # file" and returns False when no entry point can be produced, but when the
        # backend directory is missing create_enhanced_main_file() raises
        # FileNotFoundError instead.
        import shutil
        shutil.rmtree(build_env["project"] / "backend")

        assert backend.build_backend_executable() is False
        build_env["run"].assert_not_called()
