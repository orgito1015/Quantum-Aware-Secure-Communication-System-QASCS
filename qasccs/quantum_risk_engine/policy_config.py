from __future__ import annotations
import os
from pathlib import Path

import yaml

_SCENARIO_KEYS: tuple[str, ...] = ("conservative", "moderate", "aggressive")

DEFAULT_SCENARIO_SHOR_YEAR: dict[str, int] = {
    "conservative": 2045,
    "moderate": 2038,
    "aggressive": 2032,
}


class PolicyConfigError(RuntimeError):
    """Raised when a policy config file is missing, malformed, or missing required keys."""


def load_scenario_years(path: str | os.PathLike[str] | None) -> dict[str, int]:
    """Load scenario -> Shor-year overrides from a YAML file, or return the built-in defaults.

    The file must have a top-level `scenario_shor_year` mapping covering all of
    conservative/moderate/aggressive with integer year values. See
    `default_policy.yaml` for the expected format.
    """
    if path is None:
        return dict(DEFAULT_SCENARIO_SHOR_YEAR)

    p = Path(path)
    if not p.is_file():
        raise PolicyConfigError(f"Policy config file not found: {p}")

    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise PolicyConfigError(f"Could not parse policy config {p}: {e}") from e

    if not isinstance(data, dict) or "scenario_shor_year" not in data:
        raise PolicyConfigError(f"Policy config {p} must contain a top-level 'scenario_shor_year' mapping")

    years = data["scenario_shor_year"]
    if not isinstance(years, dict):
        raise PolicyConfigError(f"'scenario_shor_year' in {p} must be a mapping")

    missing = [k for k in _SCENARIO_KEYS if k not in years]
    if missing:
        raise PolicyConfigError(f"Policy config {p} is missing scenario key(s): {', '.join(missing)}")

    result: dict[str, int] = {}
    for key in _SCENARIO_KEYS:
        value = years[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PolicyConfigError(
                f"Policy config {p}: scenario_shor_year.{key} must be an integer year, got {value!r}"
            )
        result[key] = value

    return result
