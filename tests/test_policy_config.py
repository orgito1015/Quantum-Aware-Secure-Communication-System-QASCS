import pytest

from qasccs.quantum_risk_engine.models import RiskRequest
from qasccs.quantum_risk_engine.policy import evaluate_risk
from qasccs.quantum_risk_engine.policy_config import (
    DEFAULT_SCENARIO_SHOR_YEAR,
    PolicyConfigError,
    load_scenario_years,
)


def test_load_scenario_years_returns_defaults_when_no_path():
    assert load_scenario_years(None) == DEFAULT_SCENARIO_SHOR_YEAR


def test_load_scenario_years_missing_file(tmp_path):
    with pytest.raises(PolicyConfigError, match="not found"):
        load_scenario_years(tmp_path / "does-not-exist.yaml")


def test_load_scenario_years_valid_override(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(
        "scenario_shor_year:\n  conservative: 2050\n  moderate: 2040\n  aggressive: 2030\n"
    )
    years = load_scenario_years(p)
    assert years == {"conservative": 2050, "moderate": 2040, "aggressive": 2030}


def test_load_scenario_years_missing_key(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("scenario_shor_year:\n  conservative: 2050\n  moderate: 2040\n")
    with pytest.raises(PolicyConfigError, match="missing scenario key"):
        load_scenario_years(p)


def test_load_scenario_years_non_integer_value(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(
        "scenario_shor_year:\n  conservative: soon\n  moderate: 2040\n  aggressive: 2030\n"
    )
    with pytest.raises(PolicyConfigError, match="must be an integer"):
        load_scenario_years(p)


def test_load_scenario_years_missing_top_level_key(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("something_else: true\n")
    with pytest.raises(PolicyConfigError, match="scenario_shor_year"):
        load_scenario_years(p)


def test_load_scenario_years_malformed_yaml(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("scenario_shor_year: [unterminated\n")
    with pytest.raises(PolicyConfigError):
        load_scenario_years(p)


def test_evaluate_risk_uses_overridden_scenario_years():
    req = RiskRequest(algorithm="RSA-2048", data_lifetime_years=10, scenario="moderate")
    # With a moderate Shor-year far in the future, RSA over 10 years should be low/medium risk.
    baseline = evaluate_risk(req, scenario_years={"conservative": 2099, "moderate": 2099, "aggressive": 2099})
    assert baseline.recommended_mode == "classical"

    # Pull the moderate Shor-year in close, RSA should now be flagged high risk / hybrid.
    urgent = evaluate_risk(req, scenario_years={"conservative": 2099, "moderate": 2027, "aggressive": 2027})
    assert urgent.risk == "HIGH"
    assert urgent.recommended_mode == "hybrid"
