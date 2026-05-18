# Weekly Experiment Brief — 2026-05-18

## Research sources (behavior design + retention + habit UX + motivation)
1. Gollwitzer, P. M., & Sheeran, P. (2006). *Implementation Intentions and Goal Achievement: A Meta-analysis of Effects and Processes*. Advances in Experimental Social Psychology. DOI: `10.1016/S0065-2601(06)38002-1`.
2. Lally, P., van Jaarsveld, C., Potts, H., & Wardle, J. (2009). *How are habits formed: Modelling habit formation in the real world*. European Journal of Social Psychology. DOI: `10.1002/ejsp.674`.
3. Deci, E. L., & Ryan, R. M. (2000). *Self-determination theory and the facilitation of intrinsic motivation, social development, and well-being*. American Psychologist. DOI: `10.1037/0003-066X.55.1.68`.
4. Michie, S., et al. (2013). *The Behavior Change Technique Taxonomy (v1) of 93 Hierarchically Clustered Techniques*. Annals of Behavioral Medicine. DOI: `10.1007/s12160-013-9486-6`.
5. Burke, L. E., et al. (2019). *Defining Adherence to Mobile Dietary Self-Monitoring and Assessing Tracking Over Time*. Journal of the Academy of Nutrition and Dietetics. DOI: `10.1016/j.jand.2019.03.012`.

## Candidate experiments
Scoring scale: Impact (1-5, higher better), Effort (1-5, lower better), Risk (1-5, lower better), Reversibility (1-5, higher better).
Weighted total = `Impact*0.45 + (6-Effort)*0.2 + (6-Risk)*0.2 + Reversibility*0.15`.

| Experiment | Impact | Effort | Risk | Reversibility | Weighted total |
|---|---:|---:|---:|---:|---:|
| A) If-then adherence tracker + one-command logger | 5 | 2 | 2 | 5 | **4.60** |
| B) Loss-aversion streak penalty UI (red warnings + countdown) | 4 | 3 | 3 | 3 | 3.55 |
| C) Randomized reward messaging (A/B nudge variants) | 3 | 4 | 3 | 4 | 3.05 |

## Selected experiment
**A) If-then adherence tracker + one-command logger** (highest weighted score, lowest implementation risk, strongest reversibility).

## Implemented changes
- Added `tools/if_then_planner.py` to log implementation-intention rows and adherence completion.
- Added new log stream: `logs/if_then_plans.csv` (auto-created by tool).
- Added dashboard quick-action command update in both:
  - `web/dashboard.html`
  - `docs/dashboard/index.html`
- Updated marker in both dashboard paths to `weekly-experiment-if-then-adherence-v2`.
- Extended `tools/build_dashboard.py` weekly pulse section with:
  - if-then adherence (7d)
  - if-then confidence (7d)
  - if-then plans logged count
- Extended Supabase pipeline end-to-end:
  - `supabase/schema.sql`: new `if_then_plans` table + summary field `if_then_adherence_7d`
  - `tools/sync_supabase.py`: idempotent upsert from `logs/if_then_plans.csv`

## Numeric flow sample
Command:
```bash
python3 tools/if_then_planner.py --date 2026-05-18 --cue "21:30 phone charging" --action "paste minimum daily row to daily_log.csv" --obstacle "feel too tired" --fallback "log only sleep/deep/energy" --confidence 8.5 --adherence 1 --notes weekly-experiment-if-then-adherence-v2
```
Rows produced:
- `logs/if_then_plans.csv` row with adherence `1`
- `logs/outcomes.csv` row with `metric_name=if_then_adherence_done`, `actual=1.00`

## Success metric (next 7 days)
- Primary: `if_then_adherence_7d >= 0.80`
- Secondary: `daily_log coverage >= 5/7 days`
- Guardrail: no increase in alert count in `reports/dashboard.md`

## Rollback
1. Revert commit containing this experiment.
2. Optionally remove generated rows tagged `weekly-experiment-if-then-adherence-v2` from:
   - `logs/if_then_plans.csv`
   - `logs/outcomes.csv`
3. Re-run:
   - `uv run --with 'psycopg[binary]' python tools/sync_supabase.py`
   - `python3 tools/build_dashboard.py`
