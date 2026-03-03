# novawireless-rep-gen

### 250 synthetic call center reps whose bad habits show up in the data.

---

This generator builds the representative workforce for the NovaWireless Call Center Lab. Not a flat table of random KPIs — a roster of agents with correlated performance profiles, persona traits, and behavioral starting states that drift during the call simulation.

The reps generated here don't just have statistics. They have tendencies. A rep with low policy accuracy and high credit discipline is a different kind of risk than a rep with high burnout and low conflict tolerance. Those differences compound across thousands of calls, producing the emergent workforce patterns that make the lab's governance signals detectable.

---

## What It Produces

| File | What's In It |
|---|---|
| `novawireless_employee_database.csv` | 250 reps with KPIs, persona traits, and behavioral state |
| `rep_persona_profiles__v1.csv` | Slim persona-only file for transcript generation |
| `employees__csr_one_queue__<run_id>.csv` | Versioned archive copy |

---

## Why Correlated KPIs Matter

Most synthetic workforce generators sample each metric independently. That produces reps who are simultaneously the best at resolution and the worst at handle time — statistically possible, operationally meaningless.

This generator builds KPIs as **correlated proxies**. Bad weeks cluster. A rep under pressure doesn't just have a high escalation rate — their compliance risk rises, their burnout index ticks up, and their gaming propensity follows. The correlation structure means the Call Generator inherits realistic behavioral dynamics without any special-case logic.

---

## Persona Traits

Each rep is enriched with eight derived traits that feed directly into the Call Generator's behavioral model:

| Trait | What It Drives |
|---|---|
| `policy_accuracy` | Whether the rep applies the correct resolution or a workaround |
| `discovery_skill` | How well the rep identifies the actual root cause |
| `conflict_tolerance` | How the rep handles frustrated or profane customers |
| `technical_skill` | Activation and device troubleshooting competence |
| `credit_discipline` | Whether credits are applied within policy or used as band-aids |
| `ownership_bias` | Tendency to take ownership vs. deflect to another team |
| `emotional_regulation` | Composure under pressure — affects transcript tone |
| `aht_pressure_bias` | Whether the rep rushes calls to hit handle time targets |

These traits are **deterministic** — derived from KPIs via fixed formulas, not additional randomness. Same input, same output, every time.

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
python src/run_all.py --n 500 --seed 999
```

| Argument | Default | What It Controls |
|---|---|---|
| `--n` | 250 | Number of representatives |
| `--seed` | 1337 | Reproducibility seed |
| `--site` | NovaWireless | Site name in rep records |
| `--queue_name` | General Support | Queue name in rep records |

---

## Pipeline

```bash
python src/run_all.py    # runs both steps
```

| Step | Script | What It Does |
|---|---|---|
| 1 | `generate_employees_call_center_one_queue.py` | Samples KPIs from multi-source priors. Assigns skill tags, strain tiers, behavioral knobs. |
| 2 | `04_rep_persona_compiler.py` | Derives persona traits from KPIs using fixed formulas. |

Utility scripts `02_build_call_taxonomy_from_fcc.py` and `03_build_call_subreason_priors.py` only need to run if you update the FCC source data. Their outputs are committed to `data/`.

---

## Key Design Decisions

**Single queue, single role.** All reps are Customer Service Representatives in General Support. Multi-department routing complexity belongs in the Call Generator, not here.

**Skills tilt outcomes, not determine them.** A billing specialist is slightly better at billing calls. Every rep can handle every call type. This prevents scenario assignment from becoming deterministic based on rep skill tags alone.

**Rep state drifts during simulation.** The employee database provides the *starting state*. The Call Generator evolves `gaming_propensity`, `burnout_level`, and `policy_skill` per rep across calls — so the workforce looks different in month 12 than it did in month 1.

---

## Prior Data Sources

| File | Source | What It Provides |
|---|---|---|
| `kaggle_employee_persona_priors.csv` | Kaggle Employee Churn | Patience, empathy, burnout, escalation proneness |
| `fcc_cgb_consumer_complaints__rep_specialization_priors.csv` | FCC CGB | Skill tag distribution |
| `kaggle_call_center_weekday_pressure.csv` | Kaggle Call Center | Weekday pressure index |
| `ibm_telco_segment_pressure.csv` | IBM Telco Churn | Segment-level pressure adjustment |

All prior files are included in the repo. No internet access required.

---

## Repository Structure

```
novawireless-rep-gen/
├── src/
│   ├── run_all.py                                      Run this
│   ├── generate_employees_call_center_one_queue.py     Step 1: generate roster
│   ├── 04_rep_persona_compiler.py                      Step 2: enrich with persona traits
│   ├── 02_build_call_taxonomy_from_fcc.py              Utility: rebuild call type priors
│   └── 03_build_call_subreason_priors.py               Utility: rebuild subreason priors
├── data/employee_generation_inputs/                    Prior files
├── docs/                                               Citations + documentation
└── README.md
```

---

## Requirements

Python 3.10+ with `pandas` and `numpy`.

---

<p align="center">
  <b>Gina Aulabaugh</b><br>
  <a href="https://www.pixelkraze.com">www.pixelkraze.com</a>
</p>
