"""
GridSense: Comprehensive Automated Test Suite
Author: Aditya Raj (INT315 Cluster Computing)
Description: Unit and integration tests covering configuration validation,
synthetic data ingestion, schema parsing, duplicate handling, rule-based detection,
feature engineering, and Isolation Forest ML scoring.
"""

import os
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
from pathlib import Path
import yaml

# Add src and project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from spark_setup import get_spark_session, stop_spark_session
from load_data import get_raw_schema
from clean_data import audit_and_clean_data
from feature_engineering import build_features
from rule_based_detection import apply_rule_based_detection
from train_model import train_isolation_forest, score_dataframe


class TestGridSensePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initializes a lightweight local SparkSession for unit tests."""
        cls.spark = get_spark_session(
            app_name="GridSense_UnitTests",
            master="local[1]",
            shuffle_partitions=2
        )
        cls.config_path = PROJECT_ROOT / "config" / "config.yaml"
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)

    @classmethod
    def tearDownClass(cls):
        """Cleanly stops SparkSession after test suite completion."""
        stop_spark_session(cls.spark)

    def test_01_config_validation(self):
        """Verifies that config.yaml exists and contains essential sections."""
        self.assertIn("paths", self.config)
        self.assertIn("spark", self.config)
        self.assertIn("dataset", self.config)
        self.assertIn("data_quality_rules", self.config)
        self.assertIn("rule_based_detection", self.config)
        self.assertIn("machine_learning", self.config)

    def test_02_schema_definition(self):
        """Verifies explicit raw schema structure."""
        schema = get_raw_schema()
        field_names = [f.name for f in schema.fields]
        self.assertEqual(len(field_names), 6)
        self.assertIn("x_Timestamp", field_names)
        self.assertIn("t_kWh", field_names)
        self.assertIn("z_Avg Voltage (Volt)", field_names)
        self.assertIn("meter", field_names)

    def test_03_data_cleaning_and_duplicates(self):
        """Tests null handling, deduplication, and quality filtering on synthetic data."""
        # Create synthetic fixture with deliberate duplicates and nulls
        data = [
            ("2021-01-01 00:00:00", 0.05, 230.0, 1.2, 50.0, "MH01"),
            ("2021-01-01 00:00:00", 0.05, 230.0, 1.2, 50.0, "MH01"),  # duplicate
            ("2021-01-01 00:03:00", -0.01, 230.0, 0.5, 50.0, "MH01"), # negative kwh
            ("2021-01-01 00:06:00", 0.0, 0.0, 0.0, 0.0, "MH01"),      # power outage
            (None, 0.02, 230.0, 0.8, 50.0, "MH01")                     # null timestamp
        ]
        columns = ["raw_timestamp", "kwh", "voltage", "current", "frequency", "meter_id"]
        raw_df = self.spark.createDataFrame(data, columns)

        from pyspark.sql import functions as F
        raw_df = raw_df.withColumn("timestamp", F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss"))
        raw_df = raw_df.withColumn("city", F.lit("Mathura")).withColumn("year", F.lit(2021))

        clean_df, audit = audit_and_clean_data(raw_df, config=self.config)
        self.assertEqual(audit["initial_record_count"], 5)
        self.assertEqual(audit["dropped_duplicates"], 1)
        # Record with null timestamp dropped in cleaning
        self.assertEqual(clean_df.count(), 3)

    def test_04_feature_engineering_causality(self):
        """Verifies feature generation and ensures no future data leakage."""
        data = [
            ("2021-01-01 00:00:00", 0.02, 230.0, 0.5, 50.0, "BR01", "Bareilly", 2021),
            ("2021-01-01 00:03:00", 0.04, 232.0, 1.0, 50.0, "BR01", "Bareilly", 2021),
            ("2021-01-01 00:06:00", 0.08, 228.0, 2.0, 49.9, "BR01", "Bareilly", 2021),
        ]
        cols = ["raw_timestamp", "kwh", "voltage", "current", "frequency", "meter_id", "city", "year"]
        df = self.spark.createDataFrame(data, cols)

        from pyspark.sql import functions as F
        df = df.withColumn("timestamp", F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss"))

        feat_df = build_features(df, config=self.config)
        feat_cols = feat_df.columns

        self.assertIn("hour", feat_cols)
        self.assertIn("lag_1_kwh", feat_cols)
        self.assertIn("kwh_diff", feat_cols)
        self.assertIn("rolling_3_mean_kwh", feat_cols)
        self.assertIn("kwh_zscore", feat_cols)

        # Check values
        rows = feat_df.orderBy("timestamp").collect()
        self.assertAlmostEqual(rows[1]["kwh_diff"], 0.02, places=3)
        self.assertAlmostEqual(rows[2]["kwh_diff"], 0.04, places=3)

    def test_05_rule_based_detection_flags(self):
        """Tests that rule engine flags severe electrical violations accurately."""
        data = [
            ("2021-01-01 00:00:00", 0.02, 230.0, 0.5, 50.0, "MH01", 0.0, 0.0, 0.0),   # Normal
            ("2021-01-01 00:03:00", 3.2, 230.0, 5.0, 50.0, "MH01", 3.0, 5.5, 0.0),    # Spike > 2.5
            ("2021-01-01 00:06:00", 0.02, 295.0, 0.5, 50.0, "MH01", 0.0, 0.0, 65.0),  # Over-voltage > 280
            ("2021-01-01 00:09:00", 0.02, 230.0, 0.5, 52.1, "MH01", 0.0, 0.0, 0.0),   # Freq violation > 51.5
        ]
        cols = ["raw_timestamp", "kwh", "voltage", "current", "frequency", "meter_id", "kwh_diff", "kwh_zscore", "volt_dev"]
        df = self.spark.createDataFrame(data, cols)

        from pyspark.sql import functions as F
        df = df.withColumn("timestamp", F.to_timestamp(F.col("raw_timestamp"), "yyyy-MM-dd HH:mm:ss"))

        rule_df, metrics = apply_rule_based_detection(df, config=self.config)
        rows = rule_df.orderBy("timestamp").collect()

        self.assertFalse(rows[0]["is_rule_anomaly"])
        self.assertTrue(rows[1]["is_rule_anomaly"])
        self.assertIn("EXTREME_KWH_SPIKE", rows[1]["rule_flags"])
        self.assertTrue(rows[2]["is_rule_anomaly"])
        self.assertIn("OVER_VOLTAGE_SURGE", rows[2]["rule_flags"])
        self.assertTrue(rows[3]["is_rule_anomaly"])
        self.assertIn("GRID_FREQ_VIOLATION", rows[3]["rule_flags"])

    def test_06_model_training_and_serialization(self):
        """Tests unsupervised Isolation Forest training and scoring pipeline."""
        # Create a synthetic dataset of 150 rows
        np.random.seed(42)
        n = 150
        df_pd = pd.DataFrame({
            "kwh": np.random.exponential(0.05, n),
            "voltage": np.random.normal(230, 8, n),
            "current": np.random.exponential(1.0, n),
            "frequency": np.random.normal(50.0, 0.1, n),
            "hour": np.random.randint(0, 24, n),
            "dayofweek": np.random.randint(1, 8, n),
            "kwh_zscore": np.random.normal(0, 1, n),
            "kwh_diff": np.random.normal(0, 0.02, n),
            "volt_dev": np.random.exponential(5, n),
            "meter_id": ["MH01"] * n,
            "is_rule_anomaly": [False] * (n - 5) + [True] * 5,
            "timestamp": pd.date_range("2021-01-01", periods=n, freq="3min")
        })

        spark_df = self.spark.createDataFrame(df_pd)
        iso_model, scaler, meta = train_isolation_forest(spark_df, config=self.config)

        self.assertIsNotNone(iso_model)
        self.assertIsNotNone(scaler)
        self.assertIn("saved_model_path", meta)
        self.assertTrue(os.path.exists(meta["saved_model_path"]))

        # Test Scoring
        scored_df = score_dataframe(spark_df, iso_model, scaler, config=self.config)
        self.assertIn("ml_anomaly_score", scored_df.columns)
        self.assertIn("is_ml_anomaly", scored_df.columns)
        self.assertIn("agreement_type", scored_df.columns)
        self.assertEqual(scored_df.count(), n)


if __name__ == "__main__":
    unittest.main()
