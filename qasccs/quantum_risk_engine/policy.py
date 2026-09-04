from __future__ import annotations
from datetime import datetime, timezone
from .models import RiskRequest, RiskResponse, Mode, Risk
from .policy_config import DEFAULT_SCENARIO_SHOR_YEAR

# Tunable scenario model (for experiments; replace with rigorous estimates if
# needed, or override via --policy-config / QASCS_POLICY_CONFIG).
SCENARIO_SHOR_YEAR = DEFAULT_SCENARIO_SHOR_YEAR


def _is_shor_vulnerable(alg: str) -> bool:
    return alg.startswith("RSA") or alg.startswith("ECC")


def _is_grover_relevant(alg: str) -> bool:
    return alg.startswith("AES")


def _is_pqc_or_hybrid(alg: str) -> bool:
    return alg.startswith("KYBER") or alg.startswith("DILITHIUM") or alg.startswith("HYBRID")


def evaluate_risk(req: RiskRequest, scenario_years: dict[str, int] | None = None) -> RiskResponse:
    years = scenario_years if scenario_years is not None else SCENARIO_SHOR_YEAR
    now_year = datetime.now(timezone.utc).year
    shor_year = years[req.scenario]
    horizon_year = now_year + req.data_lifetime_years

    bump = {"low": 0, "medium": 0, "high": 1, "critical": 2}[req.data_classification]

    risk: Risk = "LOW"
    mode: Mode = "classical"
    safe_until: int = horizon_year
    rationale: list[str] = []

    if _is_pqc_or_hybrid(req.algorithm):
        risk = "LOW" if bump < 2 else "MEDIUM"
        mode = "hybrid" if req.algorithm == "HYBRID-ECDHE+KYBER" else "pqc"
        safe_until = horizon_year
        rationale.append("PQC/hybrid selected; modeled as quantum-resistant for the target lifetime.")
    elif _is_shor_vulnerable(req.algorithm):
        if shor_year <= horizon_year:
            risk = "HIGH"
            mode = "hybrid"
            safe_until = shor_year - 1
            rationale.append(
                f"Shor-vulnerable public-key crypto; modeled Shor year ({shor_year}) is within data lifetime."
            )
        else:
            risk = "MEDIUM" if bump >= 1 else "LOW"
            mode = "hybrid" if risk == "MEDIUM" else "classical"
            safe_until = horizon_year
            rationale.append(
                f"Shor year ({shor_year}) is after data lifetime; migration may still be needed for high/critical data."
            )
    elif _is_grover_relevant(req.algorithm):
        safe_until = horizon_year
        if req.algorithm == "AES-128":
            risk = "MEDIUM" if bump >= 1 else "LOW"
            mode = "hybrid" if bump >= 1 else "classical"
            rationale.append(
                "AES-128 modeled as ~64-bit vs Grover; avoid for high/critical long-term confidentiality."
            )
        else:
            risk = "LOW"
            mode = "classical"
            rationale.append(
                "AES-256 modeled as ~128-bit vs Grover; generally acceptable for long-term confidentiality."
            )
    else:
        risk = "MEDIUM"
        mode = "hybrid"
        safe_until = min(horizon_year, shor_year - 1)
        rationale.append("Unknown algorithm; defaulting to conservative hybrid recommendation.")

    if risk != "HIGH" and bump == 2:
        risk = "MEDIUM"
        mode = "hybrid"
        rationale.append("Critical classification elevates posture to hybrid.")

    return RiskResponse(
        risk=risk,
        recommended_mode=mode,
        quantum_safe_until_year=safe_until,
        rationale=" ".join(rationale),
        notes="Scenario years are tunable for experimentation; not a real-world forecast."
    )
