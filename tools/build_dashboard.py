#!/usr/bin/env python3
import csv
import os
from datetime import datetime, timedelta
from statistics import mean

BASE = "/workspace/life-os"
LOGS = os.path.join(BASE, "logs")
CONFIG = os.path.join(BASE, "config")
REPORTS = os.path.join(BASE, "reports")


def read_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def to_float(s, default=0.0):
    try:
        return float(s)
    except Exception:
        return default


def yes_ratio(rows, key):
    vals = [r.get(key, "").lower() for r in rows if r.get(key, "")]
    if not vals:
        return 0.0
    yes = sum(1 for v in vals if v in {"yes", "y", "true", "1"})
    return yes / len(vals)


def pct(n):
    return f"{n*100:.1f}%"


def progress_bar(actual, target, width=20):
    if target <= 0:
        frac = 0
    else:
        frac = max(0.0, min(actual / target, 1.2))
    filled = int(min(frac, 1.0) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {actual:.2f}/{target:.2f} ({(actual/target*100 if target else 0):.0f}%)"


def currency_sum(rows, start_date=None):
    by_currency = {}
    for r in rows:
        d = parse_date(r.get("date", ""))
        if start_date and (not d or d < start_date):
            continue
        cur = (r.get("currency") or "USD").upper()
        amt = to_float(r.get("amount", "0"), 0.0)
        by_currency[cur] = by_currency.get(cur, 0.0) + amt
    return by_currency


def format_currency_map(m):
    if not m:
        return "0"
    return ", ".join([f"{v:.2f} {k}" for k, v in m.items()])


def ratio_streak(rows, key):
    # consecutive days from latest backwards where key=yes
    rows_sorted = sorted(
        [(parse_date(r.get("date", "")), r) for r in rows if parse_date(r.get("date", ""))],
        key=lambda x: x[0],
        reverse=True,
    )
    streak = 0
    for _, r in rows_sorted:
        v = (r.get(key) or "").lower()
        if v in {"yes", "y", "true", "1"}:
            streak += 1
        else:
            break
    return streak


def deep_work_streak(rows, min_hours=3.0):
    rows_sorted = sorted(
        [(parse_date(r.get("date", "")), r) for r in rows if parse_date(r.get("date", ""))],
        key=lambda x: x[0],
        reverse=True,
    )
    streak = 0
    for _, r in rows_sorted:
        h = to_float(r.get("deep_work_hours", "0"), 0.0)
        if h >= min_hours:
            streak += 1
        else:
            break
    return streak


def project_risk_score(active_projects):
    # 0-100, higher = riskier
    score = 0
    high = sum(1 for p in active_projects if (p.get("priority", "").lower() == "high"))
    score += min(len(active_projects), 5) * 12
    score += min(high, 5) * 8

    today = datetime.now().date()
    for p in active_projects:
        d = parse_date(p.get("deadline", ""))
        if not d:
            score += 5
            continue
        days = (d - today).days
        if days < 0:
            score += 25
        elif days <= 7:
            score += 15
        elif days <= 14:
            score += 8

    return min(score, 100)


def on_track(actual, target, lower_is_better=False):
    if target <= 0:
        return "unknown"
    if lower_is_better:
        return "on_track" if actual <= target else "off_track"
    return "on_track" if actual >= target else "off_track"


def load_targets(path):
    out = {}
    for r in read_csv(path):
        out[r.get("metric", "")] = {
            "window": r.get("window", ""),
            "target": to_float(r.get("target", "0"), 0.0),
            "unit": r.get("unit", ""),
            "notes": r.get("notes", ""),
        }
    return out


def main():
    os.makedirs(REPORTS, exist_ok=True)

    daily = read_csv(os.path.join(LOGS, "daily_log.csv"))
    income = read_csv(os.path.join(LOGS, "income.csv"))
    expenses = read_csv(os.path.join(LOGS, "expenses.csv"))
    projects = read_csv(os.path.join(LOGS, "projects.csv"))
    targets = load_targets(os.path.join(CONFIG, "metrics_targets.csv"))

    today = datetime.now().date()
    last_7 = today - timedelta(days=6)
    last_30 = today - timedelta(days=29)

    daily_7 = [r for r in daily if (parse_date(r.get("date", "")) and parse_date(r.get("date", "")) >= last_7)]
    daily_30 = [r for r in daily if (parse_date(r.get("date", "")) and parse_date(r.get("date", "")) >= last_30)]

    deep7 = [to_float(r.get("deep_work_hours", "0")) for r in daily_7 if r.get("deep_work_hours", "")]
    learn7 = [to_float(r.get("learning_hours", "0")) for r in daily_7 if r.get("learning_hours", "")]
    energy7 = [to_float(r.get("energy", "0")) for r in daily_7 if r.get("energy", "")]
    deep30 = [to_float(r.get("deep_work_hours", "0")) for r in daily_30 if r.get("deep_work_hours", "")]

    avg_deep7 = mean(deep7) if deep7 else 0.0
    avg_learn7 = mean(learn7) if learn7 else 0.0
    main_done7 = yes_ratio(daily_7, "main_task_done")
    exercise7 = yes_ratio(daily_7, "exercise")
    avg_energy7 = mean(energy7) if energy7 else 0.0

    income30 = currency_sum(income, last_30)
    expense30 = currency_sum(expenses, last_30)
    income30_usd = income30.get("USD", 0.0)
    expense30_usd = expense30.get("USD", 0.0)
    net30_usd = income30_usd - expense30_usd

    active_projects = [p for p in projects if p.get("status", "").lower() == "active"]
    risk = project_risk_score(active_projects)

    # Velocity score (0-100)
    score = 0.0
    score += min(avg_deep7 / 4.0, 1.0) * 35
    score += min(avg_learn7 / 1.5, 1.0) * 20
    score += main_done7 * 25
    score += exercise7 * 10
    score += min(avg_energy7 / 8.0, 1.0) * 10

    trend = "unknown"
    if deep7 and deep30:
        d7 = avg_deep7
        d30 = mean(deep30)
        if d7 > d30 + 0.25:
            trend = "improving"
        elif d7 < d30 - 0.25:
            trend = "declining"
        else:
            trend = "stable"

    latest = None
    latest_date = None
    for r in daily:
        d = parse_date(r.get("date", ""))
        if d and (latest_date is None or d > latest_date):
            latest_date = d
            latest = r

    deep_work_streak_days = deep_work_streak(daily, 3.0)
    main_done_streak_days = ratio_streak(daily, "main_task_done")

    # goal tracking table based on targets
    actuals = {
        "deep_work_hours": avg_deep7,
        "learning_hours": avg_learn7,
        "main_task_done_rate": main_done7,
        "exercise_rate": exercise7,
        "energy_score": avg_energy7,
        "net_income": net30_usd,
    }

    lines = []
    lines.append("# Life Analytics Dashboard v2")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("## Executive cockpit")
    lines.append(f"- Execution velocity score: {score:.1f}/100")
    lines.append(f"- Direction trend: {trend}")
    lines.append(f"- Project delivery risk score: {risk}/100")
    lines.append(f"- Active projects: {len(active_projects)}")
    lines.append("")

    lines.append("## Goal progress bars")
    for metric, cfg in targets.items():
        if metric not in actuals:
            continue
        a = actuals[metric]
        t = cfg.get("target", 0.0)
        status = on_track(a, t)
        bar = progress_bar(a, t)
        lines.append(f"- {metric} ({cfg.get('window','')}): {bar} -> {status}")
    lines.append("")

    lines.append("## Weekly performance summary")
    lines.append(f"- Avg deep work/day: {avg_deep7:.2f}h")
    lines.append(f"- Avg learning/day: {avg_learn7:.2f}h")
    lines.append(f"- Main task completion: {pct(main_done7)}")
    lines.append(f"- Exercise consistency: {pct(exercise7)}")
    lines.append(f"- Avg energy: {avg_energy7:.2f}/10")
    lines.append("")

    lines.append("## Consistency streaks")
    lines.append(f"- Deep work >=3h streak: {deep_work_streak_days} day(s)")
    lines.append(f"- Main task done streak: {main_done_streak_days} day(s)")
    lines.append("")

    lines.append("## Finance (30d)")
    lines.append(f"- Income: {format_currency_map(income30)}")
    lines.append(f"- Expenses: {format_currency_map(expense30)}")
    lines.append(f"- Net (USD-only strict): {net30_usd:.2f} USD")
    lines.append("")

    lines.append("## Latest day snapshot")
    if latest and latest_date:
        lines.append(f"- Date: {latest_date}")
        lines.append(f"- Wake: {latest.get('wake_time','n/a')} | Sleep: {latest.get('sleep_hours','n/a')}h")
        lines.append(f"- Deep work: {latest.get('deep_work_hours','n/a')}h | Learning: {latest.get('learning_hours','n/a')}h")
        lines.append(f"- Main task done: {latest.get('main_task_done','n/a')} | Exercise: {latest.get('exercise','n/a')}")
        lines.append(f"- Mood: {latest.get('mood','n/a')} | Energy: {latest.get('energy','n/a')}/10")
    else:
        lines.append("- No daily logs yet")
    lines.append("")

    lines.append("## Project delivery watchlist")
    if active_projects:
        for p in active_projects:
            lines.append(
                f"- {p.get('project','(unnamed)')} | priority={p.get('priority','n/a')} | deadline={p.get('deadline','n/a')} | milestone={p.get('current_milestone','n/a')} | next={p.get('next_action','n/a')}"
            )
    else:
        lines.append("- No active projects")
    lines.append("")

    lines.append("## On-track / off-track flags")
    for metric, cfg in targets.items():
        if metric not in actuals:
            continue
        a = actuals[metric]
        t = cfg.get("target", 0.0)
        status = on_track(a, t)
        lines.append(f"- {metric}: {status} (actual={a:.2f}, target={t:.2f})")
    lines.append("")

    lines.append("## Auto recommendations")
    recs = []
    if avg_deep7 < targets.get("deep_work_hours", {}).get("target", 4.0):
        recs.append("Lock one non-negotiable 120-minute deep-work block in morning calendar.")
    if main_done7 < targets.get("main_task_done_rate", {}).get("target", 0.85):
        recs.append("Reduce daily plan to one must-win task before noon.")
    if exercise7 < targets.get("exercise_rate", {}).get("target", 0.70):
        recs.append("Attach exercise to an existing trigger (after waking or after work).")
    if risk >= 60:
        recs.append("Project risk is high: pause low-priority work and break deadlines into weekly milestones.")
    if net30_usd < targets.get("net_income", {}).get("target", 1000.0):
        recs.append("Income pace is below target: prioritize activities with direct cash impact this week.")

    if recs:
        for r in recs:
            lines.append(f"- {r}")
    else:
        lines.append("- Keep current pace. Focus on consistency and quality.")

    out = os.path.join(REPORTS, "dashboard.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(out)


if __name__ == "__main__":
    main()
