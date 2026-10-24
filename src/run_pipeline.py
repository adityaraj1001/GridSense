"""
GridSense: Master Pipeline Orchestrator
Author: Aditya Raj (INT315 Cluster Computing)
Description: End-to-end distributed execution pipeline that chains Spark initialization,
dataset inspection, ingestion, cleaning, feature engineering, rule-based detection,
Isolation Forest training & scoring, agreement evaluation, and chart generation.
"""

import os
import sys
import time
import json
import argparse
import logging
from pathlib import Path
import yaml

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session, stop_spark_session
from load_data import load_high_frequency_data
from clean_data import audit_and_clean_data
from feature_engineering import build_features
from rule_based_detection import apply_rule_based_detection
from train_model import train_isolation_forest, score_dataframe
from evaluate_results import evaluate_anomalies
from visualize_results import generate_all_visualizations

logger = logging.getLogger("GridSense.Pipeline")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(sample_fraction: float = None, config_path: str = None):
    pipeline_start = time.time()
    config = load_config(config_path)
    logs_dir = config["paths"]["logs_dir"]
    os.makedirs(logs_dir, exist_ok=True)

    print("=" * 80)
    print(" GridSense: End-to-End Distributed Cluster Computing Pipeline ")
    print(" Project: Electricity Consumption Anomaly Detection ")
    print(" Course: INT315 Cluster Computing | Author: Aditya Raj ")
    if sample_fraction:
        print(f" Execution Mode: Scaled Representative Sample ({sample_fraction * 100:.2f}%)")
    else:
        print(" Execution Mode: Full Dataset (All 21+ Million Records)")
    print("=" * 80)

    stage_timings = {}

    # Stage 0: Spark Initialization
    t0 = time.time()
    spark_cfg = config.get("spark", {})
    spark = get_spark_session(
        app_name=spark_cfg.get("app_name", "GridSense_Cluster_Computing"),
        master=spark_cfg.get("master", "local[*]"),
        driver_memory=spark_cfg.get("driver_memory", "4g"),
        shuffle_partitions=spark_cfg.get("shuffle_partitions", 8)
    )
    stage_timings["spark_initialization_seconds"] = round(time.time() - t0, 2)

    try:
        # Stage 1: Data Ingestion
        print("\n>>> Stage 1: Ingesting High-Frequency Smart Meter Data...")
        t1 = time.time()
        raw_df = load_high_frequency_data(spark, config=config, sample_fraction=sample_fraction)
        raw_count = raw_df.count()
        stage_timings["data_ingestion_seconds"] = round(time.time() - t1, 2)
        print(f"    Loaded {raw_count:,} records in {stage_timings['data_ingestion_seconds']}s")

        # Stage 2: Data Cleaning and Quality Audit
        print("\n>>> Stage 2: Auditing Data Quality and Cleaning...")
        t2 = time.time()
        clean_df, audit_report = audit_and_clean_data(raw_df, config=config)
        clean_count = clean_df.count()
        stage_timings["data_cleaning_seconds"] = round(time.time() - t2, 2)
        print(f"    Cleaned dataset contains {clean_count:,} records (dropped {raw_count - clean_count:,})")

        # Stage 3: Feature Engineering
        print("\n>>> Stage 3: Distributed Feature Engineering...")
        t3 = time.time()
        feat_df = build_features(clean_df, config=config)
        # Cache feature dataframe for multiple downstream passes
        feat_df.cache()
        feat_count = feat_df.count()
        stage_timings["feature_engineering_seconds"] = round(time.time() - t3, 2)
        print(f"    Engineered features for {feat_count:,} records in {stage_timings['feature_engineering_seconds']}s")

        # Stage 4: Rule-Based Detection (Method A)
        print("\n>>> Stage 4: Executing Method A (Rule-Based Detection)...")
        t4 = time.time()
        rule_df, rule_summary = apply_rule_based_detection(feat_df, config=config)
        rule_anom_count = rule_summary["total_rule_anomalies"]
        stage_timings["rule_based_detection_seconds"] = round(time.time() - t4, 2)
        print(f"    Flagged {rule_anom_count:,} rule anomalies ({rule_summary['anomaly_percentage']:.2f}%)")

        # Stage 5: Train Machine Learning Model (Method B: Isolation Forest)
        print("\n>>> Stage 5: Training Isolation Forest Model...")
        t5 = time.time()
        iso_model, scaler, model_meta = train_isolation_forest(rule_df, config=config)
        stage_timings["ml_training_seconds"] = round(time.time() - t5, 2)
        print(f"    Isolation Forest trained in {stage_timings['ml_training_seconds']}s")

        # Stage 6: Machine Learning Scoring
        print("\n>>> Stage 6: Distributed Anomaly Scoring...")
        t6 = time.time()
        scored_df = score_dataframe(rule_df, iso_model, scaler, config=config)
        scored_df.cache()
        scored_count = scored_df.count()
        stage_timings["ml_scoring_seconds"] = round(time.time() - t6, 2)
        print(f"    Scored {scored_count:,} records in {stage_timings['ml_scoring_seconds']}s")

        # Stage 7: Agreement Evaluation & Metrics Export
        print("\n>>> Stage 7: Evaluating Agreement and Exporting Summaries...")
        t7 = time.time()
        eval_results = evaluate_anomalies(scored_df, config=config)
        stage_timings["evaluation_seconds"] = round(time.time() - t7, 2)
        print("    Agreement Analysis:")
        print(f"      - High Confidence (Both Agree): {eval_results['agreement_analysis']['both_agree_count']:,} ({eval_results['agreement_analysis']['both_agree_pct']:.2f}%)")
        print(f"      - Jaccard Similarity Index: {eval_results['agreement_analysis']['jaccard_similarity']:.4f}")

        # Stage 8: Visualization Generation
        print("\n>>> Stage 8: Generating High-Resolution Charts...")
        t8 = time.time()
        generate_all_visualizations(config=config)
        stage_timings["visualization_seconds"] = round(time.time() - t8, 2)

    finally:
        # Cleanly stop Spark session
        stop_spark_session(spark)

    total_pipeline_time = round(time.time() - pipeline_start, 2)
    stage_timings["total_pipeline_seconds"] = total_pipeline_time

    # Record benchmark execution log
    benchmark_log = {
        "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "course": "INT315 Cluster Computing",
        "project": "GridSense",
        "sample_fraction": sample_fraction if sample_fraction else 1.0,
        "total_records_processed": raw_count,
        "clean_records_retained": clean_count,
        "hardware_environment": {
            "os": "Windows 11",
            "spark_version": "4.2.0",
            "python_version": "3.14.6",
            "java_version": "17.0.12",
            "master_cores": "local[*]"
        },
        "stage_timings": stage_timings
    }

    log_path = os.path.join(logs_dir, "pipeline_execution_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_log, f, indent=2)

    print("\n" + "=" * 80)
    print(" PIPELINE EXECUTION BENCHMARK SUMMARY ")
    print("=" * 80)
    for stage, sec in stage_timings.items():
        print(f"  {stage:<35}: {sec:>8.2f} seconds")
    print(f"\n[SUCCESS] GridSense end-to-end pipeline completed in {total_pipeline_time:.2f} seconds!")
    print(f"Benchmark log written to: {log_path}")
    return benchmark_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GridSense Pipeline Runner")
    parser.add_argument("--sample_fraction", type=float, default=None,
                        help="Fraction of data to sample (e.g. 0.05 for 5%%). Default is None (full dataset).")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    args = parser.parse_args()

    run_pipeline(sample_fraction=args.sample_fraction, config_path=args.config)
