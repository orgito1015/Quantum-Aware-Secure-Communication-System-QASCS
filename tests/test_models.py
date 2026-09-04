import pytest
from pydantic import ValidationError
from qasccs.quantum_risk_engine.models import RiskRequest, RiskResponse


def test_risk_request_valid():
    """Test valid RiskRequest creation"""
    req = RiskRequest(
        algorithm="ECC-P256",
        data_lifetime_years=10,
        data_classification="high",
        scenario="moderate"
    )
    assert req.algorithm == "ECC-P256"
    assert req.data_lifetime_years == 10
    assert req.data_classification == "high"
    assert req.scenario == "moderate"


def test_risk_request_defaults():
    """Test RiskRequest with default values"""
    req = RiskRequest(
        algorithm="RSA-2048",
        data_lifetime_years=5
    )
    assert req.data_classification == "medium"
    assert req.scenario == "moderate"


def test_risk_request_invalid_lifetime_too_low():
    """Test RiskRequest with data_lifetime_years below minimum"""
    with pytest.raises(ValidationError):
        RiskRequest(
            algorithm="AES-256",
            data_lifetime_years=0
        )


def test_risk_request_invalid_lifetime_too_high():
    """Test RiskRequest with data_lifetime_years above maximum"""
    with pytest.raises(ValidationError):
        RiskRequest(
            algorithm="AES-256",
            data_lifetime_years=51
        )


def test_risk_request_invalid_algorithm():
    """Test RiskRequest with invalid algorithm"""
    with pytest.raises(ValidationError):
        RiskRequest(
            algorithm="INVALID-ALGO",
            data_lifetime_years=10
        )


def test_risk_request_invalid_classification():
    """Test RiskRequest with invalid data classification"""
    with pytest.raises(ValidationError):
        RiskRequest(
            algorithm="RSA-2048",
            data_lifetime_years=10,
            data_classification="super-critical"
        )


def test_risk_request_invalid_scenario():
    """Test RiskRequest with invalid scenario"""
    with pytest.raises(ValidationError):
        RiskRequest(
            algorithm="RSA-2048",
            data_lifetime_years=10,
            scenario="extreme"
        )


def test_risk_response_creation():
    """Test valid RiskResponse creation"""
    resp = RiskResponse(
        risk="HIGH",
        recommended_mode="hybrid",
        quantum_safe_until_year=2030,
        rationale="Test rationale"
    )
    assert resp.risk == "HIGH"
    assert resp.recommended_mode == "hybrid"
    assert resp.quantum_safe_until_year == 2030
    assert resp.rationale == "Test rationale"
    assert resp.notes is None


def test_risk_response_with_notes():
    """Test RiskResponse with optional notes"""
    resp = RiskResponse(
        risk="MEDIUM",
        recommended_mode="classical",
        quantum_safe_until_year=2035,
        rationale="Test rationale",
        notes="Additional notes"
    )
    assert resp.notes == "Additional notes"


def test_all_supported_algorithms():
    """Test all supported algorithms are accepted"""
    algorithms = [
        "RSA-2048", "RSA-3072", "RSA-4096",
        "ECC-P256", "ECC-P384",
        "AES-128", "AES-256",
        "KYBER-768", "DILITHIUM-3", "HYBRID-ECDHE+KYBER"
    ]
    for algo in algorithms:
        req = RiskRequest(
            algorithm=algo,
            data_lifetime_years=10
        )
        assert req.algorithm == algo


def test_all_data_classifications():
    """Test all data classifications are accepted"""
    classifications = ["low", "medium", "high", "critical"]
    for classification in classifications:
        req = RiskRequest(
            algorithm="RSA-2048",
            data_lifetime_years=10,
            data_classification=classification
        )
        assert req.data_classification == classification


def test_all_scenarios():
    """Test all scenarios are accepted"""
    scenarios = ["conservative", "moderate", "aggressive"]
    for scenario in scenarios:
        req = RiskRequest(
            algorithm="RSA-2048",
            data_lifetime_years=10,
            scenario=scenario
        )
        assert req.scenario == scenario
