"""Command-line interface (FR-9 #3): `castor analyze`, `castor calibrate`.

Exit codes for `analyze` (CI-friendly, UC-3): 0 = no cascade, 1 = cascade
detected, 2 = monitoring failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analysis import CascadeAnalyzer
from .calibrate import ThresholdProfile, calibrate
from .trajectory import Trajectory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="castor",
        description="Castor — tells you WHERE your agent chain started hallucinating.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="analyze a trajectory file (UC-1)")
    analyze.add_argument("file", help="trajectory .json (array of steps) or .jsonl")
    analyze.add_argument("--json-out", help="also write the machine-readable report here")
    analyze.add_argument("--threshold", type=float, help="override drift threshold")
    analyze.add_argument("--profile", help="threshold profile JSON file (FR-5)")
    analyze.add_argument("--anchor", help="override anchor text (e.g. source document)")
    analyze.add_argument(
        "--no-nli", action="store_true", help="drift-only mode (skip the NLI model)"
    )

    cal = sub.add_parser(
        "calibrate", help="recommend a drift threshold from CLEAN trajectories (UC-4)"
    )
    cal.add_argument("directory", help="directory of clean trajectory .json/.jsonl files")
    cal.add_argument("--percentile", type=float, default=95.0)
    cal.add_argument("--name", default="calibrated", help="profile name")
    cal.add_argument("--save", help="write the recommended profile JSON here")
    return parser


def _cmd_analyze(args: argparse.Namespace) -> int:
    profile = ThresholdProfile.load(args.profile) if args.profile else ThresholdProfile()
    if args.threshold is not None:
        import dataclasses

        profile = dataclasses.replace(profile, drift_threshold=args.threshold)
    analyzer = CascadeAnalyzer(
        entailment=False if args.no_nli else None,
        profile=profile,
        anchor=args.anchor,
    )
    report = analyzer.analyze(Trajectory.from_json(args.file))
    print(report.to_text())
    if args.json_out:
        Path(args.json_out).write_text(report.to_json(), encoding="utf-8")
        print(f"\nJSON report written to {args.json_out}")
    if report.monitoring_failure is not None:
        return 2
    return 1 if report.verdict else 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    files = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in {".json", ".jsonl"}
    )
    if not files:
        print(f"no .json/.jsonl trajectory files found in {directory}", file=sys.stderr)
        return 2
    result = calibrate(
        (Trajectory.from_json(p) for p in files),
        percentile=args.percentile,
        profile_name=args.name,
    )
    print(
        f"calibrated from {result.n_trajectories} clean trajectories "
        f"({result.n_measurements} drift measurements)\n"
        f"drift distribution: mean {result.drift_mean}, std {result.drift_std}\n"
        f"recommended drift threshold (p{result.drift_percentile_used:g}): "
        f"{result.profile.drift_threshold}"
    )
    if args.save:
        result.profile.save(args.save)
        print(f"profile '{result.profile.name}' saved to {args.save}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (FR-9)."""
    args = _build_parser().parse_args(argv)
    if args.command == "analyze":
        return _cmd_analyze(args)
    return _cmd_calibrate(args)


if __name__ == "__main__":
    sys.exit(main())
