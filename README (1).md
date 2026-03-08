# novawireless-lab

**Synthetic call record generator for NovaWireless KPI Drift research.**

Grounded in: *"When KPIs Lie: Governance Signals for AI-Optimized Call Centers"* — Aulabaugh (2026)

---

## What this repo does

`novawireless-lab` is the simulation engine. It generates one full year of synthetic NovaWireless call center data that embeds **KPI Self-Reinforcement Drift** — the structural failure mode where a proxy metric simultaneously functions as a performance target, an incentive driver, and a machine-learning label, causing the system to look better while getting worse.

---

## Empirical anchors

| Finding | Paper target | Generator output |
|---|---|---|
| Dashboard FCR (proxy label) | 89.2% | ~89.1% |
| Ground-truth FCR (durable) | 46.9% | ~40–47% |
| Goodhart gap | 42.4 pp | ~48 pp |
| Gamed call share (December) | 47.0% | ~46–47% |
| Unauthorized credit rate (gamed) | 71.1% | ~71% |
| Trust depletion / interaction | -0.042 | -0.042 |
| Churn threshold crossings (12-mo) | ~466 customers | ~490–510 |
| CLV at risk | $420,732 | ~$430–460K |

---

## Outputs (CSV + JSON)

### `calls.csv` / `calls.json`
Interaction-level raw records. One row per call.

| Field | Description |
|---|---|
| `call_id` | UUID |
| `interaction_date` | ISO date |
| `month` | 1–12 |
| `agent_id` | AGT_XXXX |
| `customer_id` | CUST_XXXXX |
| `call_type` | billing / technical / account |
| `aht_seconds` | Handle time — compresses as gamification increases |
| `fcr_label` | **Proxy dashboard label** — what leadership sees (0/1) |
| `durable_resolution` | **Ground truth** — issue still resolved after 30 days? (0/1) |
| `is_gamed` | Structural drift flag (0/1) |
| `unauthorized_credit` | Bandaid credit used to silence customer within 30-day window (0/1) |
| `repeat_contact_30d` | Customer called back within observation window W (0/1) |
| `escalated` | Escalated after repeat contact (0/1) |
| `trust_delta` | Per-interaction trust depletion (-0.042 standard, -0.091 gamed) |
| `cumulative_trust` | Running customer trust score |
| `churn_triggered` | Customer crossed churn threshold on this call (0/1) |
| `hidden_cost_usd` | Incremental operational cost attributable to proxy gaming |

### `signals.csv` / `signals.json`
Pre-computed governance signals per agent per month. One row per agent-month.

| Field | Description |
|---|---|
| `fcr_label_rate` | Proxy dashboard FCR for this agent-month |
| `durable_rate` | Ground-truth durable resolution rate |
| `goodhart_gap` | fcr_label_rate − durable_rate |
| `DAR_raw` | F/D — repeat contacts after labeled successes |
| `DAR` | Normalized [0,1] — higher is worse |
| `DRL_raw` | Jensen-Shannon divergence of post-success workload |
| `DRL` | Normalized [0,1] — higher is worse |
| `DOV` | Predictive decay vs January baseline — higher is worse |
| `POR_raw` | Proxy/durable acceleration ratio (ΔP / ΔT) |
| `POR` | Normalized [0,1] — higher is worse |
| `SII` | System Integrity Index [0–100] |
| `SII_gated` | SII with DOV veto: gates to 100 if DOV ≥ τ (0.70) |

---

## Formal metric definitions

From Appendix A of Aulabaugh (2026):

```
clamp(x, 0, 1) = min(1, max(0, x))

N_up(x; L, H) = clamp((x - L) / (H - L), 0, 1)

DAR  = N_up(F/D; L_DAR, H_DAR)
DRL  = N_up(JS(p || q); L_DRL, H_DRL)
DOV  = clamp((A_base - A_cur) / (A_base + ε), 0, 1)
POR  = clamp((clamp(ΔP/ΔT, 0, K) - 1) / (K - 1))

SII       = 100 * (w_DAR·DAR + w_DRL·DRL + w_DOV·DOV + w_POR·POR)
SII_gated = 100 if DOV ≥ τ, else SII
```

Weights: `w_DAR=0.30, w_DRL=0.25, w_DOV=0.25, w_POR=0.20`
Veto threshold τ = 0.70

---

## Usage

```bash
cd novawireless-lab
python src/call_generator.py
# Outputs written to data/output/
```

No external dependencies. Python 3.10+ standard library only.

---

## Structure

```
novawireless-lab/
├── src/
│   └── call_generator.py    # simulation + signal computation
├── data/
│   └── output/
│       ├── calls.csv
│       ├── calls.json
│       ├── signals.csv
│       └── signals.json
└── README.md
```

---

## Related repos

| Repo | Role |
|---|---|
| `novawireless-lab` | **This repo** — synthetic call data generation |
| `novawireless-governance-pipeline` | Signal ingestion, SII computation, escalation logic |
| `NovaWireless_KPI_Drift_Observatory` | Dashboard, monitoring, executive reporting |

---

*Aulabaugh, G. (2026). When KPIs Lie: Governance Signals for AI-Optimized Call Centers.*
*Goodhart, C.A.E. (1975). Problems of monetary management: The U.K. experience.*
*Campbell, D.T. (1976). Assessing the impact of planned social change.*
