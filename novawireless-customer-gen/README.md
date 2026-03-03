# novawireless-customer-gen

### 10,000 synthetic wireless accounts with the fraud patterns already baked in.

---

This generator builds the customer base for the NovaWireless Call Center Lab — accounts, lines, devices, payment plans, usage snapshots, and a master account ledger with intentional data defects that mirror real-world fraud signatures.

Most synthetic customer datasets hand you a clean table. This one hands you a table with IMEI mismatches, ghost lines, and billing anomalies embedded at realistic rates — because that's what real data looks like, and that's what your fraud detection models need to train against.

---

## What It Produces

| File | What's In It |
|---|---|
| `customers.csv` | 10,000 accounts with tenure, churn risk, trust baseline, patience, payment method |
| `lines.csv` | Per-line records — voice lines and 5G home internet |
| `eip_agreements.csv` | Equipment Installment Plans (24/30/36 month device financing) |
| `line_device_usage.csv` | Device usage snapshots per line |
| `master_account_ledger.csv` | Everything joined flat, with IMEI anomaly flags |

---

## Why the Anomalies Matter

The master account ledger includes two categories of intentional defects:

**IMEI mismatches (~6% of accounts).** A device's IMEI in the usage table doesn't match the IMEI on the EIP agreement. In the real world, this means someone is using a device on a line it wasn't financed on — a pattern that shows up in unauthorized line additions, device swap fraud, and HIC exchange errors.

**Missing usage IMEIs (~3% of lines).** A line has an active EIP but no usage IMEI captured. Ghost lines. Capture failures. The kind of gap that makes a fraud analyst's eye twitch.

These aren't bugs. They're the upstream signals that the Call Generator uses to assign fraud scenarios downstream. The customer with the IMEI mismatch is the one who ends up calling about an unauthorized charge — because that's how the real pattern works.

---

## Quick Start

```bash
python src/run_all.py
```

Or let the lab orchestrator handle it:

```bash
cd ..
python run_lab.py
```

### Options

```bash
python src/run_all.py --n_customers 5000 --seed 99
```

| Argument | Default | What It Controls |
|---|---|---|
| `--n_customers` | 10,000 | Size of the customer base |
| `--seed` | 42 | Reproducibility seed |
| `--p_inject_eip_usage_mismatch` | 0.06 | IMEI mismatch injection rate |
| `--p_voice_eip_attach_if_plan` | 0.85 | EIP attachment probability for voice lines |

---

## Pipeline

```bash
python src/run_all.py    # runs all four steps
```

| Step | Script | What It Does |
|---|---|---|
| 1 | `generate_customers.py` | Samples customer attributes from IBM Telco-derived distributions. Builds the full account graph. |
| 2 | `02_build_master_account_ledger.py` | Joins customers, lines, EIP, and usage into a single flat ledger. |
| 3 | `03_inject_imei_anomalies.py` | Injects IMEI swaps and missing usage IMEIs at configurable rates. |
| 4 | `fix_ledger_contract_proxy.py` | Replaces the IBM-derived `contract_proxy` column with `billing_agreement_type` based on actual EIP data. |

---

## Key Design Decisions

**No service contracts.** NovaWireless customers are month-to-month. The only financial commitment is an optional Equipment Installment Plan. The `billing_agreement_type` field reflects this — not the IBM source artifact.

**Churn risk is per-customer.** Derived from individual attributes (tenure, service type, payment method), not a global mean. Ranges from ~0.01 to ~0.63.

**IMEI anomalies are intentional and documented.** They simulate real-world patterns that the Call Generator consumes to assign `fraud_line_add` and `fraud_hic_exchange` scenarios. The anomaly injection rate is logged in the generation receipt.

---

## Repository Structure

```
novawireless-customer-gen/
├── src/
│   ├── run_all.py                              Run this
│   ├── generate_customers.py                   Step 1: customers + account graph
│   ├── 02_build_master_account_ledger.py       Step 2: flatten to ledger
│   ├── 03_inject_imei_anomalies.py             Step 3: inject IMEI defects
│   └── fix_ledger_contract_proxy.py            Step 4: fix billing agreement field
├── docs/                                       Citations + documentation
├── data/external/params_sources/               Intermediate pipeline files
└── README.md
```

---

## Data Sources

Distributional parameters derived from the IBM Telco Customer Churn dataset and FCC CGB Consumer Complaints. No raw source data is included. All outputs are fully synthetic.

---

## Requirements

Python 3.10+ with `pandas` and `numpy`.

---

<p align="center">
  <b>Gina Aulabaugh</b><br>
  <a href="https://www.pixelkraze.com">www.pixelkraze.com</a>
</p>
