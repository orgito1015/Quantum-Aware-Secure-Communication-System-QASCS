# Scaling / high availability

QASCS's `secure_channel/server.py` is a single process today: one
`ThreadPoolExecutor`-backed accept loop, bounded by `QASCS_MAX_CONNECTIONS`
and `QASCS_CONN_TIMEOUT`. This is a deliberate, documented scope limit (see
the README's "Production considerations"), not an oversight — this section
describes the recommended path if you need more than one replica.

## Recommended architecture: stateless replicas behind an L4 load balancer

Because the server does mutual TLS (mTLS) — it terminates TLS and verifies
the client certificate itself — the load balancer in front of multiple
replicas **must** be a Layer 4 (TCP-passthrough) balancer, not an L7/HTTP
reverse proxy that terminates TLS itself. If TLS terminates at the LB, the
LB (not your replica) would need the client cert material and the mTLS
handshake semantics this project relies on would move outside the
application entirely.

```
            ┌───────────────┐
 clients ─▶ │  L4 LB (TCP)  │
            └───────┬───────┘
             passthrough (no TLS termination)
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   replica 1     replica 2     replica 3
  (mTLS here)   (mTLS here)   (mTLS here)
```

Each replica is a normal `qasccs server` process (or container) — no
special clustering code needed, since each one independently does its own
handshake and connection handling. This is why the current single-process
design scales out cleanly without code changes for the common case.

## What does NOT scale automatically

- **`QASCS_MAX_CONNECTIONS` is per-replica only.** Three replicas each
  configured with `QASCS_MAX_CONNECTIONS=100` give you 300 total concurrent
  connections, not a global cap of 100. If you need a true global cap
  (e.g. for a downstream capacity limit), that requires a shared external
  counter — Redis (`INCR`/`DECR` with a TTL, or a Lua script for atomicity)
  is the natural choice, but **this is not implemented** in this repo.
- **`QASCS_CONN_TIMEOUT` and rate limiting** are also per-replica/per-connection;
  there's no cross-replica request-rate coordination.
- **Prometheus metrics** (see `qasccs/secure_channel/metrics.py`,
  opt-in via `QASCS_METRICS_PORT`) are per-replica counters. Aggregate them
  at the Prometheus/Grafana layer (`sum by (...)` queries across replica
  targets), not in-process.

## Why this is intentionally out of scope here

Implementing a global connection cap would mean either:
1. Adding a hard runtime dependency on Redis (or similar) for a project
   that's otherwise dependency-light and easy to run standalone, or
2. Building a custom gossip/consensus mechanism between replicas, which is
   a large amount of complexity for a reference/demo project.

If you need this for a real deployment, treat it as a deployment-specific
decision layered on top of QASCS rather than something QASCS should bake in
by default.
