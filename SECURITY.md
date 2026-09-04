# Security Policy

QASCS is a research/reference project for quantum-aware cryptographic policy
and mutual-TLS secure communication. Its subject matter is security, so we
take reports about the project's own security seriously.

## Supported versions

The project is pre-1.0 (`0.x`). Only the latest released version receives
fixes; there is no long-term-support branch at this stage.

| Version | Supported |
| ------- | --------- |
| latest `0.x` | ✅ |
| older `0.x` releases | ❌ |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting for this repository:

1. Go to the repository's **Security** tab.
2. Select **Report a vulnerability**.
3. Describe the issue, the affected version/commit, and steps to reproduce.

This opens a private advisory visible only to the maintainers and you, and
lets us coordinate a fix and disclosure timeline before any public issue is
created.

## What's in scope

- The Quantum Risk Engine (`qasccs/quantum_risk_engine/`) — logic errors that
  cause an unsafe crypto recommendation.
- The secure channel (`qasccs/secure_channel/`) — TLS/mTLS configuration
  weaknesses, message-framing bugs, or ways policy enforcement (e.g.
  `--strict-policy`) can be silently bypassed.
- The dev cert generator (`qasccs/tools/gen_certs.py`) — as long as the report
  doesn't just restate "this is a dev-only self-signed CA," which is already
  documented and intentional.

## What's out of scope

- The bundled dev CA/certs being untrusted by browsers or OS trust stores —
  that's by design (see the README's "Production considerations" section).
- Denial of service against the demo server beyond what
  `QASCS_MAX_CONNECTIONS`/`QASCS_CONN_TIMEOUT` are documented to bound.

## Response expectations

We'll acknowledge new reports as promptly as we can and keep you updated as
we investigate. Response times aren't formally SLA'd on a project at this
stage, but private reports won't be ignored.
