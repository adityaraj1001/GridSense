"""
GridSense: Comprehensive Evaluation and Unsupervised Agreement Analysis Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Evaluates Rule-Based and Machine Learning anomaly detections,
computes Jaccard agreement metrics, spatial/temporal distributions, and exports audit tables.
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import pandas as pd

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.Evaluator")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate_anomalies(
    df: DataFrame,
    config: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Performs rigorous agreement analysis, spatial/temporal aggregation,
    and extracts anomaly case studies.
    """
    if config is None:
        config = load_config()

    start_time = time.time()
    logger.info("Starting result evaluation and agreement analysis...")

    summaries_dir = config["paths"]["summaries_dir"]
    anomalies_dir = config["paths"]["anomalies_dir"]
    os.makedirs(summaries_dir, exist_ok=True)
    os.makedirs(anomalies_dir, exist_ok=True)

    # 1. Overall Population Statistics
    total_records = df.count()
    meter_count = df.select("meter_id").distinct().count()
    date_bounds = df.select(
        F.min("timestamp").alias("min_ts"),
        F.max("timestamp").alias("max_ts")
    ).collect()[0]

    min_ts_str = str(date_bounds["min_ts"])
    max_ts_str = str(date_bounds["max_ts"])

    # 2. Agreement Matrix & Confusion Breakdown
    # Unsupervised comparison between Method A (Rules) and Method B (ML)
    agreement_counts = df.groupBy("agreement_type").count().collect()
    agreement_dict = {row["agreement_type"]: row["count"] for row in agreement_counts}

    both_agree = agreement_dict.get("BOTH_AGREE", 0)
    rule_only = agreement_dict.get("RULE_ONLY", 0)
    ml_only = agreement_dict.get("ML_ONLY", 0)
    nominal = agreement_dict.get("NOMINAL", 0)

    total_rule = both_agree + rule_only
    total_ml = both_agree + ml_only
    union_anomalies = both_agree + rule_only + ml_only

    jaccard_similarity = round(both_agree / max(union_anomalies, 1), 4)
    overlap_coefficient = round(both_agree / max(min(total_rule, total_ml), 1), 4)

    pct_rule = round((total_rule / max(total_records, 1)) * 100, 3)
    pct_ml = round((total_ml / max(total_records, 1)) * 100, 3)
    pct_union = round((union_anomalies / max(total_records, 1)) * 100, 3)
    pct_both = round((both_agree / max(total_records, 1)) * 100, 3)

    # 3. Spatial Distribution: City Breakdown
    city_df = df.groupBy("city").agg(
        F.count("*").alias("total_readings"),
        F.countDistinct("meter_id").alias("meters"),
        F.sum(F.when(F.col("is_rule_anomaly"), 1).otherwise(0)).alias("rule_anomalies"),
        F.sum(F.when(F.col("is_ml_anomaly"), 1).otherwise(0)).alias("ml_anomalies"),
        F.sum(F.when(F.col("is_combined_anomaly"), 1).otherwise(0)).alias("combined_anomalies")
    ).toPandas()

    city_df["anomaly_rate_pct"] = (city_df["combined_anomalies"] / city_df["total_readings"]) * 100
    city_summary_path = os.path.join(summaries_dir, "city_anomaly_distribution.csv")
    city_df.to_csv(city_summary_path, index=False)

    # 4. Temporal Breakdown: Hourly & Monthly
    hourly_df = df.groupBy("hour").agg(
        F.count("*").alias("total_readings"),
        F.avg("kwh").alias("avg_kwh"),
        F.sum(F.when(F.col("is_rule_anomaly"), 1).otherwise(0)).alias("rule_anomalies"),
        F.sum(F.when(F.col("is_ml_anomaly"), 1).otherwise(0)).alias("ml_anomalies"),
        F.sum(F.when(F.col("is_combined_anomaly"), 1).otherwise(0)).alias("combined_anomalies")
    ).orderBy("hour").toPandas()

    hourly_df["anomaly_rate_pct"] = (hourly_df["combined_anomalies"] / hourly_df["total_readings"]) * 100
    hourly_summary_path = os.path.join(summaries_dir, "hourly_anomaly_distribution.csv")
    hourly_df.to_csv(hourly_summary_path, index=False)

    monthly_df = df.groupBy("month").agg(
        F.count("*").alias("total_readings"),
        F.avg("kwh").alias("avg_kwh"),
        F.sum(F.when(F.col("is_combined_anomaly"), 1).otherwise(0)).alias("combined_anomalies")
    ).orderBy("month").toPandas()

    monthly_df["anomaly_rate_pct"] = (monthly_df["combined_anomalies"] / monthly_df["total_readings"]) * 100
    monthly_summary_path = os.path.join(summaries_dir, "monthly_anomaly_distribution.csv")
    monthly_df.to_csv(monthly_summary_path, index=False)

    # 5. Top Anomalous Meters
    meter_anom_df = df.groupBy("meter_id", "city").agg(
        F.count("*").alias("total_readings"),
        F.sum("kwh").alias("total_kwh"),
        F.sum(F.when(F.col("is_rule_anomaly"), 1).otherwise(0)).alias("rule_anomalies"),
        F.sum(F.when(F.col("is_ml_anomaly"), 1).otherwise(0)).alias("ml_anomalies"),
        F.sum(F.when(F.col("is_combined_anomaly"), 1).otherwise(0)).alias("combined_anomalies"),
        F.max("ml_anomaly_score").alias("max_anomaly_score")
    ).toPandas()

    meter_anom_df["anomaly_rate_pct"] = (meter_anom_df["combined_anomalies"] / meter_anom_df["total_readings"]) * 100
    meter_anom_df = meter_anom_df.sort_values(by="combined_anomalies", ascending=False)
    meter_summary_path = os.path.join(summaries_dir, "meter_anomaly_distribution.csv")
    meter_anom_df.to_csv(meter_summary_path, index=False)

    # 6. Extract Top Anomaly Records for Case Studies
    top_anomalies_df = df.filter(F.col("is_combined_anomaly")) \
        .orderBy(F.col("ml_anomaly_score").desc(), F.col("rule_anomaly_count").desc()) \
        .limit(2000) \
        .select(
            "timestamp", "meter_id", "city", "kwh", "voltage", "current",
            "frequency", "ml_anomaly_score", "is_rule_anomaly", "is_ml_anomaly",
            "agreement_type", "rule_flags"
        ).toPandas()

    top_anomalies_path = os.path.join(anomalies_dir, "top_anomalies_table.csv")
    top_anomalies_df.to_csv(top_anomalies_path, index=False)

    elapsed = time.time() - start_time

    # Comprehensive Evaluation Results Object
    eval_results = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "evaluation_time_seconds": round(elapsed, 2),
        "total_records": total_records,
        "unique_meters": meter_count,
        "date_coverage": {
            "start": min_ts_str,
            "end": max_ts_str
        },
        "rule_based_detection": {
            "count": total_rule,
            "percentage": pct_rule
        },
        "machine_learning_detection": {
            "count": total_ml,
            "percentage": pct_ml
        },
        "agreement_analysis": {
            "both_agree_count": both_agree,
            "both_agree_pct": pct_both,
            "rule_only_count": rule_only,
            "ml_only_count": ml_only,
            "nominal_count": nominal,
            "union_anomalies_count": union_anomalies,
            "union_percentage": pct_union,
            "jaccard_similarity": jaccard_similarity,
            "overlap_coefficient": overlap_coefficient,
            "methodology_note": (
                "Ground truth theft/fraud labels are unavailable in open academic smart meter datasets. "
                "Evaluation is conducted using unsupervised agreement metrics, domain-rule cross-validation, "
                "and distribution stability rather than fabricated precision/recall metrics."
            )
        },
        "city_breakdown": city_df.to_dict(orient="records"),
        "top_anomalous_meters": meter_anom_df.head(10).to_dict(orient="records")
    }

    eval_json_path = os.path.join(summaries_dir, "evaluation_summary.json")
    with open(eval_json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    logger.info("Evaluation complete in %.2f s. Summary saved to: %s", elapsed, eval_json_path)
    return eval_results


if __name__ == "__main__":
    from load_data import load_high_frequency_data
    from clean_data import audit_and_clean_data
    from feature_engineering import build_features
    from rule_based_detection import apply_rule_based_detection
    from train_model import train_isolation_forest, score_dataframe
    from spark_setup import stop_spark_session

    print("Testing evaluate_results module with 0.001 sample...")
    spark = get_spark_session(app_name="TestEvaluator", shuffle_partitions=4)
    raw_df = load_high_frequency_data(spark, sample_fraction=0.001)
    clean_df, _ = audit_and_clean_data(raw_df)
    feat_df = build_features(clean_df)
    rule_df, _ = apply_rule_based_detection(feat_df)
    model, scaler, _ = train_isolation_forest(rule_df)
    scored_df = score_dataframe(rule_df, model, scaler)

    eval_summary = evaluate_anomalies(scored_df)
    print("Evaluation Summary:")
    print(json.dumps(eval_summary["agreement_analysis"], indent=2))
    stop_spark_session(spark)
    print("Evaluation test completed successfully!")
