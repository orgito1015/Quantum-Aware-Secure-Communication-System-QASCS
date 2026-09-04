# Threat model (Quantum-aware)

This project explicitly models a **quantum-capable adversary** and focuses on **long-term confidentiality**.

## Quantum algorithms
- **Shor's algorithm** breaks RSA/DH/ECC → recorded sessions become decryptable once feasible.
- **Grover's algorithm** reduces symmetric security roughly by half (in bits).

## Design decision
Use the **Quantum Risk Engine** to decide when to require `classical`, `pqc`, or `hybrid`.

## Standards references

The `KYBER-768` / `DILITHIUM-3` algorithm literals used in
`qasccs/quantum_risk_engine/models.py` refer to the NIST post-quantum
finalists by their pre-standardization names. NIST finalized these as FIPS
standards in 2024 under new names:

| Informal name | FIPS-standardized name | Standard |
| --- | --- | --- |
| Kyber | ML-KEM (Module-Lattice-Based Key-Encapsulation Mechanism) | [FIPS 203](https://csrc.nist.gov/pubs/fips/203/final) |
| Dilithium | ML-DSA (Module-Lattice-Based Digital Signature Algorithm) | [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final) |
| SPHINCS+ | SLH-DSA (Stateless Hash-Based Digital Signature Algorithm) | [FIPS 205](https://csrc.nist.gov/pubs/fips/205/final) |

See NIST's [Post-Quantum Cryptography project page](https://csrc.nist.gov/projects/post-quantum-cryptography)
for the full standardization history and ongoing work (e.g. the additional
signature on-ramp).

`Algorithm` in `models.py` still uses the informal `KYBER-768`/`DILITHIUM-3`
names since that's how they're commonly referenced in tooling and docs today;
a future revision should consider adding the FIPS names as accepted aliases
(or migrating to them outright) as ML-KEM/ML-DSA naming becomes dominant.

## Further reading

- NIST Post-Quantum Cryptography project: https://csrc.nist.gov/projects/post-quantum-cryptography
