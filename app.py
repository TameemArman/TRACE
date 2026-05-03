import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
    "Hemoglobin (g/dL)": "Carries oxygen in your blood. Low levels cause fatigue and weakness.",
    "RBC Count (million/µL)": "Red blood cells that carry oxygen throughout your body.",
    "WBC Count (thousand/µL)": "White blood cells that fight infection.",
    "Platelets (thousand/µL)": "Help your blood clot when injured.",
    "Hematocrit (%)": "Percentage of blood made up of red blood cells.",
    "TSH (mIU/L)": "Controls your thyroid. Think of it as the remote control for your thyroid gland.",
    "T3 Total (ng/dL)": "Active thyroid hormone controlling metabolism and energy.",
    "T4 Total (µg/dL)": "Thyroid hormone that converts to T3.",
    "Free T3 (pg/mL)": "Active form of thyroid hormone available to your cells.",
    "Free T4 (ng/dL)": "Unbound thyroid hormone ready to convert to T3.",
    "Fasting Glucose (mg/dL)": "Blood sugar after fasting. First sign of diabetes risk.",
    "HbA1c (%)": "Average blood sugar over 3 months. Most important diabetes marker.",
    "Post Prandial Glucose (mg/dL)": "Blood sugar 2 hours after eating.",
    "Fasting Insulin (µIU/mL)": "Insulin when fasting. High levels indicate insulin resistance.",
    "Total Cholesterol (mg/dL)": "Total fat in blood. Needs context — not all cholesterol is bad.",
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
    "Vitamin D (ng/mL)": "Essential for bones, immunity, and mood. Very common deficiency in India.",
    "Vitamin B12 (pg/mL)": "Critical for nerves and blood. Vegetarians at high risk.",
    "Ferritin (ng/mL)": "Iron storage. Low ferritin means low iron even if hemoglobin looks normal.",
    "Serum Iron (µg/dL)": "Iron circulating in blood.",
    "Calcium (mg/dL)": "Essential for bones, muscles, and nerve function.",
    "Magnesium (mg/dL)": "Involved in 300+ body processes. Low levels cause muscle cramps.",
    "Phosphorus (mg/dL)": "Works with calcium for bone health and energy.",
    "Folate (ng/mL)": "B vitamin essential for cell growth. Critical during pregnancy.",
    "Zinc (µg/dL)": "Essential for immunity and wound healing.",
    "Testosterone Total (ng/dL)": "Primary male hormone affecting energy, muscle, and mood.",
    "Estradiol (pg/mL)": "Primary female hormone affecting cycle and bone density.",
    "FSH (mIU/mL)": "Controls egg and sperm production. Key fertility marker.",
    "LH (mIU/mL)": "Triggers ovulation in women and testosterone in men.",
    "Cortisol Morning (µg/dL)": "Stress hormone. Should be highest in morning.",
    "CRP (mg/L)": "Inflammation marker. Elevated with infection or chronic disease.",
    "ESR (mm/hr)": "General inflammation marker.",
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

    * {{ font-family: 'Space Grotesk', sans-serif; }}

    .stApp {{
        background: #05050f;
        background-image:
            radial-gradient(ellipse at 20% 50%, rgba(245,166,35,0.04) 0%, transparent 60%),
            radial-gradient(ellipse at 80% 20%, rgba(255,140,0,0.03) 0%, transparent 50%);
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    .main .block-container {{
        padding: 2.5rem 4rem;
        max-width: 1300px;
    }}

    /* NAVBAR */
    .navbar {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 1rem 0 2rem 0;
        border-bottom: 1px solid rgba(245,166,35,0.12);
        margin-bottom: 2.5rem;
    }}
    .nav-logo {{ display: flex; align-items: center; gap: 1rem; }}
    .nav-logo img {{ width: 44px; height: 44px; border-radius: 10px; }}
    .nav-brand {{
        font-family: 'Space Mono', monospace;
        font-size: 1.5rem; font-weight: 700;
        letter-spacing: 8px; color: #ffffff; text-transform: uppercase;
    }}
    .nav-tagline {{
        font-size: 0.7rem; color: rgba(245,166,35,0.7);
        letter-spacing: 3px; text-transform: uppercase; margin-top: 0.15rem;
    }}
    .nav-right {{
        display: flex; align-items: center; gap: 1.5rem;
    }}
    .nav-private {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 2px;
        color: rgba(0,230,118,0.6); text-transform: uppercase;
    }}
    .nav-badge {{
        background: rgba(245,166,35,0.06);
        border: 1px solid rgba(245,166,35,0.18);
        color: rgba(245,166,35,0.75);
        padding: 0.28rem 0.85rem;
        border-radius: 20px; font-size: 0.7rem;
        letter-spacing: 2px; text-transform: uppercase;
        font-family: 'Space Mono', monospace;
    }}

    /* CARDS */
    .glass-card {{
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 18px; padding: 2rem; margin: 1rem 0;
    }}
    .glow-card {{
        background: rgba(245,166,35,0.03);
        border: 1px solid rgba(245,166,35,0.12);
        border-radius: 18px; padding: 2rem; margin: 1rem 0;
    }}
    .marker-card {{
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px; padding: 1.4rem; margin: 0.8rem 0;
        transition: border-color 0.2s ease;
    }}
    .marker-card:hover {{
        border-color: rgba(245,166,35,0.18);
    }}

    /* ANALYTICS */
    .score-ring {{
        text-align: center; padding: 2rem 1rem;
    }}
    .score-number {{
        font-family: 'Space Mono', monospace;
        font-size: 4rem; font-weight: 700;
        color: #F5A623; line-height: 1;
    }}
    .score-label {{
        font-size: 0.65rem; letter-spacing: 4px;
        text-transform: uppercase; color: rgba(255,255,255,0.35);
        margin-top: 0.5rem;
    }}
    .score-bar {{
        height: 2px;
        background: linear-gradient(90deg, #F5A623, rgba(245,166,35,0.1));
        border-radius: 2px; margin: 0.8rem auto;
        max-width: 80px;
    }}
    .analytics-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem; margin: 1rem 0;
    }}
    .analytics-cell {{
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px; padding: 1.2rem;
        text-align: center;
    }}
    .analytics-number {{
        font-family: 'Space Mono', monospace;
        font-size: 1.8rem; font-weight: 700; line-height: 1;
    }}
    .analytics-label {{
        font-size: 0.65rem; letter-spacing: 2px;
        text-transform: uppercase; margin-top: 0.4rem;
        color: rgba(255,255,255,0.4);
    }}
    .insight-row {{
        display: flex; align-items: flex-start;
        gap: 1rem; padding: 1rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }}
    .insight-row:last-child {{ border-bottom: none; }}
    .insight-dot {{
        width: 6px; height: 6px; border-radius: 50%;
        flex-shrink: 0; margin-top: 0.4rem;
    }}
    .insight-text {{
        font-size: 0.88rem;
        color: rgba(255,255,255,0.7); line-height: 1.6;
    }}
    .insight-label {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 2px;
        text-transform: uppercase; margin-bottom: 0.2rem;
    }}

    /* STAT CARDS */
    .stat-card {{
        background: rgba(245,166,35,0.04);
        border: 1px solid rgba(245,166,35,0.12);
        border-radius: 12px; padding: 1.2rem; text-align: center;
    }}
    .stat-number {{
        font-family: 'Space Mono', monospace;
        font-size: 2rem; font-weight: 700;
        color: #F5A623; line-height: 1;
    }}
    .stat-label {{
        font-size: 0.65rem; color: rgba(255,255,255,0.45);
        text-transform: uppercase; letter-spacing: 2px; margin-top: 0.4rem;
    }}

    /* AI STORY */
    .ai-story-container {{
        background: linear-gradient(135deg, rgba(245,166,35,0.06) 0%, rgba(255,140,0,0.03) 100%);
        border: 1px solid rgba(245,166,35,0.18);
        border-radius: 18px; padding: 2rem 2.5rem;
        margin: 1rem 0; position: relative; overflow: hidden;
    }}
    .ai-story-container::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(245,166,35,0.4), transparent);
    }}
    .ai-label {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 3px; text-transform: uppercase;
        color: rgba(245,166,35,0.6); margin-bottom: 1rem;
    }}
    .ai-story-text {{
        font-size: 1.02rem; color: rgba(255,255,255,0.85);
        line-height: 1.9; font-weight: 300;
    }}

    /* MARKERS */
    .marker-name {{
        font-family: 'Space Mono', monospace;
        font-size: 0.78rem; letter-spacing: 2px;
        color: rgba(255,255,255,0.92); text-transform: uppercase;
    }}
    .marker-info {{
        font-size: 0.8rem; color: rgba(255,255,255,0.42);
        margin-top: 0.2rem; line-height: 1.5;
    }}
    .marker-trend {{
        font-size: 0.83rem; margin-top: 0.35rem;
    }}
    .panel-header {{
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem; letter-spacing: 5px; text-transform: uppercase;
        color: rgba(245,166,35,0.5); margin: 2rem 0 1rem 0;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid rgba(245,166,35,0.1);
    }}

    /* FLAGS */
    .flag {{
        display: inline-block; padding: 0.2rem 0.8rem;
        border-radius: 20px; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
        font-family: 'Space Mono', monospace;
    }}
    .flag-normal {{
        background: rgba(0,230,118,0.07);
        border: 1px solid rgba(0,230,118,0.22); color: #00e676;
    }}
    .flag-warning {{
        background: rgba(245,166,35,0.07);
        border: 1px solid rgba(245,166,35,0.25); color: #F5A623;
    }}
    .flag-danger {{
        background: rgba(255,75,75,0.07);
        border: 1px solid rgba(255,75,75,0.25); color: #ff4b4b;
    }}

    /* SECTION LABELS */
    .section-label {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 4px; text-transform: uppercase;
        color: rgba(245,166,35,0.55); margin-bottom: 1rem; margin-top: 2rem;
    }}

    /* ALERT */
    .alert-row {{
        display: flex; align-items: flex-start; gap: 0.8rem;
        padding: 0.9rem 1.2rem;
        background: rgba(245,166,35,0.04);
        border: 1px solid rgba(245,166,35,0.12);
        border-radius: 10px; margin: 0.5rem 0;
    }}
    .alert-line {{
        width: 2px; height: 100%; min-height: 18px;
        background: #F5A623; border-radius: 2px; flex-shrink: 0;
    }}
    .alert-text {{
        font-size: 0.85rem; color: rgba(255,255,255,0.7); line-height: 1.5;
    }}

    /* SHARE */
    .share-row {{
        display: flex; align-items: center; gap: 1rem;
        padding: 1.2rem 1.5rem;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px; margin: 1rem 0;
    }}

    /* FEEDBACK */
    .feedback-section {{
        margin: 4rem 0 1rem 0;
        padding-top: 2rem;
        border-top: 1px solid rgba(255,255,255,0.05);
    }}
    .feedback-heading {{
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem; letter-spacing: 5px;
        text-transform: uppercase; color: rgba(255,255,255,0.5);
        margin-bottom: 0.4rem;
    }}
    .feedback-sub {{
        font-size: 0.88rem; color: rgba(255,255,255,0.38);
        line-height: 1.7; margin-bottom: 1.5rem;
    }}

    /* RATING */
    .rating-option {{
        display: inline-block;
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem; letter-spacing: 1px;
    }}

    /* ONBOARDING */
    .onboarding-wrap {{
        padding: 3rem 2rem; text-align: center;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px; margin: 2rem 0;
    }}
    .onboarding-title {{
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem; letter-spacing: 6px;
        color: #F5A623; text-transform: uppercase; margin-bottom: 0.5rem;
    }}
    .onboarding-sub {{
        font-size: 0.88rem; color: rgba(255,255,255,0.4);
        margin-bottom: 2.5rem;
    }}
    .step-line {{
        display: flex; align-items: flex-start;
        gap: 1.5rem; text-align: left;
        padding: 1rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }}
    .step-line:last-child {{ border-bottom: none; }}
    .step-num {{
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem; color: rgba(245,166,35,0.6);
        letter-spacing: 1px; flex-shrink: 0; padding-top: 0.1rem;
    }}
    .step-desc {{
        font-size: 0.88rem; color: rgba(255,255,255,0.6); line-height: 1.6;
    }}
    .step-desc strong {{ color: rgba(255,255,255,0.88); }}

    /* LANDING */
    .landing-hero {{
        text-align: center; padding: 5rem 2rem 3rem 2rem;
    }}
    .landing-eyebrow {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 5px;
        text-transform: uppercase; color: rgba(245,166,35,0.6);
        margin-bottom: 1.5rem;
    }}
    .landing-title {{
        font-family: 'Space Mono', monospace;
        font-size: 5rem; font-weight: 700; letter-spacing: 16px;
        color: #ffffff; text-transform: uppercase; margin-bottom: 1.2rem;
        text-shadow: 0 0 100px rgba(245,166,35,0.12);
    }}
    .landing-subtitle {{
        font-size: 1.1rem; color: rgba(255,255,255,0.5);
        font-weight: 300; max-width: 520px;
        margin: 0 auto 0.8rem auto; line-height: 1.9;
    }}
    .landing-quote {{
        font-family: 'Space Mono', monospace;
        font-size: 0.78rem; color: rgba(245,166,35,0.65);
        letter-spacing: 1px; margin-bottom: 3rem;
    }}
    .feature-table {{
        max-width: 600px; margin: 2.5rem auto;
        border-top: 1px solid rgba(255,255,255,0.06);
    }}
    .feature-row {{
        display: flex; justify-content: space-between;
        align-items: center; padding: 0.9rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }}
    .feature-name {{
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem; letter-spacing: 1px; color: #F5A623;
    }}
    .feature-desc {{
        font-size: 0.82rem; color: rgba(255,255,255,0.4);
        text-align: right;
    }}
    .privacy-line {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem; letter-spacing: 3px;
        text-transform: uppercase;
        color: rgba(0,230,118,0.5); margin-top: 1.5rem;
    }}
    .landing-card {{
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px; padding: 2rem 1.5rem; text-align: center;
    }}
    .landing-card-symbol {{
        font-family: 'Space Mono', monospace;
        font-size: 1.5rem; color: #F5A623; margin-bottom: 1rem;
    }}
    .landing-card-title {{
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem; letter-spacing: 3px; color: rgba(255,255,255,0.7);
        text-transform: uppercase; margin-bottom: 0.8rem;
    }}
    .landing-card-text {{
        font-size: 0.85rem; color: rgba(255,255,255,0.4); line-height: 1.7;
    }}

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {{
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; padding: 0.35rem; gap: 0.25rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px; color: rgba(255,255,255,0.4);
        font-weight: 500; letter-spacing: 1px; padding: 0.55rem 1.4rem;
        font-family: 'Space Mono', monospace; font-size: 0.78rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: rgba(245,166,35,0.08) !important;
        color: #F5A623 !important;
        border: 1px solid rgba(245,166,35,0.18) !important;
    }}

    /* INPUTS */
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 9px !important; color: white !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: rgba(245,166,35,0.45) !important;
        box-shadow: 0 0 0 2px rgba(245,166,35,0.08) !important;
    }}
    .stTextArea textarea {{
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 9px !important; color: white !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }}
    .stTextArea textarea:focus {{
        border-color: rgba(245,166,35,0.45) !important;
    }}
    .stButton button {{
        background: linear-gradient(135deg, #F5A623 0%, #FF8C00 100%) !important;
        color: #05050f !important; border: none !important;
        border-radius: 10px !important; padding: 0.7rem 2rem !important;
        font-weight: 700 !important; font-size: 0.82rem !important;
        letter-spacing: 3px !important; text-transform: uppercase !important;
        width: 100% !important; font-family: 'Space Mono', monospace !important;
    }}
    .stButton button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 28px rgba(245,166,35,0.3) !important;
    }}
    .stSelectbox > div > div, .stMultiSelect > div > div {{
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 9px !important; color: white !important;
    }}

    /* MISC */
    .disclaimer {{
        font-size: 0.7rem; color: rgba(255,255,255,0.25);
        text-align: center; margin-top: 0.8rem; letter-spacing: 0.5px;
    }}
    .footer {{
        text-align: center; padding: 3rem 0 1rem 0;
        border-top: 1px solid rgba(255,255,255,0.05); margin-top: 5rem;
    }}
    .footer-brand {{
        font-family: 'Space Mono', monospace; font-size: 0.75rem;
        letter-spacing: 8px; color: rgba(255,255,255,0.18); text-transform: uppercase;
    }}
    .footer-sub {{
        font-size: 0.7rem; color: rgba(255,255,255,0.18); margin-top: 0.4rem;
        letter-spacing: 0.5px;
    }}
    hr {{ border-color: rgba(255,255,255,0.05) !important; }}
    ::-webkit-scrollbar {{ width: 2px; }}
    ::-webkit-scrollbar-track {{ background: #05050f; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(245,166,35,0.25); border-radius: 2px; }}
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
    marker_list = "\n".join([f"- {m}" for m in markers.keys()])
    prompt = f"""You are a medical report parser. Extract biomarker values from this blood test report.
Markers to find:
{marker_list}
Report text:
{pdf_text[:4000]}
Return ONLY valid JSON. Keys = marker names, values = numeric values only.
Only include markers present in the report. No units. No explanation.
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
    best_marker = worst_marker = best_val_str = worst_val_str = ""
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
            score = 1 - abs(latest - (low + high)/2) / (rng/2)
            if score > best_score:
                best_score = score
                best_marker = marker
                best_val_str = f"{latest:.1f}"
        elif latest < low:
            danger += 1
            pct_off = (low - latest) / low * 100
            if pct_off < worst_score:
                worst_score = pct_off
                worst_marker = marker
                worst_val_str = f"{latest:.1f} — {pct_off:.0f}% below normal"
        else:
            warning += 1
            pct_off = (latest - high) / high * 100
            if pct_off < worst_score:
                worst_score = pct_off
                worst_marker = marker
                worst_val_str = f"{latest:.1f} — {pct_off:.0f}% above normal"

        if len(series) >= 2:
            change = series.iloc[-1] - series.iloc[-2]
            if low <= series.iloc[-1] <= high:
                if change > 0 and series.iloc[-2] < low:
                    improved += 1
                elif change < 0 and series.iloc[-2] > high:
                    improved += 1
            else:
                worsened += 1

    total = normal + warning + danger
    health_score = int((normal / total * 100)) if total > 0 else 0

    return {
        "score": health_score,
        "normal": normal,
        "warning": warning,
        "danger": danger,
        "improved": improved,
        "worsened": worsened,
        "best_marker": best_marker,
        "best_val": best_val_str,
        "worst_marker": worst_marker,
        "worst_val": worst_val_str,
        "total": total
    }

def get_trend_alerts(person_df, markers):
    alerts = []
    for marker, mdata in markers.items():
        if marker not in person_df.columns:
            continue
        series = person_df[marker].dropna()
        series = series[series > 0]
        if len(series) < 2:
            continue
        first = series.iloc[0]
        last = series.iloc[-1]
        change = ((last - first) / first) * 100
        if abs(change) >= 15 and mdata["low"] <= last <= mdata["high"]:
            d = "declining" if change < 0 else "rising"
            alerts.append(f"{marker} has been {d} {abs(change):.0f}% — still within range but drifting.")
        if len(series) >= 1:
            days = (pd.Timestamp.today() - pd.Timestamp(person_df["Date"].max())).days
            if days > 180:
                alerts.append(f"Last test was {days//30} months ago. Consider scheduling your next panel soon.")
                break
    return alerts[:3]

# ── AI ────────────────────────────────────────────────────────────────────────

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
            lines.append(f"{marker}: {first:.1f} → {last:.1f} ({change:+.1f}%)")
        elif len(series) == 1:
            lines.append(f"{marker}: {series.iloc[0]:.1f}")
    if not lines:
        return "Add at least 2 tests to generate your personal health story."
    prompt = f"""You are a warm health education assistant for Trace — an Indian biomarker tracking app.
Patient: {name}, {gender}, Age {age}, Diet: {diet}
Known Conditions: {conditions or 'None'}
Biomarker trends:
{chr(10).join(lines)}
Write 4-5 sentences. Simple language. Mention numbers naturally. Factor in diet and conditions.
Flag drifting markers calmly. Suggest 2 doctor questions. Never diagnose. End with encouragement."""
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

def get_trend_message(series, md):
    series = series.dropna()
    series = series[series > 0]
    if len(series) < 2: return "Add more tests to see your trend.", "neutral"
    first, last = series.iloc[0], series.iloc[-1]
    change = ((last-first)/first)*100
    if abs(change) < 5: return f"Stable — {change:.1f}% change.", "normal"
    if change < 0:
        if last < md["low"]: return f"Dropped {abs(change):.1f}% — below normal. Consult your doctor.", "danger"
        return f"Drifting down {abs(change):.1f}% — worth monitoring.", "warning"
    if last > md["high"]: return f"Risen {change:.1f}% — above normal. Consult your doctor.", "danger"
    return f"Drifting up {change:.1f}% — worth monitoring.", "warning"

def whatsapp_summary(name, person_df, markers):
    lines = [f"Health summary from Trace", f"Name: {name}", f"Tests logged: {len(person_df)}", ""]
    for marker, mdata in markers.items():
        if marker not in person_df.columns: continue
        s = person_df[marker].dropna()
        s = s[s > 0]
        if len(s) == 0: continue
        v = s.iloc[-1]
        tag = "Normal" if mdata["low"] <= v <= mdata["high"] else "Review"
        lines.append(f"{marker}: {v} — {tag}")
    lines += ["", "Track your biomarkers at gettrace.in"]
    return "\n".join(lines)

# ── INIT ──────────────────────────────────────────────────────────────────────

df = load_data()
profiles_df = load_profiles()
feedback_df = load_feedback()

if "show_app" not in st.session_state:
    st.session_state["show_app"] = False
if "extracted_values" not in st.session_state:
    st.session_state["extracted_values"] = {}

logo_html = f'<img src="data:image/png;base64,{logo_base64}" alt="Trace" style="width:44px;height:44px;border-radius:10px;"/>' if logo_base64 else "◈"

# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state["show_app"]:
    st.markdown(f"""
    <div class="navbar">
        <div class="nav-logo">
            {logo_html}
            <div>
                <div class="nav-brand">Trace</div>
                <div class="nav-tagline">Biomarker Timeline</div>
            </div>
        </div>
        <div class="nav-right">
            <div class="nav-private">§ Private by design</div>
            <div class="nav-badge">Beta</div>
        </div>
    </div>
    <div class="landing-hero">
        <div class="landing-eyebrow">◈ Introducing Trace</div>
        <div class="landing-title">T R A C E</div>
        <div class="landing-subtitle">
            Your blood tests have been telling a story for years.<br>Nobody was reading it. Until now.
        </div>
        <div class="landing-quote">
            — Disease does not arrive. It drifts. Trace catches the drift. —
        </div>
        <div class="feature-table">
            <div class="feature-row">
                <div class="feature-name">◈ 40+ Biomarkers</div>
                <div class="feature-desc">Tracked over time with Indian ranges</div>
            </div>
            <div class="feature-row">
                <div class="feature-name">◈ AI Health Stories</div>
                <div class="feature-desc">Plain language. Personalised. Warm.</div>
            </div>
            <div class="feature-row">
                <div class="feature-name">◈ PDF Auto-Extraction</div>
                <div class="feature-desc">Upload report. Values fill automatically.</div>
            </div>
            <div class="feature-row">
                <div class="feature-name">◈ Drift Detection</div>
                <div class="feature-desc">Catch changes before symptoms appear</div>
            </div>
            <div class="feature-row">
                <div class="feature-name">◈ Family Health Vault</div>
                <div class="feature-desc">Track parents and family in one place</div>
            </div>
            <div class="feature-row">
                <div class="feature-name">◈ Health Analytics</div>
                <div class="feature-desc">Score, trends, insights at a glance</div>
            </div>
        </div>
        <div class="privacy-line">§ Your data never leaves your device. Never shared. Never sold.</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([2,2,2])
    with col_b:
        if st.button("Begin Your Timeline →"):
            st.session_state["show_app"] = True
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="landing-card">
            <div class="landing-card-symbol">∿</div>
            <div class="landing-card-title">Track</div>
            <div class="landing-card-text">Upload PDFs or enter values. Trace stores them across time and builds your biological timeline automatically.</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="landing-card">
            <div class="landing-card-symbol">⌬</div>
            <div class="landing-card-title">Detect</div>
            <div class="landing-card-text">Watch how your markers drift over months and years. Catch changes before they cross danger thresholds.</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="landing-card">
            <div class="landing-card-symbol">◎</div>
            <div class="landing-card-title">Understand</div>
            <div class="landing-card-text">AI reads your entire biomarker history and tells your health story in plain language you actually understand.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="footer">
        {logo_html}
        <div class="footer-brand" style="margin-top:1rem;">T R A C E</div>
        <div class="footer-sub">Your blood tests are telling a story. This is where you read it.</div>
        <div class="footer-sub" style="margin-top:0.8rem; color:rgba(0,230,118,0.35); letter-spacing:2px;">§ PRIVATE BY DESIGN</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="navbar">
    <div class="nav-logo">
        {logo_html}
        <div>
            <div class="nav-brand">Trace</div>
            <div class="nav-tagline">Biomarker Timeline</div>
        </div>
    </div>
    <div class="nav-right">
        <div class="nav-private">§ Private</div>
        <div class="nav-badge">Beta</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["  ⌬  Log Test  ", "  ∿  Timeline  ", "  ◈  Profiles  "])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOG TEST
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("<br>", unsafe_allow_html=True)

    if profiles_df.empty:
        st.markdown("""
        <div class="onboarding-wrap">
            <div class="onboarding-title">Welcome to Trace</div>
            <div class="onboarding-sub">Get started in three steps</div>
            <div class="step-line">
                <div class="step-num">01 —</div>
                <div class="step-desc"><strong>Create your profile</strong> in the Profiles tab. Add your name, date of birth, gender, and health context. Takes under a minute.</div>
            </div>
            <div class="step-line">
                <div class="step-num">02 —</div>
                <div class="step-desc"><strong>Log your first test</strong> here. Upload a PDF blood report and AI fills the values automatically. Or enter manually.</div>
            </div>
            <div class="step-line">
                <div class="step-num">03 —</div>
                <div class="step-desc"><strong>Go to Timeline.</strong> AI reads your biomarker history and tells you what your body has been saying in plain language.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_form, col_side = st.columns([3,2])

        with col_side:
            st.markdown('<div class="glow-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">◈ Profile</div>', unsafe_allow_html=True)
            profile_names = profiles_df["Name"].tolist()
            selected_profile = st.selectbox("Who is this test for?", profile_names)
            pr = profiles_df[profiles_df["Name"]==selected_profile].iloc[0]
            gender = pr["Gender"]
            age = calculate_age(pr["DOB"])
            conditions = pr.get("Conditions","None")
            diet = pr.get("Diet","Vegetarian")
            blood_group = pr.get("Blood Group","—")
            st.markdown(f"""
            <div style="margin-top:1rem; color:rgba(255,255,255,0.55); font-size:0.82rem; line-height:2.2; font-family:'Space Mono',monospace; letter-spacing:1px;">
                {gender} · {age}y · {blood_group}<br>
                {diet}<br>
                {conditions}
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="glow-card" style="margin-top:1rem;">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">◈ Upload PDF Report</div>', unsafe_allow_html=True)
            st.markdown('<div style="color:rgba(255,255,255,0.45); font-size:0.8rem; line-height:1.8; margin-bottom:1rem;">AI reads your lab report and fills values automatically.</div>', unsafe_allow_html=True)
            uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
            if uploaded_pdf:
                if st.button("Extract from PDF →"):
                    with st.spinner("Reading your report..."):
                        markers_temp = get_markers(gender, age)
                        pdf_text = extract_text_from_pdf(uploaded_pdf)
                        if not pdf_text.strip():
                            st.error("This PDF could not be read. It may be a scanned image. Please enter values manually below.")
                        else:
                            extracted = extract_values_with_ai(pdf_text, markers_temp, gender, age)
                            if extracted:
                                st.session_state["extracted_values"] = extracted
                                st.success(f"{len(extracted)} values found. Review below and save.")
                            else:
                                st.warning("Could not identify values clearly. Please enter values manually below.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_form:
            markers = get_markers(gender, age)
            panels = {}
            for marker, mdata in markers.items():
                p = mdata["panel"]
                if p not in panels: panels[p] = {}
                panels[p][marker] = mdata

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">◈ Test Details</div>', unsafe_allow_html=True)
            test_date = st.date_input("Test Date", value=date.today())
            st.markdown('</div>', unsafe_allow_html=True)

            extracted_vals = st.session_state.get("extracted_values", {})
            if extracted_vals:
                st.markdown(f"""
                <div style="background:rgba(0,230,118,0.04); border:1px solid rgba(0,230,118,0.18);
                border-radius:10px; padding:0.9rem 1.4rem; margin:1rem 0;">
                    <div style="font-family:'Space Mono',monospace; color:#00e676; font-size:0.7rem; letter-spacing:2px; text-transform:uppercase;">
                        {len(extracted_vals)} values extracted — review and save
                    </div>
                </div>
                """, unsafe_allow_html=True)

            values = {}
            for panel_name, panel_markers in panels.items():
                with st.expander(f"◈  {panel_name}", expanded=(panel_name=="Complete Blood Count")):
                    c1, c2 = st.columns(2)
                    for i, (marker, mdata) in enumerate(panel_markers.items()):
                        with c1 if i%2==0 else c2:
                            dv = float(extracted_vals.get(marker, 0.0))
                            dv = min(max(dv, mdata["min"]), mdata["max"])
                            info = MARKER_INFO.get(marker,"")
                            values[marker] = st.number_input(
                                marker, min_value=mdata["min"], max_value=mdata["max"],
                                value=dv, help=f"{info} | Normal: {mdata['low']}–{mdata['high']}"
                            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save Test →"):
                new_row = {"Name": selected_profile, "Date": str(test_date), "Gender": gender, "Age": age}
                new_row.update(values)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.session_state["extracted_values"] = {}
                st.success(f"Test saved for {selected_profile} on {test_date}. View your timeline to see your story.")
                st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty or profiles_df.empty:
        st.markdown("""
        <div class="onboarding-wrap">
            <div class="onboarding-title">No Timeline Yet</div>
            <div class="onboarding-sub">Create a profile, log your first test, and your story begins here.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_sel, _ = st.columns([2,4])
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
            <div class="onboarding-wrap">
                <div class="onboarding-sub">No tests logged for this profile yet. Go to Log Test to add your first blood test.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            person_df["Date"] = pd.to_datetime(person_df["Date"])
            person_df = person_df.sort_values("Date")
            num_tests = len(person_df)

            # ── ANALYTICS SECTION ─────────────────────────────────────────

            analytics = compute_analytics(person_df, markers)

            st.markdown('<div class="section-label">◈ Health Overview</div>', unsafe_allow_html=True)

            col_score, col_breakdown, col_insights = st.columns([1,2,2])

            with col_score:
                score_color = "#00e676" if analytics["score"] >= 75 else "#F5A623" if analytics["score"] >= 50 else "#ff4b4b"
                st.markdown(f"""
                <div class="glass-card" style="text-align:center; padding:2rem 1rem;">
                    <div style="font-family:'Space Mono',monospace; font-size:0.6rem; letter-spacing:4px; color:rgba(255,255,255,0.35); text-transform:uppercase; margin-bottom:1rem;">Health Score</div>
                    <div style="font-family:'Space Mono',monospace; font-size:3.5rem; font-weight:700; color:{score_color}; line-height:1;">{analytics["score"]}</div>
                    <div style="height:1px; background:linear-gradient(90deg,transparent,{score_color},transparent); margin:0.8rem auto; max-width:60px;"></div>
                    <div style="font-size:0.7rem; color:rgba(255,255,255,0.3); letter-spacing:2px; text-transform:uppercase;">out of 100</div>
                    <div style="font-size:0.72rem; color:rgba(255,255,255,0.3); margin-top:1rem; line-height:1.6;">{analytics["total"]} markers<br>analysed</div>
                </div>
                """, unsafe_allow_html=True)

            with col_breakdown:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="font-family:'Space Mono',monospace; font-size:0.6rem; letter-spacing:4px; color:rgba(255,255,255,0.35); text-transform:uppercase; margin-bottom:1.5rem;">Marker Breakdown</div>
                    <div style="display:flex; gap:0.8rem; margin-bottom:1.5rem;">
                        <div class="analytics-cell" style="flex:1; border-color:rgba(0,230,118,0.2);">
                            <div class="analytics-number" style="color:#00e676;">{analytics["normal"]}</div>
                            <div class="analytics-label">Normal</div>
                        </div>
                        <div class="analytics-cell" style="flex:1; border-color:rgba(245,166,35,0.2);">
                            <div class="analytics-number" style="color:#F5A623;">{analytics["warning"]}</div>
                            <div class="analytics-label">Drifting</div>
                        </div>
                        <div class="analytics-cell" style="flex:1; border-color:rgba(255,75,75,0.2);">
                            <div class="analytics-number" style="color:#ff4b4b;">{analytics["danger"]}</div>
                            <div class="analytics-label">Critical</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:0.8rem;">
                        <div class="analytics-cell" style="flex:1; border-color:rgba(0,230,118,0.15);">
                            <div class="analytics-number" style="color:#00e676; font-size:1.4rem;">+{analytics["improved"]}</div>
                            <div class="analytics-label">Improved</div>
                        </div>
                        <div class="analytics-cell" style="flex:1; border-color:rgba(255,75,75,0.15);">
                            <div class="analytics-number" style="color:#ff4b4b; font-size:1.4rem;">-{analytics["worsened"]}</div>
                            <div class="analytics-label">Declined</div>
                        </div>
                        <div class="analytics-cell" style="flex:1;">
                            <div class="analytics-number" style="font-size:1.4rem;">{num_tests}</div>
                            <div class="analytics-label">Tests</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_insights:
                best_html = f"""
                <div class="insight-row">
                    <div class="insight-dot" style="background:#00e676;"></div>
                    <div>
                        <div class="insight-label" style="color:#00e676;">Strongest Marker</div>
                        <div class="insight-text">{analytics["best_marker"] or "—"}<br>
                        <span style="color:rgba(255,255,255,0.4); font-size:0.8rem;">{analytics["best_val"] or ""}</span></div>
                    </div>
                </div>""" if analytics["best_marker"] else ""

                worst_html = f"""
                <div class="insight-row">
                    <div class="insight-dot" style="background:#F5A623;"></div>
                    <div>
                        <div class="insight-label" style="color:#F5A623;">Needs Attention</div>
                        <div class="insight-text">{analytics["worst_marker"] or "—"}<br>
                        <span style="color:rgba(255,255,255,0.4); font-size:0.8rem;">{analytics["worst_val"] or ""}</span></div>
                    </div>
                </div>""" if analytics["worst_marker"] else ""

                st.markdown(f"""
                <div class="glass-card">
                    <div style="font-family:'Space Mono',monospace; font-size:0.6rem; letter-spacing:4px; color:rgba(255,255,255,0.35); text-transform:uppercase; margin-bottom:1.2rem;">Key Insights</div>
                    {best_html}
                    {worst_html}
                    <div class="insight-row">
                        <div class="insight-dot" style="background:rgba(255,255,255,0.3);"></div>
                        <div>
                            <div class="insight-label" style="color:rgba(255,255,255,0.4);">Profile</div>
                            <div class="insight-text">{gender} · {age}y · {blood_group}<br>
                            <span style="color:rgba(255,255,255,0.4); font-size:0.8rem;">{diet}</span></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── MINI CHART — MARKER STATUS ────────────────────────────────

            if analytics["total"] > 0:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=["Normal", "Drifting", "Critical"],
                    values=[analytics["normal"], analytics["warning"], analytics["danger"]],
                    hole=0.72,
                    marker=dict(colors=["#00e676","#F5A623","#ff4b4b"],
                        line=dict(color="#05050f", width=2)),
                    textinfo="none",
                    hovertemplate="%{label}: %{value}<extra></extra>"
                )])
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    height=140,
                    margin=dict(l=0,r=0,t=0,b=0),
                    annotations=[dict(
                        text=f"<b>{analytics['score']}</b>",
                        x=0.5, y=0.5, font_size=28,
                        font_color="#F5A623",
                        showarrow=False
                    )]
                )

            # ── TREND ALERTS ──────────────────────────────────────────────

            alerts = get_trend_alerts(person_df, markers)
            if alerts:
                st.markdown('<div class="section-label">◈ Trend Alerts</div>', unsafe_allow_html=True)
                for alert in alerts:
                    st.markdown(f"""
                    <div class="alert-row">
                        <div class="alert-line"></div>
                        <div class="alert-text">{alert}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── AI STORY ──────────────────────────────────────────────────

            st.markdown('<div class="section-label">◈ Health Story</div>', unsafe_allow_html=True)
            with st.spinner("Reading your biomarker story..."):
                ai_story = get_ai_analysis(selected_name, person_df, gender, age, conditions, diet)
            st.markdown(f"""
            <div class="ai-story-container">
                <div class="ai-label">AI Analysis — {selected_name} · {gender} · {age}y · {diet}</div>
                <div class="ai-story-text">{ai_story}</div>
            </div>
            <p class="disclaimer">For educational purposes only. Always consult your doctor for medical advice.</p>
            """, unsafe_allow_html=True)

            # ── SHARE ─────────────────────────────────────────────────────

            st.markdown('<div class="section-label">◈ Share</div>', unsafe_allow_html=True)
            wa_text = whatsapp_summary(selected_name, person_df, markers)
            wa_url = f"https://wa.me/?text={wa_text.replace(chr(10),'%0A').replace(' ','%20')}"
            st.markdown(f"""
            <div class="share-row">
                <div style="font-size:0.82rem; color:rgba(255,255,255,0.55); flex:1; line-height:1.6;">
                    Share a clean summary with your doctor or family via WhatsApp.
                </div>
                <a href="{wa_url}" target="_blank" style="
                    background:rgba(37,211,102,0.1); border:1px solid rgba(37,211,102,0.25);
                    color:#25D366; padding:0.6rem 1.4rem; border-radius:8px;
                    text-decoration:none; font-family:'Space Mono',monospace;
                    font-size:0.7rem; letter-spacing:2px; text-transform:uppercase;
                    white-space:nowrap; font-weight:700;
                ">Share via WhatsApp</a>
            </div>
            """, unsafe_allow_html=True)

            # ── BIOMARKER TRENDS ──────────────────────────────────────────

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-label">◈ Biomarker Trends</div>', unsafe_allow_html=True)

            panels = {}
            for marker, mdata in markers.items():
                p = mdata["panel"]
                if p not in panels: panels[p] = {}
                panels[p][marker] = mdata

            for panel_name, panel_markers in panels.items():
                has_data = any(
                    m in person_df.columns and (person_df[m]>0).any()
                    for m in panel_markers
                )
                if not has_data: continue

                st.markdown(f'<div class="panel-header">◈ {panel_name}</div>', unsafe_allow_html=True)

                for marker, mdata in panel_markers.items():
                    if marker not in person_df.columns: continue
                    series = person_df[marker]
                    sc = series.dropna()
                    sc = sc[sc>0]
                    if len(sc)==0: continue

                    latest = sc.iloc[-1]
                    flag_text, flag_class = get_flag(latest, mdata)
                    trend_msg, trend_color = get_trend_message(series, mdata)
                    info = MARKER_INFO.get(marker,"")

                    tc = {"normal":"rgba(0,230,118,0.8)","warning":"rgba(245,166,35,0.8)",
                          "danger":"rgba(255,75,75,0.8)","neutral":"rgba(255,255,255,0.4)"}
                    trend_hex = tc.get(trend_color,"rgba(255,255,255,0.4)")
                    flag_html = f'<span class="flag flag-{flag_class}">{latest} — {flag_text}</span>' if flag_text else ""

                    st.markdown(f"""
                    <div class="marker-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div style="flex:1;">
                                <div class="marker-name">{marker}</div>
                                <div class="marker-info">{info}</div>
                                <div class="marker-trend" style="color:{trend_hex};">{trend_msg}</div>
                                <div style="font-size:0.72rem; color:rgba(255,255,255,0.28); margin-top:0.2rem;">
                                    Normal — {mdata['low']} to {mdata['high']}
                                </div>
                            </div>
                            <div style="margin-left:1rem; flex-shrink:0;">{flag_html}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    if len(sc) >= 2:
                        fig = go.Figure()
                        fig.add_hrect(y0=mdata["low"], y1=mdata["high"],
                            fillcolor="rgba(245,166,35,0.03)", line_width=0)
                        fig.add_trace(go.Scatter(
                            x=person_df["Date"], y=person_df[marker],
                            mode="lines+markers",
                            line=dict(color="#F5A623", width=2),
                            marker=dict(size=6, color="#F5A623", line=dict(color="#05050f", width=1.5)),
                            fill="tozeroy", fillcolor="rgba(245,166,35,0.04)"
                        ))
                        fig.add_hline(y=mdata["high"], line_dash="dot",
                            line_color="rgba(245,166,35,0.2)", line_width=1)
                        fig.add_hline(y=mdata["low"], line_dash="dot",
                            line_color="rgba(245,166,35,0.2)", line_width=1)
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=180, margin=dict(l=0,r=0,t=8,b=0), showlegend=False,
                            xaxis=dict(showgrid=False, showline=False,
                                tickfont=dict(color="rgba(255,255,255,0.25)", size=9)),
                            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                                showline=False, tickfont=dict(color="rgba(255,255,255,0.25)", size=9))
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown('</div><br>', unsafe_allow_html=True)

            # ── FEEDBACK ──────────────────────────────────────────────────

            st.markdown("""
            <div class="feedback-section">
                <div class="feedback-heading">◈ Feedback</div>
                <div class="feedback-sub">Trace is built for you. Tell us what you felt, what confused you, what you wish existed. Every message is read personally.</div>
            </div>
            """, unsafe_allow_html=True)

            rating = st.radio(
                "",
                options=["1", "2", "3", "4", "5"],
                horizontal=True,
                label_visibility="collapsed",
                help="1 = Poor · 5 = Amazing"
            )
            st.markdown('<div style="font-size:0.65rem; color:rgba(255,255,255,0.25); letter-spacing:2px; margin-bottom:1rem;">1 — Poor &nbsp;&nbsp; 5 — Amazing</div>', unsafe_allow_html=True)

            feedback_text = st.text_area("",
                placeholder="What did you feel? What confused you? What do you wish Trace could do?",
                height=110, label_visibility="collapsed")
            feedback_email = st.text_input("",
                placeholder="Email — optional, only if you would like a response",
                label_visibility="collapsed")

            col_btn, _ = st.columns([1,2])
            with col_btn:
                if st.button("Send →"):
                    if not feedback_text.strip():
                        st.error("Please write something before sending.")
                    else:
                        new_fb = pd.DataFrame([{
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Name": selected_name,
                            "Rating": rating,
                            "Message": feedback_text,
                            "Email": feedback_email
                        }])
                        feedback_df = pd.concat([feedback_df, new_fb], ignore_index=True)
                        save_feedback(feedback_df)
                        st.success("Received. Thank you.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PROFILES
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_new, col_existing = st.columns([2,3])

    with col_new:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">◈ New Profile</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-label">◈ Profiles</div>', unsafe_allow_html=True)
        if profiles_df.empty:
            st.markdown('<div class="glass-card" style="text-align:center; padding:2rem;"><div style="color:rgba(255,255,255,0.3); font-size:0.85rem;">No profiles yet.</div></div>', unsafe_allow_html=True)
        else:
            for _, row in profiles_df.iterrows():
                tc = len(df[df["Name"]==row["Name"]]) if not df.empty and "Name" in df.columns else 0
                a = calculate_age(row["DOB"])
                st.markdown(f"""
                <div class="marker-card" style="margin-bottom:0.8rem;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div class="marker-name">{row['Name']}</div>
                            <div style="color:rgba(255,255,255,0.45); font-size:0.78rem; margin-top:0.4rem; line-height:1.9; font-family:'Space Mono',monospace; letter-spacing:0.5px;">
                                {row['Gender']} · {a}y · {row.get('Blood Group','—')}<br>
                                {row.get('Diet','—')} · {row.get('Conditions','None')}
                            </div>
                        </div>
                        <div><span class="flag flag-normal">{tc} tests</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if not feedback_df.empty:
            st.markdown('<div class="section-label">◈ Feedback</div>', unsafe_allow_html=True)
            for _, fb in feedback_df.iterrows():
                email_line = f'<div style="color:rgba(255,255,255,0.25); font-size:0.72rem; margin-top:0.3rem;">{fb["Email"]}</div>' if pd.notna(fb.get("Email")) and str(fb.get("Email","")).strip() else ""
                st.markdown(f"""
                <div class="marker-card" style="margin-bottom:0.8rem;">
                    <div style="font-family:'Space Mono',monospace; color:rgba(245,166,35,0.6); font-size:0.65rem; letter-spacing:2px; margin-bottom:0.4rem;">
                        {fb['Rating']}/5 · {fb['Name']} · {fb['Timestamp']}
                    </div>
                    <div style="color:rgba(255,255,255,0.65); font-size:0.85rem; line-height:1.6;">"{fb['Message']}"</div>
                    {email_line}
                </div>
                """, unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="footer">
    {logo_html}
    <div class="footer-brand" style="margin-top:1rem;">T R A C E</div>
    <div class="footer-sub">Your blood tests are telling a story. This is where you read it.</div>
    <div class="footer-sub" style="margin-top:0.8rem; color:rgba(0,230,118,0.3); letter-spacing:3px; font-family:'Space Mono',monospace; font-size:0.62rem;">§ PRIVATE BY DESIGN</div>
</div>
""", unsafe_allow_html=True)