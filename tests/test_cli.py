import pytest
import json
import sys
from unittest.mock import patch
from qasccs.quantum_risk_engine.cli import main


def test_cli_basic_invocation(capsys):
    """Test basic CLI invocation with required arguments"""
    test_args = [
        "prog",
        "--algorithm", "RSA-2048",
        "--data-lifetime-years", "10"
    ]
    
    with patch.object(sys, 'argv', test_args):
        main()
    
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    assert "risk" in output
    assert "recommended_mode" in output
    assert "quantum_safe_until_year" in output
    assert "rationale" in output


def test_cli_with_all_arguments(capsys):
    """Test CLI with all optional arguments"""
    test_args = [
        "prog",
        "--algorithm", "ECC-P256",
        "--data-lifetime-years", "15",
        "--data-classification", "high",
        "--scenario", "aggressive"
    ]
    
    with patch.object(sys, 'argv', test_args):
        main()
    
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    assert output["risk"] in ["LOW", "MEDIUM", "HIGH"]
    assert output["recommended_mode"] in ["classical", "pqc", "hybrid"]
    assert output["quantum_safe_until_year"] > 0


def test_cli_pqc_algorithm(capsys):
    """Test CLI with PQC algorithm"""
    test_args = [
        "prog",
        "--algorithm", "KYBER-768",
        "--data-lifetime-years", "20",
        "--data-classification", "critical"
    ]
    
    with patch.object(sys, 'argv', test_args):
        main()
    
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    assert output["recommended_mode"] in ["pqc", "hybrid"]


def test_cli_conservative_scenario(capsys):
    """Test CLI with conservative scenario"""
    test_args = [
        "prog",
        "--algorithm", "RSA-4096",
        "--data-lifetime-years", "5",
        "--scenario", "conservative"
    ]
    
    with patch.object(sys, 'argv', test_args):
        main()
    
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    assert "notes" in output


def test_cli_json_output_format(capsys):
    """Test that CLI outputs valid JSON"""
    test_args = [
        "prog",
        "--algorithm", "AES-256",
        "--data-lifetime-years", "10"
    ]
    
    with patch.object(sys, 'argv', test_args):
        main()
    
    captured = capsys.readouterr()
    
    # Should not raise exception if valid JSON
    output = json.loads(captured.out)
    assert isinstance(output, dict)


def test_cli_missing_required_argument():
    """Test CLI with missing required argument"""
    test_args = [
        "prog",
        "--algorithm", "RSA-2048"
        # Missing --data-lifetime-years
    ]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            main()


def test_cli_invalid_algorithm():
    """Test CLI with invalid algorithm"""
    test_args = [
        "prog",
        "--algorithm", "INVALID-ALGO",
        "--data-lifetime-years", "10"
    ]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            # pydantic validation should fail
            main()


def test_cli_invalid_classification():
    """Test CLI with invalid classification"""
    test_args = [
        "prog",
        "--algorithm", "RSA-2048",
        "--data-lifetime-years", "10",
        "--data-classification", "ultra-high"
    ]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            main()


def test_cli_invalid_scenario():
    """Test CLI with invalid scenario"""
    test_args = [
        "prog",
        "--algorithm", "RSA-2048",
        "--data-lifetime-years", "10",
        "--scenario", "extreme"
    ]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit):
            main()
