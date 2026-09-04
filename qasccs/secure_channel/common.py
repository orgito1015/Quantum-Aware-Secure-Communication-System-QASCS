from __future__ import annotations
import os
import ssl
import struct
from pathlib import Path

# All cert paths are overridable via environment variables so a production
# deployment can point at real, ops-managed PKI material instead of the
# bundled dev-only self-signed CA (see docs/pqc-integration.md and the
# "Production considerations" section of the README).
CERT_DIR = Path(os.environ.get("QASCS_CERT_DIR", str(Path(__file__).resolve().parent / "certs")))
SERVER_CERT = Path(os.environ.get("QASCS_SERVER_CERT", str(CERT_DIR / "server.crt")))
SERVER_KEY = Path(os.environ.get("QASCS_SERVER_KEY", str(CERT_DIR / "server.key")))
CLIENT_CERT = Path(os.environ.get("QASCS_CLIENT_CERT", str(CERT_DIR / "client.crt")))
CLIENT_KEY = Path(os.environ.get("QASCS_CLIENT_KEY", str(CERT_DIR / "client.key")))
CA_CERT = Path(os.environ.get("QASCS_CA_CERT", str(CERT_DIR / "ca.crt")))

# Framed-message wire format: 4-byte big-endian length prefix + payload.
_LEN_STRUCT = struct.Struct(">I")
MAX_MESSAGE_BYTES = 16 * 1024 * 1024  # 16 MiB cap to bound memory use


class CertificateConfigError(RuntimeError):
    """Raised when required cert/key material is missing or unreadable.

    Kept distinct from ssl.SSLError so callers can print an operator-friendly
    message ("generate or provision certs") instead of a raw TLS stack trace.
    """


def _require_files(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise CertificateConfigError(
            "Missing certificate/key file(s): "
            + ", ".join(missing)
            + ". Generate dev certs with `python -m qasccs.tools.gen_certs --out <dir>`, "
              "or point QASCS_CERT_DIR (or the individual QASCS_*_CERT/KEY vars) at your "
              "production PKI material."
        )


def make_server_context() -> ssl.SSLContext:
    """Server-side TLS context. Requires and verifies a client certificate (mTLS)."""
    _require_files(SERVER_CERT, SERVER_KEY, CA_CERT)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=str(SERVER_CERT), keyfile=str(SERVER_KEY))
    # Require a client certificate signed by our trusted CA (mutual TLS).
    ctx.load_verify_locations(cafile=str(CA_CERT))
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def make_client_context() -> ssl.SSLContext:
    """Client-side TLS context. Verifies the server cert and presents a client cert (mTLS)."""
    _require_files(CLIENT_CERT, CLIENT_KEY, CA_CERT)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_verify_locations(cafile=str(CA_CERT))
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    # Present our client certificate so the server can authenticate us.
    ctx.load_cert_chain(certfile=str(CLIENT_CERT), keyfile=str(CLIENT_KEY))
    return ctx


def _recv_exact(sock: ssl.SSLSocket, n: int) -> bytes:
    """Read exactly n bytes from a (blocking) TLS socket, or raise ConnectionError."""
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(min(remaining, 65536))
        if not chunk:
            raise ConnectionError("Connection closed before expected data was received")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_msg(sock: ssl.SSLSocket, payload: bytes) -> None:
    """Send a length-prefixed message so receivers don't assume it arrives in one recv()."""
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError(f"Message too large: {len(payload)} bytes (max {MAX_MESSAGE_BYTES})")
    sock.sendall(_LEN_STRUCT.pack(len(payload)) + payload)


def recv_msg(sock: ssl.SSLSocket) -> bytes | None:
    """Receive a length-prefixed message. Returns None on clean connection close."""
    try:
        header = _recv_exact(sock, _LEN_STRUCT.size)
    except ConnectionError:
        return None
    (length,) = _LEN_STRUCT.unpack(header)
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"Peer announced an oversized message: {length} bytes (max {MAX_MESSAGE_BYTES})")
    return _recv_exact(sock, length)
