"""Unit tests for the helpers in standalone/build/test_backend.py (executable smoke test script).

The module is imported under an alias so that pytest does not collect its
``test_*`` helper functions as tests of this file.
"""
import io
import socket
import subprocess
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

from standalone.build import test_backend as smoke


@pytest.fixture
def exe_path(fake_project, relocate):
    relocate(smoke, "test_backend.py")
    return fake_project / "standalone" / "dist" / "bracket-backend.exe"


@pytest.fixture
def exe(exe_path):
    exe_path.parent.mkdir(parents=True)
    exe_path.write_bytes(b"MZ" + b"\0" * 2048)
    return exe_path


# ---------------------------------------------------------------------------
# test_port_connectivity
# ---------------------------------------------------------------------------

class TestPortConnectivity:
    def test_open_port_on_loopback(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = server.getsockname()[1]
            assert smoke.test_port_connectivity("127.0.0.1", port) is True
        finally:
            server.close()

    @pytest.mark.parametrize("code, expected", [(0, True), (111, False), (10061, False)])
    def test_result_of_connect_ex(self, monkeypatch, code, expected):
        sock = mock.Mock()
        sock.connect_ex.return_value = code
        monkeypatch.setattr(smoke.socket, "socket", mock.Mock(return_value=sock))

        assert smoke.test_port_connectivity("127.0.0.1", 8400) is expected
        sock.connect_ex.assert_called_once_with(("127.0.0.1", 8400))
        sock.settimeout.assert_called_once_with(2)
        sock.close.assert_called_once_with()

    def test_socket_error_returns_false(self, monkeypatch):
        monkeypatch.setattr(smoke.socket, "socket", mock.Mock(side_effect=OSError("no sockets")))

        assert smoke.test_port_connectivity("127.0.0.1", 8400) is False

    def test_invalid_port_returns_false(self):
        assert smoke.test_port_connectivity("127.0.0.1", 70000) is False


# ---------------------------------------------------------------------------
# test_http_endpoint
# ---------------------------------------------------------------------------

class _Response:
    def __init__(self, code):
        self._code = code

    def getcode(self):
        return self._code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestHttpEndpoint:
    @pytest.mark.parametrize("code, expected", [(200, True), (201, False), (204, False), (302, False)])
    def test_status_codes(self, monkeypatch, code, expected):
        urlopen = mock.Mock(return_value=_Response(code))
        monkeypatch.setattr(smoke, "urlopen", urlopen)

        assert smoke.test_http_endpoint("http://127.0.0.1:8400") is expected
        urlopen.assert_called_once_with("http://127.0.0.1:8400", timeout=5)

    @pytest.mark.parametrize(
        "code, expected",
        [(404, True), (422, True), (400, False), (401, False), (500, False), (503, False)],
    )
    def test_http_errors(self, monkeypatch, code, expected):
        err = HTTPError("http://127.0.0.1:8400", code, "reason", {}, io.BytesIO(b""))
        monkeypatch.setattr(smoke, "urlopen", mock.Mock(side_effect=err))

        assert smoke.test_http_endpoint("http://127.0.0.1:8400") is expected

    @pytest.mark.parametrize("error", [URLError("refused"), ConnectionResetError("reset"), TimeoutError()])
    def test_connection_failures(self, monkeypatch, error):
        monkeypatch.setattr(smoke, "urlopen", mock.Mock(side_effect=error))

        assert smoke.test_http_endpoint("http://127.0.0.1:8400") is False


# ---------------------------------------------------------------------------
# run_basic_executable_test
# ---------------------------------------------------------------------------

class TestRunBasicExecutableTest:
    def test_missing_executable(self, exe_path, monkeypatch):
        run = mock.Mock()
        monkeypatch.setattr(smoke.subprocess, "run", run)

        assert smoke.run_basic_executable_test() is False
        run.assert_not_called()

    @pytest.mark.parametrize(
        "returncode, stdout",
        [(0, ""), (2, "usage: bracket-backend"), (1, "see --help"), (1, "")],
    )
    def test_any_completed_run_is_ok(self, exe, monkeypatch, returncode, stdout):
        run = mock.Mock(return_value=subprocess.CompletedProcess([], returncode, stdout, ""))
        monkeypatch.setattr(smoke.subprocess, "run", run)

        assert smoke.run_basic_executable_test() is True
        args, kwargs = run.call_args
        assert args[0] == [str(exe), "--help"]
        assert kwargs["env"]["BRACKET_STANDALONE"] == "true"
        assert kwargs["timeout"] == 10

    def test_timeout_is_treated_as_running(self, exe, monkeypatch):
        monkeypatch.setattr(
            smoke.subprocess, "run", mock.Mock(side_effect=subprocess.TimeoutExpired("exe", 10))
        )

        assert smoke.run_basic_executable_test() is True

    def test_launch_error_fails(self, exe, monkeypatch):
        monkeypatch.setattr(smoke.subprocess, "run", mock.Mock(side_effect=OSError("bad exe")))

        assert smoke.run_basic_executable_test() is False


# ---------------------------------------------------------------------------
# test_backend_executable
# ---------------------------------------------------------------------------

class TestBackendExecutable:
    @pytest.fixture
    def harness(self, exe, monkeypatch):
        process = mock.Mock()
        process.poll.return_value = None
        process.returncode = None
        process.communicate.return_value = ("out", "err")
        popen = mock.Mock(return_value=process)
        sleep = mock.Mock()
        port = mock.Mock(return_value=False)
        http = mock.Mock(return_value=True)
        monkeypatch.setattr(smoke.subprocess, "Popen", popen)
        monkeypatch.setattr(smoke.time, "sleep", sleep)
        monkeypatch.setattr(smoke, "test_port_connectivity", port)
        monkeypatch.setattr(smoke, "test_http_endpoint", http)
        return {"process": process, "popen": popen, "sleep": sleep, "port": port, "http": http, "exe": exe}

    def test_missing_executable(self, exe_path, monkeypatch):
        popen = mock.Mock()
        monkeypatch.setattr(smoke.subprocess, "Popen", popen)

        assert smoke.test_backend_executable() is False
        popen.assert_not_called()

    def test_success_when_port_and_http_respond(self, harness):
        harness["port"].return_value = True

        assert smoke.test_backend_executable() is True

        args, kwargs = harness["popen"].call_args
        assert args[0] == [str(harness["exe"])]
        assert kwargs["env"]["BRACKET_STANDALONE"] == "true"
        harness["port"].assert_called_with("127.0.0.1", 8400)
        harness["http"].assert_called_once_with("http://127.0.0.1:8400")
        harness["process"].terminate.assert_called_once_with()

    def test_open_port_without_http_still_succeeds(self, harness):
        harness["port"].return_value = True
        harness["http"].return_value = False

        assert smoke.test_backend_executable() is True
        harness["process"].terminate.assert_called_once_with()

    def test_becomes_ready_after_some_polls(self, harness):
        harness["port"].side_effect = [False, False, True]

        assert smoke.test_backend_executable() is True
        assert harness["sleep"].call_count == 3

    def test_process_crash_fails(self, harness, capsys):
        harness["process"].poll.return_value = 3
        harness["process"].returncode = 3

        assert smoke.test_backend_executable() is False
        harness["port"].assert_not_called()
        assert "exited with code 3" in capsys.readouterr().out

    def test_startup_timeout_after_ten_attempts(self, harness):
        assert smoke.test_backend_executable() is False
        assert harness["sleep"].call_count == 10
        assert harness["port"].call_count == 10
        harness["process"].terminate.assert_called_once_with()

    def test_kills_process_that_does_not_terminate(self, harness):
        harness["port"].return_value = True
        harness["process"].wait.side_effect = [subprocess.TimeoutExpired("exe", 5), 0]

        assert smoke.test_backend_executable() is True
        harness["process"].kill.assert_called_once_with()

    def test_popen_failure_returns_false(self, harness):
        harness["popen"].side_effect = OSError("cannot execute")

        assert smoke.test_backend_executable() is False

    def test_cleanup_errors_are_swallowed(self, harness):
        harness["port"].return_value = True
        harness["process"].terminate.side_effect = ProcessLookupError()

        assert smoke.test_backend_executable() is True
