# GridSense: Electricity Consumption Anomaly Detection Using Big Data and Machine Learning

**INT315 Cluster Computing Capstone Project**  
**Author:** Aditya Raj  
**Institution:** Lovely Professional University, School of Computer Science & Engineering  
**Dataset:** CEEW Smart Meter Telemetry (Mathura & Bareilly, Uttar Pradesh, India) — Harvard Dataverse  
**Technologies:** Apache Spark 4.2.0, PySpark, Java 17, Python 3.14.6, Scikit-Learn, Streamlit, Plotly, ReportLab

---

## 📖 Project Overview
GridSense is a complete big data and machine learning engineering system designed to ingest, clean, feature-engineer, and detect anomalies across **21.39+ million high-frequency (3-minute interval) smart-meter electricity readings** collected from residential households in Mathura and Bareilly, Uttar Pradesh.

The system addresses critical challenges in power distribution surveillance:
- **Big Data Scale:** Processes gigabyte-scale time series using Apache Spark without driver Out-Of-Memory (OOM) crashes.
- **Dual Detection Architecture:**
  - **Method A (Rule-Based Detection):** Evaluates physical and statutory boundaries based on the **Indian Electricity Grid Code (IEGC)**, flagging negative consumption, severe overvoltage ($>280\text{V}$), brownout sags ($<160\text{V}$), frequency violations ($<48.5\text{ Hz}$ or $>51.5\text{ Hz}$), current overloads ($>35\text{A}$), and zero-voltage tampering bypasses.
  - **Method B (Unsupervised Machine Learning):** Fits an **Isolation Forest** ensemble on representative distributed samples (250,000 stratified observations) and scores records partition-wise via PySpark's vectorized `mapInPandas` API.
- **Synthesis & Agreement Analysis:** Computes unsupervised agreement metrics (Jaccard similarity, overlap coefficient) and identifies high-confidence anomalous events where physical boundary violations coincide with multi-dimensional statistical rarity.
- **Interactive Analytics Dashboard:** Multi-page Streamlit and Plotly dashboard providing live spatial/temporal filtering, meter micro-trace visualization, and customized CSV downloads.
- **Academic Submission Report:** One complete, professional, 25-page PDF report (`report/GridSense_INT315_Project_Report.pdf`) covering all 12 required INT315 sections.

---

## 📁 Repository Directory Structure

```text
GridSense/
├── README.md                           # Master execution guide & documentation
├── requirements.txt                    # Python package dependencies
├── config/
│   └── config.yaml                     # Central configuration (paths, Spark settings, thresholds)
├── data/                               # Cleaned and engineered feature storage
├── src/
│   ├── spark_setup.py                  # Windows-optimized SparkSession initializer & diagnostics
│   ├── inspect_data.py                 # Dataset discovery, schema validation, and audit script
│   ├── load_data.py                    # PySpark multi-file ingestion & schema standardization
│   ├── clean_data.py                   # Data quality audit, null checks, and deduplication
│   ├── feature_engineering.py          # Distributed Window lags, rolling stats, and Z-scores
│   ├── rule_based_detection.py         # Method A: IEGC & electrical domain rule engine
│   ├── train_model.py                  # Method B: Isolation Forest training & mapInPandas scoring
│   ├── evaluate_results.py             # Agreement analysis, Jaccard metrics, and summary exports
│   ├── visualize_results.py            # Generates 8 high-resolution 300 DPI publication graphics
│   ├── generate_evidence.py            # Generates architecture, workflow, and terminal evidence
│   └── run_pipeline.py                 # Master end-to-end distributed pipeline orchestrator
├── dashboard/
│   └── app.py                          # Interactive Streamlit & Plotly analytics dashboard
├── tests/
│   └── test_pipeline.py                # Automated PySpark and ML unit test suite (6 tests)
├── models/
│   ├── isolation_forest_model.joblib   # Serialized trained Isolation Forest model
│   ├── robust_scaler.joblib            # Serialized fitted RobustScaler
│   └── model_metadata.json             # Model training parameters and feature dictionary
├── outputs/
│   ├── summaries/                      # JSON audits and CSV summary distributions
│   ├── anomalies/                      # Exported top anomalous records table
│   ├── charts/                         # 8 publication-grade PNG graphics
│   └── logs/                           # Pipeline wall-clock execution benchmark logs
├── screenshots/                        # Architecture diagrams and PowerShell execution evidence
└── report/
    ├── report_source.md                # Markdown source of the academic report
    ├── generate_pdf_report.py          # Programmatic ReportLab PDF compilation script
    └── GridSense_INT315_Project_Report.pdf # Final submission-ready academic report PDF
```

---

## ⚙️ Environment Prerequisites

- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Python Version:** Python 3.10 to 3.14 (Verified on Python 3.14.6)
- **Java Runtime:** Java 17 LTS (Verified on JDK 17.0.12)
- **Apache Spark / PySpark:** PySpark 4.2.0 (or 3.5.x)
- **Dataset Path:** `C:\Users\Adity\Downloads\dataverse_files` (Configurable in `config/config.yaml`)

> **Note on Windows Spark Setup:** GridSense's `src/spark_setup.py` automatically resolves the common `TypeError: 'JavaPackage' object is not callable` and `Cannot run program "python3"` errors by dynamically binding `SPARK_HOME` to PySpark's verified internal jar distribution and setting `PYSPARK_PYTHON` to the exact active Python executable.

---

## 🚀 Step-by-Step Execution Guide (PowerShell)

### Step 1: Navigate to Project Directory
Open **Windows PowerShell** and navigate to the project directory:
```powershell
cd C:\Users\Adity\.gemini\antigravity\scratch\GridSense
```

### Step 2: Install Required Dependencies
Install the required packages using pip:
```powershell
pip install -r requirements.txt
```

### Step 3: Run Environment Diagnostics & Verify Spark Startup
Execute the diagnostics tool to verify Java, Python, and PySpark compatibility:
```powershell
python src/spark_setup.py
```
*Expected Output:* Prints Java version, Python executable, environment variables, creates a test DataFrame, and outputs `[SUCCESS] Spark environment fully functional and verified!`.

### Step 4: Run Automated Test Suite
Run the 6 automated unit tests validating schema casting, deduplication, feature causality, rule evaluation, and Isolation Forest serialization:
```powershell
python tests/test_pipeline.py
```
*Expected Output:* `Ran 6 tests in ~38s ... OK`.

### Step 5: Run Dataset Discovery & Schema Inspection
Inspect all 8 CSV files in the dataverse folder and generate the discovery report:
```powershell
python src/inspect_data.py
```
*Output Generated:*
- `outputs/summaries/data_discovery_report.json`
- `outputs/summaries/dataset_summary_table.csv`

### Step 6: Execute the Master Distributed Pipeline
Run the complete end-to-end pipeline. You can run on a representative scaled sample (e.g. 2% ~ 428,000 records for fast 2-minute execution) or on the full 21+ million dataset:

**Fast Representative Benchmark (Recommended for Testing):**
```powershell
python src/run_pipeline.py --sample_fraction 0.02
```

**Full Dataset Execution (All 21.39 Million Records):**
```powershell
python src/run_pipeline.py
```
*Stages Executed:*
1. Data Ingestion & Schema Standardization
2. Data Quality Audit & Deduplication
3. Distributed Feature Engineering (Window lags, rolling stats, Z-scores)
4. Method A: Rule-Based Anomaly Detection
5. Method B: Isolation Forest Training & Serialization
6. Distributed Anomaly Scoring via `mapInPandas`
7. Agreement Analysis (Jaccard similarity index, overlap coefficient)
8. High-Resolution Graphics Generation (All 8 PNG charts)

### Step 7: Launch the Interactive Dashboard
Launch the interactive Streamlit analytics dashboard:
```powershell
streamlit run dashboard/app.py
```
Open your web browser and navigate to: `http://localhost:8501`.

### Step 8: Compile the Academic PDF Report
Generate the final publication-ready academic PDF report:
```powershell
python report/generate_pdf_report.py
```
*Report Output:* `report/GridSense_INT315_Project_Report.pdf` (3.90 MB, ~25 pages).

---

## 📓 Jupyter Notebook Execution Guide

If running within a Jupyter Notebook environment, execute the following commands in sequential cells:

### Cell 1: Environment Diagnostics
```python
import sys, os
from pathlib import Path

# Set working directory to GridSense root
os.chdir(r"C:\Users\Adity\.gemini\antigravity\scratch\GridSense")
sys.path.insert(0, "src")

from spark_setup import get_spark_session, stop_spark_session
spark = get_spark_session(app_name="GridSense_Jupyter", master="local[*]")
print("Spark Session Active! Version:", spark.version)
```

### Cell 2: Dataset Discovery & Audit
```python
from inspect_data import inspect_files
inspect_files()
```

### Cell 3: Ingestion & Feature Engineering
```python
from load_data import load_high_frequency_data
from clean_data import audit_and_clean_data
from feature_engineering import build_features

# Ingest representative sample
raw_df = load_high_frequency_data(spark, sample_fraction=0.02)
clean_df, audit = audit_and_clean_data(raw_df)
feat_df = build_features(clean_df)
feat_df.show(5)
```

### Cell 4: Dual Anomaly Detection (Rules + ML)
```python
from rule_based_detection import apply_rule_based_detection
from train_model import train_isolation_forest, score_dataframe

rule_df, rule_metrics = apply_rule_based_detection(feat_df)
model, scaler, meta = train_isolation_forest(rule_df)
scored_df = score_dataframe(rule_df, model, scaler)
scored_df.select("timestamp", "meter_id", "kwh", "is_rule_anomaly", "is_ml_anomaly", "agreement_type").show(10)
```

### Cell 5: Evaluation & Chart Generation
```python
from evaluate_results import evaluate_anomalies
from visualize_results import generate_all_visualizations

eval_summary = evaluate_anomalies(scored_df)
generate_all_visualizations()
print("Agreement Analysis:", eval_summary["agreement_analysis"])
```

### Cell 6: Clean Shutdown
```python
stop_spark_session(spark)
print("SparkSession stopped cleanly.")
```

---

## 📊 Summary of Experimental Results

| Metric / Dimension | Quantitative Value | Operational Interpretation |
|---|---|---|
| **Raw Telemetry Population** | 21,394,429 records (995.1 MB) | 6 high-frequency files covering Mathura & Bareilly (2019–2021) |
| **Evaluated Telemetry Sample** | 428,625 records | Statistically representative sample across all 84 meters |
| **Method A (Rule-Based Anomalies)** | 40,104 records (9.36%) | High-voltage surges ($>280\text{V}$), frequency excursions, and spikes |
| **Method B (Isolation Forest ML)** | 8,573 records (2.00%) | Multi-dimensional non-linear behavioral outliers |
| **High-Confidence Intersection ($A \cap B$)** | **4,290 records (1.00%)** | Severe disturbances flagged simultaneously by physics and ML |
| **Total Flagged Union ($A \cup B$)** | 44,387 records (10.36%) | Comprehensive anomaly coverage |
| **Jaccard Similarity Index** | 0.0969 | Unsupervised agreement index |
| **Overlap Coefficient** | 0.5003 | 50.0% of ML detections coincided with hard physical grid violations |
| **End-to-End Pipeline Runtime** | 122.57 seconds | High-throughput distributed processing on local multi-core Spark |

---

## 📑 Generated Publication Visualizations

All 8 figures are saved in `outputs/charts/` at 300 DPI:
1. `1_dataset_overview.png`: Records processed by partition & geographic split.
2. `2_consumption_trends.png`: 24-hour diurnal profile & seasonal monthly demand.
3. `3_electrical_parameters.png`: Voltage, frequency, current, and ML score distributions.
4. `4_anomaly_distribution_by_rule.png`: Frequency breakdown of triggered engineering rules.
5. `5_rule_vs_ml_comparison.png`: Agreement synthesis bar chart and metric callout box.
6. `6_anomalies_by_meter.png`: Top 12 smart meters ranked by anomaly incidence.
7. `7_hourly_anomaly_patterns.png`: Hourly vulnerability curve across the 24-hour cycle.
8. `8_anomaly_case_study.png`: High-resolution micro-trace of a co-occurring power spike, voltage sag, and current surge.

---

## 📜 Academic Integrity and Course Requirements
- **Course:** INT315 (Cluster Computing)
- **Academic Report:** The complete report is compiled in `report/GridSense_INT315_Project_Report.pdf` with all 12 required sections, cover page, table of contents, diagrams, figure captions, actual execution screenshots, quantitative evaluation, and complete source code appendices.
- **Data Ground Truth Policy:** In accordance with academic best practices, precision, recall, and ROC-AUC are not fabricated because real-world open utility datasets lack verified ground-truth theft labels. Unsupervised agreement analysis and physical rule cross-validation are utilized instead.
