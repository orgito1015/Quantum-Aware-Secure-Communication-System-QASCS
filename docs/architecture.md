# Architecture (QASCS)

## High-level flow
1. Client wants confidentiality for `N` years.
2. Client requests a **policy decision** from the Quantum Risk Engine.
3. Policy returns `recommended_mode` + risk details.
4. Client enforces the decision:
   - today: Python TLS (`classical`)
   - `pqc`/`hybrid` recommended but unimplemented: refuse by default
     (`--strict-policy`, see `docs/pqc-integration.md`) unless the operator
     explicitly opts into a classical fallback.
   - extension: OQS-OpenSSL (`pqc` / `hybrid`) — not implemented yet.
5. Secure channel established (mutual TLS) → versioned message envelopes
   exchanged over the length-prefixed wire framing.

## Sequence diagram

```mermaid
sequenceDiagram
    participant U as Operator
    participant C as qasccs client
    participant R as Quantum Risk Engine
    participant S as qasccs server

    U->>C: qasccs client --algorithm ... --data-lifetime-years ...
    C->>R: evaluate_risk(RiskRequest)
    R-->>C: RiskResponse(risk, recommended_mode, ...)
    alt recommended_mode is pqc/hybrid and --strict-policy (default)
        C-->>U: exit 2 (refuse to silently downgrade)
    else classical, or --allow-classical-fallback passed
        C->>S: TCP connect + mTLS handshake (client cert presented)
        S-->>C: mTLS handshake (server cert verified)
        C->>S: send_msg(Envelope{type: echo_request, payload})
        S-->>C: send_msg(Envelope{type: echo_response, same correlation_id})
        C-->>U: log decision + server reply
    end
```

## Component diagram

```mermaid
graph TD
    subgraph quantum_risk_engine
        models[models.py<br/>RiskRequest / RiskResponse]
        policy[policy.py<br/>evaluate_risk]
        policy_config[policy_config.py<br/>YAML scenario overrides]
        policy --> models
        policy --> policy_config
    end

    subgraph secure_channel
        common[common.py<br/>mTLS contexts, framing]
        protocol[protocol.py<br/>Envelope]
        server[server.py<br/>threaded accept loop]
        client[client.py<br/>CLI]
        metrics[metrics.py<br/>Prometheus, opt-in]
        server --> common
        server --> protocol
        server --> metrics
        client --> common
        client --> protocol
        client --> policy
        client --> policy_config
    end

    subgraph tools
        gen_certs[gen_certs.py<br/>dev CA + certs]
        pqc_tls[pqc_tls.py<br/>placeholder]
    end

    subgraph webapp[webapp - optional, web extra]
        app[app.py<br/>FastAPI dashboard]
        app --> policy
        app --> policy_config
    end

    cli[__main__.py<br/>unified qasccs CLI] --> policy
    cli --> server
    cli --> client
    cli --> gen_certs
    cli --> app
```
