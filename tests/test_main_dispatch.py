import sys
from unittest.mock import patch

import pytest

from qasccs.__main__ import main


def test_dispatch_risk_calls_risk_main_with_sliced_argv():
    with patch.object(sys, "argv", ["qasccs", "risk", "--algorithm", "RSA-2048", "--data-lifetime-years", "10"]):
        with patch("qasccs.quantum_risk_engine.cli.main") as mock_main:
            exit_code = main()
            # Assert argv slicing while still inside the patch context, before it's restored.
            assert sys.argv[1:] == ["--algorithm", "RSA-2048", "--data-lifetime-years", "10"]
    mock_main.assert_called_once_with()
    assert exit_code == 0


def test_dispatch_server_calls_server_main_and_returns_its_exit_code():
    with patch.object(sys, "argv", ["qasccs", "server", "--port", "9999"]):
        with patch("qasccs.secure_channel.server.main", return_value=7) as mock_main:
            exit_code = main()
    mock_main.assert_called_once_with()
    assert exit_code == 7


def test_dispatch_client_calls_client_main_and_returns_its_exit_code():
    with patch.object(sys, "argv", ["qasccs", "client", "--data-lifetime-years", "5"]):
        with patch("qasccs.secure_channel.client.main", return_value=2) as mock_main:
            exit_code = main()
    mock_main.assert_called_once_with()
    assert exit_code == 2


def test_dispatch_gen_certs_calls_gen_certs_main():
    with patch.object(sys, "argv", ["qasccs", "gen-certs", "--out", "/tmp/certs"]):
        with patch("qasccs.tools.gen_certs.main") as mock_main:
            exit_code = main()
    mock_main.assert_called_once_with()
    assert exit_code == 0


def test_dispatch_web_calls_webapp_main_and_returns_its_exit_code():
    with patch.object(sys, "argv", ["qasccs", "web", "--port", "8000"]):
        with patch("qasccs.webapp.app.main", return_value=0) as mock_main:
            exit_code = main()
    mock_main.assert_called_once_with()
    assert exit_code == 0


def test_dispatch_web_gives_clear_error_when_web_extra_missing(capsys):
    with patch.object(sys, "argv", ["qasccs", "web"]):
        with patch.dict(sys.modules, {"qasccs.webapp.app": None}):
            exit_code = main()
    assert exit_code == 1
    assert "web" in capsys.readouterr().err


def test_dispatch_no_subcommand_prints_usage_and_returns_1(capsys):
    with patch.object(sys, "argv", ["qasccs"]):
        exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_dispatch_unknown_subcommand_exits_nonzero():
    with patch.object(sys, "argv", ["qasccs", "not-a-real-subcommand"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0
