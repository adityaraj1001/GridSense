"""
GridSense: Machine Learning Anomaly Detection Module (Method B)
Author: Aditya Raj (INT315 Cluster Computing)
Description: Fits an unsupervised Isolation Forest model on a representative distributed sample
from PySpark. Evaluates anomaly scores, serializes trained artifacts, and applies scalable scoring.
"""

import os
import sys
import time
import json
import logging
from typing import Tuple, Dict, Any, List, Optional
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, DoubleType, IntegerType, BooleanType, StringType
)

# Add src to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spark_setup import get_spark_session

logger = logging.getLogger("GridSense.ModelTrainer")


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


FEATURE_COLUMNS = [
    "kwh",
    "voltage",
    "current",
    "frequency",
    "hour",
    "dayofweek",
    "kwh_zscore",
    "kwh_diff",
    "volt_dev"
]


def train_isolation_forest(
    df: DataFrame,
    config: Optional[dict] = None
) -> Tuple[Any, RobustScaler, Dict[str, Any]]:
    """
    Draws a memory-safe representative sample from PySpark, fits a RobustScaler
    and Isolation Forest, and serializes the trained artifacts.
    """
    if config is None:
        config = load_config()

    ml_cfg = config.get("machine_learning", {})
    contamination = ml_cfg.get("contamination", 0.02)
    n_estimators = ml_cfg.get("n_estimators", 100)
    max_samples = ml_cfg.get("max_samples", 512)
    random_state = ml_cfg.get("random_state", 42)
    target_sample_size = ml_cfg.get("sample_size_for_training", 200000)

    models_dir = config["paths"]["models_dir"]
    os.makedirs(models_dir, exist_ok=True)

    start_time = time.time()
    logger.info("Training Isolation Forest Anomaly Detector...")
    logger.info("Features selected: %s", FEATURE_COLUMNS)

    # Calculate sampling fraction to yield ~target_sample_size
    total_count = df.count()
    sample_fraction = min(1.0, max(0.01, target_sample_size / max(total_count, 1)))
    logger.info("Dataset size: %d rows. Sampling fraction: %.4f (target: %d)",
                total_count, sample_fraction, target_sample_size)

    sample_spark_df = df.select(FEATURE_COLUMNS).na.drop().sample(
        fraction=sample_fraction,
        seed=random_state
    )

    # Convert only the representative sample to Pandas for scikit-learn
    sample_pdf = sample_spark_df.limit(target_sample_size).toPandas()
    sample_rows = len(sample_pdf)
    logger.info("Collected representative sample of %d rows for ML training.", sample_rows)

    X = sample_pdf[FEATURE_COLUMNS].values

    # Fit RobustScaler to guard against extreme outliers biasing scale
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # Fit Isolation Forest
    iso_forest = IsolationForest(
        n_estimators=n_estimators,
        max_samples=max_samples,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1
    )
    iso_forest.fit(X_scaled)
    fit_duration = time.time() - start_time

    # Training Diagnostics
    sample_scores = -iso_forest.score_samples(X_scaled)  # higher = more anomalous
    sample_preds = iso_forest.predict(X_scaled)          # -1 is anomaly, 1 is normal
    anomalies_detected_in_sample = int(np.sum(sample_preds == -1))

    logger.info("Isolation Forest fitted in %.2f seconds. Anomalies in sample: %d (%.2f%%)",
                fit_duration, anomalies_detected_in_sample,
                (anomalies_detected_in_sample / sample_rows) * 100)

    # Serialize Model and Scaler
    model_artifact_path = os.path.join(models_dir, "isolation_forest_model.joblib")
    scaler_artifact_path = os.path.join(models_dir, "robust_scaler.joblib")
    joblib.dump(iso_forest, model_artifact_path)
    joblib.dump(scaler, scaler_artifact_path)

    metadata = {
        "model_type": "IsolationForest",
        "contamination": contamination,
        "n_estimators": n_estimators,
        "max_samples": max_samples,
        "random_state": random_state,
        "features": FEATURE_COLUMNS,
        "training_sample_count": sample_rows,
        "training_time_seconds": round(fit_duration, 2),
        "score_min": float(np.min(sample_scores)),
        "score_max": float(np.max(sample_scores)),
        "score_mean": float(np.mean(sample_scores)),
        "score_std": float(np.std(sample_scores)),
        "anomaly_threshold": float(iso_forest.offset_),
        "saved_model_path": model_artifact_path,
        "saved_scaler_path": scaler_artifact_path
    }

    meta_path = os.path.join(models_dir, "model_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Model artifacts and metadata saved to: %s", models_dir)
    return iso_forest, scaler, metadata


def score_dataframe(
    df: DataFrame,
    iso_forest: Any,
    scaler: RobustScaler,
    config: Optional[dict] = None
) -> DataFrame:
    """
    Applies the trained Isolation Forest model to score observations.
    Computes anomaly score, ML prediction label, and agreement category with rule-based flags.
    """
    if config is None:
        config = load_config()

    start_time = time.time()
    logger.info("Scoring dataset with Isolation Forest...")

    # Broadcast or use partition-level mapping for scalable prediction
    # For robust execution across Windows environments, we apply mapInPandas or vectorized scoring
    offset = float(iso_forest.offset_)

    def score_partition(iterator):
        for pdf in iterator:
            if pdf.empty:
                yield pdf
                continue
            # Extract features and fill any remaining nulls
            X_part = pdf[FEATURE_COLUMNS].fillna(0.0).values
            X_scaled_part = scaler.transform(X_part)
            # score_samples: opposite of anomaly score in sklearn (lower = more abnormal)
            # We invert it: higher raw_score = more anomalous
            raw_scores = -iso_forest.score_samples(X_scaled_part)
            preds = iso_forest.predict(X_scaled_part)

            pdf["ml_anomaly_score"] = raw_scores
            pdf["is_ml_anomaly"] = (preds == -1)
            yield pdf

    # Build output schema for mapInPandas without mutating input df.schema
    scored_schema = StructType(
        list(df.schema.fields) + [
            StructField("ml_anomaly_score", DoubleType(), True),
            StructField("is_ml_anomaly", BooleanType(), True)
        ]
    )

    scored_df = df.mapInPandas(score_partition, schema=scored_schema)

    # Define Combined and Agreement classifications
    scored_df = scored_df.withColumn(
        "is_combined_anomaly",
        F.col("is_rule_anomaly") | F.col("is_ml_anomaly")
    ).withColumn(
        "agreement_type",
        F.when(F.col("is_rule_anomaly") & F.col("is_ml_anomaly"), F.lit("BOTH_AGREE"))
         .when(F.col("is_rule_anomaly") & (~F.col("is_ml_anomaly")), F.lit("RULE_ONLY"))
         .when((~F.col("is_rule_anomaly")) & F.col("is_ml_anomaly"), F.lit("ML_ONLY"))
         .otherwise(F.lit("NOMINAL"))
    )

    elapsed = time.time() - start_time
    logger.info("Scoring pipeline prepared in %.2f seconds.", elapsed)
    return scored_df


if __name__ == "__main__":
    from load_data import load_high_frequency_data
    from clean_data import audit_and_clean_data
    from feature_engineering import build_features
    from rule_based_detection import apply_rule_based_detection
    from spark_setup import stop_spark_session

    print("Testing train_model module with 0.001 sample...")
    spark = get_spark_session(app_name="TestTrainModel", shuffle_partitions=4)
    raw_df = load_high_frequency_data(spark, sample_fraction=0.001)
    clean_df, _ = audit_and_clean_data(raw_df)
    feat_df = build_features(clean_df)
    rule_df, _ = apply_rule_based_detection(feat_df)

    model, scaler, meta = train_isolation_forest(rule_df)
    print("Model Metadata:")
    print(json.dumps(meta, indent=2))

    scored_df = score_dataframe(rule_df, model, scaler)
    print("Scored Sample Rows:")
    scored_df.select("timestamp", "meter_id", "kwh", "is_rule_anomaly", "is_ml_anomaly", "agreement_type", "ml_anomaly_score").show(10)
    stop_spark_session(spark)
    print("Train and score test passed!")
