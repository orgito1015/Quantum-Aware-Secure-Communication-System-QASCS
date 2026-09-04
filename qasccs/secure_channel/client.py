from __future__ import annotations
import argparse
import os
import socket
import ssl
import sys

from ..logging_config import configure_logging
from ..quantum_risk_engine.models import RiskRequest
from ..quantum_risk_engine.policy import evaluate_risk
from ..quantum_risk_engine.policy_config import PolicyConfigError, load_scenario_years
from .common import CertificateConfigError, make_client_context, send_msg, recv_msg
from .protocol import Envelope, ProtocolError, decode_envelope, encode_envelope

log = configure_logging("qasccs.client")

CONNECT_TIMEOUT_SECONDS = float(os.environ.get("QASCS_CONNECT_TIMEOUT", "5"))


def main() -> int:
    ap = argparse.ArgumentParser(description="QASCS Secure Client (quantum-aware policy + mTLS demo)")
    ap.add_argument("--host", default=os.environ.get("QASCS_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("QASCS_PORT", "8443")))
    ap.add_argument(
        "--tls-server-name",
        default=os.environ.get("QASCS_TLS_SERVER_NAME"),
        help=(
            "Hostname to verify the server's certificate against (SNI + hostname check). "
            "Defaults to --host. Set this separately from --host when the connection "
            "target (a Kubernetes Service name, load balancer, container hostname, etc.) "
            "differs from the identity the certificate was issued for, e.g. the bundled "
            "dev cert is issued for 'qasccs.local'/'localhost'/'127.0.0.1'."
        ),
    )
    ap.add_argument("--data-lifetime-years", type=int, required=True)
    ap.add_argument("--data-classification", default="medium", choices=["low", "medium", "high", "critical"])
    ap.add_argument("--scenario", default="moderate", choices=["conservative", "moderate", "aggressive"])
    ap.add_argument("--algorithm", default="ECC-P256", help="Crypto used today (default ECC-P256).")
    ap.add_argument("--message", default="hello from QASCS")
    ap.add_argument(
        "--policy-config",
        default=os.environ.get("QASCS_POLICY_CONFIG"),
        help="Path to a YAML file overriding the scenario-year model (see docs/pqc-integration.md).",
    )
    ap.add_argument(
        "--strict-policy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When the Quantum Risk Engine recommends pqc/hybrid, refuse to proceed with "
            "classical-only TLS (exit 2) instead of silently downgrading. On by default. "
            "Use --no-strict-policy or --allow-classical-fallback to opt out."
        ),
    )
    ap.add_argument(
        "--allow-classical-fallback",
        action="store_true",
        default=False,
        help="Explicitly allow proceeding with classical TLS even when policy recommends pqc/hybrid.",
    )
    args = ap.parse_args()

    req = RiskRequest(
        algorithm=args.algorithm,
        data_lifetime_years=args.data_lifetime_years,
        data_classification=args.data_classification,
        scenario=args.scenario,
    )
    try:
        scenario_years = load_scenario_years(args.policy_config)
    except PolicyConfigError as e:
        log.error(str(e))
        return 1
    resp = evaluate_risk(req, scenario_years=scenario_years)

    log.info("Quantum Risk Engine decision: risk=%s recommended_mode=%s quantum_safe_until=%s",
              resp.risk, resp.recommended_mode, resp.quantum_safe_until_year)
    log.info("Rationale: %s", resp.rationale)

    if resp.recommended_mode in ("pqc", "hybrid"):
        if args.strict_policy and not args.allow_classical_fallback:
            log.error(
                "Policy recommends '%s' but only classical TLS is implemented (pqc_tls.py is a "
                "placeholder). Refusing to silently downgrade. Pass --allow-classical-fallback to "
                "proceed anyway, or --no-strict-policy to disable this check. See "
                "docs/pqc-integration.md for the OQS-OpenSSL integration path.",
                resp.recommended_mode,
            )
            return 2
        reason = "--allow-classical-fallback" if args.allow_classical_fallback else "--no-strict-policy"
        log.warning(
            "PQC/hybrid enforcement needs OQS-OpenSSL (see docs/pqc-integration.md); "
            "proceeding with classical mTLS because %s was passed.",
            reason,
        )

    try:
        ctx = make_client_context()
    except CertificateConfigError as e:
        log.error(str(e))
        return 1

    try:
        with socket.create_connection((args.host, args.port), timeout=CONNECT_TIMEOUT_SECONDS) as sock:
            server_name = args.tls_server_name or args.host
            with ctx.wrap_socket(sock, server_hostname=server_name) as tls:
                req_env = Envelope.new("echo_request", args.message.encode("utf-8"))
                send_msg(tls, encode_envelope(req_env))
                reply = recv_msg(tls)
                if reply is None:
                    log.error("Server closed the connection without replying")
                    return 1
                try:
                    resp_env = decode_envelope(reply)
                except ProtocolError as e:
                    log.error("Malformed reply from server: %s", e)
                    return 1
                if resp_env.correlation_id != req_env.correlation_id:
                    log.warning(
                        "Reply correlation_id %s does not match request %s",
                        resp_env.correlation_id, req_env.correlation_id,
                    )
                log.info("Server replied (%s): %s", resp_env.type, resp_env.payload.decode("utf-8", errors="replace"))
    except ssl.SSLError as e:
        log.error("TLS error: %s", e)
        return 1
    except (TimeoutError, OSError) as e:
        log.error("Connection error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
