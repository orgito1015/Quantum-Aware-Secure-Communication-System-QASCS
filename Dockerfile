# syntax=docker/dockerfile:1

# ---- builder: compile the package + deps into an isolated prefix ----
FROM python:3.14-slim AS builder

WORKDIR /build
COPY pyproject.toml requirements.txt README.md ./
COPY qasccs ./qasccs

RUN pip install --no-cache-dir --prefix=/install .

# ---- runtime: minimal image, no compilers/build tools, non-root user ----
FROM python:3.14-slim AS runtime

# Security-relevant OS packages only; no build toolchain in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system qascs && useradd --system --gid qascs --create-home --home-dir /home/qascs qascs

COPY --from=builder /install /usr/local

ENV PYTHONUNBUFFERED=1 \
    QASCS_HOST=0.0.0.0 \
    QASCS_PORT=8443 \
    QASCS_LOG_LEVEL=INFO \
    QASCS_CERT_DIR=/certs

# Certs are NOT baked into the image. Mount your provisioned PKI material
# (or dev certs generated with `qasccs.tools.gen_certs`) at /certs at runtime:
#   docker run -v ./certs:/certs:ro ...
# See the "Production considerations" section in README.md.
RUN mkdir -p /certs && chown qascs:qascs /certs
VOLUME ["/certs"]

USER qascs
WORKDIR /home/qascs

EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('127.0.0.1', ${QASCS_PORT:-8443}), timeout=3); s.close()" || exit 1
# Note: this is a bare TCP liveness probe (the server is mTLS-only, and the
# healthcheck has no client cert to complete a real handshake with), so each
# probe will log one benign "UNEXPECTED_EOF_WHILE_READING" warning server-side.
# That's expected noise, not a failure signal.

# Default: run the mTLS server. Override the command to run the client or
# the quantum risk-engine CLI instead, e.g.:
#   docker run qasccs qasccs risk --algorithm RSA-2048 --data-lifetime-years 10
ENTRYPOINT ["qasccs", "server"]
