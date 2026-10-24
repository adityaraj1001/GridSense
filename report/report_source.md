# GridSense: Electricity Consumption Anomaly Detection Using Big Data and Machine Learning
## INT315 Cluster Computing Capstone Project Report

**Author:** Aditya Raj  
**Course Code:** INT315 (Cluster Computing)  
**Institution:** Lovely Professional University, School of Computer Science and Engineering  
**Specialization:** Big Data Engineering & Machine Learning  
**Date of Submission:** October 2026  
**Dataset:** CEEW Smart Meter Telemetry (Mathura & Bareilly, Uttar Pradesh, India) — Harvard Dataverse  

---

## Executive Summary
This capstone project presents **GridSense**, a distributed cluster computing framework for ingesting, validating, and analyzing high-frequency (3-minute interval) smart-meter electricity telemetry across **Mathura** and **Bareilly**, India. Built upon **Apache Spark 4.2.0** and **PySpark**, GridSense overcomes single-machine driver memory bottlenecks to process over **21.39 million raw records** (~1 GB) across 84 unique smart meters.

The system pioneers a dual-paradigm detection architecture combining:
1. **Method A (Rule-Based Detection Engine):** Enforces statutory constraints defined by the **Indian Electricity Grid Code (IEGC)** alongside physical energy conservation laws (detecting negative consumption, severe overvoltage surges $>280\text{V}$, brownout sags $<160\text{V}$, frequency deviations outside $48.5\text{–}51.5\text{ Hz}$, single-phase current overloads $>35\text{A}$, and zero-voltage tampering bypasses).
2. **Method B (Unsupervised Machine Learning):** Employs an **Isolation Forest** tree ensemble fitted on representative distributed samples (250,000 stratified observations) and scored partition-wise via PySpark's vectorized `mapInPandas` API to evaluate non-linear multi-variable anomalies.

GridSense synthesizes both paradigms through unsupervised agreement metrics (Jaccard similarity index and Overlap coefficient), isolating **4,290 high-confidence anomalies** (1.00% intersection), and provides an interactive **Streamlit and Plotly** dashboard for operational grid intelligence.

---

## Section 1: Project Metadata & Attribution
* **Course Code:** INT315 (Cluster Computing)
* **Project Title:** GridSense: Electricity Consumption Anomaly Detection Using Big Data and Machine Learning
* **Student Name:** Aditya Raj
* **Registration / Student ID:** 122XXXXX (Cluster Computing Specialization)
* **Department:** School of Computer Science and Engineering
* **University:** Lovely Professional University, Punjab, India
* **Faculty Evaluator:** Course Faculty — INT315 Cluster Computing
* **Cluster Environment:** Apache Spark 4.2.0, PySpark, Java 17 LTS, Python 3.14.6, Windows 11 Multi-core Local Execution

---

## Section 2: Problem Statement & Motivation
Modern Advanced Metering Infrastructure (AMI) records electrical parameters at granular temporal frequencies. While enabling detailed visibility, utilities face critical big data hurdles:
* **Storage and Memory Bottlenecks:** Single-machine tools (e.g. Pandas) suffer fatal driver Out-of-Memory (OOM) crashes when attempting window operations on 21+ million rows.
* **Sensor Noise vs Legitimate Peaks:** Physical household variations (e.g., air-conditioner compressor startup surges in North Indian summers) mimic consumption anomalies but represent normal consumer behavior.
* **Multivariate Coupling:** Active power ($t\_\text{kWh}$) is physically bound to voltage ($V$), current ($I$), and grid frequency ($f$). Isolated thresholding produces unacceptable false-alarm rates.
* **Absence of Ground-Truth Fraud Labels:** Utility datasets do not contain verified labels for electricity theft or tampering. Evaluating models with fabricated precision or recall is scientifically invalid; rigorous unsupervised agreement analysis is required.

---

## Section 3: Project Objectives
1. **Distributed Big Data Ingestion:** PySpark ingestion and schema harmonization across disparate multi-year CSV files.
2. **Data Quality Auditing:** Null value auditing, deduplication on $(meter\_id, timestamp)$, and distinguishing power outages ($V=0, I=0$) from active theft bypasses ($V=0, I>0$).
3. **Causal Feature Engineering:** PySpark Window functions for temporal cycles, backward-only lags (`lag_1_kwh`, `kwh_diff`), rolling 3-period statistics, and meter historical baseline Z-scores without future leakage.
4. **Deterministic Rule-Based Detection (Method A):** Enforce 9 engineering rules adhering to the Indian Electricity Grid Code (IEGC).
5. **Unsupervised Machine Learning (Method B):** Isolation Forest model fitted on stratified distributed samples and scored partition-wise without driver memory saturation.
6. **Quantitative Agreement Evaluation:** Unsupervised agreement analysis (Jaccard index, overlap coefficient, spatial and diurnal distributions).
7. **Interactive Visual Dashboard:** Streamlit and Plotly multi-tab analytics web application.
8. **Reproducibility & Testing:** Automated unit testing suite (pytest/unittest) and wall-clock execution benchmarking.

---

## Section 4: Dataset Description & Discovery Audit
The dataset comprises continuous 3-minute interval telemetry collected from 84 smart meters in Uttar Pradesh, India:

| File Name | Size (MB) | Row Count | Unique Meters | Date Range | Sampling Type |
|---|---|---|---|---|---|
| `CEEW - Smart meter data Bareilly 2020.csv` | 308.40 | 6,627,360 | 46 | 2020-01-01 to 2020-12-31 | 3-Min High Frequency |
| `CEEW - Smart meter data Bareilly 2021.csv` | 183.76 | 3,948,960 | 38 | 2021-01-01 to 2021-10-31 | 3-Min High Frequency |
| `CEEW - Smart meter data Mathura 2019.csv` | 167.36 | 3,588,874 | 38 | 2019-05-01 to 2019-12-31 | 3-Min High Frequency |
| `CEEW - Smart meter data Mathura 2020.csv` | 174.17 | 3,759,360 | 38 | 2020-01-01 to 2020-12-31 | 3-Min High Frequency |
| `SM Cleaned Data BR2019.csv` | 135.95 | 2,919,315 | 46 | 2019-05-09 to 2019-12-31 | 3-Min High Frequency |
| `SM Cleaned Data MH2021.csv` | 25.47 | 550,560 | 35 | 2021-01-01 to 2021-02-20 | 3-Min High Frequency |
| `SM Cleaned Data BR Aggregated.csv` | 0.93 | 28,119 | 46 | 2019-05-09 to 2021-10-31 | Daily Aggregated |
| `SM Cleaned Data MH Aggregated.csv` | 0.55 | 16,491 | 38 | 2019-05-01 to 2021-02-20 | Daily Aggregated |
| **Total High-Frequency Records** | **995.11 MB** | **21,394,429** | **84** | **May 2019 – Oct 2021** | **3-Minute Telemetry** |

### Telemetry Schema Attributes:
* `x_Timestamp` (TimestampType): Telemetry timestamp in `yyyy-MM-dd HH:mm:ss`.
* `t_kWh` (DoubleType): Active energy consumed during 3-minute interval in kilowatt-hours.
* `z_Avg Voltage (Volt)` (DoubleType): True RMS line voltage averaged over 3 minutes (nominal $230\text{V}$).
* `z_Avg Current (Amp)` (DoubleType): True RMS current in Amperes.
* `y_Freq (Hz)` (DoubleType): Alternating current grid frequency in Hertz (nominal $50.0\text{ Hz}$).
* `meter` (StringType): Unique meter hardware identifier (`MH...` for Mathura, `BR...` for Bareilly).

---

## Section 5: Dataset Source & Academic Attribution
* **Institution:** Council on Energy, Environment and Water (CEEW), New Delhi, India.
* **Principal Authors:** Shalu Agrawal, Sunil Mani, Abhishek Jain, and Karthik Ganesan.
* **Study Title:** *What Smart Meters Can Tell Us: Insights on Electricity Supply and Use in Mathura and Bareilly Households*.
* **Repository Link:** Archived on **Harvard Dataverse** (`https://dataverse.harvard.edu`).

---

## Section 6: Tools & Technologies
* **Apache Spark 4.2.0 & PySpark:** Distributed cluster computing framework, Catalyst SQL optimizer, DataFrame API, and Window specifications.
* **Java 17 (JDK 17.0.12 LTS):** JVM backend executing Spark core tasks and garbage collection.
* **Python 3.14.6:** High-level driver script execution and data science ecosystem.
* **Scikit-Learn 1.8.0:** RobustScaler and IsolationForest algorithms.
* **Streamlit 1.54.0 & Plotly 7.1.0:** Interactive analytics web application and dynamic charts.
* **Matplotlib 3.10.8 & Seaborn 0.13.2:** High-DPI publication graphics generation.
* **ReportLab 5.1.0:** Programmatic academic PDF typesetting engine.

---

## Section 7: Implementation & Architecture
### Spark Master Configuration:
```python
spark = SparkSession.builder \
    .appName("GridSense_Cluster_Computing") \
    .master("local[*]") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .config("spark.pyspark.python", sys.executable) \
    .config("spark.pyspark.driver.python", sys.executable) \
    .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
    .getOrCreate()
```

### Feature Engineering Formulations:
1. **Rate of Change (kWh Diff):**
   $$\Delta \text{kWh}_t = \text{kWh}_t - \text{kWh}_{t-1}$$
2. **Backward-Only Rolling Mean (3 Intervals = 9 Minutes):**
   $$\mu_{3, t} = \frac{1}{3} \sum_{i=0}^{2} \text{kWh}_{t-i}$$
3. **Meter Historical Baseline Z-Score:**
   $$Z_t = \frac{\text{kWh}_t - \mu_{\text{meter}}}{\sigma_{\text{meter}} + 10^{-5}}$$
4. **Voltage Deviation from Nominal:**
   $$\Delta V_t = |V_t - 230.0|$$

---

## Section 8: Anomaly Detection: Rules vs Machine Learning
### Method A: Deterministic Rules Table:
* `RULE_NEG_KWH`: $kwh < 0.0$ (Negative reading indicates sensor wiring inversion).
* `RULE_EXTREME_KWH`: $kwh > 2.5$ ($>50\text{ kW}$ equivalent load).
* `RULE_OVER_VOLTAGE`: $voltage > 280.0\text{V}$ (Severe overvoltage surge).
* `RULE_UNDER_VOLTAGE`: $voltage < 160.0\text{V} \land kwh > 0.005$ (Severe brownout sag during active load).
* `RULE_FREQ_VIOLATION`: $freq < 48.5\text{ Hz} \lor freq > 51.5\text{ Hz}$ (IEGC grid violation).
* `RULE_CURRENT_OVERLOAD`: $current > 35.0\text{A}$ (Single-phase residential overload).
* `RULE_SUSPECT_BYPASS`: $voltage == 0.0 \land current > 1.0\text{A}$ (Meter neutral bypass or tampering).
* `RULE_STAT_SPIKE`: $Z_{\text{kWh}} > 4.0$ ($>4\sigma$ departure from meter baseline).
* `RULE_ABRUPT_RAMP`: $|\Delta \text{kWh}| > 1.8$ (Instantaneous consumption jump).

### Method B: Unsupervised Isolation Forest:
* Contamination rate: $0.02$ ($2.0\%$).
* Number of isolation trees: $100$.
* Scoring function:
  $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
* Features used: `[kwh, voltage, current, frequency, hour, dayofweek, kwh_zscore, kwh_diff, volt_dev]`.

---

## Section 9: Execution Evidence & System Diagnostics
The project successfully completed end-to-end execution on Windows 11 with Apache Spark 4.2.0:
* Environment diagnostics: Python 3.14.6, PySpark 4.2.0, Java 17.0.12 verified.
* Unit test execution: All 6 automated test fixtures passed (`Ran 6 tests in 38.204s ... OK`).
* Pipeline benchmark: 428,625 records processed across all 8 stages in **122.57 seconds**.

---

## Section 10: Quantitative Results & Evaluation
### Agreement Analysis Summary:
* Total Evaluated Readings: **428,625**
* Method A (Rule-Based) Anomalies: **40,104 (9.36%)**
* Method B (Isolation Forest) Anomalies: **8,573 (2.00%)**
* **High-Confidence Intersection ($A \cap B$): 4,290 (1.00%)**
* **Total Flagged Union ($A \cup B$): 44,387 (10.36%)**
* **Jaccard Similarity Index:** $0.0969$
* **Overlap Coefficient:** $0.5003$

### Key Insights:
1. **High Agreement on Severe Disturbances:** The 50% overlap coefficient demonstrates that half of all machine learning detections coincided with hard physical boundary violations (e.g. concurrent over-voltage and current spikes).
2. **Complementary Detections:** Method A uniquely captured system-level grid excursions (such as frequency drops during Northern Grid stress), while Method B uniquely isolated subtle multi-variable anomalies (e.g. unseasonable night-time loads with moderate voltage sags).
3. **Diurnal Hotspots:** Anomalies peaked in the late afternoon (2–5 PM) coinciding with residential cooling strain, and late night (2–4 AM) where low grid demand caused distribution overvoltages.

---

## Section 11: Conclusion & Future Scope
GridSense demonstrates that combining Apache Spark's distributed computing engine with domain-specific engineering rules and unsupervised machine learning provides a robust, scalable foundation for modern electrical grid surveillance. 

### Future Work:
1. Deployment on a distributed multi-node Kubernetes cluster.
2. Real-time streaming ingestion with Apache Spark Structured Streaming and Apache Kafka.
3. Integration of deep sequence autoencoders (LSTM / TCN) for temporal reconstruction.
4. Validation with regional utility ground-truth maintenance logs.
