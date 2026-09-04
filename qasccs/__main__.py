from __future__ import annotations
import argparse
import sys

SUBCOMMANDS = ("risk", "server", "client", "gen-certs", "web")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qasccs",
        description="QASCS — Quantum-Aware Secure Communication System",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{" + ",".join(SUBCOMMANDS) + "}")
    subparsers.add_parser("risk", help="Evaluate the Quantum Risk Engine for an algorithm/lifetime/classification.",
                           add_help=False)
    subparsers.add_parser("server", help="Run the mTLS secure-channel server.", add_help=False)
    subparsers.add_parser("client", help="Run the mTLS secure-channel client.", add_help=False)
    subparsers.add_parser("gen-certs", help="Generate dev-only CA + server/client certificates.", add_help=False)
    subparsers.add_parser("web", help="Run the optional FastAPI risk-engine dashboard (requires the 'web' extra).",
                           add_help=False)
    return parser


def main() -> int:
    parser = _build_parser()
    # Only the subcommand name is parsed here; everything after it is handed
    # off verbatim to that subcommand's own argparse parser (so e.g.
    # `qasccs client --host ... --data-lifetime-years ...` keeps working with
    # each submodule's existing, independently-tested argument definitions).
    args, remainder = parser.parse_known_args()

    if args.command is None:
        parser.print_help()
        return 1

    sys.argv = [f"qasccs {args.command}"] + remainder

    if args.command == "risk":
        from qasccs.quantum_risk_engine.cli import main as risk_main
        risk_main()
        return 0
    elif args.command == "server":
        from qasccs.secure_channel.server import main as server_main
        return server_main()
    elif args.command == "client":
        from qasccs.secure_channel.client import main as client_main
        return client_main()
    elif args.command == "gen-certs":
        from qasccs.tools.gen_certs import main as gen_certs_main
        gen_certs_main()
        return 0
    elif args.command == "web":
        try:
            from qasccs.webapp.app import main as web_main
        except ImportError:
            print(
                "The web dashboard requires the 'web' extra: pip install -e '.[web]'",
                file=sys.stderr,
            )
            return 1
        return web_main()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
