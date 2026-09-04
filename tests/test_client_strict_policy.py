import sys
from unittest.mock import patch

from qasccs.secure_channel import client as client_module


def _run_client(extra_args):
    args = [
        "prog",
        "--host", "127.0.0.1", "--port", "1",  # never actually connected to when blocked early
        "--data-lifetime-years", "20",
        "--data-classification", "critical",  # forces recommended_mode in (pqc, hybrid)
    ] + extra_args
    with patch.object(sys, "argv", args):
        return client_module.main()


def test_strict_policy_blocks_by_default_before_connecting():
    exit_code = _run_client([])
    assert exit_code == 2


def test_allow_classical_fallback_bypasses_strict_block(monkeypatch):
    # Force a deterministic connection error (no real server) rather than
    # letting this test depend on network state — we only care that we got
    # PAST the strict-policy block and attempted a connection.
    exit_code = _run_client(["--allow-classical-fallback"])
    assert exit_code == 1  # connection error (nothing listening), not the strict-policy exit(2)


def test_no_strict_policy_bypasses_strict_block():
    exit_code = _run_client(["--no-strict-policy"])
    assert exit_code == 1  # connection error, not the strict-policy exit(2)


def test_strict_policy_not_triggered_for_classical_recommendation():
    args = [
        "prog",
        "--host", "127.0.0.1", "--port", "1",
        "--data-lifetime-years", "1",
        "--data-classification", "low",
        "--algorithm", "AES-256",
    ]
    with patch.object(sys, "argv", args):
        exit_code = client_module.main()
    assert exit_code == 1  # connection error, never hit the strict-policy branch at all


def test_client_reports_policy_config_error(tmp_path):
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text("not: a valid policy config\n")
    args = [
        "prog",
        "--host", "127.0.0.1", "--port", "1",
        "--data-lifetime-years", "10",
        "--policy-config", str(bad_config),
    ]
    with patch.object(sys, "argv", args):
        exit_code = client_module.main()
    assert exit_code == 1
