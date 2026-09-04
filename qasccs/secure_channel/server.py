from __future__ import annotations
import argparse
import os
import signal
import socket
import ssl
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from ..logging_config import configure_logging
from . import metrics
from .common import CertificateConfigError, make_server_context, send_msg, recv_msg
from .protocol import Envelope, ProtocolError, decode_envelope, encode_envelope

log = configure_logging("qasccs.server")

# A client that completes neither the TLS handshake nor sends its first
# message within this many seconds is dropped, so a stalled/slow-loris peer
# can't tie up a worker thread indefinitely.
CONNECTION_TIMEOUT_SECONDS = float(os.environ.get("QASCS_CONN_TIMEOUT", "30"))
MAX_CONCURRENT_CONNECTIONS = int(os.environ.get("QASCS_MAX_CONNECTIONS", "100"))

# Opt-in: unset by default, so the server never opens an extra port unless
# an operator explicitly configures it. See docs/scaling.md.
METRICS_PORT = os.environ.get("QASCS_METRICS_PORT")
METRICS_HOST = os.environ.get("QASCS_METRICS_HOST", "0.0.0.0")


def _client_cn(tls: ssl.SSLSocket) -> str:
    """Extract the client certificate's commonName, if present.

    getpeercert()'s return type is typed by typeshed as a plain
    `dict[str, str | tuple[...] | tuple[tuple[...]]]` (not a precise per-key
    TypedDict), so the 'subject' value's static type includes `str` even
    though it's only ever a tuple-of-RDNs at runtime. isinstance-narrow at
    each level instead of destructuring-unpacking an ambiguously-typed value.
    """
    cert = tls.getpeercert()
    if not cert:
        return "<no client cert>"
    subject = cert.get("subject")
    if not isinstance(subject, tuple):
        return "<unknown CN>"
    for rdn in subject:
        if not isinstance(rdn, tuple):
            continue
        for entry in rdn:
            if isinstance(entry, tuple) and len(entry) == 2 and entry[0] == "commonName":
                return entry[1]
    return "<unknown CN>"


def _handle_connection(conn: socket.socket, addr, ctx: ssl.SSLContext) -> None:
    conn.settimeout(CONNECTION_TIMEOUT_SECONDS)
    metrics.record_connection_started()
    try:
        with ctx.wrap_socket(conn, server_side=True) as tls:
            cn = _client_cn(tls)
            log.info("Connection from %s (client cert CN=%r)", addr, cn)
            while True:
                data = recv_msg(tls)
                if data is None:
                    log.info("%s disconnected", addr)
                    return
                try:
                    req_env = decode_envelope(data)
                except ProtocolError as e:
                    log.warning("Malformed message from %s: %s", addr, e)
                    return
                log.debug("Received %s from %s (correlation_id=%s): %r",
                          req_env.type, addr, req_env.correlation_id, req_env.payload)
                metrics.observe_message_bytes(len(req_env.payload))
                ack = f"ACK (secure): {len(req_env.payload)} bytes".encode()
                resp_env = Envelope.new("echo_response", ack, correlation_id=req_env.correlation_id)
                send_msg(tls, encode_envelope(resp_env))
    except TimeoutError:
        log.warning("Connection from %s timed out after %.0fs", addr, CONNECTION_TIMEOUT_SECONDS)
        metrics.record_timeout()
    except ssl.SSLError as e:
        log.warning("TLS error from %s: %s", addr, e)
        metrics.record_handshake_failure(type(e).__name__)
    except Exception:
        log.exception("Unhandled error while serving %s", addr)
    finally:
        metrics.record_connection_ended()
        try:
            conn.close()
        except OSError:
            pass


def main(shutdown_event: threading.Event | None = None) -> int:
    """Run the server until shut down.

    `shutdown_event` is normally left as None: this installs real SIGINT/SIGTERM
    handlers (only possible from the main thread of the main interpreter) and
    creates its own event. Tests that need to run the accept loop in a
    background thread (where `signal.signal()` cannot be called) pass in their
    own `threading.Event` and trigger shutdown by setting it directly instead
    of relying on OS signal delivery.
    """
    ap = argparse.ArgumentParser(description="QASCS Secure Server (mTLS demo, framed messages)")
    ap.add_argument("--host", default=os.environ.get("QASCS_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("QASCS_PORT", "8443")))
    args = ap.parse_args()

    try:
        ctx = make_server_context()
    except CertificateConfigError as e:
        log.error(str(e))
        return 1

    if METRICS_PORT:
        try:
            metrics.start_metrics_server(int(METRICS_PORT), host=METRICS_HOST)
            log.info("Prometheus metrics listening on %s:%s/metrics", METRICS_HOST, METRICS_PORT)
        except RuntimeError as e:
            log.error(str(e))
            return 1

    if shutdown_event is None:
        shutdown_event = threading.Event()

        def _on_signal(signum, _frame):
            log.info("Received signal %s, shutting down...", signal.Signals(signum).name)
            shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, _on_signal)

    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CONNECTIONS, thread_name_prefix="qascs-conn")

    try:
        with socket.create_server((args.host, args.port), reuse_port=hasattr(socket, "SO_REUSEPORT")) as sock:
            sock.settimeout(1.0)  # let the accept loop check shutdown_event periodically
            log.info(
                "Listening on %s:%s (mTLS, client certs required, max_connections=%d, conn_timeout=%.0fs)",
                args.host, args.port, MAX_CONCURRENT_CONNECTIONS, CONNECTION_TIMEOUT_SECONDS,
            )
            while not shutdown_event.is_set():
                try:
                    conn, addr = sock.accept()
                except TimeoutError:
                    continue
                executor.submit(_handle_connection, conn, addr, ctx)
    finally:
        log.info("Waiting for in-flight connections to finish...")
        executor.shutdown(wait=True, cancel_futures=False)
        log.info("Server stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
