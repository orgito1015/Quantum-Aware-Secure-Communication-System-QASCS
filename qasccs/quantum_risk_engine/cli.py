import argparse
import json
import os
import sys
from pydantic import ValidationError
from .models import RiskRequest
from .policy import evaluate_risk
from .policy_config import PolicyConfigError, load_scenario_years

def main():
    ap = argparse.ArgumentParser(description="Quantum Risk Engine (QASCS)")
    ap.add_argument("--algorithm", required=True)
    ap.add_argument("--data-lifetime-years", type=int, required=True)
    ap.add_argument("--data-classification", default="medium", choices=["low","medium","high","critical"])
    ap.add_argument("--scenario", default="moderate", choices=["conservative","moderate","aggressive"])
    ap.add_argument(
        "--policy-config",
        default=os.environ.get("QASCS_POLICY_CONFIG"),
        help="Path to a YAML file overriding the scenario-year model (see default_policy.yaml).",
    )
    args = ap.parse_args()

    try:
        scenario_years = load_scenario_years(args.policy_config)
    except PolicyConfigError as e:
        print(f"Policy config error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        req = RiskRequest(
            algorithm=args.algorithm,
            data_lifetime_years=args.data_lifetime_years,
            data_classification=args.data_classification,
            scenario=args.scenario,
        )
        resp = evaluate_risk(req, scenario_years=scenario_years)
        print(json.dumps(resp.model_dump(), indent=2))
    except ValidationError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
