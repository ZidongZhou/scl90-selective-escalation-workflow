# Data access

The raw item-level CSV is not redistributed in this package.

Download the public dataset from Mendeley Data:

Wang S. Large sample dataset of Chinese college student (SCL-90+mindfulness). Mendeley Data, Version 1. DOI: 10.17632/btzgmr2rt2.1. License: CC BY 4.0.

The Mendeley Data record reports 14,372 first-year Chinese undergraduate students, with 3,541 from Shandong Province and 10,831 from Hunan Province. The submitted analysis excludes one invalid record after prespecified row-level quality checks, leaving 14,371 analytic records.

Recommended local file layout:

```text
data_raw/Data_collegestudent.csv
```

Run the default submitted-output reproduction path with:

```bash
python code/run_all.py --data data_raw/Data_collegestudent.csv --out outputs_final --clean --random-repeats 1000 --bootstrap-ci 500
```

This default path copies archived random-baseline and selection-stability simulation outputs from `code/static/`. Random raw-score baseline distributions can be fully recomputed by adding:

```bash
--recompute-random-baseline
```

The LASSO bootstrap selection-stability table is an archived simulation output included to reproduce the submitted experimental record; this package intentionally does not provide a separate selection-stability recomputation flag.

The code package does not reproduce SCL-90 item wording and does not write individual-level predictions unless `--write-individual-level-outputs` is explicitly supplied.
