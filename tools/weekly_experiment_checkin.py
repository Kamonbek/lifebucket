#!/usr/bin/env python3
import argparse
import csv
import os
from datetime import date

BASE = "/workspace/life-os"
OUTCOMES = os.path.join(BASE, "logs", "outcomes.csv")

HEADER = ["date", "weekly_goal", "metric_name", "target", "actual", "status", "notes"]


def ensure_file():
    os.makedirs(os.path.dirname(OUTCOMES), exist_ok=True)
    if not os.path.exists(OUTCOMES):
        with open(OUTCOMES, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADER)


def parse_args():
    p = argparse.ArgumentParser(description="Append weekly experiment commitment check-in to logs/outcomes.csv")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--goal", default="Identity-based weekly commitment")
    p.add_argument("--score", type=float, required=True, help="Actual commitment score 0-10")
    p.add_argument("--target", type=float, default=8.0)
    p.add_argument("--notes", default="weekly-identity-commitment-v1")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_file()
    status = "on_track" if args.score >= args.target else "off_track"
    row = [args.date, args.goal, "identity_commitment_score", f"{args.target:.1f}", f"{args.score:.1f}", status, args.notes]
    with open(OUTCOMES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)
    print("Appended:", ",".join(row))


if __name__ == "__main__":
    main()
