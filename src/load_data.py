"""
GridSense: Data Ingestion and Schema Standardization Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Loads high-frequency smart-meter CSV files from Bareilly and Mathura using PySpark.
Applies explicit schema casting, timestamp parsing, standardized column names, and location labeling.
"""

import os
import sys
import time
import logging
from typing import Optional, List
from pathlib import Path
import yaml

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType
)

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.DataLoader")


def load_config(config_path: Optional[str] = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_raw_schema() -> StructType:
    """Returns the explicit PySpark schema for the 3-minute smart meter readings."""
    return StructType([
        StructField("x_Timestamp", StringType(), True),
        StructField("t_kWh", DoubleType(), True),
        StructField("z_Avg Voltage (Volt)", DoubleType(), True),
        StructField("z_Avg Current (Amp)", DoubleType(), True),
        StructField("y_Freq (Hz)", DoubleType(), True),
        StructField("meter", StringType(), True)
    ])


def load_high_frequency_data(
    spark,
    config: Optional[dict] = None,
    sample_fraction: Optional[float] = None,
    selected_files: Optional[List[str]] = None
) -> DataFrame:
    """
    Ingests and standardizes the 6 high-frequency 3-minute smart meter CSV files.
    """
    if config is None:
        config = load_config()

    raw_dir = config["paths"]["raw_data_dir"]
    if selected_files is None:
        selected_files = config["dataset"]["selected_files"]

    logger.info("Initiating ingestion of %d high-frequency dataset files from: %s", len(selected_files), raw_dir)
    start_time = time.time()

    dfs = []
    schema = get_raw_schema()

    for fname in selected_files:
        fpath = os.path.join(raw_dir, fname)
        if not os.path.exists(fpath):
            logger.warning("File not found: %s. Skipping.", fpath)
            continue

        logger.info("Reading file: %s", fname)
        df_single = spark.read \
            .option("header", "true") \
            .schema(schema) \
            .csv(fpath)

        # Standardize column names
        df_standard = df_single \
            .withColumnRenamed("x_Timestamp", "raw_timestamp") \
            .withColumnRenamed("t_kWh", "kwh") \
            .withColumnRenamed("z_Avg Voltage (Volt)", "voltage") \
            .withColumnRenamed("z_Avg Current (Amp)", "current") \
            .withColumnRenamed("y_Freq (Hz)", "frequency") \
            .withColumnRenamed("meter", "meter_id")

        # Parse timestamp safely
        df_standard = df_standard.withColumn(
            "timestamp",
            F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss")
        ).drop("raw_timestamp")

        # Add city based on meter prefix (MH = Mathura, BR = Bareilly)
        df_standard = df_standard.withColumn(
            "city",
            F.when(F.col("meter_id").startswith("MH"), F.lit("Mathura"))
             .when(F.col("meter_id").startswith("BR"), F.lit("Bareilly"))
             .otherwise(F.lit("Unknown"))
        )

        # Extract year from timestamp or file name
        df_standard = df_standard.withColumn("year", F.year(F.col("timestamp")))

        # If sample fraction is specified, downsample per file
        if sample_fraction is not None and 0.0 < sample_fraction < 1.0:
            df_standard = df_standard.sample(fraction=sample_fraction, seed=42)

        dfs.append(df_standard)

    if not dfs:
        raise FileNotFoundError(f"No valid CSV files were loaded from {raw_dir}")

    # Union all datasets
    combined_df = dfs[0]
    for other_df in dfs[1:]:
        combined_df = combined_df.unionByName(other_df)

    elapsed = time.time() - start_time
    logger.info("Completed loading datasets in %.2f seconds.", elapsed)
    return combined_df


if __name__ == "__main__":
    from spark_setup import stop_spark_session
    print("Testing load_data module with a 0.001 sample...")
    spark = get_spark_session(app_name="TestLoadData", shuffle_partitions=4)
    df = load_high_frequency_data(spark, sample_fraction=0.001)
    print("Sample Schema:")
    df.printSchema()
    print("Sample Records:")
    df.show(5)
    print("Total sample rows:", df.count())
    stop_spark_session(spark)
    print("Test finished successfully!")
