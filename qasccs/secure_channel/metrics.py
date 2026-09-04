from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

if METRICS_AVAILABLE:
    _CONNECTIONS_TOTAL = Counter(
        "qascs_connections_total", "Total connections accepted by the secure channel server."
    )
    _HANDSHAKE_FAILURES_TOTAL = Counter(
        "qascs_handshake_failures_total", "Total TLS handshake failures.", ["reason"]
    )
    _CONNECTION_TIMEOUTS_TOTAL = Counter(
        "qascs_connection_timeouts_total", "Total connections dropped for idling past the configured timeout."
    )
    _ACTIVE_CONNECTIONS = Gauge(
        "qascs_active_connections", "Connections currently being served."
    )
    _MESSAGE_BYTES = Histogram(
        "qascs_message_bytes", "Size in bytes of received application-layer message payloads."
    )


def start_metrics_server(port: int, host: str = "0.0.0.0") -> None:
    """Start the Prometheus /metrics HTTP endpoint on a separate port.

    Intentionally opt-in (only called when QASCS_METRICS_PORT is set) so
    running the server never opens an extra port unless explicitly configured.
    """
    if not METRICS_AVAILABLE:
        raise RuntimeError(
            "Prometheus metrics requested but prometheus-client isn't installed. "
            "Install the 'observability' extra: pip install -e '.[observability]'"
        )
    start_http_server(port, addr=host)


# The record_* helpers below are safe to call unconditionally from server.py
# even when prometheus-client isn't installed (base install) — they just
# become no-ops, so metrics stay strictly optional.

def record_connection_started() -> None:
    if METRICS_AVAILABLE:
        _CONNECTIONS_TOTAL.inc()
        _ACTIVE_CONNECTIONS.inc()


def record_connection_ended() -> None:
    if METRICS_AVAILABLE:
        _ACTIVE_CONNECTIONS.dec()


def record_handshake_failure(reason: str) -> None:
    if METRICS_AVAILABLE:
        _HANDSHAKE_FAILURES_TOTAL.labels(reason=reason).inc()


def record_timeout() -> None:
    if METRICS_AVAILABLE:
        _CONNECTION_TIMEOUTS_TOTAL.inc()


def observe_message_bytes(n: int) -> None:
    if METRICS_AVAILABLE:
        _MESSAGE_BYTES.observe(n)
