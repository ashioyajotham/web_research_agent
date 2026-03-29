#!/usr/bin/env python3
"""
Benchmark runner for the web research agent.

Loads cases from benchmark.json, runs each query through the agent,
checks answers against expected/excluded keywords, and reports PASS/FAIL.

Usage:
    python benchmarks/run_benchmark.py
    python benchmarks/run_benchmark.py --ids geneva-ai-talks-coo
    python benchmarks/run_benchmark.py --out results/bench_run.json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _check(answer: str, case: dict) -> dict:
    """Return a verdict dict for one benchmark case."""
    answer_lower = answer.lower()
    missing = [kw for kw in case.get("expected_contains", []) if kw.lower() not in answer_lower]
    bad_hits = [kw for kw in case.get("expected_not_contains", []) if kw.lower() in answer_lower]
    return {
        "passed": len(missing) == 0 and len(bad_hits) == 0,
        "missing": missing,
        "bad_hits": bad_hits,
    }


def run(case_ids: list = None, out_path: str = None):
    bench_file = Path(__file__).parent / "benchmark.json"
    with open(bench_file, encoding="utf-8") as f:
        cases = json.load(f)

    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]
        if not cases:
            print(f"No cases matched ids: {case_ids}")
            sys.exit(1)

    from cli import initialize_agent

    results = []
    passed = 0

    print(f"\nRunning {len(cases)} benchmark case(s)...\n{'-' * 60}")

    for case in cases:
        print(f"\n[{case['id']}]")
        print(f"  query: {case['query'][:80]}{'...' if len(case['query']) > 80 else ''}")

        agent = initialize_agent()
        t0 = time.time()
        answer = agent.run(case["query"])
        elapsed = round(time.time() - t0, 1)

        verdict = _check(answer, case)
        status = "PASS" if verdict["passed"] else "FAIL"
        if verdict["passed"]:
            passed += 1

        preview = answer[:200].encode("ascii", errors="replace").decode("ascii")
        print(f"  status:  {status}  ({elapsed}s)")
        if verdict["missing"]:
            print(f"  missing: {verdict['missing']}")
        if verdict["bad_hits"]:
            print(f"  bad hits (hallucination): {verdict['bad_hits']}")
        print(f"  answer:  {preview}{'...' if len(answer) > 200 else ''}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "answer": answer,
            "verdict": verdict,
            "elapsed_s": elapsed,
            "source": case.get("source"),
            "notes": case.get("notes"),
        })

    print(f"\n{'-' * 60}")
    print(f"Score: {passed}/{len(cases)} passed")

    out = out_path or Path(__file__).parent / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"run_at": datetime.now().isoformat(), "score": f"{passed}/{len(cases)}", "results": results}, f, indent=2)
    print(f"Results saved to: {out}\n")
    return passed, len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the web research agent benchmark suite.")
    parser.add_argument("--ids", nargs="+", help="Run only these case IDs")
    parser.add_argument("--out", help="Path to save the results JSON")
    args = parser.parse_args()
    run(case_ids=args.ids, out_path=args.out)
