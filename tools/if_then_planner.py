#!/usr/bin/env python3
"""Append an implementation-intention (if-then) plan and optional adherence score.

Usage:
  python3 tools/if_then_planner.py \
    --date 2026-05-18 \
    --cue "21:30 phone charging" \
    --action "paste minimum daily row" \
    --obstacle "too tired" \
    --fallback "log sleep/deep/energy only" \
    --confidence 8 \
    --adherence 1
"""

import argparse
import csv
import os
from datetime import date

BASE = "/workspace/life-os"
PLANS = os.path.join(BASE, "logs", "if_then_plans.csv")
OUTCOMES = os.path.join(BASE, "logs", "outcomes.csv")

PLANS_HEADER = [
    "date",
    "cue",
    "action",
    "obstacle",
    "fallback",
    "confidence_1_10",
    "adherence_done",
    "notes",
]
OUTCOMES_HEADER = ["date", "weekly_goal", "metric_name", "target", "actual", "status", "notes"]


def ensure_csv(path, header):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)


def parse_args():
    p = argparse.ArgumentParser(description="Log if-then plan + adherence into Life OS logs")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--cue", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--obstacle", default="")
    p.add_argument("--fallback", default="")
    p.add_argument("--confidence", type=float, default=7.0)
    p.add_argument("--adherence", type=int, choices=[0, 1], default=0, help="1 if completed, else 0")
    p.add_argument("--target", type=float, default=0.8, help="7d adherence target ratio")
    p.add_argument("--notes", default="weekly-experiment-if-then-adherence-v2")
    p.add_argument("--skip-outcome", action="store_true", help="Only append plan row")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_csv(PLANS, PLANS_HEADER)
    ensure_csv(OUTCOMES, OUTCOMES_HEADER)

    plan_row = [
        args.date,
        args.cue,
        args.action,
        args.obstacle,
        args.fallback,
        f"{max(1.0, min(10.0, args.confidence)):.1f}",
        str(args.adherence),
        args.notes,
    ]
    with open(PLANS, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(plan_row)

    status = "on_track" if args.adherence >= 1 else "off_track"
    outcome_row = [
        args.date,
        "If-then daily logging adherence",
        "if_then_adherence_done",
        f"{args.target:.2f}",
        f"{float(args.adherence):.2f}",
        status,
        args.notes,
    ]

    if not args.skip_outcome:
        with open(OUTCOMES, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(outcome_row)

    print("Plan appended:", ",".join(plan_row))
    if not args.skip_outcome:
        print("Outcome appended:", ",".join(outcome_row))


if __name__ == "__main__":
    main()
