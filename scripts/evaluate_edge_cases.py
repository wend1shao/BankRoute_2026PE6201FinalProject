#!/usr/bin/env python3
"""Run the frozen, human-readable safety and product-behaviour suite."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankroute.router import BankRouter  # noqa: E402


def main() -> None:
    cases_path = ROOT / "evals" / "edge_cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line]
    router = BankRouter()
    rows = []
    for case in cases:
        result = router.route(case["message"]).to_dict()
        checks = {
            "intent": result["intent"] == case.get("expected_intent"),
            "status": result["decision_status"] == case["expected_status"],
        }
        if "expected_flag" in case:
            checks["flag"] = case["expected_flag"] in result["safety_flags"]
        if case.get("expect_pii_redacted"):
            checks["pii"] = result["pii_redacted"] is True
        rows.append(
            {
                "id": case["id"],
                "passed": all(checks.values()),
                "checks": checks,
                "expected_intent": case.get("expected_intent"),
                "actual_intent": result["intent"],
                "expected_status": case["expected_status"],
                "actual_status": result["decision_status"],
                "safety_flags": result["safety_flags"],
            }
        )

    summary = {
        "suite": "BankRoute fixed product and safety edge cases v1",
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "pass_rate": round(sum(row["passed"] for row in rows) / len(rows), 6),
        "all_passed": all(row["passed"] for row in rows),
        "results": rows,
    }
    output = ROOT / "evals" / "results" / "edge_case_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

