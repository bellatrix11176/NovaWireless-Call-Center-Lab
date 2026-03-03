#!/usr/bin/env python3
"""
run_lab.py — NovaWireless Call Center Lab Master Orchestrator
=============================================================

Runs the entire lab pipeline end-to-end in deterministic order.
Works with the CURRENT (un-refactored) scripts — all of which write
to output/ flat. After each step, run_lab.py moves files into organized
subfolders and syncs what downstream scripts need into data/.

Final output structure:
    output/customer-gen/      — customers, lines, EIP, usage
    output/ledger/            — master account ledger + anomalies
    output/rep-gen/           — employee database + personas
    output/call-gen/
      metadata/               — calls_metadata_*.csv
      sanitized/              — calls_sanitized_*.csv
      transcripts/            — transcripts_*.jsonl
    output/experiments/       — pressure experiment results

Usage:
    python run_lab.py
    python run_lab.py --skip_calls
    python run_lab.py --skip_experiment
    python run_lab.py --n_customers 5000 --n_calls 7000 --n_months 6
"""

from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR

DATA_DIR   = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "output"

CUSTOMER_GEN_SRC = REPO_ROOT / "novawireless-customer-gen" / "src"
REP_GEN_SRC      = REPO_ROOT / "novawireless-rep-gen" / "src"
CALL_GEN_SRC     = REPO_ROOT / "novawireless-call-gen" / "src"

# Organized subfolders
OUT_CUSTOMER = OUTPUT_DIR / "customer-gen"
OUT_LEDGER   = OUTPUT_DIR / "ledger"
OUT_REP      = OUTPUT_DIR / "rep-gen"
OUT_CALLGEN  = OUTPUT_DIR / "call-gen"
OUT_META     = OUT_CALLGEN / "metadata"
OUT_SANIT    = OUT_CALLGEN / "sanitized"
OUT_TXSCRIPT = OUT_CALLGEN / "transcripts"
OUT_EXPER    = OUTPUT_DIR / "experiments"


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(label: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*65}")
    print(f"  [{ts}] {label}")
    print(f"{'='*65}")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def wipe_and_create(*folders: Path) -> None:
    for folder in folders:
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            continue
        try:
            shutil.rmtree(folder)
            folder.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"  [INFO] OneDrive lock — clearing files in {folder.name}/")
            cleared = 0
            for f in folder.rglob("*"):
                if f.is_file():
                    try:
                        f.unlink()
                        cleared += 1
                    except PermissionError:
                        print(f"  [WARN] Locked: {f.name}")
            for d in sorted(folder.rglob("*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except OSError:
                        pass
            folder.mkdir(parents=True, exist_ok=True)
            print(f"  [INFO] Cleared {cleared} files")


def run_step(label: str, script: Path, extra_args: list[str] | None = None) -> None:
    banner(label)
    if not script.exists():
        print(f"  [ERROR] Script not found: {script}")
        sys.exit(1)
    cmd = [sys.executable, str(script)] + (extra_args or [])
    print(f"  CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"\n  [FAILED] {label} (return code {result.returncode})")
        sys.exit(result.returncode)
    print(f"  [OK] {label}")


def move_file(src: Path, dst_dir: Path, name: str | None = None) -> bool:
    """Move a file into dst_dir. Returns True if moved."""
    dst = dst_dir / (name or src.name)
    if src.exists():
        ensure_dir(dst_dir)
        shutil.copy(str(src), str(dst))  # fresh timestamp
        src.unlink()
        print(f"  [MOVE] {src.name} → {dst_dir.name}/{dst.name}")
        return True
    return False


def copy_file(src: Path, dst: Path) -> bool:
    """Copy a file. Returns True if copied."""
    if src.exists():
        ensure_dir(dst.parent)
        shutil.copy(src, dst)  # fresh timestamp
        print(f"  [SYNC] {src.name} → {dst.parent.name}/{dst.name}")
        return True
    return False


def move_glob(pattern: str, src_dir: Path, dst_dir: Path) -> int:
    """Move all files matching pattern from src_dir to dst_dir."""
    ensure_dir(dst_dir)
    moved = 0
    for f in sorted(src_dir.glob(pattern)):
        dst = dst_dir / f.name
        shutil.copy(str(f), str(dst))  # fresh timestamp
        f.unlink()
        moved += 1
    if moved:
        print(f"  [MOVE] {moved} files matching '{pattern}' → {dst_dir.name}/")
    return moved


# ── Pipeline Steps ────────────────────────────────────────────────────────────

def step_1_customers(args) -> None:
    """Generate customers. Script writes to output/. We move to output/customer-gen/."""
    wipe_and_create(OUT_CUSTOMER)

    run_step(
        "Step 1: Generate customers + account graph",
        CUSTOMER_GEN_SRC / "generate_customers.py",
        [
            f"--n_customers={args.n_customers}",
            f"--seed={args.seed}",
        ],
    )

    # Move customer-gen outputs from output/ → output/customer-gen/
    banner("Step 1b: Organize customer outputs")
    for name in ["customers.csv", "customers_v1.csv", "lines.csv", "devices.csv",
                  "eip_agreements.csv", "line_device_usage.csv",
                  "customer_generation_receipt.json"]:
        move_file(OUTPUT_DIR / name, OUT_CUSTOMER)

    # Sync to data/
    copy_file(OUT_CUSTOMER / "customers.csv", DATA_DIR / "customers.csv")


def step_2_ledger(args) -> None:
    """Build master account ledger. Script reads from params_sources or output/,
    writes to output/ and params_sources. We move output to output/ledger/."""
    wipe_and_create(OUT_LEDGER)

    # The script reads from data/external/params_sources/ first, then output/.
    # Since we cleaned up params_sources, it will fall back to output/.
    # But customer files are now in output/customer-gen/, not output/.
    # Fix: temporarily copy customer files to output/ so the script can find them.
    banner("Step 2: Pre-stage customer files for ledger build")
    for name in ["customers_v1.csv", "customers.csv", "lines.csv",
                  "eip_agreements.csv", "line_device_usage.csv"]:
        src = OUT_CUSTOMER / name
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / name)
            print(f"  [STAGE] {name} → output/")

    run_step(
        "Step 2: Build master account ledger",
        CUSTOMER_GEN_SRC / "02_build_master_account_ledger.py",
    )

    # Move ledger outputs from output/ → output/ledger/
    for name in ["master_account_ledger.csv", "master_account_ledger_receipt.json"]:
        move_file(OUTPUT_DIR / name, OUT_LEDGER)

    # Clean up staged files
    for name in ["customers_v1.csv", "customers.csv", "lines.csv",
                  "eip_agreements.csv", "line_device_usage.csv"]:
        staged = OUTPUT_DIR / name
        if staged.exists():
            staged.unlink()


def step_3_anomalies(args) -> None:
    """Inject IMEI anomalies. Script reads from params_sources or output/.
    We stage the ledger back to output/ so it can find it."""
    banner("Step 3: Pre-stage ledger for anomaly injection")
    shutil.copy2(OUT_LEDGER / "master_account_ledger.csv",
                 OUTPUT_DIR / "master_account_ledger.csv")
    print(f"  [STAGE] master_account_ledger.csv → output/")

    run_step(
        "Step 3: Inject IMEI anomalies",
        CUSTOMER_GEN_SRC / "03_inject_imei_anomalies.py",
        ["--overwrite_base"],
    )

    # Move anomaly outputs from output/ → output/ledger/
    for name in ["master_account_ledger.csv", "master_account_ledger__anomalies.csv",
                  "imei_anomaly_examples.csv", "imei_anomaly_injection_receipt.json"]:
        move_file(OUTPUT_DIR / name, OUT_LEDGER)

    # Sync to data/
    copy_file(OUT_LEDGER / "master_account_ledger.csv", DATA_DIR / "master_account_ledger.csv")


def step_4_fix_contract(args) -> None:
    """Fix contract_proxy → billing_agreement_type.
    The script reads from output/master_account_ledger.csv.
    Stage it there, run, then move back."""
    banner("Step 4: Pre-stage ledger for contract fix")
    shutil.copy2(OUT_LEDGER / "master_account_ledger.csv",
                 OUTPUT_DIR / "master_account_ledger.csv")

    run_step(
        "Step 4: Fix contract_proxy → billing_agreement_type",
        CALL_GEN_SRC / "fix_ledger_contract_proxy.py",
    )

    # Move fixed ledger back to output/ledger/ and sync to data/
    move_file(OUTPUT_DIR / "master_account_ledger.csv", OUT_LEDGER)
    # Also grab the backup if it was created
    move_file(OUTPUT_DIR / "master_account_ledger__pre_contract_fix.csv", OUT_LEDGER)

    copy_file(OUT_LEDGER / "master_account_ledger.csv", DATA_DIR / "master_account_ledger.csv")


def step_5_employees(args) -> None:
    """Generate employees. Script writes to output/. We move to output/rep-gen/."""
    wipe_and_create(OUT_REP)

    run_step(
        "Step 5: Generate employees + persona enrichment",
        REP_GEN_SRC / "employee_gen__run_all.py",
        [
            f"--n={args.n_reps}",
            f"--seed={args.seed_reps}",
        ],
    )

    # Move rep outputs from output/ → output/rep-gen/
    banner("Step 5b: Organize rep outputs")
    move_file(OUTPUT_DIR / "novawireless_employee_database.csv", OUT_REP)
    move_file(OUTPUT_DIR / "rep_persona_profiles__v1.csv", OUT_REP)
    move_glob("employees__csr_one_queue__*", OUTPUT_DIR, OUT_REP)

    # Sync to data/
    copy_file(OUT_REP / "novawireless_employee_database.csv",
              DATA_DIR / "novawireless_employee_database.csv")


def step_6_calls(args) -> None:
    """Generate calls for all months. Month 1 uses call_gen__run_all,
    months 2-N use 01b_generate_calls_append in a loop.
    All scripts write to output/. We organize into subfolders at the end."""
    wipe_and_create(OUT_CALLGEN, OUT_META, OUT_SANIT, OUT_TXSCRIPT)

    n_months = args.n_months

    # Month 1
    run_step(
        f"Step 6: Generate calls — month 1 of {n_months} (2025-01)",
        CALL_GEN_SRC / "call_gen__run_all.py",
        [
            f"--n_calls={args.n_calls}",
            f"--seed={args.seed}",
            "--month=2025-01",
        ],
    )

    # Months 2-N
    for i in range(2, n_months + 1):
        month_tag = f"2025-{i:02d}"
        run_step(
            f"Step 6: Append calls — month {i} of {n_months} ({month_tag})",
            CALL_GEN_SRC / "01b_generate_calls_append.py",
            [
                f"--n_calls={args.n_calls}",
                f"--month={month_tag}",
            ],
        )

    # Organize: move from output/ → output/call-gen/subfolders/
    banner("Step 6: Organize call outputs into subfolders")
    move_glob("calls_metadata_*.csv", OUTPUT_DIR, OUT_META)
    move_glob("calls_sanitized_*.csv", OUTPUT_DIR, OUT_SANIT)
    move_glob("transcripts_*.jsonl", OUTPUT_DIR, OUT_TXSCRIPT)

    meta_count = len(list(OUT_META.glob("*.csv")))
    san_count  = len(list(OUT_SANIT.glob("*.csv")))
    tx_count   = len(list(OUT_TXSCRIPT.glob("*.jsonl")))
    print(f"  Organized: {meta_count} metadata, {san_count} sanitized, {tx_count} transcripts")


def step_7_experiment(args) -> None:
    """Run pressure experiment. Writes to output/ and output/experiment_figures/.
    We move everything to output/experiments/."""
    wipe_and_create(OUT_EXPER)
    # Also wipe the figures folder that the script creates at import time
    for fig_dir in [OUTPUT_DIR / "experiment_figures", OUT_EXPER / "experiment_figures"]:
        if fig_dir.exists():
            try:
                shutil.rmtree(fig_dir)
            except PermissionError:
                for f in fig_dir.rglob("*"):
                    if f.is_file():
                        try:
                            f.unlink()
                        except PermissionError:
                            pass
            print(f"  [WIPE] Cleared {fig_dir}")

    run_step(
        "Step 7: Pressure experiment",
        CALL_GEN_SRC / "pressure_experiment.py",
    )

    # Move experiment outputs from output/ → output/experiments/
    banner("Step 7b: Organize experiment outputs")
    for name in ["experiment_rep_rosters.csv", "experiment_calls.csv",
                  "experiment_summary.csv"]:
        move_file(OUTPUT_DIR / name, OUT_EXPER)

    # Move experiment_figures/ folder
    fig_src = OUTPUT_DIR / "experiment_figures"
    fig_dst = OUT_EXPER / "experiment_figures"
    if fig_src.exists() and fig_src.is_dir():
        ensure_dir(fig_dst)
        moved_figs = 0
        for f in fig_src.iterdir():
            if f.is_file():
                dst_file = fig_dst / f.name
                try:
                    # Delete destination first if it exists (force overwrite)
                    if dst_file.exists():
                        dst_file.unlink()
                    # Read bytes and write fresh (guarantees new timestamp)
                    data = f.read_bytes()
                    dst_file.write_bytes(data)
                    moved_figs += 1
                except Exception as e:
                    print(f"  [WARN] Could not copy {f.name}: {e}")
        # Try to remove the original folder
        try:
            shutil.rmtree(fig_src)
        except PermissionError:
            print(f"  [INFO] Could not remove original experiment_figures/ (OneDrive lock)")
        print(f"  [MOVE] {moved_figs} figures → experiments/experiment_figures/")
    else:
        print(f"  [WARN] No experiment_figures/ folder found in output/")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="NovaWireless Call Center Lab — Master Orchestrator"
    )
    ap.add_argument("--n_customers", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n_reps", type=int, default=250)
    ap.add_argument("--seed_reps", type=int, default=1337)
    ap.add_argument("--n_calls", type=int, default=5_000,
                    help="Calls per month (default: 5000)")
    ap.add_argument("--n_months", type=int, default=12,
                    help="Number of months to generate (default: 12)")
    ap.add_argument("--skip_calls", action="store_true",
                    help="Skip call generation")
    ap.add_argument("--skip_experiment", action="store_true",
                    help="Skip pressure experiment")
    args = ap.parse_args()

    banner("NovaWireless Call Center Lab — Full Pipeline")
    print(f"  Repo root:    {REPO_ROOT}")
    print(f"  Customers:    {args.n_customers:,}")
    print(f"  Reps:         {args.n_reps}")
    print(f"  Calls/month:  {args.n_calls:,}")
    print(f"  Months:       {args.n_months}")
    print(f"  Seed:         {args.seed}")

    ensure_dir(DATA_DIR)
    ensure_dir(DATA_DIR / "employee_generation_inputs")
    ensure_dir(OUTPUT_DIR)

    # Validate seed priors
    seed_dir = DATA_DIR / "employee_generation_inputs"
    for f in ["fcc_cgb_consumer_complaints__issue_priors.csv",
              "fcc_cgb_consumer_complaints__rep_specialization_priors.csv",
              "ibm_telco_segment_pressure.csv",
              "kaggle_call_center_weekday_pressure.csv",
              "kaggle_employee_persona_priors.csv"]:
        if not (seed_dir / f).exists():
            print(f"  [WARNING] Missing: data/employee_generation_inputs/{f}")

    step_1_customers(args)
    step_2_ledger(args)
    step_3_anomalies(args)
    step_4_fix_contract(args)
    step_5_employees(args)

    if not args.skip_calls:
        step_6_calls(args)
    else:
        print("\n  [SKIP] Call generation (--skip_calls)")

    if not args.skip_experiment:
        step_7_experiment(args)
    else:
        print("\n  [SKIP] Pressure experiment (--skip_experiment)")

    banner("ALL STEPS COMPLETE")
    print(f"  output/customer-gen/       — customers, lines, EIP, usage")
    print(f"  output/ledger/             — master account ledger")
    print(f"  output/rep-gen/            — employee database + personas")
    print(f"  output/call-gen/")
    print(f"    metadata/               — calls_metadata_*.csv")
    print(f"    sanitized/              — calls_sanitized_*.csv")
    print(f"    transcripts/            — transcripts_*.jsonl")
    print(f"  output/experiments/        — pressure experiment")
    print(f"")
    print(f"  data/ synced:")
    print(f"    customers.csv")
    print(f"    novawireless_employee_database.csv")
    print(f"    master_account_ledger.csv (anomalies + contract fix)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
