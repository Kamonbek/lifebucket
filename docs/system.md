# Life OS Tracking System

## Purpose
A measurable personal operating system with daily input and visual output.

## Data model
- logs/daily_log.csv: core day metrics
- logs/income.csv, logs/expenses.csv: money flow
- logs/projects.csv: active work and delivery risk
- logs/habits.csv: habit-level consistency scores
- logs/time_blocks.csv: planned vs actual execution quality
- config/metrics_targets.csv: target thresholds for on/off track

## Input workflow (daily)
1) Fill one check-in:
python3 /workspace/life-os/tools/checkin.py \
  --wake-time 06:30 --sleep-hours 7.5 --deep-work-hours 3.5 --learning-hours 1.2 \
  --exercise yes --main-task-done yes --mood focused --energy 8 --notes "good day"

2) Optional add income/expense in same command:
  --income 120 --income-source consulting --expense 18 --expense-category food

## Output workflow
- Markdown analytics snapshot:
  python3 /workspace/life-os/tools/build_dashboard.py
  -> /workspace/life-os/reports/dashboard.md

- Visual web dashboard:
  /workspace/life-os/web/dashboard.html
  (served via GitHub Pages at lifebucket.me/dashboard)

## Weekly review loop
- Check off-track metrics
- Reduce active projects if risk > 60
- Select one metric to improve next week
- Update targets only when behavior baseline stabilizes for 3+ weeks
