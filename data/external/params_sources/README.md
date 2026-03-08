# data/external/params_sources/

This folder contains the master account ledger files used as input parameters for the call generation pipeline.

## Files

| File | Size | Description |
|------|------|-------------|
| `master_account_ledger.csv` | ~69MB | Synthetic account ledger for 100,000 customers including account history, device records, and contract data |
| `master_account_ledger__anomalies.csv` | ~70MB | Same ledger with IMEI anomalies injected for fraud scenario simulation |

## These files are not in the repo

They are too large for GitHub. Download them from the [v1.0 Release](https://github.com/bellatrix11176/NovaWireless-Call-Center-Lab/releases/tag/v1.0) and place them in this folder.

Or regenerate them by running:

```bash
python run_all.py
```
