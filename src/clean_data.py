"""
GridSense: Data Quality Auditing and Cleaning Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Performs data validation, null audits, duplicate detection,
operational boundary checks, and power-outage vs abnormal consumption categorization.
"""

import os
import sys
import time
import json
import logging
from typing import Tuple, Dict, Any
from pathlib import Path
import yaml

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.DataCleaner")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def audit_and_clean_data(
    df: DataFrame,
    config: dict = None
) -> Tuple[DataFrame, Dict[str, Any]]:
    """
    Performs comprehensive data quality audit and returns cleaned DataFrame along with metrics.
    """
    if config is None:
        config = load_config()

    output_dir = config["paths"]["summaries_dir"]
    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()

    logger.info("Commencing Data Quality Audit & Cleaning...")

    # 1. Total Raw Record Count
    initial_count = df.count()
    logger.info("Initial record count: %d", initial_count)

    # 2. Null Value Auditing
    numeric_cols = {"kwh", "voltage", "current", "frequency"}
    null_exprs = [
        F.count(
            F.when(
                (F.col(c).isNull() | F.isnan(F.col(c))) if c in numeric_cols else F.col(c).isNull(),
                c
            )
        ).alias(f"null_{c}")
        for c in ["timestamp", "kwh", "voltage", "current", "frequency", "meter_id"]
    ]
    null_stats = df.select(null_exprs).collect()[0].asDict()
    logger.info("Null audit results: %s", null_stats)

    # 3. Duplicate Detection on (meter_id, timestamp)
    dup_counts = df.groupBy("meter_id", "timestamp").count().filter("count > 1").count()
    logger.info("Detected duplicate (meter_id, timestamp) occurrences: %d", dup_counts)

    # Drop duplicates
    df_dedup = df.dropDuplicates(["meter_id", "timestamp"])
    dedup_count = df_dedup.count()
    dropped_duplicates = initial_count - dedup_count

    # 4. Data Quality Categorization & Anomaly Boundary Flags
    dq_rules = config.get("data_quality_rules", {})
    min_v = dq_rules.get("min_voltage", 100.0)
    max_v = dq_rules.get("max_voltage", 300.0)
    min_f = dq_rules.get("min_frequency", 47.0)
    max_f = dq_rules.get("max_frequency", 53.0)
    max_c = dq_rules.get("max_current", 60.0)

    # Categorize electrical status
    # Outage: Voltage == 0, Current == 0, kWh == 0
    # Normal Standby: Voltage > 0, Current == 0, kWh == 0
    # Active Load: kWh > 0 and Voltage > 0
    # Invalid Measurements: Negative kWh, or Voltage out of physical limits
    df_categorized = df_dedup.withColumn(
        "is_power_outage",
        (F.col("voltage") == 0.0) & (F.col("current") == 0.0) & (F.col("kwh") == 0.0)
    ).withColumn(
        "is_negative_kwh",
        F.col("kwh") < 0.0
    ).withColumn(
        "is_voltage_extreme",
        (F.col("voltage") < min_v) & (F.col("voltage") > 0.0) | (F.col("voltage") > max_v)
    ).withColumn(
        "is_frequency_extreme",
        (F.col("frequency") < min_f) | (F.col("frequency") > max_f)
    ).withColumn(
        "is_current_extreme",
        (F.col("current") < 0.0) | (F.col("current") > max_c)
    )

    # Aggregate counts of quality categories
    quality_summary = df_categorized.select(
        F.count(F.when(F.col("is_power_outage"), 1)).alias("power_outages_count"),
        F.count(F.when(F.col("is_negative_kwh"), 1)).alias("negative_kwh_count"),
        F.count(F.when(F.col("is_voltage_extreme"), 1)).alias("voltage_extreme_count"),
        F.count(F.when(F.col("is_frequency_extreme"), 1)).alias("frequency_extreme_count"),
        F.count(F.when(F.col("is_current_extreme"), 1)).alias("current_extreme_count")
    ).collect()[0].asDict()

    logger.info("Quality summary: %s", quality_summary)

    # Filter out corrupted records where critical columns are missing
    df_cleaned = df_categorized.filter(
        F.col("timestamp").isNotNull() &
        F.col("meter_id").isNotNull() &
        F.col("kwh").isNotNull() &
        F.col("voltage").isNotNull()
    )

    final_count = df_cleaned.count()
    elapsed = time.time() - start_time

    audit_report = {
        "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "processing_time_seconds": round(elapsed, 2),
        "initial_record_count": initial_count,
        "dropped_duplicates": dropped_duplicates,
        "final_cleaned_count": final_count,
        "null_statistics": null_stats,
        "duplicate_groups_count": dup_counts,
        "quality_metrics": quality_summary
    }

    # Save to disk
    audit_path = os.path.join(output_dir, "data_quality_audit.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    logger.info("Data Quality Audit complete in %.2f seconds. Report saved to: %s", elapsed, audit_path)
    return df_cleaned, audit_report


if __name__ == "__main__":
    from load_data import load_high_frequency_data
    from spark_setup import stop_spark_session

    print("Testing clean_data module with 0.001 sample...")
    spark = get_spark_session(app_name="TestCleanData", shuffle_partitions=4)
    raw_df = load_high_frequency_data(spark, sample_fraction=0.001)
    clean_df, audit = audit_and_clean_data(raw_df)
    print("Cleaned DataFrame sample:")
    clean_df.show(5)
    print("Audit Summary:")
    print(json.dumps(audit, indent=2))
    stop_spark_session(spark)
    print("Test passed successfully!")
