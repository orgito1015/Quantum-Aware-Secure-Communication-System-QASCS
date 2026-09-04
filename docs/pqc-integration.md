# PQC / Hybrid TLS integration

Python's `ssl` cannot do post-quantum TLS directly.

## Recommended path: OQS-OpenSSL + oqsprovider
Use `openssl s_server` / `openssl s_client` with PQC/hybrid groups, backed by
[liboqs](https://github.com/open-quantum-safe/liboqs) and
[oqs-provider](https://github.com/open-quantum-safe/oqs-provider) (OpenSSL 3.x).

This repo keeps **one policy engine** (quantum risk) and switches the enforcement layer:
- `classical` → Python TLS
- `pqc/hybrid` → OQS-OpenSSL endpoints (wrapper placeholder in `qasccs/tools/pqc_tls.py`)

## Current enforcement status

`qasccs/secure_channel/client.py` does **not** implement the OQS-OpenSSL
wrapper yet — `pqc_tls.py` is still a placeholder. Rather than silently
running classical TLS when the Quantum Risk Engine recommends `pqc`/`hybrid`,
the client enforces this loudly by default:

- `--strict-policy` (default **on**): if `recommended_mode` is `pqc` or
  `hybrid` and only classical TLS is available, the client exits with code
  `2` and an operator-actionable error instead of proceeding.
- `--allow-classical-fallback`: opt back into the old demo behavior (proceed
  with classical TLS, with a warning logged) — useful for local
  experimentation when you know the gap is expected.
- `--no-strict-policy`: disables strict enforcement entirely (same effect as
  the fallback flag, offered for symmetry with `--strict-policy`).

Implementing the real OQS-OpenSSL subprocess wrapper (shelling out to
`openssl s_server`/`s_client` built against `oqsprovider` when
`recommended_mode != "classical"`) remains a larger follow-up — it requires
`liboqs`/`oqs-provider` to be built and packaged for every target platform,
which is a substantially bigger effort than the Python-side wrapper code
itself.

## Standards references

See `docs/threat-model.md` for the FIPS 203/204/205 (ML-KEM/ML-DSA/SLH-DSA)
mapping to the informal Kyber/Dilithium/SPHINCS+ names used in this repo's
`Algorithm` literals, and NIST's
[Post-Quantum Cryptography project page](https://csrc.nist.gov/projects/post-quantum-cryptography).
