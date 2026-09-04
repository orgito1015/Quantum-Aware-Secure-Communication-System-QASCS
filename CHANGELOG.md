# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) (while
pre-1.0, breaking changes may still land in a minor version bump).

## [Unreleased]

## [0.2.0] - 2026-09-04

### Added
- Unified `qasccs` CLI: a single console-script entry point
  (`pip install .` now provides a real `qasccs` executable) with
  `risk`/`server`/`client`/`gen-certs`/`web` subcommands, alongside the
  still-supported `python -m qasccs.<module>` invocations.
- `--strict-policy` / `--allow-classical-fallback` on the secure-channel
  client: refuses (exit code 2) to silently proceed with classical-only TLS
  when the Quantum Risk Engine recommends `pqc`/`hybrid`, instead of just
  logging a warning.
- Versioned message envelope (`secure_channel/protocol.py`) replacing the
  raw-bytes echo protocol — structured `type`/`version`/`correlation_id`/
  payload, extensible for future message types.
- Configurable scenario-year model: `--policy-config` / `QASCS_POLICY_CONFIG`
  to override the Shor-year assumptions per scenario via YAML instead of
  editing source.
- Optional FastAPI risk-engine web dashboard (`qasccs web`, `pip install
  ".[web]"`) — the one place in this project where accessibility/responsive
  design genuinely applies.
- Optional Prometheus metrics for the secure-channel server
  (`QASCS_METRICS_PORT`, `pip install ".[observability]"`).
- `SECURITY.md`, `docs/scaling.md`, Mermaid architecture/sequence diagrams
  in `docs/architecture.md`, FIPS 203/204/205 references in
  `docs/threat-model.md` and `docs/pqc-integration.md`.
- `mypy` added to the toolchain and CI, alongside `ruff`.
- Test coverage for `secure_channel/server.py`'s real accept loop
  (graceful shutdown, connection timeout, max-connections behavior) and for
  `qasccs/__main__.py`'s subcommand dispatch — previously 0% covered.
- `gen_certs.py` is now idempotent by default (skips regeneration if certs
  already exist; `--force` to regenerate) — fixes a real bug where
  `docker compose run`/`up` re-triggering the one-shot `gen-certs` dependency
  service would mint a fresh random CA each time and break trust between an
  already-running server and a freshly-run client.
- `.pre-commit-config.yaml`, `.github/dependabot.yml`,
  `.github/workflows/release.yml` (PyPI Trusted Publishing on `v*` tags).

### Changed
- CI test matrix: `3.8`/`3.9` (already incompatible with this package's
  `requires-python = ">=3.10"`, so those jobs were silently broken) replaced
  with `3.10`/`3.11`/`3.12`/`3.13`, matching both the Dockerfile's Python
  version and what's actually supported.
- `Dockerfile` `ENTRYPOINT` and `docker-compose.yml` service entrypoints now
  use the unified `qasccs` command.

### Removed
- The unattributed, unreferenced PDF at the repo root (see the "Further
  reading" link in `docs/threat-model.md` instead).

## [0.1.0] - Initial release

- Quantum Risk Engine (`qasccs/quantum_risk_engine/`).
- mTLS secure channel client/server (`qasccs/secure_channel/`).
- Dev-only cert generator (`qasccs/tools/gen_certs.py`).
- CI (pytest + ruff), Dockerfile, GitHub project management scaffolding.
