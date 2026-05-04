import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import date, datetime
from groq import Groq
import base64
import fitz
import json

st.set_page_config(
    page_title="Trace — Biomarker Timeline",
    page_icon="logo.png",
    layout="wide"
)

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

logo_base64 = get_base64_image("logo.png")

MARKER_INFO = {
    "Hemoglobin (g/dL)": "Carries oxygen in your blood. Low levels cause fatigue.",
    "RBC Count (million/µL)": "Red blood cells that carry oxygen throughout your body.",
    "WBC Count (thousand/µL)": "White blood cells that fight infection.",
    "Platelets (thousand/µL)": "Help your blood clot when injured.",
    "Hematocrit (%)": "Percentage of blood made up of red blood cells.",
    "TSH (mIU/L)": "Controls your thyroid — the remote control for your metabolism.",
    "T3 Total (ng/dL)": "Active thyroid hormone controlling metabolism and energy.",
    "T4 Total (µg/dL)": "Thyroid hormone that converts to T3.",
    "Free T3 (pg/mL)": "Active form of thyroid hormone available to your cells.",
    "Free T4 (ng/dL)": "Unbound thyroid hormone ready to convert to T3.",
    "Fasting Glucose (mg/dL)": "Blood sugar after fasting. First sign of diabetes risk.",
    "HbA1c (%)": "Your average blood sugar over 3 months. Most important diabetes marker.",
    "Post Prandial Glucose (mg/dL)": "Blood sugar 2 hours after eating.",
    "Fasting Insulin (µIU/mL)": "Insulin when fasting. High levels indicate insulin resistance.",
    "Total Cholesterol (mg/dL)": "Total fat in blood. Not all cholesterol is bad.",
    "LDL Cholesterol (mg/dL)": "Bad cholesterol that builds in arteries. Lower is better.",
    "HDL Cholesterol (mg/dL)": "Good cholesterol that removes bad cholesterol. Higher is better.",
    "Triglycerides (mg/dL)": "Blood fats linked to diet and heart risk.",
    "VLDL (mg/dL)": "Carries triglycerides. Elevated levels increase heart disease risk.",
    "ALT / SGPT (U/L)": "Liver enzyme. Elevated levels signal liver stress.",
    "AST / SGOT (U/L)": "Liver and heart enzyme. Elevated with liver damage.",
    "Total Bilirubin (mg/dL)": "Processed by liver. High levels signal liver stress.",
    "Alkaline Phosphatase (U/L)": "Liver and bone enzyme.",
    "Albumin (g/dL)": "Protein made by liver. Low levels indicate poor nutrition.",
    "Total Protein (g/dL)": "Total protein in blood. Reflects nutrition and organ health.",
    "Creatinine (mg/dL)": "Waste filtered by kidneys. Rising levels signal kidney stress.",
    "Blood Urea (mg/dL)": "Waste from protein breakdown filtered by kidneys.",
    "Uric Acid (mg/dL)": "Waste from cell breakdown. High levels cause gout.",
    "eGFR (mL/min/1.73m²)": "How well kidneys filter blood. Below 60 needs attention.",
    "BUN Creatinine Ratio": "Helps identify cause of kidney problems.",
    "Vitamin D (ng/mL)": "Essential for bones, immunity and mood. Very common deficiency in India.",
    "Vitamin B12 (pg/mL)": "Critical for nerves and blood. Vegetarians at high risk.",
    "Ferritin (ng/mL)": "Iron storage. Low ferritin means low iron even if hemoglobin looks normal.",
    "Serum Iron (µg/dL)": "Iron circulating in blood.",
    "Calcium (mg/dL)": "Essential for bones, muscles and nerve function.",
    "Magnesium (mg/dL)": "Involved in 300+ body processes. Low levels cause muscle cramps.",
    "Phosphorus (mg/dL)": "Works with calcium for bone health and energy.",
    "Folate (ng/mL)": "B vitamin essential for cell growth. Critical during pregnancy.",
    "Zinc (µg/dL)": "Essential for immunity and wound healing.",
    "Testosterone Total (ng/dL)": "Primary male hormone affecting energy, muscle and mood.",
    "Estradiol (pg/mL)": "Primary female hormone affecting cycle and bone density.",
    "FSH (mIU/mL)": "Controls egg and sperm production. Key fertility marker.",
    "LH (mIU/mL)": "Triggers ovulation in women and testosterone in men.",
    "Cortisol Morning (µg/dL)": "Stress hormone. Should be highest in morning.",
    "CRP (mg/L)": "Inflammation marker. Elevated with infection or chronic disease.",
    "ESR (mm/hr)": "General inflammation marker.",
}

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    * { font-family: 'Nunito', sans-serif !important; }

    .stApp {
        background: #f7f8fa !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .main .block-container {
        padding: 1.5rem 2.5rem;
        max-width: 1200px;
    }

    /* NAVBAR */
    .t-nav {
        background: white;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .t-nav-left { display: flex; align-items: center; gap: 12px; }
    .t-nav-logo {
        width: 38px; height: 38px;
        background: #0EA5E9;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
    }
    .t-nav-logo-inner {
        width: 16px; height: 16px;
        background: white; border-radius: 50%; opacity: 0.9;
    }
    .t-nav-brand { font-size: 18px; font-weight: 800; color: #0F172A; }
    .t-nav-sub { font-size: 11px; color: #94A3B8; margin-top: 1px; font-weight: 500; }
    .t-nav-right { display: flex; align-items: center; gap: 12px; }
    .t-nav-private { font-size: 11px; color: #22C55E; font-weight: 700; }
    .t-nav-badge {
        background: #EFF6FF; color: #0EA5E9;
        font-size: 10px; font-weight: 700;
        padding: 4px 12px; border-radius: 20px;
        border: 1px solid #BFDBFE;
    }

    /* CARDS */
    .t-card {
        background: white;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .t-card-blue {
        background: white;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0EA5E9;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* HERO */
    .t-hero {
        background: linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%);
        border-radius: 20px;
        border: 1px solid #E2E8F0;
        padding: 36px 24px;
        text-align: center;
        margin-bottom: 20px;
    }
    .t-hero-tag {
        font-size: 11px; font-weight: 800;
        color: #0EA5E9; letter-spacing: 2px;
        text-transform: uppercase; margin-bottom: 12px;
    }
    .t-hero-title {
        font-size: 32px; font-weight: 900;
        color: #0F172A; margin-bottom: 10px;
        line-height: 1.2;
    }
    .t-hero-sub {
        font-size: 15px; color: #64748B;
        line-height: 1.8; margin-bottom: 24px;
        font-weight: 500;
    }
    .t-hero-privacy {
        font-size: 12px; color: #22C55E;
        margin-top: 12px; font-weight: 700;
    }

    /* FEATURE TABLE */
    .t-feature-row {
        display: flex; justify-content: space-between;
        align-items: center; padding: 10px 0;
        border-bottom: 1px solid #F1F5F9;
    }
    .t-feature-name {
        font-size: 13px; font-weight: 700; color: #0EA5E9;
    }
    .t-feature-desc {
        font-size: 12px; color: #94A3B8; font-weight: 500;
    }

    /* STATS */
    .t-stat {
        background: white;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        padding: 16px 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .t-stat-num {
        font-size: 28px; font-weight: 900; line-height: 1;
    }
    .t-stat-label {
        font-size: 10px; color: #94A3B8;
        margin-top: 4px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1px;
    }

    /* SCORE */
    .t-score-card {
        background: white;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        padding: 20px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .t-score-circle {
        width: 72px; height: 72px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; font-size: 26px; font-weight: 900;
        border: 3px solid;
    }
    .t-score-title {
        font-size: 15px; font-weight: 800; color: #0F172A; margin-bottom: 4px;
    }
    .t-score-sub {
        font-size: 12px; color: #64748B; line-height: 1.6; font-weight: 500;
    }

    /* AI STORY */
    .t-ai-label {
        font-size: 10px; font-weight: 800; color: #0EA5E9;
        letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;
    }
    .t-ai-text {
        font-size: 14px; color: #334155; line-height: 1.9; font-weight: 500;
    }
    .t-disclaimer {
        font-size: 11px; color: #CBD5E1; margin-top: 10px;
        font-weight: 500; text-align: center;
    }

    /* MARKER CARDS */
    .t-marker {
        background: white;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: border-color 0.2s;
    }
    .t-marker:hover { border-color: #BFDBFE; }
    .t-marker-name {
        font-size: 13px; font-weight: 800; color: #0F172A;
    }
    .t-marker-info {
        font-size: 11px; color: #94A3B8; margin-top: 3px; font-weight: 500;
    }
    .t-marker-range {
        font-size: 11px; color: #CBD5E1; margin-top: 2px; font-weight: 500;
    }

    /* BADGES */
    .t-badge {
        font-size: 11px; font-weight: 800;
        padding: 4px 12px; border-radius: 20px;
        display: inline-block;
    }
    .t-badge-normal {
        background: #F0FDF4; color: #16A34A; border: 1px solid #BBF7D0;
    }
    .t-badge-warning {
        background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A;
    }
    .t-badge-danger {
        background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
    }

    /* TREND TEXT */
    .t-trend { font-size: 12px; margin-top: 6px; font-weight: 600; }
    .t-trend-normal { color: #16A34A; }
    .t-trend-warning { color: #D97706; }
    .t-trend-danger { color: #DC2626; }
    .t-trend-neutral { color: #94A3B8; }

    /* PROGRESS BAR */
    .t-bar-wrap {
        background: #F1F5F9; border-radius: 6px;
        height: 6px; margin-top: 10px; overflow: hidden;
    }
    .t-bar { height: 6px; border-radius: 6px; }

    /* PANEL HEADER */
    .t-panel-head {
        font-size: 11px; font-weight: 800; color: #94A3B8;
        letter-spacing: 2px; text-transform: uppercase;
        margin: 20px 0 12px; padding-bottom: 8px;
        border-bottom: 2px solid #F1F5F9;
    }

    /* ALERT */
    .t-alert {
        background: #FFFBEB; border: 1px solid #FDE68A;
        border-radius: 12px; padding: 12px 16px;
        margin-bottom: 12px; display: flex;
        gap: 10px; align-items: flex-start;
    }
    .t-alert-dot {
        width: 8px; height: 8px; background: #F59E0B;
        border-radius: 50%; flex-shrink: 0; margin-top: 4px;
    }
    .t-alert-text { font-size: 13px; color: #92400E; line-height: 1.5; font-weight: 600; }

    /* SECTION LABEL */
    .t-section {
        font-size: 11px; font-weight: 800; color: #94A3B8;
        letter-spacing: 2px; text-transform: uppercase;
        margin: 20px 0 12px;
    }

    /* ONBOARDING */
    .t-onboard {
        background: white; border-radius: 20px;
        border: 1px solid #E2E8F0; padding: 32px 24px;
        text-align: center; margin: 16px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .t-onboard-title {
        font-size: 20px; font-weight: 900; color: #0F172A; margin-bottom: 6px;
    }
    .t-onboard-sub {
        font-size: 13px; color: #64748B; margin-bottom: 24px; font-weight: 500;
    }
    .t-step {
        display: flex; align-items: flex-start; gap: 14px;
        text-align: left; padding: 12px 0;
        border-bottom: 1px solid #F8FAFC;
    }
    .t-step:last-child { border-bottom: none; }
    .t-step-num {
        font-size: 13px; font-weight: 900; color: #0EA5E9;
        background: #EFF6FF; width: 28px; height: 28px;
        border-radius: 50%; display: flex; align-items: center;
        justify-content: center; flex-shrink: 0;
    }
    .t-step-text { font-size: 13px; color: #475569; line-height: 1.6; font-weight: 500; }
    .t-step-text strong { color: #0F172A; font-weight: 800; }

    /* SHARE */
    .t-share {
        background: #F0FDF4; border: 1px solid #BBF7D0;
        border-radius: 14px; padding: 16px 20px;
        display: flex; align-items: center;
        justify-content: space-between; gap: 16px;
        margin-bottom: 16px;
    }
    .t-share-text { font-size: 13px; color: #166534; font-weight: 600; line-height: 1.5; }

    /* FEEDBACK */
    .t-feedback {
        background: #F8FAFC; border-radius: 16px;
        border: 1px solid #E2E8F0; padding: 24px;
        margin-top: 32px;
    }
    .t-feedback-title {
        font-size: 16px; font-weight: 900; color: #0F172A; margin-bottom: 4px;
    }
    .t-feedback-sub {
        font-size: 13px; color: #64748B; font-weight: 500; line-height: 1.6; margin-bottom: 16px;
    }

    /* PILLS ROW */
    .t-pills {
        display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0;
    }
    .t-pill {
        background: #F8FAFC; border: 1px solid #E2E8F0;
        border-radius: 20px; padding: 6px 14px;
        font-size: 12px; color: #475569; font-weight: 600;
    }

    /* INSIGHTS */
    .t-insight {
        display: flex; align-items: flex-start; gap: 12px;
        padding: 12px 0; border-bottom: 1px solid #F1F5F9;
    }
    .t-insight:last-child { border-bottom: none; }
    .t-insight-dot {
        width: 8px; height: 8px; border-radius: 50%;
        flex-shrink: 0; margin-top: 5px;
    }
    .t-insight-label {
        font-size: 10px; font-weight: 800; letter-spacing: 1px;
        text-transform: uppercase; margin-bottom: 2px;
    }
    .t-insight-text { font-size: 13px; color: #475569; font-weight: 500; line-height: 1.5; }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        background: white !important;
        border-radius: 14px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 4px !important; gap: 4px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        color: #94A3B8 !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 8px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #EFF6FF !important;
        color: #0EA5E9 !important;
        border: 1px solid #BFDBFE !important;
    }

    /* INPUTS */
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #0EA5E9 !important;
        box-shadow: 0 0 0 3px rgba(14,165,233,0.1) !important;
    }
    .stTextArea textarea {
        background: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
        font-weight: 500 !important;
    }
    .stTextArea textarea:focus {
        border-color: #0EA5E9 !important;
        box-shadow: 0 0 0 3px rgba(14,165,233,0.1) !important;
    }

    /* BUTTON */
    .stButton button {
        background: #0EA5E9 !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 800 !important;
        font-size: 14px !important;
        width: 100% !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 4px 12px rgba(14,165,233,0.25) !important;
    }
    .stButton button:hover {
        background: #0284C7 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(14,165,233,0.35) !important;
    }

    /* SELECTBOX */
    .stSelectbox > div > div, .stMultiSelect > div > div {
        background: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
        font-weight: 600 !important;
    }

    /* EXPANDER */
    .streamlit-expanderHeader {
        background: #F8FAFC !important;
        border-radius: 10px !important;
        border: 1px solid #E2E8F0 !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }

    /* FOOTER */
    .t-footer {
        text-align: center; padding: 32px 0 16px;
        border-top: 1px solid #E2E8F0; margin-top: 40px;
    }
    .t-footer-brand {
        font-size: 20px; font-weight: 900; color: #0F172A;
        letter-spacing: 2px; margin-top: 12px;
    }
    .t-footer-sub { font-size: 12px; color: #94A3B8; margin-top: 4px; font-weight: 500; }
    .t-footer-privacy { font-size: 11px; color: #22C55E; margin-top: 8px; font-weight: 700; }

    hr { border-color: #F1F5F9 !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #F8FAFC; }
    ::-webkit-scrollbar-thumb { background: #BFDBFE; border-radius: 4px; }

    @media (max-width: 768px) {
        .main .block-container { padding: 1rem !important; }
        .t-hero-title { font-size: 22px !important; }
        .t-hero { padding: 24px 16px !important; }
        .t-card { padding: 14px !important; }
        .t-nav { padding: 10px 14px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── MARKER DATABASE ───────────────────────────────────────────────────────────

def get_markers(gender="Male", age=30):
    m = {}
    m["Hemoglobin (g/dL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 25.0,
        "low": 13.5 if gender=="Male" else 12.0, "high": 17.5 if gender=="Male" else 15.5}
    m["RBC Count (million/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 10.0,
        "low": 4.7 if gender=="Male" else 4.2, "high": 6.1 if gender=="Male" else 5.4}
    m["WBC Count (thousand/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 30.0, "low": 4.5, "high": 11.0}
    m["Platelets (thousand/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 800.0, "low": 150.0, "high": 400.0}
    m["Hematocrit (%)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 70.0,
        "low": 41.0 if gender=="Male" else 36.0, "high": 53.0 if gender=="Male" else 46.0}
    tl, th = (0.7,6.4) if age<18 else (0.4,4.0) if age<60 else (0.4,5.5)
    m["TSH (mIU/L)"] = {"panel": "Thyroid Panel", "min": 0.0, "max": 20.0, "low": tl, "high": th}
    m["T3 Total (ng/dL)"] = {"panel": "Thyroid Panel", "min": 0.0, "max": 300.0, "low": 80.0, "high": 200.0}
    m["T4 Total (µg/dL)"] = {"panel": "Thyroid Panel", "min": 0.0, "max": 25.0, "low": 5.0, "high": 12.0}
    m["Free T3 (pg/mL)"] = {"panel": "Thyroid Panel", "min": 0.0, "max": 15.0, "low": 2.3, "high": 4.2}
    m["Free T4 (ng/dL)"] = {"panel": "Thyroid Panel", "min": 0.0, "max": 5.0, "low": 0.8, "high": 1.8}
    m["Fasting Glucose (mg/dL)"] = {"panel": "Diabetes Panel", "min": 0.0, "max": 500.0, "low": 70.0, "high": 100.0}
    m["HbA1c (%)"] = {"panel": "Diabetes Panel", "min": 0.0, "max": 20.0, "low": 4.0, "high": 5.7}
    m["Post Prandial Glucose (mg/dL)"] = {"panel": "Diabetes Panel", "min": 0.0, "max": 600.0, "low": 70.0, "high": 140.0}
    m["Fasting Insulin (µIU/mL)"] = {"panel": "Diabetes Panel", "min": 0.0, "max": 100.0, "low": 2.0, "high": 25.0}
    m["Total Cholesterol (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 400.0, "low": 0.0, "high": 200.0}
    m["LDL Cholesterol (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 300.0, "low": 0.0, "high": 100.0}
    m["HDL Cholesterol (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 150.0,
        "low": 40.0 if gender=="Male" else 50.0, "high": 60.0}
    m["Triglycerides (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 1000.0, "low": 0.0, "high": 150.0}
    m["VLDL (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 200.0, "low": 0.0, "high": 30.0}
    m["ALT / SGPT (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 500.0,
        "low": 0.0, "high": 40.0 if gender=="Male" else 31.0}
    m["AST / SGOT (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 500.0, "low": 0.0, "high": 40.0}
    m["Total Bilirubin (mg/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 20.0, "low": 0.0, "high": 1.2}
    m["Alkaline Phosphatase (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 1000.0,
        "low": 44.0, "high": 147.0 if age<60 else 190.0}
    m["Albumin (g/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 10.0, "low": 3.5, "high": 5.0}
    m["Total Protein (g/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 15.0, "low": 6.0, "high": 8.3}
    m["Creatinine (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 20.0,
        "low": 0.7 if gender=="Male" else 0.5, "high": 1.2 if gender=="Male" else 1.0}
    m["Blood Urea (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 200.0, "low": 7.0, "high": 20.0}
    m["Uric Acid (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 20.0,
        "low": 3.5 if gender=="Male" else 2.6, "high": 7.2 if gender=="Male" else 6.0}
    m["eGFR (mL/min/1.73m²)"] = {"panel": "Kidney Function", "min": 0.0, "max": 200.0, "low": 60.0, "high": 120.0}
    m["BUN Creatinine Ratio"] = {"panel": "Kidney Function", "min": 0.0, "max": 50.0, "low": 10.0, "high": 20.0}
    m["Vitamin D (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 200.0, "low": 30.0, "high": 100.0}
    m["Vitamin B12 (pg/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 2000.0, "low": 200.0, "high": 900.0}
    m["Ferritin (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 500.0,
        "low": 24.0 if gender=="Male" else 11.0, "high": 336.0 if gender=="Male" else 307.0}
    m["Serum Iron (µg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 300.0,
        "low": 65.0 if gender=="Male" else 50.0, "high": 175.0}
    m["Calcium (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 20.0, "low": 8.5, "high": 10.5}
    m["Magnesium (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 5.0, "low": 1.7, "high": 2.4}
    m["Phosphorus (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 10.0, "low": 2.5, "high": 4.5}
    m["Folate (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 50.0, "low": 2.7, "high": 17.0}
    m["Zinc (µg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 200.0, "low": 70.0, "high": 120.0}
    if gender == "Male":
        m["Testosterone Total (ng/dL)"] = {"panel": "Hormones", "min": 0.0, "max": 1200.0,
            "low": 300.0 if age>=18 else 100.0, "high": 1000.0 if age<50 else 800.0}
    else:
        m["Estradiol (pg/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 500.0, "low": 30.0, "high": 400.0}
        m["FSH (mIU/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 100.0, "low": 3.0, "high": 10.0}
        m["LH (mIU/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 100.0, "low": 2.0, "high": 15.0}
    m["Cortisol Morning (µg/dL)"] = {"panel": "Hormones", "min": 0.0, "max": 60.0, "low": 6.2, "high": 19.4}
    m["CRP (mg/L)"] = {"panel": "Inflammation", "min": 0.0, "max": 200.0, "low": 0.0, "high": 3.0}
    m["ESR (mm/hr)"] = {"panel": "Inflammation", "min": 0.0, "max": 100.0,
        "low": 0.0, "high": 15.0 if gender=="Male" else 20.0}
    return m

# ── PDF ───────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc)
    except:
        return ""

def extract_values_with_ai(pdf_text, markers, gender, age):
    if not pdf_text.strip():
        return {}
    marker_list = "\n".join([f"- {mk}" for mk in markers.keys()])
    prompt = f"""You are a medical report parser. Extract biomarker values from this blood test report.
Markers to find:
{marker_list}
Report text:
{pdf_text[:4000]}
Return ONLY valid JSON. Keys = marker names exactly as listed, values = numeric only.
Be flexible with name matching. No units. No explanation.
Example: {{"Hemoglobin (g/dL)": 14.5, "TSH (mIU/L)": 2.3}}"""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except:
        return {}

# ── ANALYTICS ─────────────────────────────────────────────────────────────────

def compute_analytics(person_df, markers):
    normal = warning = danger = improved = worsened = 0
    best_marker = worst_marker = best_val = worst_val = ""
    best_score = -1
    worst_score = 999

    for marker, mdata in markers.items():
        if marker not in person_df.columns:
            continue
        series = person_df[marker].dropna()
        series = series[series > 0]
        if len(series) == 0:
            continue
        latest = series.iloc[-1]
        low = mdata["low"]
        high = mdata["high"]
        rng = high - low if high > low else 1

        if low <= latest <= high:
            normal += 1
            score = 1 - abs(latest - (low+high)/2) / (rng/2)
            if score > best_score:
                best_score = score
                best_marker = marker
                best_val = f"{latest:.1f}"
        elif latest < low:
            danger += 1
            pct = (low-latest)/low*100
            if pct < worst_score:
                worst_score = pct
                worst_marker = marker
                worst_val = f"{latest:.1f} — {pct:.0f}% below normal"
        else:
            warning += 1
            pct = (latest-high)/high*100
            if pct < worst_score:
                worst_score = pct
                worst_marker = marker
                worst_val = f"{latest:.1f} — {pct:.0f}% above normal"

        if len(series) >= 2:
            if low <= series.iloc[-1] <= high and (series.iloc[-2] < low or series.iloc[-2] > high):
                improved += 1
            elif not (low <= series.iloc[-1] <= high) and (low <= series.iloc[-2] <= high):
                worsened += 1

    total = normal + warning + danger
    score = int((normal/total*100)) if total > 0 else 0
    return {"score": score, "normal": normal, "warning": warning, "danger": danger,
            "improved": improved, "worsened": worsened, "total": total,
            "best_marker": best_marker, "best_val": best_val,
            "worst_marker": worst_marker, "worst_val": worst_val}

def get_trend_alerts(person_df, markers):
    alerts = []
    for marker, mdata in markers.items():
        if marker not in person_df.columns:
            continue
        series = person_df[marker].dropna()
        series = series[series > 0]
        if len(series) < 2:
            continue
        first, last = series.iloc[0], series.iloc[-1]
        change = ((last-first)/first)*100
        if abs(change) >= 15 and mdata["low"] <= last <= mdata["high"]:
            d = "declining" if change < 0 else "rising"
            alerts.append(f"{marker} has been {d} {abs(change):.0f}% — still within range but worth watching.")
        days = (pd.Timestamp.today() - pd.Timestamp(person_df["Date"].max())).days
        if days > 180:
            alerts.append(f"Your last test was {days//30} months ago. Time to schedule your next panel.")
            break
    return alerts[:3]

def get_ai_analysis(name, person_df, gender, age, conditions, diet):
    markers = get_markers(gender, age)
    lines = []
    for marker, mdata in markers.items():
        if marker not in person_df.columns:
            continue
        series = person_df[marker].dropna()
        series = series[series > 0]
        if len(series) >= 2:
            first, last = series.iloc[0], series.iloc[-1]
            change = ((last-first)/first)*100
            lines.append(f"{marker}: {first:.1f} to {last:.1f} ({change:+.1f}%)")
        elif len(series) == 1:
            lines.append(f"{marker}: {series.iloc[0]:.1f}")
    if not lines:
        return "Add at least 2 tests to generate your personal health story."
    prompt = f"""You are a warm health education assistant for Trace — an Indian biomarker tracking app.
Patient: {name}, {gender}, Age {age}, Diet: {diet}
Known Conditions: {conditions or 'None'}
Biomarker trends:
{chr(10).join(lines)}
Write 4-5 warm sentences. Simple language. Mention numbers naturally.
Factor in diet and conditions. Flag drifting markers calmly.
Suggest 2 specific doctor questions. Never diagnose. End with encouragement."""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            max_tokens=1000
        )
        return r.choices[0].message.content
    except:
        return "AI analysis is unavailable right now. Your trends are shown below."

def whatsapp_summary(name, person_df, markers):
    lines = [f"My health summary from Trace", f"Name: {name}", f"Tests logged: {len(person_df)}", ""]
    for marker, mdata in markers.items():
        if marker not in person_df.columns:
            continue
        s = person_df[marker].dropna()
        s = s[s > 0]
        if len(s) == 0:
            continue
        v = s.iloc[-1]
        tag = "Normal" if mdata["low"] <= v <= mdata["high"] else "Review needed"
        lines.append(f"{marker}: {v} — {tag}")
    lines += ["", "Track your health at gettrace.in"]
    return "\n".join(lines)

# ── HELPERS ───────────────────────────────────────────────────────────────────

DATA_FILE = "trace_data.csv"
PROFILES_FILE = "trace_profiles.csv"
FEEDBACK_FILE = "trace_feedback.csv"

def load_data():
    return pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()
def save_data(df): df.to_csv(DATA_FILE, index=False)
def load_profiles():
    return pd.read_csv(PROFILES_FILE) if os.path.exists(PROFILES_FILE) else \
        pd.DataFrame(columns=["Name","DOB","Gender","Blood Group","Conditions","Diet"])
def save_profiles(df): df.to_csv(PROFILES_FILE, index=False)
def load_feedback():
    return pd.read_csv(FEEDBACK_FILE) if os.path.exists(FEEDBACK_FILE) else \
        pd.DataFrame(columns=["Timestamp","Name","Rating","Message","Email"])
def save_feedback(df): df.to_csv(FEEDBACK_FILE, index=False)

def calculate_age(dob_str):
    try:
        dob = datetime.strptime(str(dob_str), "%Y-%m-%d")
        t = datetime.today()
        return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))
    except:
        return 25

def get_flag(value, md):
    if value == 0.0: return None, None
    if value < md["low"]: return "Low", "danger"
    if value > md["high"]: return "High", "danger"
    return "Normal", "normal"

def get_trend_msg(series, md):
    series = series.dropna()
    series = series[series > 0]
    if len(series) < 2: return "Add more tests to see your trend.", "neutral"
    first, last = series.iloc[0], series.iloc[-1]
    change = ((last-first)/first)*100
    if abs(change) < 5: return f"Stable — {change:.1f}% change over time.", "normal"
    if change < 0:
        if last < md["low"]: return f"Dropped {abs(change):.1f}% — below normal. Talk to your doctor.", "danger"
        return f"Drifting down {abs(change):.1f}% over time — worth watching.", "warning"
    if last > md["high"]: return f"Risen {change:.1f}% — above normal. Talk to your doctor.", "danger"
    return f"Drifting up {change:.1f}% over time — worth watching.", "warning"

def bar_pct(value, md):
    low, high = md["low"], md["high"]
    if high == low: return 50
    pct = ((value - low) / (high - low)) * 70 + 15
    return max(5, min(95, pct))

def bar_color(flag_class):
    if flag_class == "normal": return "#22C55E"
    if flag_class == "danger": return "#EF4444"
    return "#F59E0B"

# ── LOAD ──────────────────────────────────────────────────────────────────────

df = load_data()
profiles_df = load_profiles()
feedback_df = load_feedback()

if "show_app" not in st.session_state:
    st.session_state["show_app"] = False
if "extracted_values" not in st.session_state:
    st.session_state["extracted_values"] = {}

logo_img = f'<img src="data:image/png;base64,{logo_base64}" style="width:38px;height:38px;border-radius:10px;object-fit:cover;"/>' if logo_base64 else ""

# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state["show_app"]:

    st.markdown(f"""
    <div class="t-nav">
        <div class="t-nav-left">
            {logo_img}
            <div>
                <div class="t-nav-brand">Trace</div>
                <div class="t-nav-sub">Biomarker Timeline</div>
            </div>
        </div>
        <div class="t-nav-right">
            <div class="t-nav-private">Your data stays private</div>
            <div class="t-nav-badge">Beta</div>
        </div>
    </div>

    <div class="t-hero">
        <div class="t-hero-tag">Introducing Trace</div>
        <div class="t-hero-title">Your blood tests are<br>telling a story</div>
        <div class="t-hero-sub">
            Track your biomarkers over months and years.<br>
            Catch drift before it becomes disease.<br>
            Finally understand what your body has been saying.
        </div>
        <div class="t-pills">
            <div class="t-pill">40+ Biomarkers</div>
            <div class="t-pill">AI Health Stories</div>
            <div class="t-pill">PDF Auto-Extract</div>
            <div class="t-pill">Drift Detection</div>
            <div class="t-pill">Family Vault</div>
            <div class="t-pill">Indian Lab Ranges</div>
        </div>
        <div class="t-hero-privacy">Your data never leaves your device</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([2,2,2])
    with col_b:
        if st.button("Begin Your Timeline →"):
            st.session_state["show_app"] = True
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="t-card" style="text-align:center; padding:24px 20px;">
            <div style="font-size:28px; margin-bottom:12px;">📈</div>
            <div style="font-size:14px; font-weight:800; color:#0F172A; margin-bottom:8px;">Track</div>
            <div style="font-size:12px; color:#64748B; line-height:1.7; font-weight:500;">Upload your lab PDF or enter values manually. Your timeline builds automatically over time.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="t-card" style="text-align:center; padding:24px 20px;">
            <div style="font-size:28px; margin-bottom:12px;">🔍</div>
            <div style="font-size:14px; font-weight:800; color:#0F172A; margin-bottom:8px;">Detect</div>
            <div style="font-size:12px; color:#64748B; line-height:1.7; font-weight:500;">Watch your markers drift over months. Catch changes before they cross danger thresholds.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="t-card" style="text-align:center; padding:24px 20px;">
            <div style="font-size:28px; margin-bottom:12px;">💬</div>
            <div style="font-size:14px; font-weight:800; color:#0F172A; margin-bottom:8px;">Understand</div>
            <div style="font-size:12px; color:#64748B; line-height:1.7; font-weight:500;">AI reads your entire biomarker history and explains it in plain language you actually understand.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="t-footer">
        {logo_img}
        <div class="t-footer-brand">Trace</div>
        <div class="t-footer-sub">Your blood tests are telling a story. This is where you read it.</div>
        <div class="t-footer-privacy">Your data never leaves your device</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="t-nav">
    <div class="t-nav-left">
        {logo_img}
        <div>
            <div class="t-nav-brand">Trace</div>
            <div class="t-nav-sub">Biomarker Timeline</div>
        </div>
    </div>
    <div class="t-nav-right">
        <div class="t-nav-private">Private</div>
        <div class="t-nav-badge">Beta</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["  Log Test  ", "  My Timeline  ", "  Profiles  "])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOG TEST
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("<br>", unsafe_allow_html=True)

    if profiles_df.empty:
        st.markdown("""
        <div class="t-onboard">
            <div style="font-size:36px; margin-bottom:16px;">👋</div>
            <div class="t-onboard-title">Welcome to Trace!</div>
            <div class="t-onboard-sub">Get started in three simple steps</div>
            <div class="t-step">
                <div class="t-step-num">1</div>
                <div class="t-step-text"><strong>Create your profile</strong> in the Profiles tab. Add your name, date of birth, gender and health context. Takes under a minute.</div>
            </div>
            <div class="t-step">
                <div class="t-step-num">2</div>
                <div class="t-step-text"><strong>Log your first test</strong> here. Upload a PDF blood report and AI fills values automatically. Or enter them manually.</div>
            </div>
            <div class="t-step">
                <div class="t-step-num">3</div>
                <div class="t-step-text"><strong>See your timeline.</strong> AI reads your biomarker history and tells you what your body has been saying in plain language.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_form, col_side = st.columns([3, 2])

        with col_side:
            st.markdown('<div class="t-card">', unsafe_allow_html=True)
            st.markdown('<div class="t-section">Select Profile</div>', unsafe_allow_html=True)
            profile_names = profiles_df["Name"].tolist()
            selected_profile = st.selectbox("Who is this test for?", profile_names)
            pr = profiles_df[profiles_df["Name"]==selected_profile].iloc[0]
            gender = pr["Gender"]
            age = calculate_age(pr["DOB"])
            conditions = pr.get("Conditions","None")
            diet = pr.get("Diet","Vegetarian")
            blood_group = pr.get("Blood Group","—")
            st.markdown(f"""
            <div style="background:#F8FAFC; border-radius:10px; padding:12px 14px; margin-top:12px; border:1px solid #E2E8F0;">
                <div style="font-size:13px; font-weight:700; color:#0F172A;">{selected_profile}</div>
                <div style="font-size:12px; color:#64748B; margin-top:4px; font-weight:500; line-height:1.8;">
                    {gender} · {age} years · {blood_group}<br>
                    {diet} · {conditions}
                </div>
                <div style="font-size:11px; color:#0EA5E9; margin-top:6px; font-weight:700;">Ranges calibrated for your profile</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="t-card" style="margin-top:12px;">', unsafe_allow_html=True)
            st.markdown('<div class="t-section">Upload PDF Report</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px; color:#94A3B8; margin-bottom:12px; font-weight:500;">AI reads your lab report and fills values automatically.</div>', unsafe_allow_html=True)
            uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
            if uploaded_pdf:
                if st.button("Extract from PDF →"):
                    with st.spinner("Reading your report..."):
                        markers_temp = get_markers(gender, age)
                        pdf_text = extract_text_from_pdf(uploaded_pdf)
                        if not pdf_text.strip():
                            st.error("This PDF could not be read. Please enter values manually below.")
                        else:
                            extracted = extract_values_with_ai(pdf_text, markers_temp, gender, age)
                            if extracted:
                                st.session_state["extracted_values"] = extracted
                                st.success(f"{len(extracted)} values found. Review and save below.")
                            else:
                                st.warning("Could not read values clearly. Please enter manually below.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_form:
            markers = get_markers(gender, age)
            panels = {}
            for marker, mdata in markers.items():
                p = mdata["panel"]
                if p not in panels: panels[p] = {}
                panels[p][marker] = mdata

            st.markdown('<div class="t-card">', unsafe_allow_html=True)
            st.markdown('<div class="t-section">Test Date</div>', unsafe_allow_html=True)
            test_date = st.date_input("", value=date.today(), label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)

            extracted_vals = st.session_state.get("extracted_values", {})
            if extracted_vals:
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:12px 16px; margin-bottom:12px;">
                    <div style="font-size:13px; font-weight:700; color:#166534;">
                        {len(extracted_vals)} values extracted from PDF — review and save below
                    </div>
                </div>
                """, unsafe_allow_html=True)

            values = {}
            for panel_name, panel_markers in panels.items():
                with st.expander(f"  {panel_name}", expanded=(panel_name=="Complete Blood Count")):
                    c1, c2 = st.columns(2)
                    for i, (marker, mdata) in enumerate(panel_markers.items()):
                        with c1 if i%2==0 else c2:
                            dv = float(extracted_vals.get(marker, 0.0))
                            dv = min(max(dv, mdata["min"]), mdata["max"])
                            info = MARKER_INFO.get(marker,"")
                            values[marker] = st.number_input(
                                marker,
                                min_value=mdata["min"],
                                max_value=mdata["max"],
                                value=dv,
                                help=f"{info} | Normal: {mdata['low']} – {mdata['high']}"
                            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save Test →"):
                new_row = {"Name": selected_profile, "Date": str(test_date), "Gender": gender, "Age": age}
                new_row.update(values)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.session_state["extracted_values"] = {}
                st.success(f"Test saved for {selected_profile} on {test_date}. Go to My Timeline to see your story.")
                st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty or profiles_df.empty:
        st.markdown("""
        <div class="t-onboard">
            <div style="font-size:36px; margin-bottom:12px;">📊</div>
            <div class="t-onboard-title">No timeline yet</div>
            <div class="t-onboard-sub">Create a profile and log your first test to see your biomarker story here.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_sel, _ = st.columns([2, 4])
        with col_sel:
            selected_name = st.selectbox("", profiles_df["Name"].tolist(), label_visibility="collapsed")

        pr = profiles_df[profiles_df["Name"]==selected_name].iloc[0]
        gender = pr["Gender"]
        age = calculate_age(pr["DOB"])
        conditions = pr.get("Conditions","None")
        diet = pr.get("Diet","Vegetarian")
        blood_group = pr.get("Blood Group","—")
        markers = get_markers(gender, age)
        person_df = df[df["Name"]==selected_name].copy() if "Name" in df.columns else pd.DataFrame()

        if person_df.empty:
            st.markdown("""
            <div class="t-onboard">
                <div class="t-onboard-sub">No tests logged for this profile yet. Go to Log Test to add your first blood test.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            person_df["Date"] = pd.to_datetime(person_df["Date"])
            person_df = person_df.sort_values("Date")
            num_tests = len(person_df)
            analytics = compute_analytics(person_df, markers)

            score_color = "#22C55E" if analytics["score"] >= 75 else "#F59E0B" if analytics["score"] >= 50 else "#EF4444"
            score_bg = "#F0FDF4" if analytics["score"] >= 75 else "#FFFBEB" if analytics["score"] >= 50 else "#FEF2F2"

            st.markdown(f"""
            <div class="t-score-card">
                <div class="t-score-circle" style="background:{score_bg}; border-color:{score_color}; color:{score_color};">
                    {analytics["score"]}
                </div>
                <div>
                    <div class="t-score-title">{selected_name}'s Health Score</div>
                    <div class="t-score-sub">
                        {analytics["normal"]} normal · {analytics["warning"]} drifting · {analytics["danger"]} critical<br>
                        {num_tests} tests recorded · {gender} · {age} years · {blood_group}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f'<div class="t-stat"><div class="t-stat-num" style="color:#22C55E;">{analytics["normal"]}</div><div class="t-stat-label">Normal</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="t-stat"><div class="t-stat-num" style="color:#F59E0B;">{analytics["warning"]}</div><div class="t-stat-label">Drifting</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="t-stat"><div class="t-stat-num" style="color:#EF4444;">{analytics["danger"]}</div><div class="t-stat-label">Critical</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="t-stat"><div class="t-stat-num" style="color:#0EA5E9;">+{analytics["improved"]}</div><div class="t-stat-label">Improved</div></div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div class="t-stat"><div class="t-stat-num">{num_tests}</div><div class="t-stat-label">Tests</div></div>', unsafe_allow_html=True)

            alerts = get_trend_alerts(person_df, markers)
            if alerts:
                st.markdown('<div class="t-section">Trend Alerts</div>', unsafe_allow_html=True)
                for alert in alerts:
                    st.markdown(f"""
                    <div class="t-alert">
                        <div class="t-alert-dot"></div>
                        <div class="t-alert-text">{alert}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if analytics["best_marker"] or analytics["worst_marker"]:
                st.markdown('<div class="t-section">Key Insights</div>', unsafe_allow_html=True)
                st.markdown('<div class="t-card">', unsafe_allow_html=True)
                if analytics["best_marker"]:
                    st.markdown(f"""
                    <div class="t-insight">
                        <div class="t-insight-dot" style="background:#22C55E;"></div>
                        <div>
                            <div class="t-insight-label" style="color:#22C55E;">Strongest marker</div>
                            <div class="t-insight-text">{analytics["best_marker"]} — {analytics["best_val"]}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                if analytics["worst_marker"]:
                    st.markdown(f"""
                    <div class="t-insight">
                        <div class="t-insight-dot" style="background:#F59E0B;"></div>
                        <div>
                            <div class="t-insight-label" style="color:#F59E0B;">Needs attention</div>
                            <div class="t-insight-text">{analytics["worst_marker"]} — {analytics["worst_val"]}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="t-section">Your Health Story</div>', unsafe_allow_html=True)
            with st.spinner("Reading your biomarker story..."):
                ai_story = get_ai_analysis(selected_name, person_df, gender, age, conditions, diet)
            st.markdown(f"""
            <div class="t-card-blue">
                <div class="t-ai-label">AI Analysis — {selected_name} · {gender} · {age}y · {diet}</div>
                <div class="t-ai-text">{ai_story}</div>
            </div>
            <p class="t-disclaimer">For educational purposes only. Always consult your doctor for medical advice.</p>
            """, unsafe_allow_html=True)

            wa_text = whatsapp_summary(selected_name, person_df, markers)
            wa_url = f"https://wa.me/?text={wa_text.replace(chr(10),'%0A').replace(' ','%20')}"
            st.markdown(f"""
            <div class="t-share">
                <div class="t-share-text">Share your health summary with your doctor or family via WhatsApp</div>
                <a href="{wa_url}" target="_blank" style="
                    background:#22C55E; color:white; padding:9px 18px;
                    border-radius:10px; text-decoration:none; font-size:12px;
                    font-weight:800; white-space:nowrap; font-family:'Nunito',sans-serif;
                ">Share on WhatsApp</a>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="t-section">Detailed Biomarker Trends</div>', unsafe_allow_html=True)

            panels = {}
            for marker, mdata in markers.items():
                p = mdata["panel"]
                if p not in panels: panels[p] = {}
                panels[p][marker] = mdata

            for panel_name, panel_markers in panels.items():
                has_data = any(
                    mk in person_df.columns and (person_df[mk]>0).any()
                    for mk in panel_markers
                )
                if not has_data: continue

                st.markdown(f'<div class="t-panel-head">{panel_name}</div>', unsafe_allow_html=True)

                for marker, mdata in panel_markers.items():
                    if marker not in person_df.columns: continue
                    series = person_df[marker]
                    sc = series.dropna()
                    sc = sc[sc > 0]
                    if len(sc) == 0: continue

                    latest = sc.iloc[-1]
                    flag_text, flag_class = get_flag(latest, mdata)
                    trend_msg, trend_color = get_trend_msg(series, mdata)
                    info = MARKER_INFO.get(marker,"")

                    trend_css = {
                        "normal": "t-trend-normal",
                        "warning": "t-trend-warning",
                        "danger": "t-trend-danger",
                        "neutral": "t-trend-neutral"
                    }.get(trend_color, "t-trend-neutral")

                    badge_css = {
                        "normal": "t-badge-normal",
                        "danger": "t-badge-danger"
                    }.get(flag_class, "t-badge-warning") if flag_class else ""

                    flag_html = f'<span class="t-badge {badge_css}">{latest} — {flag_text}</span>' if flag_text else ""
                    pct = bar_pct(latest, mdata) if flag_text else 50
                    bc = bar_color(flag_class) if flag_class else "#94A3B8"

                    st.markdown(f"""
                    <div class="t-marker">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div style="flex:1;">
                                <div class="t-marker-name">{marker}</div>
                                <div class="t-marker-info">{info}</div>
                                <div class="t-trend {trend_css}">{trend_msg}</div>
                                <div class="t-marker-range">Normal: {mdata['low']} – {mdata['high']}</div>
                            </div>
                            <div style="margin-left:12px; flex-shrink:0;">{flag_html}</div>
                        </div>
                        <div class="t-bar-wrap"><div class="t-bar" style="width:{pct}%; background:{bc};"></div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if len(sc) >= 2:
                        fig = go.Figure()
                        fig.add_hrect(y0=mdata["low"], y1=mdata["high"],
                            fillcolor="rgba(34,197,94,0.06)", line_width=0)
                        fig.add_trace(go.Scatter(
                            x=person_df["Date"], y=person_df[marker],
                            mode="lines+markers",
                            line=dict(color="#0EA5E9", width=2.5),
                            marker=dict(size=7, color="#0EA5E9",
                                line=dict(color="white", width=2)),
                            fill="tozeroy",
                            fillcolor="rgba(14,165,233,0.06)"
                        ))
                        fig.add_hline(y=mdata["high"], line_dash="dot",
                            line_color="rgba(239,68,68,0.35)", line_width=1.5)
                        fig.add_hline(y=mdata["low"], line_dash="dot",
                            line_color="rgba(239,68,68,0.35)", line_width=1.5)
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            height=180,
                            margin=dict(l=0,r=0,t=8,b=0),
                            showlegend=False,
                            xaxis=dict(showgrid=False, showline=False,
                                tickfont=dict(color="#94A3B8", size=10, family="Nunito")),
                            yaxis=dict(showgrid=True,
                                gridcolor="rgba(226,232,240,0.8)",
                                showline=False,
                                tickfont=dict(color="#94A3B8", size=10, family="Nunito"))
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div class="t-feedback">
                <div class="t-feedback-title">How did this feel?</div>
                <div class="t-feedback-sub">Trace is built for you. Tell us what you felt, what confused you, or what you wish existed. Every message is read personally.</div>
            </div>
            """, unsafe_allow_html=True)

            rating = st.radio("", ["1","2","3","4","5"], horizontal=True, label_visibility="collapsed")
            st.markdown('<div style="font-size:11px; color:#CBD5E1; font-weight:600; margin-bottom:12px;">1 — Poor &nbsp; 5 — Amazing</div>', unsafe_allow_html=True)
            feedback_text = st.text_area("", placeholder="What did you feel? What confused you? What do you wish Trace could do?", height=100, label_visibility="collapsed")
            feedback_email = st.text_input("", placeholder="Email — optional, only if you'd like us to respond", label_visibility="collapsed")

            col_btn, _ = st.columns([1,2])
            with col_btn:
                if st.button("Send Feedback →"):
                    if not feedback_text.strip():
                        st.error("Please write something before sending.")
                    else:
                        new_fb = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Name": selected_name, "Rating": rating,
                            "Message": feedback_text, "Email": feedback_email
                        }])
                        feedback_df = pd.concat([feedback_df, new_fb], ignore_index=True)
                        save_feedback(feedback_df)
                        st.success("Received. Thank you so much.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PROFILES
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_new, col_existing = st.columns([2, 3])

    with col_new:
        st.markdown('<div class="t-card">', unsafe_allow_html=True)
        st.markdown('<div class="t-section">Create Profile</div>', unsafe_allow_html=True)
        new_name = st.text_input("Full Name", placeholder="e.g. Arman Khan", key="new_name")
        new_dob = st.date_input("Date of Birth", value=date(2000,1,1),
            min_value=date(1920,1,1), max_value=date.today(), key="new_dob")
        new_gender = st.selectbox("Gender", ["Male","Female","Other"], key="new_gender")
        new_blood = st.selectbox("Blood Group",
            ["A+","A-","B+","B-","AB+","AB-","O+","O-","Unknown"], key="new_blood")
        new_conditions = st.multiselect("Known Conditions",
            ["Diabetes","Thyroid Disorder","Hypertension","PCOS","Heart Disease","Kidney Disease","None"],
            default=["None"], key="new_conditions")
        new_diet = st.selectbox("Diet Type",
            ["Vegetarian","Non-Vegetarian","Vegan","Eggetarian"], key="new_diet")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Profile →"):
            if not new_name:
                st.error("Please enter a name.")
            elif new_name in profiles_df["Name"].tolist():
                st.warning("A profile with this name already exists.")
            else:
                new_profile = pd.DataFrame([{
                    "Name": new_name, "DOB": str(new_dob),
                    "Gender": new_gender, "Blood Group": new_blood,
                    "Conditions": ", ".join(new_conditions), "Diet": new_diet
                }])
                profiles_df = pd.concat([profiles_df, new_profile], ignore_index=True)
                save_profiles(profiles_df)
                st.success(f"Profile created for {new_name}.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_existing:
        st.markdown('<div class="t-section">Your Profiles</div>', unsafe_allow_html=True)
        if profiles_df.empty:
            st.markdown("""
            <div class="t-card" style="text-align:center; padding:32px;">
                <div style="font-size:32px; margin-bottom:12px;">👤</div>
                <div style="font-size:14px; font-weight:700; color:#0F172A; margin-bottom:4px;">No profiles yet</div>
                <div style="font-size:12px; color:#94A3B8; font-weight:500;">Create your first profile to get started</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for _, row in profiles_df.iterrows():
                tc = len(df[df["Name"]==row["Name"]]) if not df.empty and "Name" in df.columns else 0
                a = calculate_age(row["DOB"])
                st.markdown(f"""
                <div class="t-marker" style="margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div class="t-marker-name">{row['Name']}</div>
                            <div class="t-marker-info" style="margin-top:4px; line-height:1.8;">
                                {row['Gender']} · {a} years · {row.get('Blood Group','—')}<br>
                                {row.get('Diet','—')} · {row.get('Conditions','None')}
                            </div>
                        </div>
                        <span class="t-badge t-badge-normal">{tc} tests</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if not feedback_df.empty:
            st.markdown('<div class="t-section">Feedback Received</div>', unsafe_allow_html=True)
            for _, fb in feedback_df.iterrows():
                email_html = f'<div style="font-size:11px; color:#CBD5E1; margin-top:4px; font-weight:500;">{fb["Email"]}</div>' if pd.notna(fb.get("Email")) and str(fb.get("Email","")).strip() else ""
                st.markdown(f"""
                <div class="t-marker" style="margin-bottom:10px;">
                    <div style="font-size:11px; font-weight:700; color:#0EA5E9; margin-bottom:6px; letter-spacing:1px;">
                        {fb['Rating']}/5 · {fb['Name']} · {fb['Timestamp']}
                    </div>
                    <div style="font-size:13px; color:#475569; line-height:1.6; font-weight:500;">"{fb['Message']}"</div>
                    {email_html}
                </div>
                """, unsafe_allow_html=True)

st.markdown(f"""
<div class="t-footer">
    {logo_img}
    <div class="t-footer-brand">Trace</div>
    <div class="t-footer-sub">Your blood tests are telling a story. This is where you read it.</div>
    <div class="t-footer-privacy">Your data never leaves your device</div>
</div>
""", unsafe_allow_html=True)
