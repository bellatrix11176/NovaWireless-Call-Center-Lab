# NovaWireless Call Center Lab

### The only synthetic call center framework that gives you ground truth for the metrics everyone else is guessing about.

---

Real call centers don't tell you when a KPI is lying. Resolution rates look healthy while the same customers call back a month later. Fraud hides inside compliant-looking transactions. AI-optimized routing makes the dashboard glow green while the trust signal underneath decays quietly.

This lab builds the environment where all of that is visible — because every call, every rep decision, every gamed metric, and every fraudulent transaction has a ground-truth label attached to it.

**NovaWireless is a fictional wireless carrier.** The lab generates one year of synthetic call center operations — 60,000+ calls, 10,000 customers, 250 representatives — with the kind of data transparency that doesn't exist in production. The dataset is designed for AI governance research, KPI integrity auditing, fraud detection development, and executive decision support.

---

## Why This Matters

Most call center analytics begin with the assumption that the data is clean. It isn't.

When agents are optimized against a proxy KPI like "resolution rate," they learn to game it. Service credits suppress repeat contacts inside the measurement window. Proxy resolution diverges from actual resolution. The 30-day FCR metric looks stable while the 31–60 day repeat rate quietly climbs.

This lab makes that divergence measurable. Every call carries both the **proxy label** (what the system recorded) and the **ground truth** (what actually happened). That gap is where governance begins.

The framework operationalizes five governance signals from the accompanying research:

| Signal | What It Detects |
|---|---|
| **DAR** — Delayed Adverse Rate | Failures that surface after a call was labeled "resolved" |
| **DRL** — Downstream Remediation Load | Hidden workload created by upstream metric gaming |
| **DOV** — Durable Outcome Validation | Decay in the predictive validity of proxy KPIs over time |
| **POR** — Proxy Overfit Ratio | Acceleration gap between what the dashboard says and what's true |
| **SII** — System Integrity Index | Composite governance health score across all signals |

If you're responsible for a contact center operation under AI optimization pressure, these are the signals your current dashboards don't show you.

---

## Quick Start

```bash
pip install -r requirements.txt
python run_lab.py
```

One command. Generates customers, representatives, 12 months of calls with full transcripts, and runs the pressure experiment. Everything lands in `output/`, organized and ready for analysis.

```bash
python run_lab.py --n_customers 5000    # smaller customer base
python run_lab.py --n_calls 7000        # more calls per month
python run_lab.py --n_months 6          # half-year simulation
python run_lab.py --seed 99             # different random seed
```

---

## What's Inside

```
NovaWireless-Call Center Lab/
│
├── novawireless-call-gen/          Call Generator — 12 months of call records + transcripts
├── novawireless-customer-gen/      Customer Generator — 10K accounts + account graph
├── novawireless-rep-gen/           Rep Generator — 250 representatives + persona profiles
│
├── data/                           Shared inputs (auto-synced by run_lab.py)
├── output/                         All generated artifacts
├── assets/                         Static resources
├── docs/                           Research papers + documentation
│
├── run_lab.py                      Master orchestrator — runs everything
├── requirements.txt                Single dependency file for the entire lab
├── .labroot                        Sentinel file for path resolution
└── README.md                       You are here
```

Each generator is a self-contained module with its own README, source code, and documentation. The master orchestrator handles execution order, file organization, and data syncing between stages — so you never have to think about which script runs before which.

---

## The Three Generators

### Customer Generator → `novawireless-customer-gen/`

Produces **10,000 synthetic wireless accounts** with tenure, churn risk, trust baseline, patience, device payment plans, and a full account graph including lines, devices, EIP agreements, and usage snapshots. The master account ledger includes intentional IMEI anomalies (~8% mismatch rate) that simulate real-world fraud patterns downstream.

Distributions are grounded in the IBM Telco Customer Churn dataset. No real customer data is used.

### Rep Generator → `novawireless-rep-gen/`

Produces **250 synthetic call center representatives** with correlated KPI profiles — FCR, AHT, escalation rate, compliance risk, burnout index, resilience, and volatility. KPIs are synthesized as correlated proxies, not independent draws, so bad weeks cluster and high-pressure conditions degrade performance realistically.

Each rep is enriched with persona traits (policy accuracy, discovery skill, conflict tolerance, credit discipline) that feed directly into the call generator's behavioral drift model.

### Call Generator → `novawireless-call-gen/`

Produces **12 months of call records** — metadata CSVs, sanitized analysis-ready CSVs, and full turn-by-turn dialogue transcripts in JSONL format. 10 scenario types cover clean resolutions, metric gaming, four fraud variants, activations, and legitimate line additions.

The call generator is where Goodhart's Law becomes data. Rep gaming propensity drifts upward over gamed calls. Customer trust decays per scenario. Repeat contact chains show the 31–60 day spike that the 30-day FCR window hides. A contextual frustration injection system adds realistic profanity to transcripts based on scenario severity and deflection language in the agent's turns.

---

## How run_lab.py Works

| Step | What It Does | Where It Writes |
|---|---|---|
| 1 | Generate 10K customers + account graph | `output/customer-gen/` |
| 2 | Build master account ledger | `output/ledger/` |
| 3 | Inject IMEI anomalies (realistic ~8% rate) | `output/ledger/` |
| 4 | Fix contract_proxy → billing_agreement_type | `output/ledger/` + `data/` |
| 5 | Generate 250 employees + persona enrichment | `output/rep-gen/` |
| 6 | Generate calls: month 1 + append months 2–12 | `output/call-gen/` |
| 7 | Organize into metadata/sanitized/transcripts | `output/call-gen/` |
| 8 | Run pressure experiment | `output/experiments/` |

Each step wipes its output subfolder before running. Files that downstream scripts need are automatically copied into `data/`. No stale artifacts, no manual file shuffling.

---

## Scenario Mix

| Scenario | Share | What Happens |
|---|---|---|
| `clean` | 44% | Genuine issue, genuine resolution |
| `unresolvable_clean` | 11% | Rep tried; system couldn't fix it |
| `gamed_metric` | 10% | System records resolution without genuine fix — the core gaming signal |
| `fraud_store_promo` | 7% | Store promised a promotion the customer wasn't eligible for |
| `fraud_line_add` | 6% | Line added to account without customer consent |
| `activation_clean` | 8% | Successful device activation |
| `activation_failed` | 4% | SIM or IMEI provisioning failure |
| `line_add_legitimate` | 4% | Customer legitimately adds a line |
| `fraud_hic_exchange` | 3% | Device exchange opened on wrong line |
| `fraud_care_promo` | 3% | Care rep applied unauthorized discount |

---

## Key Signals in the Data

| Column | Why It Matters |
|---|---|
| `resolution_flag` | System-recorded disposition — the proxy KPI |
| `true_resolution` | What actually happened — the ground truth |
| `repeat_contact_30d` | Repeat inside the gaming window (suppressed by bandaid credits) |
| `repeat_contact_31_60d` | Repeat *after* the gaming window — the tell |
| `credit_type` | `bandaid` = credit issued to suppress repeat, not fix the problem |
| `rep_gaming_propensity` | Drifts upward over gamed calls — emergent workforce risk |
| `customer_trust_baseline` | Decays per scenario across the simulation — invisible to dashboards |

The `bandaid` credit pattern is the core detectable signal: `credit_type=bandaid` + `repeat_contact_31_60d=True` means the issue resurfaced after the measurement window closed. That pattern is the proof that the KPI is lying.

---

## Downstream Analysis

The lab's sanitized output feeds four downstream research pipelines:

| Repository | What It Does |
|---|---|
| **novawireless-governance-pipeline** | Structured trust signal diagnostics — friction scoring, trust decay |
| **novawireless-transcript-analysis** | Linguistic signal diagnostics — TF-IDF term lift, profanity analysis |
| **NovaWireless_KPI_Drift_Observatory** | Formal SII evidence — the "When KPIs Lie" governance framework |
| **NovaFabric Validation Checklist** | Causal validation — friction lift, logistic models, negative controls |

---

## Research Papers

This lab supports four published works:

- **When KPIs Lie: Governance Signals for AI-Optimized Call Centers** — formal definitions of DAR, DRL, DOV, POR, and SII
- **Trust Signal Health Assessment of the NovaWireless Synthetic Call Center** — four-layer diagnostic pipeline for proxy-outcome divergence
- **Linguistic Signatures of Proxy-Outcome Divergence in Synthetic Call Center Transcripts** — TF-IDF term lift and profanity analysis
- **Governance-Grade Evidence for KPI Risk Under AI-Optimized Call Center Dynamics** — causal validation with friction lift, odds ratios, and negative controls

All papers by Gina Aulabaugh, 2026.

---

## Requirements

```bash
pip install -r requirements.txt
```

One file covers the entire lab: `numpy`, `pandas`, `matplotlib`, and `scikit-learn`.

---

## Data Sources

Distributional parameters are derived from publicly available datasets including IBM Telco Customer Churn, FCC CGB Consumer Complaints, and Kaggle call center and workforce datasets. No raw source data is included. All outputs are fully synthetic. Full citations are in each generator's `docs/` folder.

---

## License

MIT License — see LICENSE.txt for details.

All data is fully synthetic. No real customer or employee data was used. NovaWireless is a fictional entity.

---

<p align="center">
  <b>Gina Aulabaugh</b><br>
  <a href="https://www.pixelkraze.com">www.pixelkraze.com</a>
</p>
