from qasccs.quantum_risk_engine.models import RiskRequest
from qasccs.quantum_risk_engine.policy import evaluate_risk

def test_ecc_high_risk_when_shor_within_lifetime_aggressive():
    req = RiskRequest(algorithm="ECC-P256", data_lifetime_years=20, data_classification="high", scenario="aggressive")
    resp = evaluate_risk(req)
    assert resp.risk in ("HIGH", "MEDIUM")
    assert resp.recommended_mode in ("hybrid", "classical", "pqc")

def test_aes256_low():
    req = RiskRequest(algorithm="AES-256", data_lifetime_years=20, data_classification="high", scenario="aggressive")
    resp = evaluate_risk(req)
    assert resp.risk == "LOW"

def test_pqc_mode():
    req = RiskRequest(
        algorithm="KYBER-768", data_lifetime_years=10, data_classification="critical", scenario="moderate"
    )
    resp = evaluate_risk(req)
    assert resp.recommended_mode in ("pqc", "hybrid")
