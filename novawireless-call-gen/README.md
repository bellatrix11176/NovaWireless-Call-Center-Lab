# novawireless-call-gen

### 12 months of synthetic call center data where every gamed metric has a receipt.

---

This is the engine behind the NovaWireless Call Center Lab. It generates call records, full turn-by-turn dialogue transcripts, and a sanitized 48-column analysis dataset — with ground-truth labels that separate what the agent *reported* from what *actually happened*.

If you've ever suspected that a high resolution rate is hiding a repeat contact problem, this generator builds the data that proves it.

---

## What Makes This Different

Most synthetic call data generators produce flat tables with random labels. This one produces **behavioral dynamics**:

- **Rep state drift.** Gaming propensity, burnout, and policy skill evolve across calls. A rep who starts gaming doesn't stop — the propensity ratchets upward, producing emergent workforce risk patterns visible over months.
- **Customer trust decay.** Trust and churn risk adjust per call based on scenario severity. A customer who hits a gamed call followed by a fraud scenario doesn't just get two bad labels — their trust baseline erodes in a way that compounds across the simulation.
- **Repeat contact chains.** Gamed calls suppress repeats in the 0–30 day window (the FCR measurement period) but spike in the 31–60 day window. That delayed signal is the tell.
- **Contextual frustration.** A profanity injection system adds realistic customer language based on scenario severity, deflection in the agent's turns, and within-call escalation — not random insertion.

The result is a dataset where proxy KPI divergence from ground truth is *measurable, detectable, and consistent* across 60,000+ records.

---

## Quick Start

```bash
python call_gen__run_all.py
```

Or let the lab orchestrator handle it:

```bash
cd ..
python run_lab.py
```

Each invocation generates one month of data. The lab orchestrator runs all 12 months automatically.

---

## What It Produces

| File | Description |
|---|---|
| `calls_sanitized_2025-MM.csv` | 48-column analysis-ready dataset — use this for everything |
| `calls_metadata_2025-MM.csv` | Full metadata including internal scenario labels |
| `transcripts_2025-MM.jsonl` | Turn-by-turn dialogue with speaker tags |
| `call_generation_receipt.json` | Seed, schema version, row count, SHA-256 hashes |

---

## 10 Scenario Types

| Scenario | Mix | The Story |
|---|---|---|
| `clean` | 44% | Real problem, real fix. The baseline. |
| `unresolvable_clean` | 11% | Rep tried everything. System couldn't fix it. Honest failure. |
| `gamed_metric` | 10% | Rep marks it resolved, applies a bandaid credit, moves on. The problem comes back in 31–60 days. |
| `fraud_store_promo` | 7% | Store promised a promo the customer wasn't eligible for. Now care has to clean it up. |
| `fraud_line_add` | 6% | Someone added a line to the account without consent. |
| `activation_clean` | 8% | New device, successful activation. |
| `activation_failed` | 4% | SIM swap or IMEI provisioning failure. |
| `line_add_legitimate` | 4% | Customer adds a line intentionally. |
| `fraud_hic_exchange` | 3% | Device exchange opened on the wrong line — creates a billing mess. |
| `fraud_care_promo` | 3% | Care rep applied an unauthorized discount to close the call faster. |

The `gamed_metric` scenario is the core signal. Proxy resolution says "resolved." Ground truth says "not resolved." The bandaid credit buys 30 days of silence. Then the customer calls back — outside the measurement window, where no one is watching.

---

## Contextual Frustration Injection

The profanity system (`src/profanity_injection.py`) doesn't randomly scatter expletives. It models frustration as a function of five variables — patience, trust, repeat status, churn risk, and scenario severity — and fires contextually when the agent's turn contains deflection language like "unfortunately" or "seven business days."

Over 60 unique phrases across three intensity tiers. Within-call escalation means the third customer turn hits harder than the first. Gaming and fraud scenarios produce more frustration than clean scenarios — because customers whose problems are deflected express it.

---

## Repository Structure

```
novawireless-call-gen/
├── src/
│   ├── generate_calls.py            Main generation logic
│   ├── transcript_builder.py        Template-driven transcript assembly
│   ├── profanity_injection.py       Contextual frustration injection (447 lines)
│   ├── sanitize_calls.py            Sanitization to 48-column schema
│   └── build_analysis_dataset.py    NLP feature extraction + join
├── docs/                            Companion paper + citations
├── call_gen__run_all.py             Top-level runner
└── README.md
```

---

## Upstream Dependencies

This generator requires two input files produced by sibling generators:

| File | Source |
|---|---|
| `customers.csv` | `novawireless-customer-gen` |
| `novawireless_employee_database.csv` | `novawireless-rep-gen` |

The lab orchestrator (`run_lab.py`) handles this automatically.

---

## Companion Paper

> Aulabaugh, G. (2026). *Goodhart Meets the Agent: When KPIs Break Under AI Speed — A Synthetic Framework for Fraud Detection, Metric Gaming, and Behavioral Drift.* NovaWireless Applied Research.

---

## Requirements

Python 3.10+ with `pandas` and `numpy`. No external APIs. No proprietary libraries.

Reproducibility is deterministic given the same seed. Each run produces a receipt with SHA-256 hashes for full auditability.

---

<p align="center">
  <b>Gina Aulabaugh</b><br>
  <a href="https://www.pixelkraze.com">www.pixelkraze.com</a>
</p>
