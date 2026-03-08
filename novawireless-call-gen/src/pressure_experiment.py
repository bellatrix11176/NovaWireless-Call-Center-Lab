"""
pressure_experiment.py
======================
NovaWireless Ecosystem Pressure Experiment — PRE-GOVERNANCE (Status Quo)

What it shows:
  This is the BEFORE state. Reps operate under a proxy-KPI regime where
  FCR is measured by CRM closure, not durable resolution. Gaming is
  rational under this incentive structure. High pressure accelerates it.

  Baseline vs. High-Pressure conditions show:
    - ~42pp gap between proxy FCR (~89%) and true FCR (~47%)
    - Repeat contacts at 30d AND 31-60d (customers keep calling back)
    - Gaming and fraud scenarios concentrate sharply under pressure
    - Clean call share collapses
    - Burnout, compliance risk, and strain all worsen

  This is the dumpster fire the governance framework is designed to fix.

Outputs:
  output/experiments/experiment_rep_rosters.csv
  output/experiments/experiment_calls.csv
  output/experiments/experiment_summary.csv
  output/experiments/experiment_figures/  (5 PNG charts)

Run:
  python src/pressure_experiment.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript_builder import build_transcript, transcript_to_text


# ── Paths ─────────────────────────────────────────────────────────────────────

def find_repo_root(start=None) -> Path:
    cur = Path(start or __file__).resolve()
    if cur.is_file():
        cur = cur.parent
    labroot_paths = []
    node = cur
    while True:
        if (node / ".labroot").exists():
            labroot_paths.append(node)
        if node.parent == node:
            break
        node = node.parent
    if labroot_paths:
        return labroot_paths[-1]
    node = cur
    while True:
        if (node / "src").is_dir() and (node / "data").is_dir():
            return node
        if node.parent == node:
            break
        node = node.parent
    return Path.cwd().resolve()


REPO_ROOT  = find_repo_root()
OUTPUT_DIR = REPO_ROOT / "output"
EXP_DIR    = OUTPUT_DIR / "experiments"
FIG_DIR    = EXP_DIR / "experiment_figures"


# ── Experiment config ─────────────────────────────────────────────────────────

SEED          = 2026_02_26
N_REPS        = 250
N_CALLS       = 5_000
BASE_TRAINING = 6.5

CONDITIONS = {
    "baseline": {
        "base_strain":  0.52,
        "pressure":     0.14,
        "label":        "Baseline",
        "color":        "#2E5FA3",
    },
    "high_pressure": {
        "base_strain":  0.78,    # severely understaffed
        "pressure":     0.72,    # crisis staffing / quota crunch
        "label":        "High Pressure",
        "color":        "#C45B1A",
    },
}

# Baseline scenario mix — mostly clean but fraud/gaming already present
BASELINE_SCENARIO_MIX = {
    "clean":                0.48,
    "unresolvable_clean":   0.09,
    "gamed_metric":         0.10,
    "fraud_store_promo":    0.07,
    "fraud_line_add":       0.05,
    "fraud_hic_exchange":   0.03,
    "fraud_care_promo":     0.03,
    "loyalty_offer_missed": 0.15,  # present from the start — systemic failure
}

# High-pressure scenario mix — gaming, fraud, and loyalty failures all concentrate
HIGH_PRESSURE_SCENARIO_MIX = {
    "clean":                0.22,
    "unresolvable_clean":   0.05,
    "gamed_metric":         0.22,
    "fraud_store_promo":    0.12,
    "fraud_line_add":       0.10,
    "fraud_hic_exchange":   0.06,
    "fraud_care_promo":     0.04,
    "loyalty_offer_missed": 0.19,  # on almost every other call in Q4 — the missed retention play
}

GAMING_SCENARIOS = {
    "gamed_metric", "fraud_store_promo", "fraud_line_add",
    "fraud_hic_exchange", "fraud_care_promo", "loyalty_offer_missed"
}


# ── KPI synthesis ─────────────────────────────────────────────────────────────

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def z_noise(rng: random.Random, sigma: float = 0.15) -> float:
    u1 = max(1e-9, rng.random())
    u2 = rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2) * sigma


def synthesize_rep(rng: random.Random, base_strain: float,
                   pressure: float, training: float) -> dict:
    patience           = clamp(0.505 + z_noise(rng, 0.08))
    empathy            = clamp(0.500 + z_noise(rng, 0.07))
    escalation_prone   = clamp(0.512 + z_noise(rng, 0.09))
    burnout_risk_prior = clamp(0.481 + z_noise(rng, 0.10))

    burnout    = clamp(0.55 * burnout_risk_prior
                       + 0.30 * base_strain
                       + 0.15 * (pressure - 0.5)
                       - 0.10 * patience
                       + z_noise(rng, 0.10))
    resilience = clamp(1.0 - burnout * 0.65
                       + (training / 12.0) * 0.20
                       + z_noise(rng, 0.08))
    volatility = clamp(0.30 + burnout * 0.60 + z_noise(rng, 0.12))

    qa = clamp(0.58
               + 0.12 * patience
               + 0.10 * (training / 12.0)
               - 0.18 * burnout
               + z_noise(rng, 0.06))

    fcr = clamp(0.55
                + 0.18 * qa
                + 0.10 * patience
                - 0.18 * burnout
                - 0.08 * (pressure - 0.5)
                + z_noise(rng, 0.06), 0.10, 0.95)

    base_aht = 560.0
    aht = clamp(base_aht
                * (1.0 + 0.35 * burnout + 0.18 * (pressure - 0.5))
                * (1.0 - 0.08 * (training / 12.0))
                * (1.0 - 0.06 * qa)
                + z_noise(rng, 0.20) * 120,
                240.0, 1600.0)

    escalation = clamp(0.05
                       + 0.18 * escalation_prone
                       + 0.10 * burnout
                       - 0.12 * qa
                       + z_noise(rng, 0.04), 0.01, 0.55)

    repeat_rate = clamp(0.08
                        + 0.65 * (1.0 - fcr)
                        + 0.06 * (pressure - 0.5)
                        + z_noise(rng, 0.04), 0.02, 0.80)

    compliance = clamp(0.10
                       + 0.35 * burnout
                       + 0.25 * (1.0 - qa)
                       + 0.12 * escalation
                       + z_noise(rng, 0.06), 0.01, 0.95)

    aht_norm     = clamp((1600.0 - aht) / (1600.0 - 240.0))
    productivity = clamp(0.42 * fcr + 0.33 * qa + 0.25 * aht_norm
                         - 0.15 * burnout + z_noise(rng, 0.04))

    strain_score = clamp(0.6 * base_strain +
                         0.3 * pressure + 0.1 * burnout + z_noise(rng, 0.05))

    return {
        "patience":           patience,
        "empathy":            empathy,
        "escalation_prone":   escalation_prone,
        "burnout":            burnout,
        "resilience":         resilience,
        "volatility":         volatility,
        "qa":                 qa,
        "fcr":                fcr,
        "aht":                aht,
        "escalation":         escalation,
        "repeat_rate":        repeat_rate,
        "compliance":         compliance,
        "productivity":       productivity,
        "strain_score":       strain_score,
    }


# ── BASE KPI TABLES (per scenario) ────────────────────────────────────────────

# True resolution probability (durable fix, no callback needed)
BASE_TRUE_FCR = {
    "clean":                0.92,
    "unresolvable_clean":   0.10,
    "gamed_metric":         0.18,
    "fraud_store_promo":    0.25,
    "fraud_line_add":       0.22,
    "fraud_hic_exchange":   0.15,
    "fraud_care_promo":     0.30,
    "loyalty_offer_missed": 0.14,  # band-aid discount doesn't fix competitive gap
}

# Proxy resolution probability (CRM closure — what the dashboard sees)
BASE_PROXY_FCR = {
    "clean":                0.90,
    "unresolvable_clean":   0.55,
    "gamed_metric":         0.91,
    "fraud_store_promo":    0.88,
    "fraud_line_add":       0.85,
    "fraud_hic_exchange":   0.87,
    "fraud_care_promo":     0.92,
    "loyalty_offer_missed": 0.93,  # rep marks resolved after applying discount — inflates dashboard
}

# 30-day repeat contact rate
BASE_REPEAT_30D = {
    "clean":                0.06,
    "unresolvable_clean":   0.30,
    "gamed_metric":         0.12,
    "fraud_store_promo":    0.28,
    "fraud_line_add":       0.25,
    "fraud_hic_exchange":   0.32,
    "fraud_care_promo":     0.20,
    "loyalty_offer_missed": 0.18,
}

# 31–60 day repeat contact rate — the smoking gun: discount expired, issue unresolved
BASE_REPEAT_31_60D = {
    "clean":                0.04,
    "unresolvable_clean":   0.25,
    "gamed_metric":         0.45,
    "fraud_store_promo":    0.40,
    "fraud_line_add":       0.38,
    "fraud_hic_exchange":   0.42,
    "fraud_care_promo":     0.35,
    "loyalty_offer_missed": 0.58,  # highest — customer calls back when discount expires
}

# Churn contribution per scenario (multiplier on base churn)
BASE_CHURN_PROB = {
    "clean":                0.028,
    "unresolvable_clean":   0.048,
    "gamed_metric":         0.055,
    "fraud_store_promo":    0.062,
    "fraud_line_add":       0.071,
    "fraud_hic_exchange":   0.065,
    "fraud_care_promo":     0.058,
    "loyalty_offer_missed": 0.085,  # highest base churn — competitor offer never countered
}

# Monthly company churn forecast (flat — based on false proxy FCR world view)
CHURN_FORECAST = {m: 0.042 for m in range(1, 13)}

# Monthly pressure escalation — Q4 is the breaking point
MONTHLY_CONDITIONS = {
    1:  {"base_strain": 0.42, "pressure": 0.12, "label": "Jan"},
    2:  {"base_strain": 0.44, "pressure": 0.14, "label": "Feb"},
    3:  {"base_strain": 0.45, "pressure": 0.14, "label": "Mar"},
    4:  {"base_strain": 0.47, "pressure": 0.18, "label": "Apr"},
    5:  {"base_strain": 0.49, "pressure": 0.20, "label": "May"},
    6:  {"base_strain": 0.50, "pressure": 0.22, "label": "Jun"},
    7:  {"base_strain": 0.54, "pressure": 0.32, "label": "Jul"},   # loyalty calls start spiking
    8:  {"base_strain": 0.57, "pressure": 0.38, "label": "Aug"},
    9:  {"base_strain": 0.60, "pressure": 0.44, "label": "Sep"},   # Q3 pressure builds
    10: {"base_strain": 0.66, "pressure": 0.55, "label": "Oct"},   # Q4 begins
    11: {"base_strain": 0.74, "pressure": 0.66, "label": "Nov"},   # holiday season, competitor promos
    12: {"base_strain": 0.82, "pressure": 0.78, "label": "Dec"},   # breaking point
}

# Loyalty offer missed rate scales with month (competitors ramp holiday promos)
MONTHLY_LOYALTY_MISS_RATE = {
    1: 0.09, 2: 0.09, 3: 0.10, 4: 0.10, 5: 0.11, 6: 0.11,
    7: 0.14, 8: 0.15, 9: 0.17, 10: 0.19, 11: 0.22, 12: 0.25,
}


# ── Scenario sampling ─────────────────────────────────────────────────────────

def sample_scenario(rng: random.Random, scenario_mix: dict) -> str:
    keys   = list(scenario_mix.keys())
    probs  = [scenario_mix[k] for k in keys]
    total  = sum(probs)
    probs  = [p / total for p in probs]
    cumsum = 0.0
    r = rng.random()
    for k, p in zip(keys, probs):
        cumsum += p
        if r <= cumsum:
            return k
    return keys[-1]


def get_scenario_mix_for_month(month: int) -> dict:
    """Blend baseline toward high-pressure as strain/pressure increases monthly."""
    cond   = MONTHLY_CONDITIONS[month]
    strain = cond["base_strain"]
    # pressure weight: 0 at strain=0.42, 1 at strain=0.82
    w = clamp((strain - 0.42) / (0.82 - 0.42))
    mix = {}
    for k in BASELINE_SCENARIO_MIX:
        base_val = BASELINE_SCENARIO_MIX[k]
        hp_val   = HIGH_PRESSURE_SCENARIO_MIX.get(k, base_val)
        mix[k] = base_val + w * (hp_val - base_val)
    # Override loyalty_offer_missed with monthly scaling
    mix["loyalty_offer_missed"] = MONTHLY_LOYALTY_MISS_RATE[month]
    # Re-normalize
    total = sum(mix.values())
    return {k: v / total for k, v in mix.items()}


# ── Single-call simulation ────────────────────────────────────────────────────

def simulate_call(rng: random.Random, rep: dict, scenario: str,
                  pressure: float) -> dict:
    """Simulate one call and return KPI outcomes."""
    true_fcr_base  = BASE_TRUE_FCR.get(scenario, 0.50)
    proxy_fcr_base = BASE_PROXY_FCR.get(scenario, 0.85)
    repeat_30d     = BASE_REPEAT_30D.get(scenario, 0.10)
    repeat_31_60d  = BASE_REPEAT_31_60D.get(scenario, 0.15)
    churn_base     = BASE_CHURN_PROB.get(scenario, 0.04)

    # Rep quality degrades true FCR; proxy FCR is defended under pressure
    true_fcr  = clamp(true_fcr_base  * rep["fcr"] + z_noise(rng, 0.04))
    proxy_fcr = clamp(proxy_fcr_base + 0.04 * pressure + z_noise(rng, 0.03))

    # Repeat contacts worsen with pressure and low true FCR
    rep_30d     = clamp(repeat_30d  * (1 + 0.5 * pressure) + z_noise(rng, 0.03))
    rep_31_60d  = clamp(repeat_31_60d * (1 + 0.8 * pressure) + z_noise(rng, 0.04))

    churn = clamp(churn_base * (1 + 1.2 * pressure) * (2.0 - rep["fcr"]) + z_noise(rng, 0.02))

    return {
        "scenario":       scenario,
        "true_fcr":       round(true_fcr, 4),
        "proxy_fcr":      round(proxy_fcr, 4),
        "repeat_30d":     round(rep_30d, 4),
        "repeat_31_60d":  round(rep_31_60d, 4),
        "churn":          round(churn, 4),
        "aht":            round(rep["aht"], 1),
        "burnout":        round(rep["burnout"], 4),
        "compliance":     round(rep["compliance"], 4),
        "strain":         round(rep["strain_score"], 4),
    }


# ── Condition-level simulation ────────────────────────────────────────────────

def run_condition(condition_name: str, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one experimental condition (baseline or high_pressure)."""
    cond   = CONDITIONS[condition_name]
    rng_r  = random.Random(seed)
    rng_c  = random.Random(seed + 1)

    # Generate rep roster
    rep_rows = []
    for i in range(N_REPS):
        training = clamp(rng_r.gauss(BASE_TRAINING, 1.5), 1.0, 12.0)
        rep      = synthesize_rep(rng_r, cond["base_strain"], cond["pressure"], training)
        rep["rep_id"]   = f"REP-{i+1:04d}"
        rep["condition"] = condition_name
        rep["training"]  = round(training, 2)
        rep_rows.append(rep)
    reps = pd.DataFrame(rep_rows)

    # Generate calls
    scenario_mix = (BASELINE_SCENARIO_MIX
                    if condition_name == "baseline"
                    else HIGH_PRESSURE_SCENARIO_MIX)
    call_rows = []
    for i in range(N_CALLS):
        rep      = reps.iloc[i % N_REPS].to_dict()
        scenario = sample_scenario(rng_c, scenario_mix)
        result   = simulate_call(rng_c, rep, scenario, cond["pressure"])
        result["rep_id"]    = rep["rep_id"]
        result["condition"] = condition_name
        result["call_id"]   = f"{condition_name.upper()}-{i+1:05d}"
        call_rows.append(result)
    calls = pd.DataFrame(call_rows)

    return reps, calls


# ── Monthly time series simulation ───────────────────────────────────────────

def run_monthly_series(seed: int) -> pd.DataFrame:
    """Simulate 12 months of call center metrics showing the Q4 collapse."""
    rng_r = random.Random(seed + 99)
    rng_c = random.Random(seed + 100)

    rows = []
    for month in range(1, 13):
        cond  = MONTHLY_CONDITIONS[month]
        mix   = get_scenario_mix_for_month(month)
        label = cond["label"]

        # Generate rep cohort for this month (matches N_REPS for consistency)
        month_reps = []
        for _ in range(N_REPS):
            training = clamp(rng_r.gauss(BASE_TRAINING, 1.5), 1.0, 12.0)
            rep = synthesize_rep(rng_r, cond["base_strain"], cond["pressure"], training)
            month_reps.append(rep)

        # Rep-level aggregates for this month
        burnout_mean    = round(sum(r["burnout"]    for r in month_reps) / len(month_reps), 4)
        compliance_mean = round(sum(r["compliance"] for r in month_reps) / len(month_reps), 4)

        # Simulate calls for the month
        true_fcrs, proxy_fcrs = [], []
        rep_30d_list, rep_31_60d_list, churn_list = [], [], []
        gaming_flags = []

        for _ in range(N_CALLS):
            rep      = month_reps[int(rng_c.random() * len(month_reps))]
            scenario = sample_scenario(rng_c, mix)
            result   = simulate_call(rng_c, rep, scenario, cond["pressure"])
            true_fcrs.append(result["true_fcr"])
            proxy_fcrs.append(result["proxy_fcr"])
            rep_30d_list.append(result["repeat_30d"])
            rep_31_60d_list.append(result["repeat_31_60d"])
            churn_list.append(result["churn"])
            gaming_flags.append(1 if scenario in GAMING_SCENARIOS else 0)

        loyalty_share = mix.get("loyalty_offer_missed", 0.0)
        actual_churn  = round(sum(churn_list) / len(churn_list), 4)
        gaming_share  = round(sum(gaming_flags) / len(gaming_flags), 4)

        rows.append({
            "month":               month,
            "month_label":         label,
            "proxy_fcr":           round(sum(proxy_fcrs) / len(proxy_fcrs), 4),
            "true_fcr":            round(sum(true_fcrs) / len(true_fcrs), 4),
            "goodhart_gap":        round(
                                       sum(proxy_fcrs) / len(proxy_fcrs)
                                       - sum(true_fcrs) / len(true_fcrs), 4),
            "repeat_30d":          round(sum(rep_30d_list) / len(rep_30d_list), 4),
            "repeat_31_60d":       round(sum(rep_31_60d_list) / len(rep_31_60d_list), 4),
            "actual_churn":        actual_churn,
            "forecast_churn":      CHURN_FORECAST[month],
            "churn_excess":        round(actual_churn - CHURN_FORECAST[month], 4),
            "loyalty_miss_share":  round(loyalty_share, 4),
            "burnout_mean":        burnout_mean,
            "compliance_mean":     compliance_mean,
            "gaming_share":        gaming_share,
            "base_strain":         cond["base_strain"],
            "pressure":            cond["pressure"],
        })

    return pd.DataFrame(rows)


# ── Figures ───────────────────────────────────────────────────────────────────

NOVA_BLUE   = "#2E5FA3"
NOVA_ORANGE = "#C45B1A"
NOVA_RED    = "#B03A2E"
NOVA_GREY   = "#6B7280"
NOVA_GREEN  = "#2E7D52"


def figure_scenario_breakdown(calls_baseline: pd.DataFrame,
                               calls_hp: pd.DataFrame,
                               fig_dir: Path) -> None:
    """Figure 1 — Scenario mix comparison bar chart."""
    scenarios = list(BASELINE_SCENARIO_MIX.keys())
    x = range(len(scenarios))

    base_counts = calls_baseline["scenario"].value_counts(normalize=True).reindex(scenarios, fill_value=0)
    hp_counts   = calls_hp["scenario"].value_counts(normalize=True).reindex(scenarios, fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 5))
    w = 0.35
    bars_b = ax.bar([i - w/2 for i in x], base_counts.values, w,
                    label="Baseline", color=NOVA_BLUE, alpha=0.85)
    bars_h = ax.bar([i + w/2 for i in x], hp_counts.values, w,
                    label="High Pressure", color=NOVA_ORANGE, alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=8)
    ax.set_ylabel("Share of Calls")
    ax.set_title("Figure 1 — Scenario Mix: Baseline vs High Pressure\n"
                 "Gaming and loyalty failures concentrate sharply under pressure",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig1_scenario_breakdown.png", dpi=150)
    plt.close(fig)


def figure_kpi_comparison(calls_baseline: pd.DataFrame,
                           calls_hp: pd.DataFrame,
                           fig_dir: Path) -> None:
    """Figure 2 — KPI comparison: True FCR, Proxy FCR, Goodhart gap, Churn."""
    metrics = {
        "True FCR":       ("true_fcr",  NOVA_BLUE),
        "Proxy FCR":      ("proxy_fcr", NOVA_GREEN),
        "Repeat 30d":     ("repeat_30d", NOVA_GREY),
        "Repeat 31-60d":  ("repeat_31_60d", NOVA_ORANGE),
        "Churn Rate":     ("churn",     NOVA_RED),
    }

    cond_means = {
        "Baseline":      calls_baseline[[c for _, (c, _) in metrics.items()]].mean(),
        "High Pressure": calls_hp[[c for _, (c, _) in metrics.items()]].mean(),
    }

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(metrics))
    w = 0.35
    labels   = list(metrics.keys())
    col_keys = [c for _, (c, _) in metrics.items()]

    ax.bar([i - w/2 for i in x],
           [cond_means["Baseline"][k] for k in col_keys], w,
           label="Baseline", color=NOVA_BLUE, alpha=0.85)
    ax.bar([i + w/2 for i in x],
           [cond_means["High Pressure"][k] for k in col_keys], w,
           label="High Pressure", color=NOVA_ORANGE, alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Rate")
    ax.set_title("Figure 2 — KPI Comparison: Baseline vs High Pressure\n"
                 "Proxy FCR stays high while true FCR collapses; churn and repeat contacts rise",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig2_kpi_comparison.png", dpi=150)
    plt.close(fig)


def figure_rep_burnout(reps_baseline: pd.DataFrame,
                       reps_hp: pd.DataFrame,
                       fig_dir: Path) -> None:
    """Figure 3 — Rep burnout and strain distribution."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, col, title in [
        (axes[0], "burnout",     "Burnout Score"),
        (axes[1], "strain_score", "Strain Score"),
    ]:
        ax.hist(reps_baseline[col], bins=30, alpha=0.65,
                color=NOVA_BLUE, label="Baseline", density=True)
        ax.hist(reps_hp[col],      bins=30, alpha=0.65,
                color=NOVA_ORANGE, label="High Pressure", density=True)
        ax.set_xlabel(title)
        ax.set_ylabel("Density")
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    fig.suptitle("Figure 3 — Rep Burnout and Strain Distribution\n"
                 "High-pressure condition shifts population toward crisis range",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(fig_dir / "fig3_rep_burnout.png", dpi=150)
    plt.close(fig)


def figure_goodhart_gap(calls_baseline: pd.DataFrame,
                        calls_hp: pd.DataFrame,
                        fig_dir: Path) -> None:
    """Figure 4 — Per-scenario Goodhart gap (proxy FCR minus true FCR)."""
    scenarios = list(BASELINE_SCENARIO_MIX.keys())

    def gap(df: pd.DataFrame) -> list:
        g = []
        for s in scenarios:
            sub = df[df["scenario"] == s]
            if len(sub) == 0:
                g.append(0.0)
            else:
                g.append(float(sub["proxy_fcr"].mean() - sub["true_fcr"].mean()))
        return g

    base_gap = gap(calls_baseline)
    hp_gap   = gap(calls_hp)

    x = range(len(scenarios))
    w = 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([i - w/2 for i in x], base_gap, w,
           label="Baseline", color=NOVA_BLUE, alpha=0.85)
    ax.bar([i + w/2 for i in x], hp_gap,   w,
           label="High Pressure", color=NOVA_ORANGE, alpha=0.85)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=8)
    ax.set_ylabel("Proxy FCR − True FCR")
    ax.set_title("Figure 4 — Per-Scenario Goodhart Gap\n"
                 "loyalty_offer_missed shows largest gap: dashboard says resolved, customer churns",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:+.0%}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig4_goodhart_gap.png", dpi=150)
    plt.close(fig)


def figure_monthly_degradation(monthly: pd.DataFrame, fig_dir: Path) -> None:
    """
    Figure 5 — 3-panel monthly time series showing the Q4 collapse.
      Panel 1: Proxy FCR vs True FCR (42pp gap annotated)
      Panel 2: Repeat 30d vs Repeat 31-60d (31-60d explodes in Q4)
      Panel 3: Actual churn vs company forecast (Q4 excess annotated)
    """
    months = monthly["month"].tolist()
    labels = monthly["month_label"].tolist()

    fig, axes = plt.subplots(3, 1, figsize=(12, 13), sharex=True)

    # ── Panel 1: FCR ──────────────────────────────────────────────────────────
    ax1 = axes[0]
    ax1.plot(months, monthly["proxy_fcr"],  color=NOVA_GREEN,  linewidth=2.5,
             label="Proxy FCR (dashboard)", marker="o", markersize=5)
    ax1.plot(months, monthly["true_fcr"],   color=NOVA_RED,    linewidth=2.5,
             label="True FCR (durable)",    marker="s", markersize=5)
    ax1.fill_between(months, monthly["true_fcr"], monthly["proxy_fcr"],
                     alpha=0.12, color=NOVA_RED, label="Goodhart gap")

    # Annotate Q4 gap
    q4_month  = 12
    q4_proxy  = float(monthly.loc[monthly["month"] == q4_month, "proxy_fcr"].iloc[0])
    q4_true   = float(monthly.loc[monthly["month"] == q4_month, "true_fcr"].iloc[0])
    q4_gap_pp = round((q4_proxy - q4_true) * 100, 1)
    ax1.annotate(
        f"Q4 gap: {q4_gap_pp}pp",
        xy=(q4_month, (q4_proxy + q4_true) / 2),
        xytext=(q4_month - 2.2, (q4_proxy + q4_true) / 2 + 0.04),
        arrowprops=dict(arrowstyle="->", color=NOVA_RED, lw=1.5),
        color=NOVA_RED, fontsize=10, fontweight="bold",
    )
    ax1.set_ylabel("FCR Rate")
    ax1.set_title("Panel 1 — Proxy FCR vs True FCR\n"
                  "Dashboard stays green while durable resolution collapses",
                  fontsize=10, fontweight="bold")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)
    ax1.set_ylim(0.0, 1.05)

    # ── Panel 2: Repeat contacts ──────────────────────────────────────────────
    ax2 = axes[1]
    ax2.plot(months, monthly["repeat_30d"],    color=NOVA_BLUE,   linewidth=2.5,
             label="Repeat ≤30d",  marker="o", markersize=5)
    ax2.plot(months, monthly["repeat_31_60d"], color=NOVA_ORANGE, linewidth=2.5,
             label="Repeat 31-60d (discount expired)", marker="s", markersize=5)

    # Annotate Q4 repeat 31-60d spike
    q4_rep_31_60 = float(monthly.loc[monthly["month"] == q4_month, "repeat_31_60d"].iloc[0])
    ax2.annotate(
        f"Q4 31-60d:\n{q4_rep_31_60:.0%} of calls",
        xy=(q4_month, q4_rep_31_60),
        xytext=(q4_month - 2.5, q4_rep_31_60 - 0.06),
        arrowprops=dict(arrowstyle="->", color=NOVA_ORANGE, lw=1.5),
        color=NOVA_ORANGE, fontsize=10, fontweight="bold",
    )
    ax2.set_ylabel("Repeat Contact Rate")
    ax2.set_title("Panel 2 — Repeat Contacts: ≤30d vs 31-60d\n"
                  "31-60d contacts explode when band-aid discounts expire",
                  fontsize=10, fontweight="bold")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)

    # ── Panel 3: Churn vs forecast ────────────────────────────────────────────
    ax3 = axes[2]
    ax3.plot(months, monthly["actual_churn"],   color=NOVA_RED,   linewidth=2.5,
             label="Actual churn", marker="o", markersize=5)
    ax3.plot(months, monthly["forecast_churn"], color=NOVA_GREY,  linewidth=2.0,
             label="Company forecast (based on proxy FCR)", linestyle="--", marker="s", markersize=4)
    ax3.fill_between(months, monthly["forecast_churn"], monthly["actual_churn"],
                     where=[a > f for a, f in zip(monthly["actual_churn"], monthly["forecast_churn"])],
                     alpha=0.15, color=NOVA_RED, label="Forecast miss")

    # Annotate Q4 churn excess
    q4_actual   = float(monthly.loc[monthly["month"] == q4_month, "actual_churn"].iloc[0])
    q4_forecast = float(monthly.loc[monthly["month"] == q4_month, "forecast_churn"].iloc[0])
    q4_excess   = round((q4_actual - q4_forecast) * 100, 1)
    ax3.annotate(
        f"Q4 churn excess:\n+{q4_excess}pp above forecast",
        xy=(q4_month, q4_actual),
        xytext=(q4_month - 3.0, q4_actual + 0.008),
        arrowprops=dict(arrowstyle="->", color=NOVA_RED, lw=1.5),
        color=NOVA_RED, fontsize=10, fontweight="bold",
    )
    ax3.set_ylabel("Monthly Churn Rate")
    ax3.set_title("Panel 3 — Actual Churn vs Company Forecast\n"
                  "Company staffed for a false reality; Q4 excess triggers emergency response",
                  fontsize=10, fontweight="bold")
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))
    ax3.set_xticks(months)
    ax3.set_xticklabels(labels, fontsize=9)
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)

    fig.suptitle("Figure 5 — Q4 Breaking Point: The Three Signals That Appeared Too Late\n"
                 "NovaWireless Governance Lab — Pre-Governance (Status Quo)",
                 fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig5_monthly_degradation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Summary stats ─────────────────────────────────────────────────────────────

def build_summary(reps_b: pd.DataFrame, calls_b: pd.DataFrame,
                  reps_h: pd.DataFrame, calls_h: pd.DataFrame,
                  monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cname, reps, calls in [("baseline", reps_b, calls_b),
                                ("high_pressure", reps_h, calls_h)]:
        gaming_share = calls["scenario"].isin(GAMING_SCENARIOS).mean()
        rows.append({
            "condition":          cname,
            "n_reps":             len(reps),
            "n_calls":            len(calls),
            "proxy_fcr_mean":     round(calls["proxy_fcr"].mean(), 4),
            "true_fcr_mean":      round(calls["true_fcr"].mean(), 4),
            "goodhart_gap_pp":    round((calls["proxy_fcr"].mean() - calls["true_fcr"].mean()) * 100, 1),
            "repeat_30d_mean":    round(calls["repeat_30d"].mean(), 4),
            "repeat_31_60d_mean": round(calls["repeat_31_60d"].mean(), 4),
            "churn_mean":         round(calls["churn"].mean(), 4),
            "burnout_mean":       round(reps["burnout"].mean(), 4),
            "compliance_mean":    round(calls["compliance"].mean(), 4),
            "gaming_share":       round(gaming_share, 4),
            "loyalty_miss_share": round((calls["scenario"] == "loyalty_offer_missed").mean(), 4),
        })

    # Add Q4 monthly stats
    q4 = monthly[monthly["month"] == 12].iloc[0]
    rows.append({
        "condition":          "Q4_monthly_series",
        "n_reps":             N_REPS,
        "n_calls":            N_CALLS,
        "proxy_fcr_mean":     round(float(q4["proxy_fcr"]), 4),
        "true_fcr_mean":      round(float(q4["true_fcr"]), 4),
        "goodhart_gap_pp":    round(float(q4["goodhart_gap"]) * 100, 1),
        "repeat_30d_mean":    round(float(q4["repeat_30d"]), 4),
        "repeat_31_60d_mean": round(float(q4["repeat_31_60d"]), 4),
        "churn_mean":         round(float(q4["actual_churn"]), 4),
        "burnout_mean":       round(float(q4["burnout_mean"]), 4),
        "compliance_mean":    round(float(q4["compliance_mean"]), 4),
        "gaming_share":       round(float(q4["gaming_share"]), 4),
        "loyalty_miss_share": round(float(q4["loyalty_miss_share"]), 4),
    })

    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    import os
    os.makedirs(EXP_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    print("[pressure_experiment] running baseline condition...")
    reps_b, calls_b = run_condition("baseline",      SEED)

    print("[pressure_experiment] running high_pressure condition...")
    reps_h, calls_h = run_condition("high_pressure", SEED + 10)

    print("[pressure_experiment] running 12-month time series...")
    monthly = run_monthly_series(SEED + 20)

    print("[pressure_experiment] writing CSVs...")
    reps_combined  = pd.concat([reps_b,  reps_h],  ignore_index=True)
    calls_combined = pd.concat([calls_b, calls_h], ignore_index=True)
    summary        = build_summary(reps_b, calls_b, reps_h, calls_h, monthly)

    reps_combined.to_csv(EXP_DIR  / "experiment_rep_rosters.csv",    index=False)
    calls_combined.to_csv(EXP_DIR / "experiment_calls.csv",          index=False)
    summary.to_csv(EXP_DIR        / "experiment_summary.csv",        index=False)
    monthly.to_csv(EXP_DIR        / "experiment_monthly_series.csv", index=False)

    print("[pressure_experiment] generating figures...")
    figure_scenario_breakdown(calls_b, calls_h, FIG_DIR)
    figure_kpi_comparison(calls_b, calls_h, FIG_DIR)
    figure_rep_burnout(reps_b, reps_h, FIG_DIR)
    figure_goodhart_gap(calls_b, calls_h, FIG_DIR)
    figure_monthly_degradation(monthly, FIG_DIR)

    # Print summary to console
    print("\n── Experiment Summary ────────────────────────────────────────────")
    for _, row in summary.iterrows():
        print(f"\n  Condition: {row['condition']}")
        print(f"    Proxy FCR:          {row['proxy_fcr_mean']:.1%}")
        print(f"    True FCR:           {row['true_fcr_mean']:.1%}")
        print(f"    Goodhart gap:       {row['goodhart_gap_pp']:.1f}pp")
        print(f"    Repeat ≤30d:        {row['repeat_30d_mean']:.1%}")
        print(f"    Repeat 31-60d:      {row['repeat_31_60d_mean']:.1%}")
        print(f"    Churn mean:         {row['churn_mean']:.1%}")
        print(f"    Gaming share:       {row['gaming_share']:.1%}")
        print(f"    Loyalty miss share: {row['loyalty_miss_share']:.1%}")
    print("\n── Outputs ───────────────────────────────────────────────────────")
    print(f"  {EXP_DIR / 'experiment_summary.csv'}")
    print(f"  {EXP_DIR / 'experiment_monthly_series.csv'}")
    print(f"  {FIG_DIR} (5 figures)")
    print("[done]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
