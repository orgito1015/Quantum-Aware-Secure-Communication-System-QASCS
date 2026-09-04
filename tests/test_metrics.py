import socket
import sys
import threading
import time
import urllib.request
from unittest.mock import patch

import pytest

prometheus_client = pytest.importorskip("prometheus_client")

from qasccs.secure_channel import client as client_module  # noqa: E402
from qasccs.secure_channel import server as server_module  # noqa: E402
from qasccs.secure_channel import metrics  # noqa: E402

from conftest import _patched_cert_paths, free_port  # noqa: E402


def _wait_for_listening(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server never started listening on {host}:{port}")


def test_metrics_endpoint_serves_prometheus_text_after_real_connection(temp_certs, monkeypatch):
    server_port = free_port()
    metrics_port = free_port()
    monkeypatch.setattr(server_module, "METRICS_PORT", str(metrics_port))
    monkeypatch.setattr(server_module, "METRICS_HOST", "127.0.0.1")

    shutdown_event = threading.Event()
    result = {}

    def _target():
        with patch.object(sys, "argv", ["prog", "--host", "127.0.0.1", "--port", str(server_port)]):
            result["exit_code"] = server_module.main(shutdown_event=shutdown_event)

    with _patched_cert_paths(temp_certs):
        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        try:
            _wait_for_listening("127.0.0.1", server_port)
            _wait_for_listening("127.0.0.1", metrics_port)

            client_args = [
                "prog", "--host", "127.0.0.1", "--port", str(server_port),
                "--tls-server-name", "localhost",
                "--data-lifetime-years", "5",
                "--message", "metrics smoke test",
            ]
            with patch.object(sys, "argv", client_args):
                exit_code = client_module.main()
            assert exit_code == 0

            with urllib.request.urlopen(f"http://127.0.0.1:{metrics_port}/metrics", timeout=5) as resp:
                body = resp.read().decode("utf-8")
            assert "qascs_connections_total" in body
            assert "qascs_active_connections" in body
            assert "qascs_message_bytes" in body
        finally:
            shutdown_event.set()
            thread.join(timeout=5)


def test_record_helpers_are_safe_when_metrics_unavailable(monkeypatch):
    monkeypatch.setattr(metrics, "METRICS_AVAILABLE", False)
    # Should not raise even though the underlying prometheus objects aren't touched.
    metrics.record_connection_started()
    metrics.record_connection_ended()
    metrics.record_handshake_failure("SSLError")
    metrics.record_timeout()
    metrics.observe_message_bytes(123)


def test_start_metrics_server_raises_clear_error_when_unavailable(monkeypatch):
    monkeypatch.setattr(metrics, "METRICS_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="observability"):
        metrics.start_metrics_server(free_port())
