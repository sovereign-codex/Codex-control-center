"""Reproduce the three local suites, without changing any archived evidence.

Usage: python -B run_tests.py --output-dir /a/new/directory
Uses only the Python standard library. Does not contact any external service.
The output directory must not exist; baseline tests and red regressions are unedited.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ["BRIDGE_CANDIDATE_DIR"] = str(HERE)
    sys.path.insert(0, str(HERE))
    source_files = ["bridge_specimen.py", "test_bridge_specimen.py",
                    "test_review_regressions.py", "test_repair_regressions.py",
                    "run_tests.py", "fixtures/packet.json"]
    before = {name: sha(HERE / name) for name in source_files}
    groups = [
        ("original_22", "test_bridge_specimen"),
        ("review_9", "test_review_regressions"),
        ("repair_30", "test_repair_regressions"),
    ]
    results = []
    started = time.perf_counter()
    for label, module_name in groups:
        module = importlib.import_module(module_name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        with (output / (label + ".log")).open("w", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        results.append({"suite": label, "tests_run": result.testsRun,
                        "failures": len(result.failures), "errors": len(result.errors),
                        "skipped": len(result.skipped),
                        "passed": result.wasSuccessful() and not result.skipped,
                        "failure_ids": [test.id() for test, _ in result.failures],
                        "error_ids": [test.id() for test, _ in result.errors]})
        if module_name == "test_review_regressions":
            (output / "review_regression_observations.json").write_text(
                json.dumps(module.OBSERVATIONS, indent=2, ensure_ascii=False,
                           allow_nan=False) + "\n", encoding="utf-8")
        print(label, results[-1], flush=True)
    after = {name: sha(HERE / name) for name in source_files}
    passed = all(result["passed"] for result in results) and before == after
    report = {
        "artifact_id": "BRIDGE_LOCAL_REPAIR_001", "standing": "candidate_noncanonical",
        "test_verdict": "PASS" if passed else "FAIL", "tests_run": sum(r["tests_run"] for r in results),
        "failures": sum(r["failures"] for r in results), "errors": sum(r["errors"] for r in results),
        "skipped": sum(r["skipped"] for r in results), "suites": results,
        "execution_exit_code": 0 if passed else 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_source": "container_or_reviewer_clock_not_attested",
        "duration_seconds": round(time.perf_counter() - started, 6),
        "environment": {"python": sys.version, "platform": platform.system(),
                        "machine": platform.machine()},
        "tested_files_sha256": before, "source_unchanged_during_run": before == after,
        "independent_review": "NOT_PERFORMED_BY_THIS_RUNNER",
        "model_execution": "not_performed", "source_system_writes": False,
        "institutional_acceptance": "not_assessed", "authority_effect": "none",
        "hall_receipt_claimed": False, "handoff_ready": False,
        "next_gate": "independent_review_of_exact_repaired_bytes",
        "limits": [
            "Single-writer local specimen, not remote delivery or a live queue.",
            "Python socket audit guard, not an operating-system firewall.",
            "Same account/container, not hostile-principal isolation.",
            "Fault-injected local writes and clocks, not power-loss crash proof.",
            "Deadline checked through decision preparation, immediately before publication.",
            "Atomic publication syscall and function-return latency are not preemptible or timed to completion.",
            "File fsync and no-overwrite hard link do not establish directory or host-crash durability.",
            "Historical byte/profile verification does not check or renew current authorization.",
        ],
    }
    (output / "test_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report["execution_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
