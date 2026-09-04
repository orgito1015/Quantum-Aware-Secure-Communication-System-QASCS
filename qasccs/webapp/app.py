from __future__ import annotations
import argparse
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ..logging_config import configure_logging
from ..quantum_risk_engine.models import RiskRequest, RiskResponse
from ..quantum_risk_engine.policy import evaluate_risk
from ..quantum_risk_engine.policy_config import PolicyConfigError, load_scenario_years

log = configure_logging("qasccs.webapp")

app = FastAPI(
    title="QASCS Quantum Risk Engine",
    description="Evaluate whether a crypto choice is quantum-safe for a given data lifetime and classification.",
    version="1",
)

_POLICY_CONFIG_PATH = os.environ.get("QASCS_POLICY_CONFIG")


@app.post("/api/risk", response_model=RiskResponse)
def api_risk(req: RiskRequest) -> RiskResponse:
    try:
        scenario_years = load_scenario_years(_POLICY_CONFIG_PATH)
    except PolicyConfigError as e:
        log.error(str(e))
        scenario_years = None
    return evaluate_risk(req, scenario_years=scenario_years)


_ALGORITHMS = [
    "RSA-2048", "RSA-3072", "RSA-4096",
    "ECC-P256", "ECC-P384",
    "AES-128", "AES-256",
    "KYBER-768", "DILITHIUM-3", "HYBRID-ECDHE+KYBER",
]

_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QASCS Quantum Risk Engine</title>
<meta name="description" content="Evaluate whether a crypto choice is quantum-safe for a given data lifetime
  and classification.">
<style>
  :root { color-scheme: light dark; }
  body {
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 42rem;
    margin: 0 auto;
    padding: 1.5rem 1rem 3rem;
    line-height: 1.5;
  }
  h1 { font-size: 1.5rem; }
  form { display: flex; flex-direction: column; gap: 1rem; margin-top: 1.5rem; }
  label { display: block; font-weight: 600; margin-bottom: 0.25rem; }
  select, input {
    width: 100%;
    padding: 0.5rem;
    font-size: 1rem;
    box-sizing: border-box;
  }
  button {
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    cursor: pointer;
    align-self: flex-start;
  }
  #result {
    margin-top: 1.5rem;
    padding: 1rem;
    border: 1px solid CanvasText;
    border-radius: 0.25rem;
  }
  #result[hidden] { display: none; }
  .risk-LOW { color: #1a7f37; }
  .risk-MEDIUM { color: #9a6700; }
  .risk-HIGH { color: #cf222e; }
  dt { font-weight: 600; }
  dd { margin: 0 0 0.5rem 0; }
  #error { color: #cf222e; margin-top: 1rem; }
</style>
</head>
<body>
<h1>QASCS Quantum Risk Engine</h1>
<p>
  Enter a crypto choice, how long the data needs confidentiality, and its
  classification. The engine models Shor's- and Grover's-algorithm impact and
  recommends <code>classical</code>, <code>pqc</code>, or <code>hybrid</code>.
</p>

<form id="risk-form">
  <div>
    <label for="algorithm">Algorithm</label>
    <select id="algorithm" name="algorithm">
      __ALGORITHM_OPTIONS__
    </select>
  </div>
  <div>
    <label for="data_lifetime_years">Data lifetime (years)</label>
    <input type="number" id="data_lifetime_years" name="data_lifetime_years" min="1" max="50" value="10" required>
  </div>
  <div>
    <label for="data_classification">Data classification</label>
    <select id="data_classification" name="data_classification">
      <option value="low">low</option>
      <option value="medium" selected>medium</option>
      <option value="high">high</option>
      <option value="critical">critical</option>
    </select>
  </div>
  <div>
    <label for="scenario">Quantum-timeline scenario</label>
    <select id="scenario" name="scenario">
      <option value="conservative">conservative</option>
      <option value="moderate" selected>moderate</option>
      <option value="aggressive">aggressive</option>
    </select>
  </div>
  <button type="submit">Evaluate</button>
</form>

<div id="error" role="alert" hidden></div>

<dl id="result" hidden aria-live="polite">
  <dt>Risk</dt>
  <dd id="r-risk"></dd>
  <dt>Recommended mode</dt>
  <dd id="r-mode"></dd>
  <dt>Quantum-safe until</dt>
  <dd id="r-until"></dd>
  <dt>Rationale</dt>
  <dd id="r-rationale"></dd>
</dl>

<script>
document.getElementById("risk-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const errorBox = document.getElementById("error");
  const result = document.getElementById("result");
  errorBox.hidden = true;
  result.hidden = true;

  const body = {
    algorithm: form.algorithm.value,
    data_lifetime_years: parseInt(form.data_lifetime_years.value, 10),
    data_classification: form.data_classification.value,
    scenario: form.scenario.value,
  };

  try {
    const resp = await fetch("/api/risk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail) : "Request failed");
    }
    document.getElementById("r-risk").textContent = data.risk;
    document.getElementById("r-risk").className = "risk-" + data.risk;
    document.getElementById("r-mode").textContent = data.recommended_mode;
    document.getElementById("r-until").textContent = data.quantum_safe_until_year;
    document.getElementById("r-rationale").textContent = data.rationale;
    result.hidden = false;
  } catch (e) {
    errorBox.textContent = "Error: " + e.message;
    errorBox.hidden = false;
  }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    options = "\n".join(f'<option value="{a}">{a}</option>' for a in _ALGORITHMS)
    return _INDEX_HTML.replace("__ALGORITHM_OPTIONS__", options)


def main() -> int:
    ap = argparse.ArgumentParser(description="QASCS Quantum Risk Engine web dashboard")
    ap.add_argument("--host", default=os.environ.get("QASCS_WEB_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("QASCS_WEB_PORT", "8000")))
    args = ap.parse_args()

    try:
        import uvicorn
    except ImportError:
        log.error("The web dashboard requires the 'web' extra: pip install -e '.[web]'")
        return 1

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
