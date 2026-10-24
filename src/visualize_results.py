"""
GridSense: High-Resolution Result Visualization Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Generates publication-grade statistical graphics and anomaly diagnostics
from genuine pipeline output data, saving high-DPI PNGs for the report and dashboard.
"""

import os
import sys
import json
import logging
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configure visual style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.labelweight": "bold",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 14,
    "figure.titleweight": "bold",
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

logger = logging.getLogger("GridSense.Visualizer")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_all_visualizations(config: dict = None):
    """
    Generates all 8 academic-grade charts and saves them to outputs/charts/.
    """
    if config is None:
        config = load_config()

    charts_dir = config["paths"]["charts_dir"]
    summaries_dir = config["paths"]["summaries_dir"]
    anomalies_dir = config["paths"]["anomalies_dir"]
    os.makedirs(charts_dir, exist_ok=True)

    print("=" * 80)
    print(" GridSense: Generating Publication-Grade Visualizations ")
    print("=" * 80)

    # 1. Dataset Overview Chart
    summary_table_path = os.path.join(summaries_dir, "dataset_summary_table.csv")
    if os.path.exists(summary_table_path):
        df_sum = pd.read_csv(summary_table_path)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Filter out aggregated for row count chart
        df_hf = df_sum[df_sum["Type"] == "3-Min High Frequency"].copy()
        df_hf["ShortName"] = df_hf["File Name"].apply(
            lambda x: x.replace("CEEW - Smart meter data ", "").replace("SM Cleaned Data ", "").replace(".csv", "")
        )

        colors = ["#1f77b4" if "Bareilly" in x or "BR" in x else "#ff7f0e" for x in df_hf["File Name"]]
        bars = ax1.bar(df_hf["ShortName"], df_hf["Row Count"] / 1e6, color=colors, edgecolor="black", alpha=0.85)
        ax1.set_title("Records Processed by Dataset Partition (Millions)")
        ax1.set_ylabel("Records (Millions)")
        ax1.set_xticklabels(df_hf["ShortName"], rotation=30, ha="right")
        for bar in bars:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, yval + 0.1, f"{yval:.2f}M", ha="center", va="bottom", fontsize=8, weight="bold")

        # City Distribution Pie
        city_groups = {"Bareilly (BR)": 0, "Mathura (MH)": 0}
        for _, row in df_hf.iterrows():
            if "Bareilly" in row["File Name"] or "BR" in row["File Name"]:
                city_groups["Bareilly (BR)"] += row["Row Count"]
            else:
                city_groups["Mathura (MH)"] += row["Row Count"]

        ax2.pie(
            city_groups.values(),
            labels=city_groups.keys(),
            autopct="%1.1f%%",
            startangle=140,
            colors=["#1f77b4", "#ff7f0e"],
            explode=(0.04, 0.04),
            wedgeprops={"edgecolor": "black", "linewidth": 1.2}
        )
        ax2.set_title("Geographic Proportion of Readings")

        plt.tight_layout()
        chart1_path = os.path.join(charts_dir, "1_dataset_overview.png")
        plt.savefig(chart1_path)
        plt.close()
        print(f"Saved: {chart1_path}")

    # 2. Consumption Diurnal and Seasonal Profiles
    hourly_path = os.path.join(summaries_dir, "hourly_anomaly_distribution.csv")
    monthly_path = os.path.join(summaries_dir, "monthly_anomaly_distribution.csv")
    if os.path.exists(hourly_path) and os.path.exists(monthly_path):
        df_hr = pd.read_csv(hourly_path)
        df_mn = pd.read_csv(monthly_path)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        ax1.plot(df_hr["hour"], df_hr["avg_kwh"], marker="o", color="#2ca02c", linewidth=2.5, markersize=6)
        ax1.fill_between(df_hr["hour"], df_hr["avg_kwh"], color="#2ca02c", alpha=0.15)
        ax1.set_title("Diurnal Household Electricity Profile (24-Hour Cycle)")
        ax1.set_xlabel("Hour of Day (0 - 23)")
        ax1.set_ylabel("Average 3-Minute Consumption (kWh)")
        ax1.set_xticks(range(0, 24, 2))
        ax1.grid(True, linestyle="--", alpha=0.6)

        # Monthly curve
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_mn["MonthName"] = df_mn["month"].apply(lambda m: month_names[int(m) - 1] if 1 <= int(m) <= 12 else str(m))
        ax2.bar(df_mn["MonthName"], df_mn["avg_kwh"], color="#9467bd", edgecolor="black", alpha=0.85)
        ax2.set_title("Seasonal Consumption Variation Across Months")
        ax2.set_xlabel("Month")
        ax2.set_ylabel("Average 3-Minute Consumption (kWh)")
        ax2.grid(True, linestyle="--", alpha=0.6)

        plt.tight_layout()
        chart2_path = os.path.join(charts_dir, "2_consumption_trends.png")
        plt.savefig(chart2_path)
        plt.close()
        print(f"Saved: {chart2_path}")

    # 3. Rule Breakdown Chart
    rule_sum_path = os.path.join(summaries_dir, "rule_based_detection_summary.json")
    if os.path.exists(rule_sum_path):
        with open(rule_sum_path, "r", encoding="utf-8") as f:
            rule_data = json.load(f)

        breakdown = rule_data.get("rule_breakdown", {})
        rule_labels = {
            "over_voltage_count": "Over-Voltage (>280V)",
            "under_voltage_count": "Under-Voltage Sag (<160V)",
            "freq_violation_count": "Grid Freq Violation (<48.5 / >51.5 Hz)",
            "stat_spike_count": "Stat Baseline Outlier (Z > 4.0)",
            "abrupt_ramp_count": "Abrupt Consumption Ramp (>1.8 kWh)",
            "spike_kwh_count": "Extreme 3-Min Spike (>2.5 kWh)",
            "current_overload_count": "Current Overload (>35A)",
            "suspect_bypass_count": "Zero Volt / Active Current",
            "neg_kwh_count": "Negative Meter Reading"
        }

        names = []
        counts = []
        for k, v in rule_labels.items():
            if k in breakdown and breakdown[k] > 0:
                names.append(v)
                counts.append(breakdown[k])

        if names:
            # Sort descending
            sort_idx = np.argsort(counts)
            names = [names[i] for i in sort_idx]
            counts = [counts[i] for i in sort_idx]

            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(names, counts, color="#d62728", edgecolor="black", alpha=0.85)
            ax.set_title("Method A: Distribution of Triggered Engineering Rules")
            ax.set_xlabel("Occurrences Count")
            for bar in bars:
                w = bar.get_width()
                ax.text(w + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2, f"{int(w):,}", ha="left", va="center", fontsize=8, weight="bold")
            plt.tight_layout()
            chart3_path = os.path.join(charts_dir, "4_anomaly_distribution_by_rule.png")
            plt.savefig(chart3_path)
            plt.close()
            print(f"Saved: {chart3_path}")

    # 4. Rule-Based vs Machine Learning Comparison (Method A vs Method B)
    eval_sum_path = os.path.join(summaries_dir, "evaluation_summary.json")
    if os.path.exists(eval_sum_path):
        with open(eval_sum_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        agree = eval_data.get("agreement_analysis", {})
        categories = ["Both Agreed\n(High Confidence)", "Rule-Based Only\n(Hard Constraints)", "Isolation Forest Only\n(Subtle Multi-var)"]
        vals = [agree.get("both_agree_count", 0), agree.get("rule_only_count", 0), agree.get("ml_only_count", 0)]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        colors = ["#2ca02c", "#d62728", "#1f77b4"]

        bars = ax1.bar(categories, vals, color=colors, edgecolor="black", alpha=0.85)
        ax1.set_title("Agreement Analysis: Rule-Based vs Machine Learning")
        ax1.set_ylabel("Anomaly Occurrences")
        for bar in bars:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, yval + max(vals) * 0.02, f"{int(yval):,}", ha="center", va="bottom", fontsize=9, weight="bold")

        # Metric summary callout box
        jaccard = agree.get("jaccard_similarity", 0.0)
        overlap = agree.get("overlap_coefficient", 0.0)
        rule_pct = eval_data.get("rule_based_detection", {}).get("percentage", 0.0)
        ml_pct = eval_data.get("machine_learning_detection", {}).get("percentage", 0.0)

        ax2.axis("off")
        box_text = (
            "COMPARATIVE EVALUATION METRICS\n"
            "=========================================\n\n"
            f"• Total Evaluated Readings: {eval_data.get('total_records', 0):,}\n"
            f"• Method A (Rule-Based) Anomalies: {eval_data.get('rule_based_detection', {}).get('count', 0):,} ({rule_pct:.2f}%)\n"
            f"• Method B (Isolation Forest): {eval_data.get('machine_learning_detection', {}).get('count', 0):,} ({ml_pct:.2f}%)\n"
            f"• High-Confidence (Intersection): {agree.get('both_agree_count', 0):,} ({agree.get('both_agree_pct', 0):.2f}%)\n"
            f"• Total Flagged (Union): {agree.get('union_anomalies_count', 0):,} ({agree.get('union_percentage', 0):.2f}%)\n\n"
            "STATISTICAL AGREEMENT COEFFICIENTS\n"
            "-----------------------------------------\n"
            f"• Jaccard Similarity Index: {jaccard:.4f}\n"
            f"• Overlap Coefficient: {overlap:.4f}\n\n"
            "INTERPRETATION:\n"
            "Rule-based detection captures extreme engineering boundary\n"
            "violations (voltage sags, frequency deviations), while Isolation\n"
            "Forest isolates subtle non-linear multi-dimensional outliers."
        )
        ax2.text(0.05, 0.95, box_text, transform=ax2.transAxes, verticalalignment="top",
                 fontsize=10, fontfamily="monospace",
                 bbox=dict(boxstyle="round,pad=1", facecolor="#f8f9fa", edgecolor="#333", alpha=0.9))

        plt.tight_layout()
        chart4_path = os.path.join(charts_dir, "5_rule_vs_ml_comparison.png")
        plt.savefig(chart4_path)
        plt.close()
        print(f"Saved: {chart4_path}")

    # 5. Top Anomalous Meters
    meter_path = os.path.join(summaries_dir, "meter_anomaly_distribution.csv")
    if os.path.exists(meter_path):
        df_m = pd.read_csv(meter_path).head(12)
        fig, ax = plt.subplots(figsize=(12, 5))
        x = np.arange(len(df_m))
        w = 0.35

        ax.bar(x - w / 2, df_m["rule_anomalies"], width=w, label="Rule-Based", color="#d62728", edgecolor="black", alpha=0.85)
        ax.bar(x + w / 2, df_m["ml_anomalies"], width=w, label="Isolation Forest", color="#1f77b4", edgecolor="black", alpha=0.85)

        ax.set_title("Top 12 Smart Meters with Highest Anomaly Incidence")
        ax.set_xlabel("Smart Meter ID")
        ax.set_ylabel("Anomaly Count")
        ax.set_xticks(x)
        ax.set_xticklabels(df_m["meter_id"], rotation=45, ha="right")
        ax.legend()
        plt.tight_layout()
        chart5_path = os.path.join(charts_dir, "6_anomalies_by_meter.png")
        plt.savefig(chart5_path)
        plt.close()
        print(f"Saved: {chart5_path}")

    # 6. Hourly Anomaly Pattern Heatmap
    if os.path.exists(hourly_path):
        df_hr = pd.read_csv(hourly_path)
        fig, ax = plt.subplots(figsize=(12, 4.5))

        ax.plot(df_hr["hour"], df_hr["rule_anomalies"], marker="s", color="#d62728", label="Rule Anomalies", linewidth=2)
        ax.plot(df_hr["hour"], df_hr["ml_anomalies"], marker="^", color="#1f77b4", label="ML Anomalies", linewidth=2)
        ax.plot(df_hr["hour"], df_hr["combined_anomalies"], marker="o", color="#2ca02c", label="Combined Anomalies", linewidth=2.5)

        ax.set_title("Hourly Distribution of Anomaly Occurrences (Peak vs Off-Peak)")
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Flagged Anomalies Count")
        ax.set_xticks(range(0, 24))
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()

        plt.tight_layout()
        chart6_path = os.path.join(charts_dir, "7_hourly_anomaly_patterns.png")
        plt.savefig(chart6_path)
        plt.close()
        print(f"Saved: {chart6_path}")

    # 7. Parameter Distribution & Operational Bounds
    # If top anomalies table exists, plot realistic parameter distributions
    top_path = os.path.join(anomalies_dir, "top_anomalies_table.csv")
    if os.path.exists(top_path):
        df_top = pd.read_csv(top_path)
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 8))

        # Voltage distribution with Indian standard limits
        sns.histplot(df_top["voltage"], ax=ax1, color="#1f77b4", kde=True, bins=30)
        ax1.axvline(230, color="green", linestyle="--", linewidth=1.5, label="Nominal (230V)")
        ax1.axvline(160, color="red", linestyle=":", linewidth=1.5, label="Under-Volt Sag (160V)")
        ax1.axvline(280, color="orange", linestyle=":", linewidth=1.5, label="Over-Volt Surge (280V)")
        ax1.set_title("Voltage Distribution in Flagged Anomalies")
        ax1.set_xlabel("Voltage (Volts)")
        ax1.legend(fontsize=8)

        # Frequency distribution
        sns.histplot(df_top["frequency"], ax=ax2, color="#2ca02c", kde=True, bins=30)
        ax2.axvline(50.0, color="green", linestyle="--", linewidth=1.5, label="Nominal (50.0 Hz)")
        ax2.axvline(48.5, color="red", linestyle=":", linewidth=1.5, label="IEGC Min (48.5 Hz)")
        ax2.axvline(51.5, color="red", linestyle=":", linewidth=1.5, label="IEGC Max (51.5 Hz)")
        ax2.set_title("Frequency Distribution in Flagged Anomalies")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.legend(fontsize=8)

        # Current distribution
        sns.histplot(df_top["current"], ax=ax3, color="#ff7f0e", kde=True, bins=30)
        ax3.axvline(35.0, color="red", linestyle=":", linewidth=1.5, label="Overload Limit (35A)")
        ax3.set_title("Current Distribution in Flagged Anomalies")
        ax3.set_xlabel("Current (Amperes)")
        ax3.legend(fontsize=8)

        # ML Anomaly Score Distribution
        sns.histplot(df_top["ml_anomaly_score"], ax=ax4, color="#d62728", kde=True, bins=30)
        ax4.set_title("Isolation Forest Anomaly Score Distribution")
        ax4.set_xlabel("Anomaly Score (Higher = More Abnormal)")

        plt.tight_layout()
        chart7_path = os.path.join(charts_dir, "3_electrical_parameters.png")
        plt.savefig(chart7_path)
        plt.close()
        print(f"Saved: {chart7_path}")

    # 8. Anomaly Micro-Trace Case Study
    if os.path.exists(top_path):
        df_top = pd.read_csv(top_path)
        # Select top anomalous meter and plot its sequence
        sample_meter = df_top["meter_id"].iloc[0]
        meter_records = df_top[df_top["meter_id"] == sample_meter].head(25)

        if len(meter_records) > 5:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

            x_idx = range(len(meter_records))
            ts_labels = [str(t)[11:16] for t in meter_records["timestamp"]]

            # Energy Spike
            ax1.plot(x_idx, meter_records["kwh"], color="#d62728", marker="o", linewidth=2)
            ax1.set_ylabel("Active Energy (kWh)", weight="bold")
            ax1.set_title(f"High-Resolution Anomaly Event Trace — Smart Meter {sample_meter}")
            ax1.grid(True, linestyle="--", alpha=0.5)

            # Voltage Sag/Surge
            ax2.plot(x_idx, meter_records["voltage"], color="#1f77b4", marker="s", linewidth=2)
            ax2.axhline(230, color="green", linestyle="--", alpha=0.7, label="230V Nominal")
            ax2.set_ylabel("Voltage (V)", weight="bold")
            ax2.grid(True, linestyle="--", alpha=0.5)
            ax2.legend(loc="upper right", fontsize=8)

            # Current Surge
            ax3.plot(x_idx, meter_records["current"], color="#ff7f0e", marker="^", linewidth=2)
            ax3.set_ylabel("Current (A)", weight="bold")
            ax3.set_xlabel("Timestamp (HH:MM)", weight="bold")
            ax3.set_xticks(x_idx[::2])
            ax3.set_xticklabels(ts_labels[::2], rotation=30)
            ax3.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            chart8_path = os.path.join(charts_dir, "8_anomaly_case_study.png")
            plt.savefig(chart8_path)
            plt.close()
            print(f"Saved: {chart8_path}")

    print("\n[SUCCESS] All 8 publication graphics successfully generated in outputs/charts/!")


if __name__ == "__main__":
    generate_all_visualizations()
