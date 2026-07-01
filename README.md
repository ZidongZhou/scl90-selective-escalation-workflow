# SCL-90 selective escalation workflow analysis package

This package accompanies the manuscript:

Selective escalation for approximating an SCL-90 psychological symptom total-score screening rule in Chinese first-year students: a reproducible workflow study

## Contents

- `code/`: analysis scripts for the manuscript tables, supporting tables, figures, calibration checks, workflow simulations, and sensitivity analyses.
- `outputs/`: aggregate tables and figures from the submitted run.
- `figure_files_for_upload/`: Fig 1-Fig 5 in PNG, TIFF, SVG, and PDF formats.
- `supporting_info/`: SI-ready S1-S23 Tables. S1 is an XLSX workbook; S2-S23 are CSV files.
- `data_access/DATA_ACCESS.md`: source and placement instructions for the public raw CSV.
- `requirements-lock.txt`, `environment.yml`, `MANIFEST.md`, `LICENSE`, and `CITATION.cff`: environment, file map, license, and citation metadata.

The raw item-level CSV and SCL-90 item wording are not redistributed in this package.

## Data

Download the raw data separately from Mendeley Data and place the CSV as `data_raw/Data_collegestudent.csv` before running the full pipeline:

Wang S. Large sample dataset of Chinese college student (SCL-90+mindfulness). Mendeley Data, Version 1. DOI: 10.17632/btzgmr2rt2.1. License: CC BY 4.0.

The submitted S1 Code archive does not redistribute the raw item-level CSV and does not reproduce SCL-90 item wording.

Place the file at `data_raw/Data_collegestudent.csv`, or pass its path with `--data`.

## Reproduce the submitted outputs

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
python code/run_all.py --data data_raw/Data_collegestudent.csv --out outputs_final --clean --random-repeats 1000 --bootstrap-ci 500
```

This route reruns the main models, workflow tables, calibration summaries, nested resampling checks, bootstrap confidence intervals, and figure generation. It uses the archived random raw-score baseline and LASSO bootstrap selection-stability files supplied in `code/static/`, so reviewers can reproduce the submitted package without long simulation reruns or solver-version drift.

To recompute the random raw-score baselines, add `--recompute-random-baseline`. To rerun the optional LightGBM/XGBoost sensitivity analysis, add `--include-tree`.

XGBoost and LightGBM are included in the locked environment only to support optional tree-based sensitivity analysis; the main workflow does not require them.

## Fast check

```bash
python -m pytest -q
```

Without raw data, this checks package structure and static-output consistency. With raw data, set `SCL90_TEST_DATA=/path/to/Data_collegestudent.csv` before running pytest to trigger a quick pipeline check.

A quick manual run is also available:

```bash
python code/run_all.py --data data_raw/Data_collegestudent.csv --out outputs_quick --clean --quick
```

The quick route checks wiring and file creation. It is not a replacement for the submitted full run.

## Optional full reruns

Random-baseline recomputation:

```bash
python code/run_all.py   --data data_raw/Data_collegestudent.csv   --out outputs_full_recompute   --clean   --random-repeats 1000   --bootstrap-ci 500   --recompute-random-baseline
```

Tree-based sensitivity:

```bash
python code/run_all.py   --data data_raw/Data_collegestudent.csv   --out outputs_final   --clean   --random-repeats 1000   --bootstrap-ci 500   --include-tree
```

The wrapper sets common thread-control environment variables for child processes unless they are already set. This reduces OpenMP-related failures in constrained reviewer environments.

## Notes for interpretation

- The submitted 15-item LASSO/L1 order is stored in `code/static/archived_lasso_l1_item_ranking_hunan_all90.csv` and treated as a fixed operational example, not as a new short-form instrument.
- Current-environment LASSO/L1 sensitivity is reported in `outputs/tables/tableS_current_environment_lasso_sensitivity.csv`.
- Random raw-score baselines are redundancy benchmarks. They are scored by raw sums and do not refit logistic models.
- Bootstrap confidence intervals are conditional on the fixed validation sample and fixed 15-item operational example.
- The order-assumed domain-balanced comparator assumes the conventional SCL-90 item order because the public dataset did not redistribute item wording.
- The submitted bootstrap selection-stability table is provided as an archived simulation record; exact regeneration may vary across solver/library versions. It was not used as the final rule-selection criterion. Current-environment LASSO sensitivity is provided separately to document robustness.
- XGBoost contribution ranking uses `pred_contribs=True`; no separate SHAP package is required.

## Output map

Manuscript-facing aggregate tables are in `outputs/tables/`, with supporting tables copied to `supporting_info/` as S1-S23 Tables. Main figure files are in `outputs/figures/` and `figure_files_for_upload/`.

Key workflow and sensitivity files include:

- `table3_performance_by_item_count_and_selection.csv`
- `table5_random_rawsum_item_set_summary.csv`
- `table10_triage_capacity_coverage.csv`
- `table11_selective_full_form_escalation.csv`
- `table12_nonoverlap_and_severity_validation.csv`
- `table13_fully_nested_item_selection_cv_summary.csv`
- `table14_response_pattern_audit.csv`
- `tableS_response_quality_restricted_selective_escalation.csv`
- `tableS_nested_selective_escalation_cv_summary.csv`
- `tableS_order_assumed_domain_balanced_item_selection.csv`
- `tableS_selective_escalation_threshold_tradeoff.csv`
- `tableS_retrospective_response_quality_audit.csv`
- `tableS_first_stage_observable_quality_flags.csv`
- `tableS_intended_use_deployment_card.csv`

See `MANIFEST.md` for the full file-to-manuscript mapping.

## Repository
Public repository: https://github.com/ZidongZhou/scl90-selective-escalation-workflow
Archived release: https://doi.org/10.5281/zenodo.21118063
