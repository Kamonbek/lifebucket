# Daily Insight Brief
_Data anchor date: 2026-05-03_

## Metrics (strict)
- Sleep duration (latest 2026-04-29): 06:25:37 **[confidence: low]**
- Sleep duration (7d avg): 06:25:37 (n=1) **[confidence: low]**
- Wake-time consistency (std dev): N/A (requires >=5 points; got 1) **[confidence: low]**
- Deep-work 7d vs prior 7d delta: N/A (latest7 n=1, prior7 n=0) **[confidence: low]**
- Learning 7d vs prior 7d delta: N/A (latest7 n=1, prior7 n=0) **[confidence: low]**
- Message volume trend: down (slope=-91.70 msgs/day over 4 days) **[confidence: medium]**
- Voice/Text ratio: 110/303 = 0.363 **[confidence: medium]**

## Top 3 Risk Signals
- Wake-time consistency cannot be measured (<5 recent points).
- Message volume trend is down (negative slope across observed days).
- Voice/text ratio is low (text-heavy communication mix).

## Up
- Sleep log has a valid latest duration (06:25:37).
- Voice capture is present (110 voice vs 303 text messages).

## Down
- Message volume trend is down.

## Drift
- Wake-time consistency is unmeasurable due to sparse points.
- Communication mix is drifting text-heavy (voice/text < 0.5).
- Sleep trend reliability is low (insufficient sleep rows).

## Immediate Action
- Capture at least 5 wake times in the next 7 days to unlock wake consistency metric.
