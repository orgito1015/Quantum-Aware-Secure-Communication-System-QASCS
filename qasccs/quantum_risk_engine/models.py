from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

Algorithm = Literal[
    "RSA-2048", "RSA-3072", "RSA-4096",
    "ECC-P256", "ECC-P384",
    "AES-128", "AES-256",
    "KYBER-768", "DILITHIUM-3", "HYBRID-ECDHE+KYBER"
]

DataClass = Literal["low", "medium", "high", "critical"]
Mode = Literal["classical", "pqc", "hybrid"]
Risk = Literal["LOW", "MEDIUM", "HIGH"]
Scenario = Literal["conservative", "moderate", "aggressive"]

class RiskRequest(BaseModel):
    algorithm: Algorithm
    data_lifetime_years: int = Field(..., ge=1, le=50)
    data_classification: DataClass = "medium"
    scenario: Scenario = "moderate"

class RiskResponse(BaseModel):
    risk: Risk
    recommended_mode: Mode
    quantum_safe_until_year: int
    rationale: str
    notes: str | None = None
