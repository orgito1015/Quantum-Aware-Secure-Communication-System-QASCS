import pytest
import shutil
import socket
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from qasccs.tools.gen_certs import main as gen_certs_main


@pytest.fixture
def temp_certs():
    """Create temporary CA + server + client certificates for testing"""
    temp_dir = tempfile.mkdtemp()
    cert_dir = Path(temp_dir) / "certs"
    cert_dir.mkdir()

    test_args = ["prog", "--out", str(cert_dir)]
    with patch.object(sys, 'argv', test_args):
        gen_certs_main()

    yield cert_dir
    shutil.rmtree(temp_dir)


@contextmanager
def _patched_cert_paths(cert_dir: Path):
    """Point qasccs.secure_channel.common's module-level cert paths at cert_dir."""
    import qasccs.secure_channel.common as common_module
    originals = {
        "CERT_DIR": common_module.CERT_DIR,
        "SERVER_CERT": common_module.SERVER_CERT,
        "SERVER_KEY": common_module.SERVER_KEY,
        "CLIENT_CERT": common_module.CLIENT_CERT,
        "CLIENT_KEY": common_module.CLIENT_KEY,
        "CA_CERT": common_module.CA_CERT,
    }
    try:
        common_module.CERT_DIR = cert_dir
        common_module.SERVER_CERT = cert_dir / "server.crt"
        common_module.SERVER_KEY = cert_dir / "server.key"
        common_module.CLIENT_CERT = cert_dir / "client.crt"
        common_module.CLIENT_KEY = cert_dir / "client.key"
        common_module.CA_CERT = cert_dir / "ca.crt"
        yield common_module
    finally:
        for attr, value in originals.items():
            setattr(common_module, attr, value)


def free_port() -> int:
    """Pick a currently-free TCP port on 127.0.0.1 (best-effort; not reserved)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
