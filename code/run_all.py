#!/usr/bin/env python3
"""Run the reproducible analysis pipeline.

Default route:
python code/run_all.py --data /path/to/Data_collegestudent.csv --out outputs_final \
  --random-repeats 1000 --bootstrap-ci 500

The default route reruns the main models, calibration, top-k tables, selective
full-form escalation, order-assumed domain-balanced item sets, non-overlapping/severity labels,
fully nested item-selection CV, response-quality audits, and Figures 1-5. It copies
archived random-baseline and selection-stability simulations for a stable reviewer
runtime.

Full random-baseline recomputation:
python code/run_all.py --data /path/to/Data_collegestudent.csv --out outputs_full \
  --random-repeats 1000 --bootstrap-ci 500 --recompute-random-baseline

Tree-based sensitivity is optional and can be enabled with --include-tree or run
separately with code/run_tree_based_sensitivity.py.
"""
from __future__ import annotations
import argparse, csv, json, os, shutil, subprocess, sys, zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def thread_limited_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env.setdefault(key, "1")
    return env


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.check_call(cmd, env=thread_limited_env())




def _col_letter(idx: int) -> str:
    letters = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _cell_xml(row_idx: int, col_idx: int, value: str, header: bool = False) -> str:
    ref = f"{_col_letter(col_idx)}{row_idx}"
    style = ' s="1"' if header else ""
    if value is None:
        value = ""
    value = str(value)
    if value == "":
        return f'<c r="{ref}"{style}/>'
    try:
        float(value)
        is_number = True
    except ValueError:
        is_number = False
    if is_number and not value.startswith("0"):
        return f'<c r="{ref}"{style}><v>{escape(value)}</v></c>'
    return f'<c r="{ref}"{style} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _sheet_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for r_idx, row in enumerate(rows, start=1):
        cells = ''.join(_cell_xml(r_idx, c_idx, val, header=(r_idx == 1)) for c_idx, val in enumerate(row, start=1))
        row_xml.append(f'<row r="{r_idx}">{cells}</row>')
    n_cols = max((len(row) for row in rows), default=1)
    n_rows = max(len(rows), 1)
    widths = []
    for idx in range(n_cols):
        width = min(40, max(10, max((len(str(row[idx])) if idx < len(row) else 0 for row in rows), default=10) + 2))
        widths.append(f'<col min="{idx + 1}" max="{idx + 1}" width="{width}" customWidth="1"/>')
    table_ref = f"A1:{_col_letter(n_cols)}{n_rows}"
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/><cols>' + ''.join(widths) + '</cols>'
            '<sheetData>' + ''.join(row_xml) + f'</sheetData><autoFilter ref="{table_ref}"/></worksheet>')


def _read_csv_rows(path: Path) -> list[list[str]]:
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.reader(f))


def _writestr_deterministic(zf: zipfile.ZipFile, name: str, content: str) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 6, 21, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    zf.writestr(info, content)


def _write_s1_table_workbook(summary_csv: Path, folds_csv: Path, out_xlsx: Path) -> None:
    """Create a single S1 Table workbook with summary and fold-level sheets."""
    sheets = [("summary", _read_csv_rows(summary_csv)), ("folds", _read_csv_rows(folds_csv))]
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="summary" sheetId="1" r:id="rId1"/><sheet name="folds" sheetId="2" r:id="rId2"/></sheets></workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><top style="thin"/><bottom style="thin"/><left/><right/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>"""
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_xlsx, 'w', zipfile.ZIP_DEFLATED) as zf:
        _writestr_deterministic(zf, '[Content_Types].xml', content_types)
        _writestr_deterministic(zf, '_rels/.rels', root_rels)
        _writestr_deterministic(zf, 'xl/workbook.xml', workbook_xml)
        _writestr_deterministic(zf, 'xl/_rels/workbook.xml.rels', workbook_rels)
        _writestr_deterministic(zf, 'xl/styles.xml', styles_xml)
        for idx, (_, rows) in enumerate(sheets, start=1):
            _writestr_deterministic(zf, f'xl/worksheets/sheet{idx}.xml', _sheet_xml(rows))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path, help="Path to Data_collegestudent.csv from the public Mendeley dataset")
    ap.add_argument("--out", default=Path("outputs_final"), type=Path)
    ap.add_argument("--random-repeats", default=1000, type=int)
    ap.add_argument("--bootstrap-ci", default=500, type=int)
    ap.add_argument("--recompute-random-baseline", action="store_true", help="Recompute random raw-score item-set baselines instead of copying archived static simulation outputs")
    ap.add_argument("--include-tree", action="store_true", help="Also run the supplementary LightGBM/XGBoost tree-based sensitivity analysis. Off by default to avoid OpenMP/threading stalls in constrained reviewer environments.")
    ap.add_argument("--quick", action="store_true", help="Reviewer smoke-run mode: skip bootstrap resampling and keep archived simulations unless explicitly recomputing.")
    ap.add_argument("--skip-nested-cv", action="store_true", help="Skip nested CV stages for a faster reviewer smoke-run.")
    ap.add_argument("--si-out", type=Path, default=None, help="Directory for SI-ready table copies. Defaults to <out>/supporting_info.")
    ap.add_argument("--clean", action="store_true", help="Delete the output directory before running")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    package_root = here.parent
    if args.quick:
        args.bootstrap_ci = 0
        args.skip_nested_cv = True
        if args.recompute_random_baseline:
            args.random_repeats = min(args.random_repeats, 5)
    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    main_cmd = [sys.executable, str(here/"run_plos_one_analysis.py"), "--data", str(args.data), "--out", str(args.out), "--random-repeats", str(args.random_repeats), "--bootstrap-ci", str(args.bootstrap_ci)]
    if args.recompute_random_baseline:
        main_cmd.append("--recompute-random-baseline")
    if args.quick:
        main_cmd.append("--quick")
    if args.skip_nested_cv:
        main_cmd.append("--skip-nested-cv")
    run(main_cmd)
    if args.include_tree:
        run([sys.executable, str(here/"run_tree_based_sensitivity.py"), "--data", str(args.data), "--out", str(args.out)])
    else:
        print("\nSkipping supplementary tree-based sensitivity by default. Use --include-tree to run it.", flush=True)
    run([sys.executable, str(here/"make_figures_and_summary.py"), "--out", str(args.out), "--upload-dir", str(args.out / "figure_files_for_upload")])

    # Create SI-ready copies for the main supplementary tables. This keeps the
    # rerun package aligned with the manuscript Supporting information captions.
    si_dir = args.si_out if args.si_out is not None else args.out / "supporting_info"
    si_dir.mkdir(parents=True, exist_ok=True)
    summary_csv = args.out / "tables" / "pooled_region_stratified_cv_summary.csv"
    folds_csv = args.out / "tables" / "pooled_region_stratified_cv_folds.csv"
    if summary_csv.exists() and folds_csv.exists():
        _write_s1_table_workbook(summary_csv, folds_csv, si_dir / "S1_Table.xlsx")

    table_map = {
        "lasso_bootstrap_selection_stability_1000_stratified_subsamples.csv": "S2_Table_lasso_bootstrap_selection_stability.csv",
        "tableS_tree_based_selection_sensitivity.csv": "S3_Table_tree_based_selection_sensitivity.csv",
        "random_rawsum_item_set_distributions.csv": "S4_Table_random_rawsum_item_set_distributions.csv",
        "tableS_current_environment_lasso_sensitivity.csv": "S5_Table_current_environment_lasso_sensitivity.csv",
        "tableS_data_quality_exclusion_sensitivity.csv": "S6_Table_data_quality_exclusion_sensitivity.csv",
        "tableS_topk_triage_bootstrap_ci.csv": "S7_Table_topk_triage_bootstrap_ci.csv",
        "table11_selective_full_form_escalation.csv": "S8_Table_selective_full_form_escalation.csv",
        "tableS_selective_escalation_bootstrap_ci.csv": "S9_Table_selective_escalation_bootstrap_ci.csv",
        "tableS_order_assumed_domain_balanced_item_selection.csv": "S10_Table_order_assumed_domain_balanced_item_selection.csv",
        "table12_nonoverlap_and_severity_validation.csv": "S11_Table_nonoverlap_and_severity_validation.csv",
        "table13_fully_nested_item_selection_cv_summary.csv": "S12_Table_fully_nested_item_selection_cv_summary.csv",
        "table13_fully_nested_item_selection_stability.csv": "S13_Table_fully_nested_item_selection_stability.csv",
        "table14_response_pattern_audit.csv": "S14_Table_response_pattern_audit.csv",
        "tableS_response_quality_restricted_selective_escalation.csv": "S15_Table_response_quality_restricted_selective_escalation.csv",
        "tableS_nested_selective_escalation_cv_summary.csv": "S16_Table_nested_selective_escalation_cv_summary.csv",
        "tableS_selective_escalation_error_profile.csv": "S17_Table_selective_escalation_error_profile.csv",
        "tableS_subgroup_workflow_diagnostics.csv": "S18_Table_subgroup_workflow_diagnostics.csv",
        "tableS_tripod_ai_informed_reporting_checklist.csv": "S19_Table_tripod_ai_informed_reporting_checklist.csv",
        "tableS_intended_use_deployment_card.csv": "S20_Table_intended_use_deployment_card.csv",
        "tableS_selective_escalation_threshold_tradeoff.csv": "S21_Table_selective_escalation_threshold_tradeoff.csv",
        "tableS_retrospective_response_quality_audit.csv": "S22_Table_retrospective_response_quality_audit.csv",
        "tableS_first_stage_observable_quality_flags.csv": "S23_Table_first_stage_observable_quality_flags.csv",
    }
    for src_name, dst_name in table_map.items():
        src = args.out / "tables" / src_name
        if src.exists():
            shutil.copy2(src, si_dir / dst_name)
            continue
        archived = package_root / "supporting_info" / dst_name
        if archived.exists():
            shutil.copy2(archived, si_dir / dst_name)

    config_path = args.out / "analysis_run_config.json"
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            config = json.load(f)
        config.update({
            "include_tree_requested": bool(args.include_tree),
            "tree_based_sensitivity_source": (
                "recomputed_current_run" if args.include_tree
                else "archived_packaged_output" if (si_dir / "S3_Table_tree_based_selection_sensitivity.csv").exists()
                else "not_available"
            ),
            "figure_export_formats": ["PNG preview", "600-dpi LZW TIFF", "editable-text SVG", "editable-text PDF"],
            "full_wrapper_completed": True,
        })
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
