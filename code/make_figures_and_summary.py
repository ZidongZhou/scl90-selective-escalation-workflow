#!/usr/bin/env python3
"""Create data-derived manuscript Figures 1-5 and a JSON summary from generated output tables."""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

# PLOS ONE allows Arial, Times, and Symbol in figure text. Use Arial as
# the preferred statistical-figure font; if Arial is unavailable in the local
# execution environment, fall back to metrically compatible sans-serif fonts
# rather than Matplotlib's default DejaVu Sans. All figure text is set to 8 pt.
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Arimo", "Liberation Sans", "Nimbus Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "svg.fonttype": "none",
    "svg.hashsalt": "scl90-v17-final",
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

FIGURE_SPECS = {
    "figure1_burden_performance_frontier": "Fig1",
    "figure2_random_itemset_distribution": "Fig2",
    "figure3_selective_escalation_workflow": "Fig3",
    "figure4_capacity_coverage_curve": "Fig4",
    "figure5_calibration_recalibration": "Fig5",
}


def _read_first_existing(*paths: Path) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError("None of the expected input tables exists: " + ", ".join(str(p) for p in paths))


def _save_figure(fig, figures_dir: Path, upload_dir: Path, stem: str) -> tuple[str, ...]:
    """Save preview, high-resolution raster, and editable vector outputs.

    PNGs are retained for lightweight inspection. TIFFs are rendered directly at
    600 dpi. SVG and PDF preserve editable text for publication-stage revision.
    """
    upload_stem = FIGURE_SPECS[stem]
    png_path = figures_dir / f"{stem}.png"
    tif_path = figures_dir / f"{stem}.tif"
    svg_path = figures_dir / f"{stem}.svg"
    pdf_path = figures_dir / f"{stem}.pdf"
    upload_png = upload_dir / f"{upload_stem}.png"
    upload_tif = upload_dir / f"{upload_stem}.tif"
    upload_svg = upload_dir / f"{upload_stem}.svg"
    upload_pdf = upload_dir / f"{upload_stem}.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(tif_path, dpi=600, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
    with Image.open(tif_path) as tif:
        dpi = tif.info.get("dpi", (600, 600))
        if tif.mode == "RGBA":
            rgb = Image.new("RGB", tif.size, "white")
            rgb.paste(tif, mask=tif.getchannel("A"))
        else:
            rgb = tif.convert("RGB")
        rgb.save(tif_path, compression="tiff_lzw", dpi=dpi)
    fig.savefig(svg_path, bbox_inches="tight", metadata={"Date": None})
    fig.savefig(pdf_path, bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    shutil.copyfile(png_path, upload_png)
    shutil.copyfile(tif_path, upload_tif)
    shutil.copyfile(svg_path, upload_svg)
    shutil.copyfile(pdf_path, upload_pdf)
    return (
        str(png_path.name), str(tif_path.name), str(svg_path.name), str(pdf_path.name),
        str(upload_png.relative_to(upload_dir.parent)), str(upload_tif.relative_to(upload_dir.parent)),
        str(upload_svg.relative_to(upload_dir.parent)), str(upload_pdf.relative_to(upload_dir.parent)),
    )


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.13,
        1.08,
        label,
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=8,
        fontweight="bold",
        clip_on=False,
        bbox=dict(facecolor="white", edgecolor="none", pad=0.8),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=Path("outputs"), type=Path)
    ap.add_argument("--upload-dir", default=None, type=Path, help="Optional directory for journal-upload Fig1-Fig5 files. Defaults to <out>/figure_files_for_upload.")
    args = ap.parse_args()
    T = args.out / "tables"
    F = args.out / "figures"
    F.mkdir(parents=True, exist_ok=True)
    upload_dir = args.upload_dir if args.upload_dir is not None else args.out / "figure_files_for_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample = pd.read_csv(T / "table1_sample_characteristics_quality.csv")
    perf = pd.read_csv(T / "table3_performance_by_item_count_and_selection.csv")
    random_dist = _read_first_existing(
        T / "random_rawsum_item_set_distributions.csv",
        T / "random_rawsum_item_set_distributions_1000_each_size.csv",
    )
    random_sum = _read_first_existing(
        T / "table5_random_rawsum_item_set_summary.csv",
        T / "table5_random_rawsum_item_set_summary_1000_each_size.csv",
    )
    triage = pd.read_csv(T / "table10_triage_capacity_coverage.csv")
    selective = _read_first_existing(T / "table11_selective_full_form_escalation.csv")
    threshold_tradeoff = pd.read_csv(T / "tableS_selective_escalation_threshold_tradeoff.csv")
    calib = pd.read_csv(T / "calibration_curve_bins_figure5.csv")
    lasso = perf[(perf.method == "LASSO/L1 ranking") & (perf.item_count.isin([5, 10, 15, 20, 30]))].sort_values("item_count")

    generated_figures = []
    journal_upload_figures = []

    # Fig 1: burden-performance frontier, two panels to avoid mixing Brier with higher-is-better metrics.
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.8), dpi=300)
    for c, lab in [("roc_auc", "ROC-AUC"), ("pr_auc", "PR-AUC"), ("top10_recall", "Top-10 recall")]:
        axes[0].plot(lasso.item_count, lasso[c], marker="o", label=lab)
    axes[0].set_xlabel("Number of SCL-90 items")
    axes[0].set_ylabel("Higher-is-better metric")
    axes[0].set_xticks([5, 10, 15, 20, 30])
    axes[0].set_ylim(.45, 1.02)
    axes[0].legend(frameon=False)
    axes[1].plot(lasso.item_count, lasso["brier"], marker="o")
    axes[1].set_xlabel("Number of SCL-90 items")
    axes[1].set_ylabel("Brier score (lower is better)")
    axes[1].set_xticks([5, 10, 15, 20, 30])
    for x, label in [(0.025, "a"), (0.520, "b")]:
        fig.text(x, 0.965, label, ha="left", va="top", fontsize=8, fontweight="bold")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.18, wspace=0.18)
    paths = _save_figure(fig, F, upload_dir, "figure1_burden_performance_frontier")
    generated_figures.extend(paths[:4])
    journal_upload_figures.extend(paths[4:])
    plt.close(fig)

    # Fig 2: random item-set distributions, two panels.
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.8), dpi=300)
    for panel, (ax, metric, label) in zip("ab", [(axes[0], "roc_auc", "ROC-AUC"), (axes[1], "pr_auc", "PR-AUC")]):
        vals = [random_dist.loc[random_dist.item_count == k, metric].values for k in [5, 10, 15, 20, 30]]
        ax.boxplot(vals, positions=[5, 10, 15, 20, 30], widths=1.8, showfliers=False)
        ax.plot(lasso.item_count, lasso[metric], marker="o", linestyle="--", label="LASSO/L1 selected logistic model")
        ax.set_xlabel("Random item-set size")
        ax.set_ylabel(label)
        ax.set_xticks([5, 10, 15, 20, 30])
        ax.legend(frameon=False)
        _panel_label(ax, panel)
    fig.tight_layout(pad=0.6)
    paths = _save_figure(fig, F, upload_dir, "figure2_random_itemset_distribution")
    generated_figures.extend(paths[:4])
    journal_upload_figures.extend(paths[4:])
    plt.close(fig)

    # Fig 3: data-only selective escalation summary.
    holdout = selective[selective["sample"].str.contains("Shandong", case=False, na=False)].iloc[0]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.6), dpi=300)
    ax_route, ax_burden, ax_trade = axes
    zone_colors = ["#b8dce9", "#e9ca70", "#d98b47"]

    zone_names = ["Provisional", "Full form", "Priority review"]
    zone_values = [holdout["low_zone_n"], holdout["middle_escalation_n"], holdout["high_zone_n"]]
    total = sum(zone_values)
    left = 0
    for idx, (name, value, color) in enumerate(zip(zone_names, zone_values, zone_colors)):
        pct = 100 * value / total
        ax_route.barh([0], [pct], left=left, height=0.23, color=color, edgecolor="white", linewidth=0.8)
        centre = left + pct / 2
        if idx == 0:
            ax_route.text(centre, 0, f"{name}\n{int(value):,} ({pct:.1f}%)",
                          ha="center", va="center", fontsize=6.1, color="#20252b")
        else:
            label_y = 0.29 if idx == 1 else -0.29
            va = "bottom" if idx == 1 else "top"
            ax_route.annotate(
                f"{name}: {int(value):,} ({pct:.1f}%)", xy=(centre, 0), xytext=(centre, label_y),
                ha="center", va=va, fontsize=6.0, color="#20252b",
                arrowprops=dict(arrowstyle="-", color="#7a838d", lw=0.62),
            )
        left += pct
    ax_route.set_xlim(0, 100)
    ax_route.set_ylim(-0.58, 0.58)
    ax_route.set_yticks([])
    ax_route.set_xlabel("Share of mapped hold-out group (%)")
    ax_route.set_title("Routing distribution", loc="left", pad=8)
    ax_route.spines["left"].set_visible(False)

    selective_burden = float(holdout["average_item_burden"])
    ax_burden.hlines(0, selective_burden, 90, color="#9aa3ad", lw=1.20, zorder=1)
    ax_burden.scatter([selective_burden], [0], s=54, color="#5d8fb4", zorder=3)
    ax_burden.scatter([90], [0], s=54, facecolor="white", edgecolor="#59636f", linewidth=1.0, zorder=3)
    ax_burden.text(selective_burden, 0.16, f"Selective workflow\n{selective_burden:.1f} items",
                   ha="center", va="bottom", fontsize=6.4)
    ax_burden.text(90, 0.16, "Universal full form\n90 items", ha="center", va="bottom", fontsize=6.4)
    ax_burden.text((selective_burden + 90) / 2, -0.18,
                   f'{holdout["burden_reduction_vs_90"]*100:.1f}% lower burden',
                   ha="center", va="top", fontsize=6.9, color="#3f4c5f", fontweight="bold")
    ax_burden.set_xlim(0, 100)
    ax_burden.set_ylim(-0.45, 0.55)
    ax_burden.set_yticks([])
    ax_burden.set_xlabel("Average items per student")
    ax_burden.set_title("Questionnaire burden", loc="left", pad=8)
    ax_burden.spines["left"].set_visible(False)
    low_trade = threshold_tradeoff[threshold_tradeoff["analysis"].eq("low-threshold trade-off with high threshold fixed")].copy()
    low_trade = low_trade.sort_values("low_cut_rawsum_le")
    ax_trade.plot(low_trade["low_cut_rawsum_le"], low_trade["holdout_low_zone_npv"] * 100,
                  marker="o", color="#426d8f", label="Low-zone NPV")
    ax_trade.set_xlabel("Low-zone threshold")
    ax_trade.set_ylabel("Hold-out low-zone NPV (%)", color="#426d8f")
    ax_trade.tick_params(axis="y", labelcolor="#426d8f")
    ax_trade.set_xticks(low_trade["low_cut_rawsum_le"].astype(int).tolist())
    ax_trade.set_xticklabels([f"<={int(x)}" for x in low_trade["low_cut_rawsum_le"]])
    ax_trade.set_ylim(97.5, 100.0)
    ax_trade2 = ax_trade.twinx()
    ax_trade2.plot(low_trade["low_cut_rawsum_le"], low_trade["holdout_average_item_burden"],
                   marker="s", color="#9a6a20", label="Mean items")
    ax_trade2.set_ylabel("Mean items", color="#9a6a20")
    ax_trade2.tick_params(axis="y", labelcolor="#9a6a20")
    ax_trade2.spines["top"].set_visible(False)
    ax_trade.set_title("NPV-burden trade-off", loc="left", pad=8)
    for x, label in [(0.025, "a"), (0.355, "b"), (0.690, "c")]:
        fig.text(x, 0.965, label, ha="left", va="top", fontsize=8, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.93, top=0.84, bottom=0.20, wspace=0.58)
    paths = _save_figure(fig, F, upload_dir, "figure3_selective_escalation_workflow")
    generated_figures.extend(paths[:4])
    journal_upload_figures.extend(paths[4:])
    plt.close(fig)

    # Fig 4: capacity coverage.
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    ax.plot(triage.capacity_percent, triage.coverage_recall_of_full_score_screen_positive, marker="o", label="Observed coverage of screen-positive students")
    if "theoretical_max_recall_given_capacity" in triage.columns:
        ax.plot(triage.capacity_percent, triage.theoretical_max_recall_given_capacity, linestyle="--", label="Theoretical maximum recall at capacity")
    ax.plot(triage.capacity_percent, triage.positive_rate_in_reviewed_group, marker="s", label="Screen-positive rate among reviewed students")
    ax.set_xlabel("Follow-up capacity (% ranked highest)")
    ax.set_ylabel("Proportion")
    ax.set_ylim(0, 1.05)
    ax.set_xticks([5, 10, 15, 20, 25, 30])
    ax.legend(frameon=False)
    fig.tight_layout(pad=0.6)
    paths = _save_figure(fig, F, upload_dir, "figure4_capacity_coverage_curve")
    generated_figures.extend(paths[:4])
    journal_upload_figures.extend(paths[4:])
    plt.close(fig)

    # Fig 5: calibration before and after recalibration.
    fig, ax = plt.subplots(figsize=(6.0, 5.2), dpi=300)
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Ideal calibration")
    for model, g in calib.groupby("model"):
        g = g.sort_values("mean_predicted_probability")
        ax.plot(g["mean_predicted_probability"], g["observed_screen_positive_rate"], marker="o", label=model)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed screen-positive rate")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False)
    fig.tight_layout(pad=0.6)
    paths = _save_figure(fig, F, upload_dir, "figure5_calibration_recalibration")
    generated_figures.extend(paths[:4])
    journal_upload_figures.extend(paths[4:])
    plt.close(fig)

    summary = {
        "sample": sample.to_dict("records"),
        "lasso_item_count_metrics": lasso.to_dict("records"),
        "random_rawsum_summary": random_sum.to_dict("records"),
        "triage": triage.to_dict("records"),
        "selective_escalation": selective.to_dict("records"),
        "generated_figures": generated_figures,
        "journal_upload_figures": journal_upload_figures,
    }
    with open(args.out / "analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Created data-derived Figures 1-5 as PNG, 600-dpi TIFF, SVG, and PDF in", F)
    print("Wrote journal-upload figure files in", upload_dir)


if __name__ == "__main__":
    main()
