"""
GridSense: Apache Spark Initialization and Diagnostics Module
Author: Aditya Raj (INT315 Cluster Computing)
Description: Robust SparkSession initialization tailored for Windows, PySpark 4.2.0,
Java 17, and local/cluster computing environments. Handles py4j and worker paths safely.
"""

import os
import sys
import platform
import subprocess
import logging
from typing import Optional, Dict, Any

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("GridSense.SparkSetup")


def configure_environment_variables() -> Dict[str, str]:
    """
    Ensures environment variables are appropriately set for PySpark on Windows.
    Specifically guarantees worker processes use current Python executable
    and PySpark points to its own verified internal jar distribution.
    """
    import pyspark
    pyspark_home = os.path.dirname(pyspark.__file__)

    # Set SPARK_HOME to pyspark's own package directory to ensure binary/jar parity
    os.environ["SPARK_HOME"] = pyspark_home
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    # Check HADOOP_HOME if available
    hadoop_home = os.environ.get("HADOOP_HOME", "C:\\hadoop")
    if not os.environ.get("HADOOP_HOME") and os.path.exists(hadoop_home):
        os.environ["HADOOP_HOME"] = hadoop_home

    env_info = {
        "PYTHON_EXECUTABLE": sys.executable,
        "PYTHON_VERSION": platform.python_version(),
        "PYSPARK_VERSION": pyspark.__version__,
        "SPARK_HOME": os.environ["SPARK_HOME"],
        "JAVA_HOME": os.environ.get("JAVA_HOME", "Not Explicitly Set"),
        "HADOOP_HOME": os.environ.get("HADOOP_HOME", "Not Set"),
        "OS_PLATFORM": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
    }
    return env_info


def verify_java() -> bool:
    """Verifies that Java runtime is accessible and returns version."""
    try:
        result = subprocess.run(
            ["java", "-version"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info("Java Runtime Verified: %s", result.stderr.splitlines()[0] if result.stderr else "OK")
        return True
    except Exception as e:
        logger.error("Java verification failed: %s", e)
        return False


def get_spark_session(
    app_name: str = "GridSense_Cluster_Computing",
    master: str = "local[*]",
    driver_memory: str = "4g",
    shuffle_partitions: int = 8,
    extra_configs: Optional[Dict[str, str]] = None
):
    """
    Creates or retrieves an active SparkSession with optimized cluster/local parameters.
    """
    env_info = configure_environment_variables()
    logger.info("Configuring SparkSession with environment:")
    for k, v in env_info.items():
        logger.info("  %s = %s", k, v)

    from pyspark.sql import SparkSession

    builder = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.driver.memory", driver_memory) \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .config("spark.driver.host", "127.0.0.1") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .config("spark.pyspark.python", sys.executable) \
        .config("spark.pyspark.driver.python", sys.executable) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.ui.enabled", "true") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")

    if extra_configs:
        for k, v in extra_configs.items():
            builder = builder.config(k, v)

    try:
        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        logger.info("SparkSession successfully initialized! Spark Version: %s", spark.version)
        logger.info("Spark Master: %s | App ID: %s", spark.sparkContext.master, spark.sparkContext.applicationId)
        return spark
    except Exception as e:
        logger.critical("Failed to create SparkSession: %s", e, exc_info=True)
        raise RuntimeError(
            f"Spark initialization failed. Verify Java 17 and PySpark configuration. Details: {e}"
        ) from e


def stop_spark_session(spark) -> None:
    """Safely closes an active SparkSession."""
    if spark is not None:
        try:
            app_id = spark.sparkContext.applicationId
            spark.stop()
            logger.info("SparkSession (App ID: %s) stopped cleanly.", app_id)
        except Exception as e:
            logger.warning("Error while stopping SparkSession: %s", e)


if __name__ == "__main__":
    print("=" * 70)
    print(" GridSense: Spark Environment Diagnostic Tool ")
    print("=" * 70)
    java_ok = verify_java()
    if not java_ok:
        print("[ERROR] Java is missing or misconfigured.")
        sys.exit(1)

    spark = get_spark_session()
    test_df = spark.createDataFrame([
        (1, "Bareilly", 230.5, 50.01),
        (2, "Mathura", 228.2, 49.98)
    ], ["id", "location", "voltage", "frequency"])
    print("\n--- Diagnostic DataFrame Test ---")
    test_df.show()
    print("Count verification:", test_df.count())
    stop_spark_session(spark)
    print("\n[SUCCESS] Spark environment fully functional and verified!")
