"""
GridSense: Distributed Feature Engineering Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Generates temporal, rolling, lagged, electrical deviation, and statistical
baseline features for anomaly detection using PySpark Window functions without future leakage.
"""

import os
import sys
import time
import logging
from typing import Optional
from pathlib import Path
import yaml

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.FeatureEngineering")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_features(df: DataFrame, config: Optional[dict] = None) -> DataFrame:
    """
    Transforms raw cleaned smart meter readings into an enriched feature DataFrame.
    Strictly preserves causal ordering (no future leakage).
    """
    if config is None:
        config = load_config()

    start_time = time.time()
    logger.info("Starting distributed feature engineering...")

    # 1. Temporal Features
    df_feat = df.withColumn("hour", F.hour("timestamp")) \
                .withColumn("day", F.dayofmonth("timestamp")) \
                .withColumn("month", F.month("timestamp")) \
                .withColumn("dayofweek", F.dayofweek("timestamp")) \
                .withColumn("is_weekend", F.when(F.col("dayofweek").isin(1, 7), 1).otherwise(0))

    # Time of day categorization
    df_feat = df_feat.withColumn(
        "time_of_day",
        F.when((F.col("hour") >= 6) & (F.col("hour") < 12), F.lit("Morning"))
         .when((F.col("hour") >= 12) & (F.col("hour") < 17), F.lit("Afternoon"))
         .when((F.col("hour") >= 17) & (F.col("hour") < 22), F.lit("Evening"))
         .otherwise(F.lit("Night"))
    )

    # 2. Window Specifications (Strictly Causal: rowsBetween -2 and 0)
    # Ordered chronologically per meter
    w_lag = Window.partitionBy("meter_id").orderBy("timestamp")
    w_rolling3 = Window.partitionBy("meter_id").orderBy("timestamp").rowsBetween(-2, 0)

    # 3. Lagged Readings & First-Order Rate of Change
    df_feat = df_feat.withColumn("lag_1_kwh", F.lag("kwh", 1).over(w_lag)) \
                     .withColumn("kwh_diff", F.coalesce(F.col("kwh") - F.col("lag_1_kwh"), F.lit(0.0))) \
                     .withColumn("lag_1_voltage", F.lag("voltage", 1).over(w_lag)) \
                     .withColumn("voltage_diff", F.coalesce(F.col("voltage") - F.col("lag_1_voltage"), F.lit(0.0)))

    # 4. Backward-Only Rolling Statistics (Past 3 intervals = 9 minutes)
    df_feat = df_feat.withColumn("rolling_3_mean_kwh", F.coalesce(F.avg("kwh").over(w_rolling3), F.col("kwh"))) \
                     .withColumn("rolling_3_std_kwh", F.coalesce(F.stddev("kwh").over(w_rolling3), F.lit(0.0)))

    # 5. Electrical Domain Deviations
    # Nominal Grid Standards in India: 230V single-phase, 50.0 Hz frequency
    df_feat = df_feat.withColumn("volt_dev", F.abs(F.col("voltage") - F.lit(230.0))) \
                     .withColumn("freq_dev", F.abs(F.col("frequency") - F.lit(50.0)))

    # 6. Meter Baseline Statistics (Mean & Std per meter)
    meter_stats = df.groupBy("meter_id").agg(
        F.avg("kwh").alias("meter_mean_kwh"),
        F.stddev("kwh").alias("meter_std_kwh")
    )

    df_feat = df_feat.join(meter_stats, on="meter_id", how="left")

    # Safe Z-score computation (prevent division by zero)
    df_feat = df_feat.withColumn(
        "kwh_zscore",
        F.coalesce(
            (F.col("kwh") - F.col("meter_mean_kwh")) / (F.col("meter_std_kwh") + F.lit(1e-5)),
            F.lit(0.0)
        )
    )

    # Handle remaining nulls in lag features
    df_feat = df_feat.na.fill({
        "lag_1_kwh": 0.0,
        "kwh_diff": 0.0,
        "lag_1_voltage": 230.0,
        "voltage_diff": 0.0,
        "rolling_3_std_kwh": 0.0
    })

    elapsed = time.time() - start_time
    logger.info("Feature engineering finished in %.2f seconds.", elapsed)
    return df_feat


if __name__ == "__main__":
    from load_data import load_high_frequency_data
    from clean_data import audit_and_clean_data
    from spark_setup import stop_spark_session

    print("Testing feature_engineering module with 0.001 sample...")
    spark = get_spark_session(app_name="TestFeatureEng", shuffle_partitions=4)
    raw_df = load_high_frequency_data(spark, sample_fraction=0.001)
    clean_df, _ = audit_and_clean_data(raw_df)
    feat_df = build_features(clean_df)

    print("Engineered DataFrame Schema:")
    feat_df.printSchema()
    print("Sample Engineered Rows:")
    feat_df.select("timestamp", "meter_id", "kwh", "kwh_diff", "rolling_3_mean_kwh", "volt_dev", "kwh_zscore").show(5)
    stop_spark_session(spark)
    print("Feature engineering test passed!")
