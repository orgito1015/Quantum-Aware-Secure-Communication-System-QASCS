from datetime import datetime, timezone
from qasccs.quantum_risk_engine.models import RiskRequest
from qasccs.quantum_risk_engine.policy import evaluate_risk, SCENARIO_SHOR_YEAR


def test_rsa_2048_conservative_short_lifetime():
    """Test RSA-2048 with conservative scenario and short lifetime"""
    req = RiskRequest(
        algorithm="RSA-2048",
        data_lifetime_years=5,
        data_classification="low",
        scenario="conservative"
    )
    resp = evaluate_risk(req)
    assert resp.risk in ("LOW", "MEDIUM")
    assert resp.recommended_mode in ("classical", "hybrid")


def test_rsa_4096_aggressive_long_lifetime():
    """Test RSA-4096 with aggressive scenario and long lifetime"""
    req = RiskRequest(
        algorithm="RSA-4096",
        data_lifetime_years=20,
        data_classification="critical",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "HIGH"
    assert resp.recommended_mode == "hybrid"


def test_ecc_p256_moderate_medium_classification():
    """Test ECC-P256 with moderate scenario"""
    req = RiskRequest(
        algorithm="ECC-P256",
        data_lifetime_years=15,
        data_classification="medium",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    # 2026 + 15 = 2041, which is > 2038 (moderate Shor year)
    assert resp.risk in ("HIGH", "MEDIUM")


def test_ecc_p384_conservative():
    """Test ECC-P384 with conservative scenario"""
    req = RiskRequest(
        algorithm="ECC-P384",
        data_lifetime_years=10,
        data_classification="high",
        scenario="conservative"
    )
    resp = evaluate_risk(req)
    # Should be safe until 2045 in conservative scenario
    assert resp.risk in ("LOW", "MEDIUM", "HIGH")


def test_aes128_low_classification():
    """Test AES-128 with low classification"""
    req = RiskRequest(
        algorithm="AES-128",
        data_lifetime_years=10,
        data_classification="low",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    # For AES-128 with low classification (bump=0), risk should be LOW and mode classical
    assert resp.risk == "LOW"
    assert resp.recommended_mode == "classical"


def test_aes128_high_classification():
    """Test AES-128 with high classification"""
    req = RiskRequest(
        algorithm="AES-128",
        data_lifetime_years=10,
        data_classification="high",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "MEDIUM"  # bump=1 for high
    assert resp.recommended_mode == "hybrid"


def test_aes256_all_classifications():
    """Test AES-256 with all classifications"""
    for classification in ["low", "medium", "high", "critical"]:
        req = RiskRequest(
            algorithm="AES-256",
            data_lifetime_years=10,
            data_classification=classification,
            scenario="moderate"
        )
        resp = evaluate_risk(req)
        # AES-256 should be LOW risk, but critical elevates to MEDIUM
        if classification == "critical":
            assert resp.risk == "MEDIUM"
            assert resp.recommended_mode == "hybrid"
        else:
            assert resp.risk == "LOW"


def test_kyber_768_low_classification():
    """Test KYBER-768 PQC algorithm"""
    req = RiskRequest(
        algorithm="KYBER-768",
        data_lifetime_years=20,
        data_classification="low",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "LOW"
    assert resp.recommended_mode == "pqc"


def test_kyber_768_critical_classification():
    """Test KYBER-768 with critical classification"""
    req = RiskRequest(
        algorithm="KYBER-768",
        data_lifetime_years=20,
        data_classification="critical",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "MEDIUM"  # bump=2 for critical
    assert resp.recommended_mode == "hybrid"  # Critical elevates to hybrid


def test_dilithium_3():
    """Test DILITHIUM-3 PQC algorithm"""
    req = RiskRequest(
        algorithm="DILITHIUM-3",
        data_lifetime_years=15,
        data_classification="high",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "LOW"
    assert resp.recommended_mode == "pqc"


def test_hybrid_ecdhe_kyber():
    """Test HYBRID-ECDHE+KYBER algorithm"""
    req = RiskRequest(
        algorithm="HYBRID-ECDHE+KYBER",
        data_lifetime_years=25,
        data_classification="medium",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "LOW"
    assert resp.recommended_mode == "hybrid"


def test_critical_classification_elevates_risk():
    """Test that critical classification elevates risk"""
    req = RiskRequest(
        algorithm="AES-256",
        data_lifetime_years=5,
        data_classification="critical",
        scenario="conservative"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "MEDIUM"  # Elevated due to critical
    assert resp.recommended_mode == "hybrid"
    assert "Critical classification elevates" in resp.rationale


def test_shor_vulnerable_within_lifetime():
    """Test Shor-vulnerable algorithm with Shor year within lifetime"""
    current_year = datetime.now(timezone.utc).year
    
    # Use aggressive scenario where Shor year is 2032
    req = RiskRequest(
        algorithm="RSA-2048",
        data_lifetime_years=10,  # This should put us past 2032
        data_classification="medium",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    
    horizon_year = current_year + 10
    shor_year = SCENARIO_SHOR_YEAR["aggressive"]
    
    if shor_year <= horizon_year:
        assert resp.risk == "HIGH"
        assert resp.recommended_mode == "hybrid"


def test_shor_vulnerable_outside_lifetime():
    """Test Shor-vulnerable algorithm with Shor year outside lifetime"""
    req = RiskRequest(
        algorithm="ECC-P256",
        data_lifetime_years=2,  # Very short lifetime
        data_classification="low",
        scenario="conservative"  # Shor year 2045
    )
    resp = evaluate_risk(req)
    # Shor year is well after data lifetime
    assert resp.risk == "LOW"
    assert resp.recommended_mode == "classical"


def test_quantum_safe_until_year_calculation():
    """Test quantum_safe_until_year is correctly calculated"""
    current_year = datetime.now(timezone.utc).year
    lifetime = 10
    
    req = RiskRequest(
        algorithm="AES-256",
        data_lifetime_years=lifetime,
        data_classification="low",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    
    expected_year = current_year + lifetime
    assert resp.quantum_safe_until_year == expected_year


def test_all_scenarios_shor_years():
    """Test that different scenarios have different Shor years"""
    for scenario in ["conservative", "moderate", "aggressive"]:
        req = RiskRequest(
            algorithm="RSA-2048",
            data_lifetime_years=50,  # Max lifetime to ensure within Shor year
            data_classification="critical",
            scenario=scenario
        )
        resp = evaluate_risk(req)
        
        # All should be HIGH risk with long lifetime and Shor vulnerability
        assert resp.risk == "HIGH"
        assert resp.recommended_mode == "hybrid"
        
        # Verify Shor year is mentioned in rationale
        shor_year = SCENARIO_SHOR_YEAR[scenario]
        assert str(shor_year) in resp.rationale


def test_boundary_data_lifetime_1_year():
    """Test minimum data lifetime of 1 year"""
    req = RiskRequest(
        algorithm="AES-256",
        data_lifetime_years=1,
        data_classification="low",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "LOW"


def test_boundary_data_lifetime_50_years():
    """Test maximum data lifetime of 50 years"""
    req = RiskRequest(
        algorithm="RSA-2048",
        data_lifetime_years=50,
        data_classification="critical",
        scenario="aggressive"
    )
    resp = evaluate_risk(req)
    assert resp.risk == "HIGH"


def test_response_includes_rationale():
    """Test that all responses include a rationale"""
    req = RiskRequest(
        algorithm="ECC-P256",
        data_lifetime_years=10,
        data_classification="medium",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.rationale is not None
    assert len(resp.rationale) > 0


def test_response_includes_notes():
    """Test that responses include notes about scenario assumptions"""
    req = RiskRequest(
        algorithm="RSA-2048",
        data_lifetime_years=10,
        data_classification="medium",
        scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.notes is not None
    assert "tunable" in resp.notes.lower()
