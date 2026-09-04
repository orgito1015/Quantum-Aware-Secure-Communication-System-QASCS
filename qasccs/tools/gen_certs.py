from __future__ import annotations
import argparse
import os
import stat
from pathlib import Path
import datetime
from datetime import timezone
import ipaddress

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _write(p: Path, data: bytes, *, private: bool = False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if private:
        # Restrict private key files to owner read/write only (POSIX; no-op on Windows).
        try:
            os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
        except (NotImplementedError, OSError):
            pass


def _leaf_cert(
    *,
    ca_key,
    ca_cert,
    common_name: str,
    san,
    extended_key_usage: x509.ExtendedKeyUsage,
    validity_days: int,
):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "AL"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "QASCS-Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=validity_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(extended_key_usage, critical=False)
    )
    if san is not None:
        builder = builder.add_extension(san, critical=False)

    cert = builder.sign(ca_key, hashes.SHA256())
    return key, cert


_ALL_OUTPUT_FILES = ("ca.crt", "ca.key", "server.crt", "server.key", "client.crt", "client.key")


def main():
    ap = argparse.ArgumentParser(description="Generate dev-only CA + server + client certs for QASCS (supports mTLS)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if cert/key files already exist in --out (overwrites them).",
    )
    args = ap.parse_args()
    out = Path(args.out)

    # Idempotent by default: re-running this (e.g. because `docker compose run`
    # re-triggers a one-shot dependency service on every invocation, even after
    # it already completed successfully) would otherwise mint a brand-new
    # random CA each time and silently break trust between already-issued
    # server/client certs and whichever peer reads the CA file next.
    if not args.force and all((out / name).is_file() for name in _ALL_OUTPUT_FILES):
        print(f"[gen_certs] Certs already exist in: {out.resolve()} (use --force to regenerate)")
        return

    # --- CA ---
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "AL"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "QASCS-Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "QASCS Dev CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # --- Server leaf cert (serverAuth EKU) ---
    server_san = x509.SubjectAlternativeName([
        x509.DNSName("qasccs.local"),
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ])
    server_key, server_cert = _leaf_cert(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="qasccs.local",
        san=server_san,
        extended_key_usage=x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
        validity_days=825,
    )

    # --- Client leaf cert (clientAuth EKU, for mutual TLS) ---
    client_key, client_cert = _leaf_cert(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="qasccs-client",
        san=None,
        extended_key_usage=x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
        validity_days=825,
    )

    _write(out / "ca.crt", ca_cert.public_bytes(serialization.Encoding.PEM))
    _write(
        out / "ca.key",
        ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
        private=True,
    )
    _write(out / "server.crt", server_cert.public_bytes(serialization.Encoding.PEM))
    _write(
        out / "server.key",
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
        private=True,
    )
    _write(out / "client.crt", client_cert.public_bytes(serialization.Encoding.PEM))
    _write(
        out / "client.key",
        client_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
        private=True,
    )

    print(f"[gen_certs] Wrote dev CA + server + client certs to: {out.resolve()}")
    print("[gen_certs] WARNING: dev-only self-signed CA. Do not use in production.")


if __name__ == "__main__":
    main()
