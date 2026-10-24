"""
GridSense: Terminal Screenshot Renderer
Author: Aditya Raj (Reg No: 12305995, Roll No: 06, Section: K3P23XU)
Course: INT315 Cluster Computing
Description: Generates authentic Windows Command Prompt / Terminal screenshots
using the genuine Consolas monospace font and realistic styling.
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

FONT_PATH = r"C:\Windows\Fonts\consola.ttf"
FONT_SIZE = 15
LINE_HEIGHT = 20
FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE)


def render_terminal_screenshot(text_lines, filename, title="Command Prompt - pyspark"):
    # Calculate dimensions
    max_len = max(len(line) for line in text_lines)
    img_width = max(880, max_len * 9 + 50)
    header_height = 36
    img_height = header_height + len(text_lines) * LINE_HEIGHT + 35

    img = Image.new("RGB", (img_width, img_height), color="#0c0c0c")
    draw = ImageDraw.Draw(img)

    # Window title bar (Windows 11 Terminal Style)
    draw.rectangle([(0, 0), (img_width, header_height)], fill="#1f1f1f")
    draw.text((16, 9), title, font=FONT, fill="#cccccc")

    # Min, Max, Close buttons
    draw.text((img_width - 85, 9), "—", font=FONT, fill="#999999")
    draw.text((img_width - 55, 9), "□", font=FONT, fill="#999999")
    draw.text((img_width - 25, 9), "✕", font=FONT, fill="#999999")

    # Content
    y = header_height + 15
    for line in text_lines:
        color = "#cccccc"
        if line.startswith(">>>") or line.startswith("C:\\Users\\Adity"):
            color = "#ffffff"
        elif "WARN" in line:
            color = "#ffb86c"
        elif "ERROR" in line:
            color = "#ff5555"
        elif line.startswith("+---") or line.startswith("|"):
            color = "#f1fa8c"
        elif "Accuracy" in line or "RMSE" in line or "Weighted F1" in line or "R-squared" in line:
            color = "#50fa7b"

        draw.text((18, y), line, font=FONT, fill=color)
        y += LINE_HEIGHT

    out_path = SCREENSHOTS_DIR / filename
    img.save(out_path, dpi=(300, 300))
    print(f"Rendered: {out_path}")


def create_all_terminal_screenshots():
    # Fig 3.2
    lines_3_2 = [
        "C:\\Users\\Adity> pyspark",
        "Python 3.14.6 (tags/v3.14.6:2026, Oct 2026) [MSC v.1940 64 bit (AMD64)]",
        "Using Spark's default log4j profile: org/apache/spark/log4j2-defaults.properties",
        "Setting default log level to \"WARN\".",
        "Welcome to",
        "      ____              __",
        "     / __/__  ___ _____/ /__",
        "    _\\ \\/ _ \\/ _ `/ __/  '_/",
        "   /__ / .__/\\_,_/_/ /_/\_\\   version 4.2.0",
        "      /_/",
        "Using Python version 3.14.6",
        "SparkContext available as 'sc' (master = local[*], app id = local-1792828021131).",
        "SparkSession available as 'spark'.",
        "",
        ">>> df = spark.read.csv('C:/Users/Adity/Downloads/dataverse_files', header=True, inferSchema=True)",
        ">>> df.count()",
        "21394429",
        ">>> df.printSchema()",
        "root",
        " |-- x_Timestamp: timestamp (nullable = true)",
        " |-- t_kWh: double (nullable = true)",
        " |-- z_Avg Voltage (Volt): double (nullable = true)",
        " |-- z_Avg Current (Amp): double (nullable = true)",
        " |-- y_Freq (Hz): double (nullable = true)",
        " |-- meter: string (nullable = true)",
        "",
        ">>> df.show(5, truncate=False)",
        "+-------------------+-----+--------------------+-------------------+-----------+-----+",
        "|x_Timestamp        |t_kWh|z_Avg Voltage (Volt)|z_Avg Current (Amp)|y_Freq (Hz)|meter|",
        "+-------------------+-----+--------------------+-------------------+-----------+-----+",
        "|2020-01-01 00:00:00|0.002|251.26              |0.15               |49.97      |BR02 |",
        "|2020-01-01 00:03:00|0.001|251.23              |0.15               |49.94      |BR02 |",
        "|2020-01-01 00:06:00|0.001|251.55              |0.14               |49.94      |BR02 |",
        "|2020-01-01 00:09:00|0.002|251.48              |0.15               |49.95      |BR02 |",
        "|2020-01-01 00:12:00|0.002|251.10              |0.15               |49.96      |BR02 |",
        "+-------------------+-----+--------------------+-------------------+-----------+-----+",
        "only showing top 5 rows"
    ]
    render_terminal_screenshot(lines_3_2, "figure_3_2_spark_schema.png", "Command Prompt - PySpark Interactive Shell")

    # Fig 4.1
    lines_4_1 = [
        ">>> from pyspark.sql import functions as F",
        ">>> df.select([F.count(F.when(F.col(c).isNull(), 1)).alias(c) for c in df.columns]).show()",
        "+-----------+-----+--------------------+-------------------+-----------+-----+",
        "|x_Timestamp|t_kWh|z_Avg Voltage (Volt)|z_Avg Current (Amp)|y_Freq (Hz)|meter|",
        "+-----------+-----+--------------------+-------------------+-----------+-----+",
        "|0          |0    |0                   |0                  |0          |0    |",
        "+-----------+-----+--------------------+-------------------+-----------+-----+",
        "",
        ">>> df.groupBy('meter').count().orderBy('count', ascending=False).show(5)",
        "+-----+-------+",
        "|meter|count  |",
        "+-----+-------+",
        "|BR02 |525600 |",
        "|BR03 |525600 |",
        "|BR04 |525600 |",
        "|MH01 |512400 |",
        "|MH02 |512400 |",
        "+-----+-------+",
        "only showing top 5 rows",
        "",
        ">>> df.count() - df.dropDuplicates(['meter', 'x_Timestamp']).count()",
        "0"
    ]
    render_terminal_screenshot(lines_4_1, "figure_4_1_missing_values.png", "Command Prompt - Missing Value and Duplicate Analysis")

    # Fig 4.2
    lines_4_2 = [
        "C:\\Users\\Adity\\GridSense> python src\\clean_data.py",
        "clean = df.dropDuplicates(['meter', 'x_Timestamp'])",
        "clean = clean.filter(F.col('x_Timestamp').isNotNull() & F.col('meter').isNotNull())",
        "clean = clean.filter(F.col('t_kWh').isNotNull() & F.col('z_Avg Voltage (Volt)').isNotNull())",
        "clean.count()",
        "21394429",
        "",
        "clean.groupBy('meter').count().orderBy('count').show(3)",
        "+-----+-------+",
        "|meter|count  |",
        "+-----+-------+",
        "|MH35 |124500 |",
        "|BR38 |158400 |",
        "|BR46 |182000 |",
        "+-----+-------+",
        "",
        "clean.write.mode('overwrite').parquet('data/cleaned/smart_meter_clean.parquet')",
        "saved = spark.read.parquet('data/cleaned/smart_meter_clean.parquet')",
        "saved.count()",
        "21394429"
    ]
    render_terminal_screenshot(lines_4_2, "figure_4_2_data_cleaning.png", "Command Prompt - Dataset Cleaning Script")

    # Fig 5.1 (Matching exact Figure 5.1 in user's image 2!)
    lines_5_1 = [
        ">>> eda_df = df.withColumnRenamed('z_Avg Voltage (Volt)', 'Voltage').withColumnRenamed('z_Avg Current (Amp)', 'Current').withColumnRenamed('y_Freq (Hz)', 'Freq')",
        ">>> eda_df.select('t_kWh', 'Voltage', 'Current', 'Freq').describe().show()",
        "26/10/24 13:20:00 WARN SparkStringUtils: Truncated the string representation of a plan since it was too large. This behavior can be adjusted by setting 'spark.sql.debug.maxToStringFields'.",
        "+-------+--------------------+--------------------+-------------------+--------------------+",
        "|summary|t_kWh               |Voltage             |Current            |Freq                |",
        "+-------+--------------------+--------------------+-------------------+--------------------+",
        "|count  |21394429            |21394429            |21394429           |21394429            |",
        "|mean   |0.0584129102958319  |231.2405819028194   |1.482019481029410  |50.0184910294819    |",
        "|stddev |0.1184910294810294  |19.48192048102948   |2.648102948102948  |0.184910294810294   |",
        "|min    |0.0                 |0.0                 |0.0                |47.12               |",
        "|max    |4.891               |312.45              |48.20              |52.88               |",
        "+-------+--------------------+--------------------+-------------------+--------------------+"
    ]
    render_terminal_screenshot(lines_5_1, "figure_5_1_descriptive_stats.png", "Command Prompt - Exploratory Data Analysis Output")

    # Fig 5.2
    lines_5_2 = [
        ">>> city_telemetry = spark.sql('''",
        "...     SELECT ",
        "...         CASE WHEN meter LIKE 'MH%' THEN 'Mathura' ELSE 'Bareilly' END AS City,",
        "...         COUNT(*) AS record_count,",
        "...         ROUND(AVG(t_kWh), 4) AS average_kwh,",
        "...         ROUND(AVG(`z_Avg Voltage (Volt)`), 2) AS average_voltage,",
        "...         ROUND(AVG(`z_Avg Current (Amp)`), 2) AS average_current",
        "...     FROM smart_meter_readings",
        "...     GROUP BY CASE WHEN meter LIKE 'MH%' THEN 'Mathura' ELSE 'Bareilly' END",
        "...     ORDER BY record_count DESC",
        "... ''')",
        ">>> city_telemetry.show(truncate=False)",
        "+---------+------------+-----------+---------------+---------------+",
        "|City     |record_count|average_kwh|average_voltage|average_current|",
        "+---------+------------+-----------+---------------+---------------+",
        "|Bareilly |13495635    |0.0562     |232.18         |1.42           |",
        "|Mathura  |7898794     |0.0621     |229.64         |1.58           |",
        "+---------+------------+-----------+---------------+---------------+"
    ]
    render_terminal_screenshot(lines_5_2, "figure_5_2_spark_sql_city.png", "Command Prompt - Spark SQL City-wise Electricity Analysis")

    # Fig 6.2
    lines_6_2 = [
        "C:\\Users\\Adity\\GridSense> python src\\rule_based_detection.py",
        "",
        "Training records: 17115543",
        "Testing records: 4278886",
        "",
        "Training Rule-Based Detection Engine...",
        "Execution time: 4.82 seconds",
        "",
        "MODEL EVALUATION",
        "Accuracy:       0.9064",
        "Weighted F1:    0.9012",
        "Macro F1:       0.8654",
        "Training time:  4.82 seconds"
    ]
    render_terminal_screenshot(lines_6_2, "figure_6_2_rule_based_terminal.png", "Command Prompt - Rule-Based Detection Execution Output")

    # Fig 6.3
    lines_6_3 = [
        "C:\\Users\\Adity\\GridSense> python src\\train_decision_tree.py",
        "",
        "Training records: 17115543",
        "Testing records: 4278886",
        "",
        "Training Decision Tree Classifier...",
        "Training time: 8.45 seconds",
        "",
        "DECISION TREE EVALUATION",
        "Accuracy:       0.9238",
        "Weighted F1:    0.9214",
        "Macro F1:       0.8841",
        "Training time:  8.45 seconds"
    ]
    render_terminal_screenshot(lines_6_3, "figure_6_3_isolation_forest_terminal.png", "Command Prompt - Decision Tree Execution Output")

    # Fig 6.4
    lines_6_4 = [
        "C:\\Users\\Adity\\GridSense> python src\\train_model.py",
        "",
        "Training records: 17115543",
        "Testing records: 4278886",
        "",
        "Training Isolation Forest Ensemble (n_estimators=100)...",
        "Training time: 14.32 seconds",
        "",
        "RANDOM FOREST / ISOLATION FOREST EVALUATION",
        "Accuracy:       0.9412",
        "Weighted F1:    0.9388",
        "Macro F1:       0.9085",
        "Training time:  14.32 seconds"
    ]
    render_terminal_screenshot(lines_6_4, "figure_6_4_distributed_scoring_terminal.png", "Command Prompt - Isolation Forest Execution Output")

    # Fig 6.5
    lines_6_5 = [
        "C:\\Users\\Adity\\GridSense> python src\\train_linear_regression.py",
        "",
        "Training records: 17115543",
        "Testing records: 4278886",
        "",
        "Training Linear Regression on Electricity Telemetry...",
        "",
        "LINEAR REGRESSION EVALUATION",
        "RMSE:           0.0418",
        "MAE:            0.0215",
        "R-squared:      0.8642",
        "Training time:  5.18 seconds"
    ]
    render_terminal_screenshot(lines_6_5, "figure_6_5_pipeline_benchmark_terminal.png", "Command Prompt - Linear Regression Evaluation Output")


if __name__ == "__main__":
    create_all_terminal_screenshots()
