"""
GridSense: Rule-Based Anomaly Detection Module (Method A)
Author: Aditya Raj (INT315 Cluster Computing)
Description: Evaluates electrical domain engineering rules, statistical baseline bounds,
and metering anomalies. Appends explicit rule codes and human-readable diagnostic reasons.
"""

import os
import sys
import time
import json
import logging
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
import yaml

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.RuleBasedDetection")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_rule_based_detection(
    df: DataFrame,
    config: Optional[dict] = None
) -> Tuple[DataFrame, Dict[str, Any]]:
    """
    Applies configurable engineering and statistical rules to flag anomalies.
    Returns DataFrame with rule flags, anomaly count, and evaluation metrics summary.
    """
    if config is None:
        config = load_config()

    start_time = time.time()
    logger.info("Executing Method A: Rule-Based Anomaly Detection...")

    # Individual Rule Conditions
    cond_neg_kwh = F.col("kwh") < 0.0
    cond_spike_kwh = F.col("kwh") > 2.5
    cond_over_voltage = F.col("voltage") > 280.0
    cond_under_voltage = (F.col("voltage") < 160.0) & (F.col("voltage") > 0.0) & (F.col("kwh") > 0.005)
    cond_freq_violation = (F.col("frequency") < 48.5) | (F.col("frequency") > 51.5)
    cond_current_overload = F.col("current") > 35.0
    cond_suspect_bypass = (F.col("voltage") == 0.0) & (F.col("current") > 1.0)
    cond_stat_spike = F.col("kwh_zscore") > 4.0
    cond_abrupt_ramp = F.abs(F.col("kwh_diff")) > 1.8

    # Create individual boolean indicator columns
    df_rules = df.withColumn("flag_neg_kwh", F.when(cond_neg_kwh, 1).otherwise(0)) \
                 .withColumn("flag_spike_kwh", F.when(cond_spike_kwh, 1).otherwise(0)) \
                 .withColumn("flag_over_voltage", F.when(cond_over_voltage, 1).otherwise(0)) \
                 .withColumn("flag_under_voltage", F.when(cond_under_voltage, 1).otherwise(0)) \
                 .withColumn("flag_freq_violation", F.when(cond_freq_violation, 1).otherwise(0)) \
                 .withColumn("flag_current_overload", F.when(cond_current_overload, 1).otherwise(0)) \
                 .withColumn("flag_suspect_bypass", F.when(cond_suspect_bypass, 1).otherwise(0)) \
                 .withColumn("flag_stat_spike", F.when(cond_stat_spike, 1).otherwise(0)) \
                 .withColumn("flag_abrupt_ramp", F.when(cond_abrupt_ramp, 1).otherwise(0))

    # Total rule anomaly count
    rule_sum_expr = (
        F.col("flag_neg_kwh") +
        F.col("flag_spike_kwh") +
        F.col("flag_over_voltage") +
        F.col("flag_under_voltage") +
        F.col("flag_freq_violation") +
        F.col("flag_current_overload") +
        F.col("flag_suspect_bypass") +
        F.col("flag_stat_spike") +
        F.col("flag_abrupt_ramp")
    )
    df_rules = df_rules.withColumn("rule_anomaly_count", rule_sum_expr)
    df_rules = df_rules.withColumn("is_rule_anomaly", F.col("rule_anomaly_count") > 0)

    # Build human-readable diagnostic tag and reasons
    reasons_array = F.array([
        F.when(cond_neg_kwh, F.lit("NEGATIVE_KWH")).otherwise(F.lit(None)),
        F.when(cond_spike_kwh, F.lit("EXTREME_KWH_SPIKE")).otherwise(F.lit(None)),
        F.when(cond_over_voltage, F.lit("OVER_VOLTAGE_SURGE")).otherwise(F.lit(None)),
        F.when(cond_under_voltage, F.lit("UNDER_VOLTAGE_SAG")).otherwise(F.lit(None)),
        F.when(cond_freq_violation, F.lit("GRID_FREQ_VIOLATION")).otherwise(F.lit(None)),
        F.when(cond_current_overload, F.lit("CURRENT_OVERLOAD")).otherwise(F.lit(None)),
        F.when(cond_suspect_bypass, F.lit("ZERO_VOLT_ACTIVE_CURRENT")).otherwise(F.lit(None)),
        F.when(cond_stat_spike, F.lit("STATISTICAL_ZSCORE_OUTLIER")).otherwise(F.lit(None)),
        F.when(cond_abrupt_ramp, F.lit("ABRUPT_CONSUMPTION_RAMP")).otherwise(F.lit(None))
    ])

    # Filter out nulls from array and concatenate
    df_rules = df_rules.withColumn(
        "rule_flags",
        F.coalesce(
            F.array_join(F.filter(reasons_array, lambda x: x.isNotNull()), ", "),
            F.lit("NORMAL")
        )
    )

    # Aggregate Rule Breakdown
    total_records = df_rules.count()
    rule_metrics = df_rules.select(
        F.sum("flag_neg_kwh").alias("neg_kwh_count"),
        F.sum("flag_spike_kwh").alias("spike_kwh_count"),
        F.sum("flag_over_voltage").alias("over_voltage_count"),
        F.sum("flag_under_voltage").alias("under_voltage_count"),
        F.sum("flag_freq_violation").alias("freq_violation_count"),
        F.sum("flag_current_overload").alias("current_overload_count"),
        F.sum("flag_suspect_bypass").alias("suspect_bypass_count"),
        F.sum("flag_stat_spike").alias("stat_spike_count"),
        F.sum("flag_abrupt_ramp").alias("abrupt_ramp_count"),
        F.count(F.when(F.col("is_rule_anomaly"), 1)).alias("total_rule_anomalies")
    ).collect()[0].asDict()

    total_rule_anomalies = rule_metrics["total_rule_anomalies"]
    anomaly_rate_pct = round((total_rule_anomalies / total_records) * 100, 4) if total_records > 0 else 0.0

    elapsed = time.time() - start_time
    summary_data = {
        "detection_method": "Rule-Based (Method A)",
        "execution_time_seconds": round(elapsed, 2),
        "total_records_analyzed": total_records,
        "total_rule_anomalies": total_rule_anomalies,
        "anomaly_percentage": anomaly_rate_pct,
        "rule_breakdown": rule_metrics
    }

    # Save summary
    out_dir = config["paths"]["summaries_dir"]
    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, "rule_based_detection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    logger.info("Rule-based detection complete. Flagged %d anomalies (%.2f%%) in %.2f s.",
                total_rule_anomalies, anomaly_rate_pct, elapsed)
    return df_rules, summary_data


if __name__ == "__main__":
    from load_data import load_high_frequency_data
    from clean_data import audit_and_clean_data
    from feature_engineering import build_features
    from spark_setup import stop_spark_session

    print("Testing rule_based_detection module with 0.001 sample...")
    spark = get_spark_session(app_name="TestRuleDetection", shuffle_partitions=4)
    raw_df = load_high_frequency_data(spark, sample_fraction=0.001)
    clean_df, _ = audit_and_clean_data(raw_df)
    feat_df = build_features(clean_df)
    rule_df, metrics = apply_rule_based_detection(feat_df)

    print("Rule Detection Sample Results:")
    rule_df.filter(F.col("is_rule_anomaly")).select(
        "timestamp", "meter_id", "kwh", "voltage", "current", "rule_flags"
    ).show(5, truncate=False)

    print("Summary Metrics:")
    print(json.dumps(metrics, indent=2))
    stop_spark_session(spark)
    print("Rule detection test passed!")
