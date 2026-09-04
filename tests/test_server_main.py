import socket
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest

from qasccs.secure_channel import client as client_module
from qasccs.secure_channel import server as server_module

from conftest import _patched_cert_paths, free_port


def _run_server_in_thread(argv, shutdown_event):
    """Start server_module.main() in a background thread, driven by shutdown_event
    (can't rely on OS signal delivery here: signal.signal() only works on the
    main thread of the main interpreter, which this background thread is not).
    """
    result = {}

    def _target():
        with patch.object(sys, "argv", argv):
            result["exit_code"] = server_module.main(shutdown_event=shutdown_event)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    return thread, result


def _wait_for_listening(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server never started listening on {host}:{port}")


def test_server_main_serves_real_client_and_drains_on_shutdown(temp_certs):
    port = free_port()
    shutdown_event = threading.Event()
    with _patched_cert_paths(temp_certs):
        thread, result = _run_server_in_thread(
            ["prog", "--host", "127.0.0.1", "--port", str(port)], shutdown_event
        )
        try:
            _wait_for_listening("127.0.0.1", port)

            client_args = [
                "prog", "--host", "127.0.0.1", "--port", str(port),
                "--tls-server-name", "localhost",
                "--data-lifetime-years", "5",
                "--message", "hello from test_server_main",
            ]
            with patch.object(sys, "argv", client_args):
                exit_code = client_module.main()
            assert exit_code == 0
        finally:
            shutdown_event.set()
            thread.join(timeout=5)

        assert not thread.is_alive(), "server.main() did not return after shutdown_event was set"
        assert result.get("exit_code") == 0


def test_server_connection_timeout_drops_idle_client(temp_certs, monkeypatch):
    monkeypatch.setattr(server_module, "CONNECTION_TIMEOUT_SECONDS", 0.3)

    port = free_port()
    shutdown_event = threading.Event()
    with _patched_cert_paths(temp_certs):
        thread, result = _run_server_in_thread(
            ["prog", "--host", "127.0.0.1", "--port", str(port)], shutdown_event
        )
        try:
            _wait_for_listening("127.0.0.1", port)

            from qasccs.secure_channel.common import make_client_context
            ctx = make_client_context()
            with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname="localhost") as tls:
                    # Complete the handshake but never send a message; the server
                    # should drop us once CONNECTION_TIMEOUT_SECONDS elapses.
                    tls.settimeout(5)
                    data = tls.recv(16)
                    assert data == b""  # connection closed by server
        finally:
            shutdown_event.set()
            thread.join(timeout=5)


def test_server_handles_more_clients_than_max_connections(temp_certs, monkeypatch):
    monkeypatch.setattr(server_module, "MAX_CONCURRENT_CONNECTIONS", 1)

    port = free_port()
    shutdown_event = threading.Event()
    with _patched_cert_paths(temp_certs):
        thread, result = _run_server_in_thread(
            ["prog", "--host", "127.0.0.1", "--port", str(port)], shutdown_event
        )
        try:
            _wait_for_listening("127.0.0.1", port)

            # Two sequential clients against a max_workers=1 pool: both must be
            # served correctly (the pool queues rather than crashing/rejecting).
            for i in range(2):
                client_args = [
                    "prog", "--host", "127.0.0.1", "--port", str(port),
                    "--tls-server-name", "localhost",
                    "--data-lifetime-years", "5",
                    "--message", f"client {i}",
                ]
                with patch.object(sys, "argv", client_args):
                    exit_code = client_module.main()
                assert exit_code == 0
        finally:
            shutdown_event.set()
            thread.join(timeout=5)


def test_server_main_missing_certs_returns_1(tmp_path):
    empty_dir = tmp_path / "no-certs"
    empty_dir.mkdir()
    with _patched_cert_paths(empty_dir):
        with patch.object(sys, "argv", ["prog", "--host", "127.0.0.1", "--port", str(free_port())]):
            exit_code = server_module.main(shutdown_event=threading.Event())
    assert exit_code == 1


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="SIGTERM maps to forceful terminate() on Windows, bypassing the graceful-shutdown path being tested here",
)
def test_server_subprocess_drains_and_exits_cleanly_on_sigterm(temp_certs):
    """End-to-end: a real child process, a real SIGTERM, real graceful shutdown."""
    import os
    import signal

    port = free_port()
    env = dict(os.environ)
    env["QASCS_CERT_DIR"] = str(temp_certs)

    proc = subprocess.Popen(
        [sys.executable, "-m", "qasccs.secure_channel.server", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
    )
    try:
        _wait_for_listening("127.0.0.1", port, timeout=10)
        proc.send_signal(signal.SIGTERM)
        exit_code = proc.wait(timeout=10)
        assert exit_code == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
