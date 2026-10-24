"""
GridSense: Interactive Smart Meter Anomaly Analytics Dashboard
Course: INT315 Cluster Computing | Author: Aditya Raj
Technology Stack: Streamlit, Plotly, Pandas, NumPy
Description: Visualizes big data smart-meter consumption patterns, electrical parameters,
rule-based detections, and Isolation Forest ML predictions with interactive filters.
"""

import os
import sys
import json
from pathlib import Path
import yaml
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure Streamlit page layout
st.set_page_config(
    page_title="GridSense: Electricity Anomaly Detection",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
OUTPUTS_DIR = BASE_DIR / "outputs"
SUMMARIES_DIR = OUTPUTS_DIR / "summaries"
ANOMALIES_DIR = OUTPUTS_DIR / "anomalies"
CHARTS_DIR = OUTPUTS_DIR / "charts"
LOGS_DIR = OUTPUTS_DIR / "logs"


@st.cache_data
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@st.cache_data
def load_discovery_data():
    summary_path = SUMMARIES_DIR / "dataset_summary_table.csv"
    if summary_path.exists():
        return pd.read_csv(summary_path)
    return pd.DataFrame()


@st.cache_data
def load_eval_summary():
    eval_path = SUMMARIES_DIR / "evaluation_summary.json"
    if eval_path.exists():
        with open(eval_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data
def load_rule_summary():
    rule_path = SUMMARIES_DIR / "rule_based_detection_summary.json"
    if rule_path.exists():
        with open(rule_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data
def load_top_anomalies():
    top_path = ANOMALIES_DIR / "top_anomalies_table.csv"
    if top_path.exists():
        return pd.read_csv(top_path)
    return pd.DataFrame()


@st.cache_data
def load_hourly_distribution():
    h_path = SUMMARIES_DIR / "hourly_anomaly_distribution.csv"
    if h_path.exists():
        return pd.read_csv(h_path)
    return pd.DataFrame()


@st.cache_data
def load_meter_distribution():
    m_path = SUMMARIES_DIR / "meter_anomaly_distribution.csv"
    if m_path.exists():
        return pd.read_csv(m_path)
    return pd.DataFrame()


@st.cache_data
def load_pipeline_log():
    log_path = LOGS_DIR / "pipeline_execution_log.json"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.image("https://img.icons8.com/fluency/96/electricity.png", width=70)
st.sidebar.title("GridSense")
st.sidebar.caption("⚡ Smart Meter Big Data Anomaly Detection")
st.sidebar.markdown("**Course:** INT315 Cluster Computing  \n**Student:** Aditya Raj  \n**Dataset:** CEEW Smart Meters (UP, India)")
st.sidebar.divider()

nav = st.sidebar.radio(
    "Navigation",
    [
        "🏛️ Executive Overview",
        "📈 Consumption & Grid Trends",
        "🔍 Anomaly Detection (Rules vs ML)",
        "🏢 Spatial & Temporal Patterns",
        "🔬 Case Studies & Data Export",
        "⚙️ Spark & Cluster Diagnostics"
    ]
)

st.sidebar.divider()
st.sidebar.info("💡 **Local Execution Mode:** Powered by Apache Spark 4.2.0 & PySpark on Java 17.")

# Load primary cached datasets
df_summary = load_discovery_data()
eval_meta = load_eval_summary()
rule_meta = load_rule_summary()
df_anom = load_top_anomalies()
df_hourly = load_hourly_distribution()
df_meters = load_meter_distribution()
log_meta = load_pipeline_log()


# ---------------- TAB 1: EXECUTIVE OVERVIEW ----------------
if nav == "🏛️ Executive Overview":
    st.title("⚡ GridSense: Big Data Electricity Anomaly Detection")
    st.subheader("High-Frequency Smart-Meter Analytics Across Mathura and Bareilly, India")

    st.markdown("""
    GridSense processes millions of high-frequency (3-minute interval) smart-meter electricity readings
    collected from residential households in **Mathura** and **Bareilly**, Uttar Pradesh.
    Utilizing **Apache Spark**, distributed feature engineering, and a dual-paradigm detection engine
    combining **domain engineering rules (Method A)** and **unsupervised Isolation Forest (Method B)**,
    GridSense isolates grid faults, severe voltage sags/surges, power outages, and abnormal consumption spikes.
    """)

    # Metric Row
    total_raw_rows = df_summary["Row Count"].sum() if not df_summary.empty else 21394429
    total_meters = eval_meta.get("unique_meters", 84)
    total_anom = eval_meta.get("agreement_analysis", {}).get("union_anomalies_count", 0)
    anom_pct = eval_meta.get("agreement_analysis", {}).get("union_percentage", 0.0)
    jaccard = eval_meta.get("agreement_analysis", {}).get("jaccard_similarity", 0.0)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Readings Audited", f"{total_raw_rows:,}")
    m2.metric("Smart Meters Monitored", f"{total_meters}")
    m3.metric("Sampling Cadence", "3 Minutes")
    m4.metric("Flagged Anomalies", f"{total_anom:,} ({anom_pct:.2f}%)")
    m5.metric("Jaccard Agreement", f"{jaccard:.4f}")

    st.divider()

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("### 📊 Dataset Partitions & Ingestion Audit")
        if not df_summary.empty:
            st.dataframe(
                df_summary.style.format({"Size (MB)": "{:.2f}", "Row Count": "{:,}"}),
                use_container_width=True,
                height=320
            )
        else:
            st.warning("Dataset summary table not found. Run `src/inspect_data.py` to generate.")

    with c2:
        st.markdown("### 🗺️ Geographic Distribution")
        if not df_summary.empty:
            pie_df = pd.DataFrame([
                {"City": "Bareilly (BR)", "Readings": df_summary[df_summary["File Name"].str.contains("Bareilly|BR")]["Row Count"].sum()},
                {"City": "Mathura (MH)", "Readings": df_summary[df_summary["File Name"].str.contains("Mathura|MH")]["Row Count"].sum()}
            ])
            fig_pie = px.pie(
                pie_df,
                values="Readings",
                names="City",
                color="City",
                color_discrete_map={"Bareilly (BR)": "#1f77b4", "Mathura (MH)": "#ff7f0e"},
                hole=0.4
            )
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 🏗️ Big Data Processing Architecture")
    st.markdown("""
    ```mermaid
    flowchart LR
        A[Raw Smart Meter CSVs<br/>21.3M+ Rows | 1GB] --> B[PySpark DataLoader<br/>Schema Alignment & Parsing]
        B --> C[Data Quality Cleaner<br/>Nulls, Deduplication, Outages]
        C --> D[Feature Engineering<br/>Lags, Rolling Stats, Z-scores]
        D --> E[Method A: Rule-Based Engine<br/>IEGC Volt, Freq, Spike Rules]
        D --> F[Method B: Isolation Forest<br/>Unsupervised ML Scoring]
        E --> G[Agreement Evaluation & Synthesis]
        F --> G
        G --> H[Interactive Streamlit Dashboard & Report]
    ```
    """)


# ---------------- TAB 2: CONSUMPTION & GRID TRENDS ----------------
elif nav == "📈 Consumption & Grid Trends":
    st.title("📈 Electricity Consumption & Electrical Grid Analytics")
    st.markdown("Auditing active power consumption ($t\\_\\text{kWh}$), voltage, current, and grid frequency.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🕒 24-Hour Diurnal Electricity Profile")
        if not df_hourly.empty:
            fig_hr = go.Figure()
            fig_hr.add_trace(go.Scatter(
                x=df_hourly["hour"],
                y=df_hourly["avg_kwh"],
                mode="lines+markers",
                name="Avg Consumption",
                line=dict(color="#2ca02c", width=3),
                marker=dict(size=7)
            ))
            fig_hr.update_layout(
                xaxis_title="Hour of Day (0–23)",
                yaxis_title="Average 3-Min Consumption (kWh)",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350
            )
            st.plotly_chart(fig_hr, use_container_width=True)
            st.caption("Notice typical residential peaks: early morning (6–9 AM) and evening peak demand (6–10 PM).")
        else:
            st.info("Hourly statistics will appear after running the pipeline.")

    with col2:
        st.markdown("#### ⚡ Voltage Distribution vs IEGC Standards")
        if not df_anom.empty:
            fig_v = px.histogram(
                df_anom,
                x="voltage",
                nbins=40,
                color_discrete_sequence=["#1f77b4"],
                marginal="box"
            )
            fig_v.add_vline(x=230, line_dash="dash", line_color="green", annotation_text="Nominal (230V)")
            fig_v.add_vline(x=160, line_dash="dot", line_color="red", annotation_text="Sag (<160V)")
            fig_v.add_vline(x=280, line_dash="dot", line_color="orange", annotation_text="Surge (>280V)")
            fig_v.update_layout(
                xaxis_title="Voltage (Volts)",
                yaxis_title="Count",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350
            )
            st.plotly_chart(fig_v, use_container_width=True)
        else:
            st.info("Anomaly sample data needed for parameter distribution.")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### 🔄 Grid Frequency Compliance (50.0 Hz)")
        if not df_anom.empty:
            fig_f = px.histogram(
                df_anom,
                x="frequency",
                nbins=35,
                color_discrete_sequence=["#2ca02c"]
            )
            fig_f.add_vline(x=50.0, line_dash="dash", line_color="green", annotation_text="50.0 Hz")
            fig_f.add_vline(x=48.5, line_dash="dot", line_color="red", annotation_text="IEGC Min (48.5)")
            fig_f.add_vline(x=51.5, line_dash="dot", line_color="red", annotation_text="IEGC Max (51.5)")
            fig_f.update_layout(
                xaxis_title="Frequency (Hz)",
                yaxis_title="Count",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350
            )
            st.plotly_chart(fig_f, use_container_width=True)

    with col4:
        st.markdown("#### 🔌 Current Load Distribution")
        if not df_anom.empty:
            fig_c = px.histogram(
                df_anom,
                x="current",
                nbins=35,
                color_discrete_sequence=["#ff7f0e"]
            )
            fig_c.add_vline(x=35.0, line_dash="dot", line_color="red", annotation_text="Overload (35A)")
            fig_c.update_layout(
                xaxis_title="Current (Amperes)",
                yaxis_title="Count",
                margin=dict(t=20, b=20, l=20, r=20),
                height=350
            )
            st.plotly_chart(fig_c, use_container_width=True)


# ---------------- TAB 3: ANOMALY DETECTION (RULES VS ML) ----------------
elif nav == "🔍 Anomaly Detection (Rules vs ML)":
    st.title("🔍 Anomaly Detection: Method A (Rules) vs Method B (Machine Learning)")
    st.markdown("Comparing explicit electrical domain rules with unsupervised Isolation Forest multi-dimensional outlier scoring.")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("### ⚖️ Agreement & Venn Synthesis")
        if eval_meta:
            agree = eval_meta.get("agreement_analysis", {})
            df_agr = pd.DataFrame([
                {"Category": "High Confidence (Both Agree)", "Count": agree.get("both_agree_count", 0), "Color": "#2ca02c"},
                {"Category": "Rule-Based Only (Boundary Sags/Surges)", "Count": agree.get("rule_only_count", 0), "Color": "#d62728"},
                {"Category": "Isolation Forest Only (Subtle Outliers)", "Count": agree.get("ml_only_count", 0), "Color": "#1f77b4"}
            ])
            fig_agr = px.bar(
                df_agr,
                x="Category",
                y="Count",
                color="Category",
                color_discrete_map={row["Category"]: row["Color"] for _, row in df_agr.iterrows()},
                text="Count"
            )
            fig_agr.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig_agr.update_layout(showlegend=False, height=380, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_agr, use_container_width=True)

            st.metric("Jaccard Similarity Index", f"{agree.get('jaccard_similarity', 0.0):.4f}")
            st.metric("Overlap Coefficient", f"{agree.get('overlap_coefficient', 0.0):.4f}")
        else:
            st.warning("Evaluation summary missing. Please execute the pipeline.")

    with c2:
        st.markdown("### 📋 Breakdown of Triggered Rules (Method A)")
        if rule_meta:
            breakdown = rule_meta.get("rule_breakdown", {})
            rule_map = {
                "over_voltage_count": "Over-Voltage (>280V)",
                "under_voltage_count": "Under-Voltage Sag (<160V)",
                "freq_violation_count": "Grid Freq Violation (<48.5 / >51.5)",
                "stat_spike_count": "Statistical Spike (Z-Score > 4.0)",
                "abrupt_ramp_count": "Abrupt Consumption Jump (>1.8 kWh)",
                "spike_kwh_count": "Extreme 3-Min Spike (>2.5 kWh)",
                "current_overload_count": "Current Overload (>35A)",
                "suspect_bypass_count": "Zero Volt with Active Current",
                "neg_kwh_count": "Negative Meter Reading"
            }
            items = []
            for k, label in rule_map.items():
                if k in breakdown and breakdown[k] > 0:
                    items.append({"Rule": label, "Occurrences": breakdown[k]})

            df_r = pd.DataFrame(items).sort_values(by="Occurrences", ascending=True)
            if not df_r.empty:
                fig_r = px.bar(
                    df_r,
                    x="Occurrences",
                    y="Rule",
                    orientation="h",
                    color="Occurrences",
                    color_continuous_scale="Reds"
                )
                fig_r.update_layout(height=450, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_r, use_container_width=True)
        else:
            st.info("Rule summary will appear after pipeline execution.")


# ---------------- TAB 4: SPATIAL & TEMPORAL PATTERNS ----------------
elif nav == "🏢 Spatial & Temporal Patterns":
    st.title("🏢 Spatial & Temporal Anomaly Distributions")
    st.markdown("Pinpointing geographic hotspots and temporal vulnerabilities across smart meter clusters.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🏆 Top 12 Anomalous Smart Meters")
        if not df_meters.empty:
            top_12 = df_meters.head(12)
            fig_m = px.bar(
                top_12,
                x="meter_id",
                y=["rule_anomalies", "ml_anomalies"],
                barmode="group",
                title="Rule-Based vs ML Flagged Counts by Meter",
                labels={"value": "Anomaly Count", "meter_id": "Meter ID", "variable": "Method"},
                color_discrete_map={"rule_anomalies": "#d62728", "ml_anomalies": "#1f77b4"}
            )
            fig_m.update_layout(height=380, margin=dict(t=30, b=20, l=20, r=20))
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("Meter distribution data unavailable.")

    with c2:
        st.markdown("### ⏰ Hourly Vulnerability Curve")
        if not df_hourly.empty:
            fig_h_anom = px.line(
                df_hourly,
                x="hour",
                y=["rule_anomalies", "ml_anomalies", "combined_anomalies"],
                title="Anomaly Frequency by Hour of Day",
                markers=True,
                labels={"value": "Anomalies Count", "hour": "Hour of Day (0–23)", "variable": "Category"},
                color_discrete_map={
                    "rule_anomalies": "#d62728",
                    "ml_anomalies": "#1f77b4",
                    "combined_anomalies": "#2ca02c"
                }
            )
            fig_h_anom.update_layout(height=380, margin=dict(t=30, b=20, l=20, r=20))
            st.plotly_chart(fig_h_anom, use_container_width=True)
        else:
            st.info("Hourly anomaly data unavailable.")

    st.markdown("### 📊 City-Level Anomaly Aggregates")
    if eval_meta and "city_breakdown" in eval_meta:
        city_data = pd.DataFrame(eval_meta["city_breakdown"])
        st.dataframe(
            city_data.style.format({
                "total_readings": "{:,}",
                "rule_anomalies": "{:,}",
                "ml_anomalies": "{:,}",
                "combined_anomalies": "{:,}",
                "anomaly_rate_pct": "{:.2f}%"
            }),
            use_container_width=True
        )


# ---------------- TAB 5: CASE STUDIES & DATA EXPORT ----------------
elif nav == "🔬 Case Studies & Data Export":
    st.title("🔬 Anomaly Case Studies & Filterable Explorer")
    st.markdown("Inspect granular high-resolution readings, explore specific anomalies, and download customized audit reports.")

    if not df_anom.empty:
        # Filter controls
        f1, f2, f3 = st.columns(3)
        cities = ["All"] + list(df_anom["city"].dropna().unique())
        sel_city = f1.selectbox("Filter by City", cities)

        agreements = ["All"] + list(df_anom["agreement_type"].dropna().unique())
        sel_agr = f2.selectbox("Filter by Agreement Type", agreements)

        meters = ["All"] + list(df_anom["meter_id"].dropna().unique())
        sel_meter = f3.selectbox("Filter by Smart Meter ID", meters)

        # Apply filters
        filtered = df_anom.copy()
        if sel_city != "All":
            filtered = filtered[filtered["city"] == sel_city]
        if sel_agr != "All":
            filtered = filtered[filtered["agreement_type"] == sel_agr]
        if sel_meter != "All":
            filtered = filtered[filtered["meter_id"] == sel_meter]

        st.markdown(f"**Showing {len(filtered):,} matching anomalous observations:**")
        st.dataframe(
            filtered[["timestamp", "meter_id", "city", "kwh", "voltage", "current", "frequency", "ml_anomaly_score", "agreement_type", "rule_flags"]],
            use_container_width=True,
            height=320
        )

        # Download CSV
        csv_data = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Anomalies as CSV",
            data=csv_data,
            file_name="GridSense_Filtered_Anomalies.csv",
            mime="text/csv"
        )

        st.divider()

        # Meter Micro-Trace Deep Dive
        st.markdown("### 🔬 Temporal Micro-Trace for Selected Meter")
        active_meter = sel_meter if sel_meter != "All" else df_anom["meter_id"].iloc[0]
        meter_seq = df_anom[df_anom["meter_id"] == active_meter].head(30)

        if len(meter_seq) > 2:
            st.caption(f"Visualizing continuous 3-minute sequence for smart meter **{active_meter}**:")
            fig_trace = go.Figure()
            fig_trace.add_trace(go.Scatter(
                x=meter_seq["timestamp"],
                y=meter_seq["kwh"],
                mode="lines+markers",
                name="Active Energy (kWh)",
                line=dict(color="#d62728", width=2)
            ))
            fig_trace.add_trace(go.Scatter(
                x=meter_seq["timestamp"],
                y=meter_seq["voltage"] / 100,
                mode="lines+markers",
                name="Voltage (x100 V)",
                line=dict(color="#1f77b4", width=2, dash="dash")
            ))
            fig_trace.add_trace(go.Scatter(
                x=meter_seq["timestamp"],
                y=meter_seq["current"] / 10,
                mode="lines+markers",
                name="Current (x10 A)",
                line=dict(color="#ff7f0e", width=2, dash="dot")
            ))
            fig_trace.update_layout(
                xaxis_title="Reading Timestamp",
                yaxis_title="Normalized Electrical Readings",
                height=350,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_trace, use_container_width=True)
    else:
        st.warning("Anomaly records not yet generated. Please run `python src/run_pipeline.py`.")


# ---------------- TAB 6: SPARK & CLUSTER DIAGNOSTICS ----------------
elif nav == "⚙️ Spark & Cluster Diagnostics":
    st.title("⚙️ Apache Spark & Cluster Computing Diagnostics")
    st.markdown("System execution environment, hardware resources, and stage performance profiling.")

    if log_meta:
        env = log_meta.get("hardware_environment", {})
        timings = log_meta.get("stage_timings", {})

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🖥️ Cluster Computing Environment")
            st.json(env)

        with c2:
            st.markdown("### ⏱️ Stage Execution Benchmark")
            df_time = pd.DataFrame([
                {"Stage": k.replace("_seconds", "").replace("_", " ").title(), "Duration (Seconds)": v}
                for k, v in timings.items() if k != "total_pipeline_seconds"
            ])
            if not df_time.empty:
                fig_time = px.bar(
                    df_time,
                    x="Duration (Seconds)",
                    y="Stage",
                    orientation="h",
                    color="Duration (Seconds)",
                    color_continuous_scale="Viridis",
                    text="Duration (Seconds)"
                )
                fig_time.update_traces(texttemplate="%{text:.2f}s", textposition="outside")
                fig_time.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_time, use_container_width=True)

        st.success(f"⚡ Total End-to-End Execution Time: **{timings.get('total_pipeline_seconds', 0.0):.2f} seconds**")
    else:
        st.info("Pipeline execution log not found. Run `src/run_pipeline.py` to populate performance benchmarks.")
