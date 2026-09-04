import pytest
import ssl
import socket
import threading
import time

from qasccs.secure_channel.common import make_server_context, make_client_context, send_msg, recv_msg
from qasccs.secure_channel.protocol import Envelope, decode_envelope, encode_envelope

from conftest import _patched_cert_paths


def test_make_server_context_with_certs(temp_certs):
    """Test creating server SSL context"""
    with _patched_cert_paths(temp_certs):
        ctx = make_server_context()

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
        # Server now requires a client certificate (mutual TLS)
        assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_make_client_context_with_certs(temp_certs):
    """Test creating client SSL context"""
    with _patched_cert_paths(temp_certs):
        ctx = make_client_context()

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_mtls_handshake_and_framed_messages(temp_certs):
    """Test a full mutual-TLS handshake using the length-prefixed message framing."""
    with _patched_cert_paths(temp_certs):
        server_ctx = make_server_context()
        client_ctx = make_client_context()

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        server_error = None
        server_received = None
        server_peer_cn = None

        def server_thread():
            nonlocal server_error, server_received, server_peer_cn
            try:
                conn, _ = server_sock.accept()
                with server_ctx.wrap_socket(conn, server_side=True) as tls:
                    peer_cert = tls.getpeercert()
                    for rdn in peer_cert.get("subject", ()):
                        for key, value in rdn:
                            if key == "commonName":
                                server_peer_cn = value
                    data = recv_msg(tls)
                    server_received = data.decode("utf-8")
                    send_msg(tls, b"ACK")
            except Exception as e:
                server_error = e
            finally:
                server_sock.close()

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        with client_ctx.wrap_socket(client_sock, server_hostname="localhost") as tls:
            send_msg(tls, b"Hello mTLS")
            reply = recv_msg(tls)
            assert reply == b"ACK"

        thread.join(timeout=2)

        assert server_error is None, f"Server error: {server_error}"
        assert server_received == "Hello mTLS"
        # Server should have seen and verified the client's certificate.
        assert server_peer_cn == "qasccs-client"


def test_server_rejects_connection_without_client_cert(temp_certs):
    """Test that the server refuses a TLS client that presents no certificate."""
    with _patched_cert_paths(temp_certs):
        server_ctx = make_server_context()

        # A bare client context that verifies the server but presents no client cert.
        no_cert_client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        no_cert_client_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        no_cert_client_ctx.load_verify_locations(cafile=str(temp_certs / "ca.crt"))
        no_cert_client_ctx.check_hostname = True
        no_cert_client_ctx.verify_mode = ssl.CERT_REQUIRED

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        server_error = None

        def server_thread():
            nonlocal server_error
            try:
                conn, _ = server_sock.accept()
                try:
                    with server_ctx.wrap_socket(conn, server_side=True):
                        pass
                except ssl.SSLError as e:
                    server_error = e
            finally:
                server_sock.close()

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        # Depending on TLS version, the client may see the failure as an SSLError during
        # the handshake, or (TLS 1.3 posts the cert request after the handshake completes)
        # as the connection being reset/closed on a subsequent read. Either way the
        # server-side rejection (asserted below) is what actually matters here.
        with pytest.raises((ssl.SSLError, OSError)):
            with no_cert_client_ctx.wrap_socket(client_sock, server_hostname="localhost") as tls:
                tls.recv(16)

        thread.join(timeout=2)
        assert server_error is not None


def test_missing_certs_raise_clear_config_error(tmp_path):
    """Test that make_server_context/make_client_context fail with a clear,
    operator-actionable error (not a raw traceback) when cert files are absent."""
    from qasccs.secure_channel.common import CertificateConfigError

    empty_dir = tmp_path / "no-certs-here"
    empty_dir.mkdir()
    with _patched_cert_paths(empty_dir):
        with pytest.raises(CertificateConfigError, match="Missing certificate/key file"):
            make_server_context()
        with pytest.raises(CertificateConfigError, match="Missing certificate/key file"):
            make_client_context()


def test_client_tls_server_name_overrides_hostname_check(temp_certs):
    """Test that --tls-server-name lets the client verify against a name in the
    cert's SAN even when --host is something else (e.g. a container/service name
    not present in the cert, as happens behind a proxy or in docker-compose)."""
    import sys as _sys
    from unittest.mock import patch as _patch
    from qasccs.secure_channel import client as client_module

    with _patched_cert_paths(temp_certs):
        server_ctx = make_server_context()

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        def server_thread():
            conn, _ = server_sock.accept()
            with server_ctx.wrap_socket(conn, server_side=True) as tls:
                data = recv_msg(tls)
                req_env = decode_envelope(data)
                ack = f"ACK (secure): {len(req_env.payload)} bytes".encode()
                resp_env = Envelope.new("echo_response", ack, correlation_id=req_env.correlation_id)
                send_msg(tls, encode_envelope(resp_env))
            server_sock.close()

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.1)

        # --host is "127.0.0.1" (which the connection uses), but we force TLS
        # identity verification against "localhost" via --tls-server-name -
        # both are in the dev cert's SAN, proving the two are independently
        # controllable rather than always being the same value.
        test_args = [
            "prog",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--tls-server-name", "localhost",
            "--data-lifetime-years", "5",
            "--message", "override test",
        ]
        with _patch.object(_sys, "argv", test_args):
            exit_code = client_module.main()

        thread.join(timeout=2)
        assert exit_code == 0


def test_server_context_requires_tls12_minimum(temp_certs):
    """Test that server context requires TLS 1.2 minimum"""
    with _patched_cert_paths(temp_certs):
        ctx = make_server_context()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2


def test_client_context_requires_tls12_minimum(temp_certs):
    """Test that client context requires TLS 1.2 minimum"""
    with _patched_cert_paths(temp_certs):
        ctx = make_client_context()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2


def test_client_verifies_server_cert(temp_certs):
    """Test that client properly verifies server certificate"""
    with _patched_cert_paths(temp_certs):
        ctx = make_client_context()
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True


def test_send_recv_msg_roundtrip(temp_certs):
    """Test the length-prefixed framing helpers roundtrip arbitrary payloads over a real TLS pipe."""
    with _patched_cert_paths(temp_certs):
        server_ctx = make_server_context()
        client_ctx = make_client_context()

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        received = []

        def server_thread():
            conn, _ = server_sock.accept()
            with server_ctx.wrap_socket(conn, server_side=True) as tls:
                while True:
                    msg = recv_msg(tls)
                    if msg is None:
                        break
                    received.append(msg)
                    send_msg(tls, b"ok")
            server_sock.close()

        thread = threading.Thread(target=server_thread)
        thread.start()
        time.sleep(0.1)

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))
        with client_ctx.wrap_socket(client_sock, server_hostname="localhost") as tls:
            payloads = [b"", b"short", b"x" * 70000]  # includes empty and >64KiB to exercise chunked recv
            for p in payloads:
                send_msg(tls, p)
                assert recv_msg(tls) == b"ok"

        thread.join(timeout=2)
        assert received == [b"", b"short", b"x" * 70000]
