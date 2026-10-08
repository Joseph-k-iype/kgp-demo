"""Explicit, bounded evaluation; provider is offline unless requested live.

Existing reports are never overwritten. Partial progress is preserved on every
case. Reports contain public claims, IDs, usage and versions, not model receipts.
"""

import argparse
import json
import hashlib
import subprocess
from pathlib import Path
from importlib.metadata import version
from app.config import settings
from evals.cases import load_cases
from evals.runner import evaluate_engine

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--engine", choices=["legacy", "graph_fixed", "adaptive"], default="adaptive"
    )
    p.add_argument("--split", choices=["development", "heldout"], default="development")
    p.add_argument("--provider", choices=["offline", "live"], default="offline")
    p.add_argument("--max-runs", type=int)
    p.add_argument("--case-id", help="Development diagnosis only")
    p.add_argument(
        "--probe-provider",
        action="store_true",
        help="Separate explicit three-request compatibility probe",
    )
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.max_runs is not None and args.max_runs < 1:
        p.error("max-runs must be positive")
    if args.case_id and args.split != "development":
        p.error("Case selection is only allowed for development")
    if args.probe_provider:
        from probe_search_provider import probe

        if args.output.exists():
            p.error("Report already exists")
        report = probe()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as out:
            json.dump(report, out, indent=2)
        print(json.dumps(report, indent=2))
        raise SystemExit(0)
    cases = load_cases(args.split)
    if args.case_id:
        cases = [c for c in cases if c.id == args.case_id]
    if not cases:
        p.error("No matching cases")
    if args.provider == "live" and (
        args.engine != "adaptive" or min(args.max_runs or len(cases), len(cases)) > 20
    ):
        p.error("Live provider requires adaptive engine and at most 20 cases")
    c = settings()
    code_digest = hashlib.sha256()
    for source in sorted(Path("backend/app").rglob("*.py")):
        code_digest.update(str(source).encode())
        code_digest.update(source.read_bytes())
    environment = {
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        ),
        "backend_source_sha256": code_digest.hexdigest(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "split": args.split,
        "model": c.llm_model if args.provider == "live" else None,
        "upstream": c.openrouter_upstream if args.provider == "live" else None,
        "adapter": c.agent_adapter if args.provider == "live" else "offline",
        "structured_mode": c.openrouter_structured_mode
        if args.provider == "live"
        else None,
        "openai_sdk": version("openai"),
        "langgraph": version("langgraph"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        json.dump({"environment": environment, "status": "started"}, out, indent=2)

    def save(report, status="running"):
        value = {
            "environment": environment,
            "status": status,
            **report.model_dump(mode="json"),
        }
        pending = args.output.with_suffix(args.output.suffix + ".tmp")
        pending.write_text(json.dumps(value, indent=2) + "\n")
        pending.replace(args.output)

    result = evaluate_engine(
        args.engine, cases, args.provider, args.max_runs, on_case=save
    )
    save(result, "complete")
    print(json.dumps(result.summary, indent=2))
