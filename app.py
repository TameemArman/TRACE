import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
from groq import Groq
import base64
import fitz
import json
import uuid
import threading
import time
import requests
import streamlit.components.v1 as components
from supabase import create_client

st.set_page_config(
    page_title="Trace — Biomarker Timeline",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── KEEP ALIVE ────────────────────────────────────────────────────────────────
def keep_alive():
    while True:
        time.sleep(300)
        try:
            requests.get("https://gettrace.streamlit.app", timeout=10)
        except:
            pass
threading.Thread(target=keep_alive, daemon=True).start()

# ── SUPABASE ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

def sign_in_with_google():
    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": "https://gettrace.streamlit.app"
            }
        })
        return res.url
    except:
        return None

def get_current_user():
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            return session.user
        return None
    except:
        return None

def load_profiles_db(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["name","dob","gender","blood_group","conditions","diet"])
    except:
        return pd.DataFrame(columns=["name","dob","gender","blood_group","conditions","diet"])

def save_profile_db(user_id, name, dob, gender, blood_group, conditions, diet):
    try:
        supabase.table("profiles").insert({
            "user_id": user_id,
            "name": name,
            "dob": str(dob),
            "gender": gender,
            "blood_group": blood_group,
            "conditions": conditions,
            "diet": diet
        }).execute()
        return True
    except:
        return False

def load_tests_db(user_id, profile_name):
    try:
        res = supabase.table("tests").select("*").eq("user_id", user_id).eq("profile_name", profile_name).execute()
        if res.data:
            rows = []
            for r in res.data:
                row = {"Name": r["profile_name"], "Date": r["test_date"], "Gender": r["gender"], "Age": r["age"]}
                if r.get("data"):
                    row.update(r["data"])
                rows.append(row)
            return pd.DataFrame(rows)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def save_test_db(user_id, profile_name, test_date, gender, age, values):
    try:
        supabase.table("tests").insert({
            "user_id": user_id,
            "profile_name": profile_name,
            "test_date": str(test_date),
            "gender": gender,
            "age": age,
            "data": values
        }).execute()
        return True
    except:
        return False

def save_feedback_db(user_id, profile_name, rating, message, email):
    try:
        supabase.table("feedback").insert({
            "user_id": user_id,
            "profile_name": profile_name,
            "rating": rating,
            "message": message,
            "email": email
        }).execute()
        return True
    except:
        return False

# ── IMAGE ─────────────────────────────────────────────────────────────────────
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    * { font-family: 'Inter', sans-serif !important; }
    .stApp, html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="block-container"] {
        background: #f0f4f8 !important;
        color: #0F172A !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main .block-container { padding: 1.5rem 2.5rem; max-width: 1200px; }
    .stMarkdown, .stText, p, div, span, label { color: #0F172A !important; }
    details { background: white !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; padding: 4px !important; margin-bottom: 8px !important; }
    details summary { background: white !important; color: #0F172A !important; font-weight: 700 !important; font-size: 13px !important; padding: 10px 14px !important; border-radius: 10px !important; cursor: pointer !important; list-style: none !important; }
    details summary::marker { display: none !important; }
    details summary::-webkit-details-marker { display: none !important; }
    details[open] { background: white !important; }
    details[open] summary { border-bottom: 1px solid #F1F5F9 !important; margin-bottom: 8px !important; }
    [data-testid="stExpander"] { background: white !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; }
    [data-testid="stExpander"] > div { background: white !important; }
    .streamlit-expanderHeader { background: white !important; color: #0F172A !important; font-weight: 700 !important; }
    .streamlit-expanderContent { background: white !important; }
    [data-testid="stFileUploader"] { background: white !important; border: 1.5px dashed #E2E8F0 !important; border-radius: 12px !important; }
    [data-testid="stFileUploader"] * { color: #64748B !important; }
    [data-testid="stFileUploadDropzone"] { background: white !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploader"] button { background: #0EA5E9 !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 700 !important; padding: 6px 16px !important; width: auto !important; box-shadow: none !important; font-size: 13px !important; }
    [data-testid="stFileUploader"] button span { display: none !important; }
    [data-testid="stFileUploader"] button::after { content: "Upload PDF" !important; }
    [data-testid="stFileUploader"] small { color: #94A3B8 !important; font-size: 11px !important; }
    .t-nav { background: white; border-radius: 16px; border: 1px solid #E2E8F0; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .t-nav-left { display: flex; align-items: center; gap: 12px; }
    .t-logo-wrap { width: 40px; height: 40px; border-radius: 12px; background: #1a1a2e; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; }
    .t-logo-wrap img { width: 36px; height: 36px; border-radius: 9px; object-fit: cover; }
    .t-nav-brand { font-size: 19px; font-weight: 900; color: #0F172A !important; letter-spacing: 0.5px; }
    .t-nav-sub { font-size: 11px; color: #94A3B8 !important; font-weight: 600; margin-top: 1px; }
    .t-nav-right { display: flex; align-items: center; gap: 12px; }
    .t-nav-private { font-size: 11px; color: #22C55E !important; font-weight: 800; }
    .t-nav-badge { background: #EFF6FF; color: #0EA5E9 !important; font-size: 10px; font-weight: 800; padding: 4px 12px; border-radius: 20px; border: 1px solid #BFDBFE; }
    .t-hero { background: linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%); border-radius: 20px; border: 1px solid #E2E8F0; padding: 40px 32px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-hero-tag { font-size: 11px; font-weight: 800; color: #0EA5E9 !important; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 14px; }
    .t-hero-title { font-size: 34px; font-weight: 900; color: #0F172A !important; margin-bottom: 12px; line-height: 1.25; }
    .t-hero-title span { color: #0EA5E9 !important; }
    .t-hero-sub { font-size: 15px; color: #64748B !important; line-height: 1.8; margin-bottom: 12px; font-weight: 500; max-width: 540px; margin-left: auto; margin-right: auto; }
    .t-hero-focus { font-size: 12px; color: #7C3AED !important; font-weight: 700; background: #F5F3FF; padding: 6px 16px; border-radius: 20px; display: inline-block; margin-bottom: 20px; border: 1px solid #DDD6FE; }
    .t-hero-privacy { font-size: 12px; color: #22C55E !important; margin-top: 12px; font-weight: 700; }
    .t-pills { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 16px 0; }
    .t-pill { background: white; border: 1px solid #E2E8F0; border-radius: 20px; padding: 6px 14px; font-size: 12px; color: #475569 !important; font-weight: 700; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .t-card { background: white; border-radius: 16px; border: 1px solid #E2E8F0; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-card-accent { background: white; border-radius: 16px; border: 1px solid #E2E8F0; border-left: 4px solid #0EA5E9; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-card-amber { background: white; border-radius: 16px; border: 1px solid #E2E8F0; border-left: 4px solid #F59E0B; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-feature-card { background: white; border-radius: 16px; border: 1px solid #E2E8F0; padding: 24px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-feature-icon { width: 48px; height: 48px; border-radius: 14px; margin: 0 auto 14px; display: flex; align-items: center; justify-content: center; }
    .t-feature-title { font-size: 14px; font-weight: 800; color: #0F172A !important; margin-bottom: 8px; }
    .t-feature-text { font-size: 12px; color: #64748B !important; line-height: 1.7; font-weight: 500; }
    .t-diabetes-card { background: linear-gradient(135deg, #FFF7ED 0%, #FFFBEB 100%); border-radius: 16px; border: 1px solid #FED7AA; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-diabetes-title { font-size: 14px; font-weight: 800; color: #9A3412 !important; margin-bottom: 4px; }
    .t-diabetes-sub { font-size: 12px; color: #C2410C !important; font-weight: 500; line-height: 1.6; }
    .t-diabetes-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-top: 14px; }
    .t-diabetes-stat { background: white; border-radius: 10px; border: 1px solid #FED7AA; padding: 12px; text-align: center; }
    .t-diabetes-num { font-size: 20px; font-weight: 900; color: #EA580C !important; line-height: 1; }
    .t-diabetes-label { font-size: 10px; color: #9A3412 !important; font-weight: 700; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
    .t-stat { background: white; border-radius: 14px; border: 1px solid #E2E8F0; padding: 16px 12px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
    .t-stat-num { font-size: 28px; font-weight: 900; line-height: 1; }
    .t-stat-label { font-size: 10px; color: #94A3B8 !important; margin-top: 4px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    .t-score-card { background: white; border-radius: 16px; border: 1px solid #E2E8F0; padding: 20px; margin-bottom: 16px; display: flex; align-items: center; gap: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-score-circle { width: 76px; height: 76px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 26px; font-weight: 900; border: 3px solid; }
    .t-score-title { font-size: 15px; font-weight: 800; color: #0F172A !important; margin-bottom: 4px; }
    .t-score-sub { font-size: 12px; color: #64748B !important; line-height: 1.6; font-weight: 500; }
    .t-ai-label { font-size: 10px; font-weight: 800; color: #0EA5E9 !important; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
    .t-ai-text { font-size: 14px; color: #334155 !important; line-height: 1.9; font-weight: 500; }
    .t-disclaimer { font-size: 11px; color: #CBD5E1 !important; margin-top: 10px; font-weight: 500; text-align: center; }
    .t-marker { background: white; border-radius: 14px; border: 1px solid #E2E8F0; padding: 16px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.03); }
    .t-marker-name { font-size: 13px; font-weight: 800; color: #0F172A !important; }
    .t-marker-info { font-size: 11px; color: #94A3B8 !important; margin-top: 3px; font-weight: 500; }
    .t-marker-range { font-size: 11px; color: #CBD5E1 !important; margin-top: 2px; font-weight: 500; }
    .t-badge { font-size: 11px; font-weight: 800; padding: 4px 12px; border-radius: 20px; display: inline-block; }
    .t-badge-normal { background: #F0FDF4; color: #16A34A !important; border: 1px solid #BBF7D0; }
    .t-badge-warning { background: #FFFBEB; color: #D97706 !important; border: 1px solid #FDE68A; }
    .t-badge-danger { background: #FEF2F2; color: #DC2626 !important; border: 1px solid #FECACA; }
    .t-trend { font-size: 12px; margin-top: 6px; font-weight: 700; }
    .t-trend-normal { color: #16A34A !important; }
    .t-trend-warning { color: #D97706 !important; }
    .t-trend-danger { color: #DC2626 !important; }
    .t-trend-neutral { color: #94A3B8 !important; }
    .t-bar-wrap { background: #F1F5F9; border-radius: 6px; height: 6px; margin-top: 10px; overflow: hidden; }
    .t-bar { height: 6px; border-radius: 6px; }
    .t-panel-head { font-size: 11px; font-weight: 800; color: #64748B !important; letter-spacing: 2px; text-transform: uppercase; margin: 20px 0 12px; padding-bottom: 8px; border-bottom: 2px solid #F1F5F9; display: flex; align-items: center; gap: 8px; }
    .t-alert { background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; display: flex; gap: 10px; align-items: flex-start; }
    .t-alert-line { width: 3px; background: #F59E0B; border-radius: 3px; align-self: stretch; flex-shrink: 0; min-height: 20px; }
    .t-alert-text { font-size: 13px; color: #92400E !important; line-height: 1.5; font-weight: 600; }
    .t-section { font-size: 11px; font-weight: 800; color: #94A3B8 !important; letter-spacing: 2px; text-transform: uppercase; margin: 20px 0 12px; }
    .t-label { font-size: 12px; font-weight: 800; color: #475569 !important; margin-bottom: 4px; margin-top: 10px; }
    .t-onboard { background: white; border-radius: 20px; border: 1px solid #E2E8F0; padding: 36px 28px; text-align: center; margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .t-onboard-icon { width: 56px; height: 56px; border-radius: 16px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; }
    .t-onboard-title { font-size: 20px; font-weight: 900; color: #0F172A !important; margin-bottom: 6px; }
    .t-onboard-sub { font-size: 13px; color: #64748B !important; margin-bottom: 24px; font-weight: 500; }
    .t-step { display: flex; align-items: flex-start; gap: 14px; text-align: left; padding: 12px 0; border-bottom: 1px solid #F8FAFC; }
    .t-step:last-child { border-bottom: none; }
    .t-step-num { font-size: 12px; font-weight: 900; color: white !important; background: #0EA5E9; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .t-step-text { font-size: 13px; color: #475569 !important; line-height: 1.6; font-weight: 500; }
    .t-step-text strong { color: #0F172A !important; font-weight: 800; }
    .t-insight { display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid #F1F5F9; }
    .t-insight:last-child { border-bottom: none; }
    .t-insight-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }
    .t-insight-label { font-size: 10px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px; }
    .t-insight-text { font-size: 13px; color: #475569 !important; font-weight: 500; line-height: 1.5; }
    .t-share { background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 14px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
    .t-share-text { font-size: 13px; color: #166534 !important; font-weight: 600; line-height: 1.5; }
    .t-feedback { background: #F8FAFC; border-radius: 16px; border: 1px solid #E2E8F0; padding: 24px; margin-top: 32px; }
    .t-feedback-title { font-size: 16px; font-weight: 900; color: #0F172A !important; margin-bottom: 4px; }
    .t-feedback-sub { font-size: 13px; color: #64748B !important; font-weight: 500; line-height: 1.6; margin-bottom: 16px; }
    .t-profile-item { background: white; border-radius: 14px; border: 1px solid #E2E8F0; padding: 16px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.03); }
    .t-profile-name { font-size: 14px; font-weight: 800; color: #0F172A !important; }
    .t-profile-info { font-size: 12px; color: #64748B !important; margin-top: 4px; font-weight: 500; line-height: 1.8; }
    .stTabs [data-baseweb="tab-list"] { background: white !important; border-radius: 14px !important; border: 1px solid #E2E8F0 !important; padding: 4px !important; gap: 4px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px !important; color: #94A3B8 !important; font-weight: 800 !important; font-size: 13px !important; padding: 8px 20px !important; background: transparent !important; }
    .stTabs [aria-selected="true"] { background: #EFF6FF !important; color: #0EA5E9 !important; border: 1px solid #BFDBFE !important; }
    .stTextInput input, .stNumberInput input, .stDateInput input { background: white !important; border: 1.5px solid #E2E8F0 !important; border-radius: 10px !important; color: #0F172A !important; font-weight: 600 !important; font-size: 14px !important; }
    .stTextArea textarea { background: white !important; border: 1.5px solid #E2E8F0 !important; border-radius: 10px !important; color: #0F172A !important; font-weight: 500 !important; }
    .stSelectbox > div > div, .stMultiSelect > div > div { background: white !important; border: 1.5px solid #E2E8F0 !important; border-radius: 10px !important; color: #0F172A !important; font-weight: 600 !important; }
    .stSelectbox svg, .stMultiSelect svg { fill: #64748B !important; }
    .stNumberInput button { background: #F1F5F9 !important; border: 1px solid #E2E8F0 !important; color: #0F172A !important; }
    .stButton button { background: #0EA5E9 !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 800 !important; font-size: 14px !important; width: 100% !important; box-shadow: 0 4px 12px rgba(14,165,233,0.25) !important; }
    .stButton button:hover { background: #0284C7 !important; box-shadow: 0 6px 16px rgba(14,165,233,0.35) !important; }
    .t-footer { text-align: center; padding: 32px 0 16px; border-top: 1px solid #E2E8F0; margin-top: 40px; }
    .t-footer-brand { font-size: 20px; font-weight: 900; color: #0F172A !important; margin-top: 12px; }
    .t-footer-sub { font-size: 12px; color: #94A3B8 !important; margin-top: 4px; font-weight: 500; }
    .t-footer-privacy { font-size: 11px; color: #22C55E !important; margin-top: 6px; font-weight: 700; }
    .t-login-card { background: white; border-radius: 20px; border: 1px solid #E2E8F0; padding: 40px 32px; text-align: center; max-width: 440px; margin: 40px auto; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
    .t-google-btn { display: inline-flex; align-items: center; gap: 10px; background: white; border: 1.5px solid #E2E8F0; border-radius: 12px; padding: 12px 24px; text-decoration: none; font-size: 14px; font-weight: 700; color: #0F172A !important; box-shadow: 0 2px 8px rgba(0,0,0,0.06); cursor: pointer; transition: all 0.2s; }
    .t-google-btn:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
    hr { border-color: #F1F5F9 !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #F8FAFC; }
    ::-webkit-scrollbar-thumb { background: #BFDBFE; border-radius: 4px; }
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem !important; }
        .t-hero { padding: 24px 16px !important; }
        .t-hero-title { font-size: 22px !important; }
        .t-card { padding: 14px !important; }
        .t-nav { padding: 10px 14px !important; }
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<script async src="https://www.googletagmanager.com/gtag/js?id=G-M7MXDH3YV1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-M7MXDH3YV1');
</script>
""", unsafe_allow_html=True)

def icon_heartbeat():
    return """<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 12h3l3-9 4 18 3-9h5" stroke="#0EA5E9" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
def icon_chart():
    return """<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 20l5-7 4 4 5-8 4 5" stroke="#22C55E" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 20h18" stroke="#22C55E" stroke-width="2" stroke-linecap="round"/></svg>"""
def icon_brain():
    return """<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" stroke="#7C3AED" stroke-width="2.5"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="#7C3AED" stroke-width="2" stroke-linecap="round"/></svg>"""
def icon_shield():
    return """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3L4 7v5c0 5 3.5 9.7 8 11 4.5-1.3 8-6 8-11V7L12 3z" stroke="#22C55E" stroke-width="2.5" stroke-linejoin="round"/><path d="M9 12l2 2 4-4" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
def icon_drop():
    return """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3C12 3 5 10.5 5 15a7 7 0 0014 0c0-4.5-7-12-7-12z" stroke="#EF4444" stroke-width="2.5" stroke-linejoin="round"/></svg>"""
def icon_timeline():
    return """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="6" cy="12" r="2" fill="#0EA5E9"/><circle cx="12" cy="7" r="2" fill="#0EA5E9"/><circle cx="18" cy="10" r="2" fill="#0EA5E9"/><path d="M6 12l6-5 6 3" stroke="#0EA5E9" stroke-width="1.5" stroke-linecap="round"/><path d="M3 20h18" stroke="#E2E8F0" stroke-width="1.5" stroke-linecap="round"/></svg>"""
def icon_google():
    return """<svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>"""

def get_markers(gender="Male", age=30):
    m = {}
    m["Hemoglobin (g/dL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 25.0, "low": 13.5 if gender=="Male" else 12.0, "high": 17.5 if gender=="Male" else 15.5}
    m["RBC Count (million/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 10.0, "low": 4.7 if gender=="Male" else 4.2, "high": 6.1 if gender=="Male" else 5.4}
    m["WBC Count (thousand/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 30.0, "low": 4.5, "high": 11.0}
    m["Platelets (thousand/µL)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 800.0, "low": 150.0, "high": 400.0}
    m["Hematocrit (%)"] = {"panel": "Complete Blood Count", "min": 0.0, "max": 70.0, "low": 41.0 if gender=="Male" else 36.0, "high": 53.0 if gender=="Male" else 46.0}
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
    m["HDL Cholesterol (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 150.0, "low": 40.0 if gender=="Male" else 50.0, "high": 60.0}
    m["Triglycerides (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 1000.0, "low": 0.0, "high": 150.0}
    m["VLDL (mg/dL)"] = {"panel": "Lipid Profile", "min": 0.0, "max": 200.0, "low": 0.0, "high": 30.0}
    m["ALT / SGPT (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 500.0, "low": 0.0, "high": 40.0 if gender=="Male" else 31.0}
    m["AST / SGOT (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 500.0, "low": 0.0, "high": 40.0}
    m["Total Bilirubin (mg/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 20.0, "low": 0.0, "high": 1.2}
    m["Alkaline Phosphatase (U/L)"] = {"panel": "Liver Function", "min": 0.0, "max": 1000.0, "low": 44.0, "high": 147.0 if age<60 else 190.0}
    m["Albumin (g/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 10.0, "low": 3.5, "high": 5.0}
    m["Total Protein (g/dL)"] = {"panel": "Liver Function", "min": 0.0, "max": 15.0, "low": 6.0, "high": 8.3}
    m["Creatinine (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 20.0, "low": 0.7 if gender=="Male" else 0.5, "high": 1.2 if gender=="Male" else 1.0}
    m["Blood Urea (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 200.0, "low": 7.0, "high": 20.0}
    m["Uric Acid (mg/dL)"] = {"panel": "Kidney Function", "min": 0.0, "max": 20.0, "low": 3.5 if gender=="Male" else 2.6, "high": 7.2 if gender=="Male" else 6.0}
    m["eGFR (mL/min/1.73m²)"] = {"panel": "Kidney Function", "min": 0.0, "max": 200.0, "low": 60.0, "high": 120.0}
    m["BUN Creatinine Ratio"] = {"panel": "Kidney Function", "min": 0.0, "max": 50.0, "low": 10.0, "high": 20.0}
    m["Vitamin D (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 200.0, "low": 30.0, "high": 100.0}
    m["Vitamin B12 (pg/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 2000.0, "low": 200.0, "high": 900.0}
    m["Ferritin (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 500.0, "low": 24.0 if gender=="Male" else 11.0, "high": 336.0 if gender=="Male" else 307.0}
    m["Serum Iron (µg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 300.0, "low": 65.0 if gender=="Male" else 50.0, "high": 175.0}
    m["Calcium (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 20.0, "low": 8.5, "high": 10.5}
    m["Magnesium (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 5.0, "low": 1.7, "high": 2.4}
    m["Phosphorus (mg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 10.0, "low": 2.5, "high": 4.5}
    m["Folate (ng/mL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 50.0, "low": 2.7, "high": 17.0}
    m["Zinc (µg/dL)"] = {"panel": "Vitamins & Minerals", "min": 0.0, "max": 200.0, "low": 70.0, "high": 120.0}
    if gender == "Male":
        m["Testosterone Total (ng/dL)"] = {"panel": "Hormones", "min": 0.0, "max": 1200.0, "low": 300.0 if age>=18 else 100.0, "high": 1000.0 if age<50 else 800.0}
    else:
        m["Estradiol (pg/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 500.0, "low": 30.0, "high": 400.0}
        m["FSH (mIU/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 100.0, "low": 3.0, "high": 10.0}
        m["LH (mIU/mL)"] = {"panel": "Hormones", "min": 0.0, "max": 100.0, "low": 2.0, "high": 15.0}
    m["Cortisol Morning (µg/dL)"] = {"panel": "Hormones", "min": 0.0, "max": 60.0, "low": 6.2, "high": 19.4}
    m["CRP (mg/L)"] = {"panel": "Inflammation", "min": 0.0, "max": 200.0, "low": 0.0, "high": 3.0}
    m["ESR (mm/hr)"] = {"panel": "Inflammation", "min": 0.0, "max": 100.0, "low": 0.0, "high": 15.0 if gender=="Male" else 20.0}
    return m

def get_diabetes_intelligence(person_df, conditions):
    diabetes_markers = ["HbA1c (%)", "Fasting Glucose (mg/dL)", "Post Prandial Glucose (mg/dL)", "Fasting Insulin (µIU/mL)"]
    has_data = any(m in person_df.columns and (person_df[m] > 0).any() for m in diabetes_markers)
    if not has_data: return None
    intel = {"risk_level": "Normal", "trajectory": None, "insulin_resistance": False}
    if "HbA1c (%)" in person_df.columns:
        series = person_df["HbA1c (%)"].dropna(); series = series[series > 0]
        if len(series) >= 1:
            latest = series.iloc[-1]
            if latest >= 6.5: intel["risk_level"] = "Diabetic"
            elif latest >= 5.7: intel["risk_level"] = "Pre-Diabetic"
            else: intel["risk_level"] = "Normal"
            if len(series) >= 2:
                change = ((latest - series.iloc[0]) / series.iloc[0]) * 100
                intel["trajectory"] = "rising" if change > 5 else "improving" if change < -5 else "stable"
    if "Fasting Insulin (µIU/mL)" in person_df.columns and "Fasting Glucose (mg/dL)" in person_df.columns:
        ins = person_df["Fasting Insulin (µIU/mL)"].dropna(); glu = person_df["Fasting Glucose (mg/dL)"].dropna()
        ins = ins[ins > 0]; glu = glu[glu > 0]
        if len(ins) > 0 and len(glu) > 0:
            intel["insulin_resistance"] = (ins.iloc[-1] * glu.iloc[-1]) / 405 > 2.5
    return intel

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc)
    except: return ""

def extract_values_with_ai(pdf_text, markers, gender, age):
    if not pdf_text.strip(): return {}
    marker_list = "\n".join([f"- {mk}" for mk in markers.keys()])
    prompt = f"""Parse this blood report. Return ONLY valid JSON with marker names as keys and numeric values only.
Markers: {marker_list}
Report: {pdf_text[:4000]}
Example: {{"Hemoglobin (g/dL)": 14.5}}"""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], max_tokens=1000)
        raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except: return {}

def compute_analytics(person_df, markers):
    normal = warning = danger = improved = 0
    best_marker = worst_marker = best_val = worst_val = ""
    best_score = -1; worst_score = 999
    for marker, mdata in markers.items():
        if marker not in person_df.columns: continue
        series = person_df[marker].dropna(); series = series[series > 0]
        if len(series) == 0: continue
        latest = series.iloc[-1]; low, high = mdata["low"], mdata["high"]
        rng = high - low if high > low else 1
        if low <= latest <= high:
            normal += 1
            score = 1 - abs(latest - (low+high)/2) / (rng/2)
            if score > best_score: best_score = score; best_marker = marker; best_val = f"{latest:.1f}"
        elif latest < low:
            danger += 1; pct = (low-latest)/low*100
            if pct < worst_score: worst_score = pct; worst_marker = marker; worst_val = f"{latest:.1f} — {pct:.0f}% below normal"
        else:
            warning += 1; pct = (latest-high)/high*100
            if pct < worst_score: worst_score = pct; worst_marker = marker; worst_val = f"{latest:.1f} — {pct:.0f}% above normal"
        if len(series) >= 2:
            if low <= series.iloc[-1] <= high and (series.iloc[-2] < low or series.iloc[-2] > high): improved += 1
    total = normal + warning + danger
    return {"score": int((normal/total*100)) if total > 0 else 0, "normal": normal, "warning": warning, "danger": danger, "improved": improved, "total": total, "best_marker": best_marker, "best_val": best_val, "worst_marker": worst_marker, "worst_val": worst_val}

def get_trend_alerts(person_df, markers):
    alerts = []
    for marker, mdata in markers.items():
        if marker not in person_df.columns: continue
        series = person_df[marker].dropna(); series = series[series > 0]
        if len(series) < 2: continue
        first, last = series.iloc[0], series.iloc[-1]
        change = ((last-first)/first)*100
        if abs(change) >= 15 and mdata["low"] <= last <= mdata["high"]:
            alerts.append(f"{marker} has been {'declining' if change < 0 else 'rising'} {abs(change):.0f}% — still within range but worth watching.")
        days = (pd.Timestamp.today() - pd.Timestamp(person_df["Date"].max())).days
        if days > 180: alerts.append(f"Your last test was {days//30} months ago. Time to schedule your next panel."); break
    return alerts[:3]

def get_ai_analysis(name, person_df, gender, age, conditions, diet):
    markers = get_markers(gender, age)
    lines = []
    for marker, mdata in markers.items():
        if marker not in person_df.columns: continue
        series = person_df[marker].dropna(); series = series[series > 0]
        if len(series) >= 2:
            first, last = series.iloc[0], series.iloc[-1]
            lines.append(f"{marker}: {first:.1f} to {last:.1f} ({((last-first)/first*100):+.1f}%)")
        elif len(series) == 1: lines.append(f"{marker}: {series.iloc[0]:.1f}")
    if not lines: return "Add at least 2 tests to generate your personal health story."
    prompt = f"""Warm health assistant for Trace — Indian biomarker app.
Patient: {name}, {gender}, Age {age}, Diet: {diet}, Conditions: {conditions or 'None'}
Trends: {chr(10).join(lines)}
Write 4-5 warm sentences. Simple language. Flag drifting markers calmly. Suggest 2 doctor questions. Never diagnose. End with encouragement."""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], max_tokens=1000)
        return r.choices[0].message.content
    except: return "AI analysis unavailable right now. Your trends are shown below."

def whatsapp_summary(name, person_df, markers):
    lines = [f"Health summary from Trace", f"Name: {name}", f"Tests: {len(person_df)}", ""]
    for marker, mdata in markers.items():
        if marker not in person_df.columns: continue
        s = person_df[marker].dropna(); s = s[s > 0]
        if len(s) == 0: continue
        v = s.iloc[-1]
        lines.append(f"{marker}: {v} — {'Normal' if mdata['low'] <= v <= mdata['high'] else 'Review needed'}")
    lines += ["", "Track your health at gettrace.in"]
    return "\n".join(lines)

def calculate_age(dob_str):
    try:
        dob = datetime.strptime(str(dob_str), "%Y-%m-%d"); t = datetime.today()
        return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))
    except: return 25

def clean(val, default="—"):
    return str(val) if pd.notna(val) and str(val).strip() not in ["", "nan", "None"] else default

def get_flag(value, md):
    if value == 0.0: return None, None
    if value < md["low"]: return "Low", "danger"
    if value > md["high"]: return "High", "danger"
    return "Normal", "normal"

def get_trend_msg(series, md):
    series = series.dropna(); series = series[series > 0]
    if len(series) < 2: return "Add more tests to see your trend.", "neutral"
    first, last = series.iloc[0], series.iloc[-1]
    change = ((last-first)/first)*100
    if abs(change) < 5: return f"Stable — {change:.1f}% change over time.", "normal"
    if change < 0:
        if last < md["low"]: return f"Dropped {abs(change):.1f}% — now below normal.", "danger"
        return f"Drifting down {abs(change):.1f}% — worth monitoring.", "warning"
    if last > md["high"]: return f"Risen {change:.1f}% — now above normal.", "danger"
    return f"Drifting up {change:.1f}% — worth monitoring.", "warning"

def bar_pct(value, md):
    low, high = md["low"], md["high"]
    if high == low: return 50
    return max(5, min(95, ((value - low) / (high - low)) * 70 + 15))

def bar_color(fc):
    return "#22C55E" if fc=="normal" else "#EF4444" if fc=="danger" else "#F59E0B"

# ── SESSION & AUTH ────────────────────────────────────────────────────────────
if "extracted_values" not in st.session_state:
    st.session_state["extracted_values"] = {}
if "user" not in st.session_state:
    st.session_state["user"] = None

# Check for existing session
if st.session_state["user"] is None:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state["user"] = session.user
    except:
        pass

logo_img = f'<img src="data:image/png;base64,{logo_base64}" style="width:34px;height:34px;border-radius:8px;object-fit:cover;"/>' if logo_base64 else ""

FOOTER = f"""
<div class="t-footer">
    <div class="t-logo-wrap" style="margin:0 auto;width:44px;height:44px;">{logo_img}</div>
    <div class="t-footer-brand">Trace</div>
    <div class="t-footer-sub">Your blood tests are telling a story. This is where you read it.</div>
    <div class="t-footer-privacy">{icon_shield()} Your data never leaves your device</div>
    <div style="margin-top:20px;padding-top:16px;border-top:1px solid #E2E8F0;">
        <div style="font-size:11px;font-weight:800;color:#94A3B8;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Contact</div>
        <div style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:4px;">Mohammad Tameem Arman</div>
        <div style="font-size:12px;color:#64748B;margin-bottom:8px;font-weight:500;">Founder · Biotechnology Student · Hyderabad</div>
        <a href="mailto:tameemarman1@gmail.com" style="display:inline-block;background:#0EA5E9;color:white;padding:7px 18px;border-radius:8px;text-decoration:none;font-size:12px;font-weight:700;">tameemarman1@gmail.com</a>
    </div>
    <div style="margin-top:16px;font-size:11px;color:#CBD5E1;font-weight:500;">© 2026 Trace. Built in Hyderabad, India.</div>
</div>
"""

# ── NAV ───────────────────────────────────────────────────────────────────────
def show_nav(user=None):
    user_email = user.email if user and hasattr(user, 'email') else ""
    user_info = f'<div style="font-size:12px;font-weight:700;color:#0F172A;margin-right:4px;">{user_email}</div>' if user_email else ""
    st.markdown(f"""
    <div class="t-nav">
        <div class="t-nav-left">
            <div class="t-logo-wrap">{logo_img}</div>
            <div><div class="t-nav-brand">Trace</div><div class="t-nav-sub">Biomarker Timeline</div></div>
        </div>
        <div class="t-nav-right">
            {user_info}
            <div class="t-nav-private" style="color:#22C55E;font-size:11px;font-weight:800;">&#x2713; Private</div>
            <div class="t-nav-badge">Beta</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ══ LANDING ══════════════════════════════════════════════════════════════════
if st.session_state["user"] is None:
    show_nav()
    st.markdown(f"""
    <div class="t-hero">
        <div class="t-hero-tag">Introducing Trace</div>
        <div class="t-hero-title">Your blood tests are<br><span>telling a story</span></div>
        <div class="t-hero-sub">Track your biomarkers over months and years.<br>Catch drift before it becomes disease.<br>Finally understand what your body has been saying.</div>
        <div class="t-hero-focus">Especially built for families managing Diabetes, Thyroid and PCOS</div>
        <div class="t-pills">
            <div class="t-pill">40+ Biomarkers</div>
            <div class="t-pill">AI Health Stories</div>
            <div class="t-pill">PDF Auto-Extract</div>
            <div class="t-pill">Drift Detection</div>
            <div class="t-pill">Family Vault</div>
            <div class="t-pill">Indian Lab Ranges</div>
            <div class="t-pill">Diabetes Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Login card
    st.markdown(f"""
    <div class="t-login-card">
        <div style="font-size:22px;font-weight:900;color:#0F172A;margin-bottom:8px;">Sign in to Trace</div>
        <div style="font-size:13px;color:#64748B;font-weight:500;margin-bottom:24px;">Your health data stays private and secure.<br>Sign in once — access from any device.</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1.5, 1, 1.5])
    with col_b:
        if st.button("Continue with Google →"):
            url = sign_in_with_google()
            if url:
                st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
            else:
                st.error("Could not connect to Google. Please try again.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;font-size:12px;color:#94A3B8;font-weight:600;margin-bottom:16px;">— or sign in with email —</div>
    """, unsafe_allow_html=True)

    col_x, col_y, col_z = st.columns([1.5, 1, 1.5])
    with col_y:
        email_input = st.text_input("", placeholder="your@email.com", label_visibility="collapsed", key="email_login")
        if st.button("Send Magic Link →"):
            if email_input.strip():
                try:
                    supabase.auth.sign_in_with_otp({"email": email_input.strip()})
                    st.success("Magic link sent to your email. Click it to sign in.")
                except:
                    st.error("Could not send email. Please try again.")
            else:
                st.error("Please enter your email.")

    st.markdown("""
    <div style="text-align:center;font-size:12px;color:#94A3B8;font-weight:600;margin:16px 0;">— or continue as guest —</div>
    """, unsafe_allow_html=True)

    col_p, col_q, col_r = st.columns([1.5, 1, 1.5])
    with col_q:
        if st.button("Continue as Guest →"):
            guest_id = str(uuid.uuid4())
            class GuestUser:
                def __init__(self, gid):
                    self.id = gid
                    self.email = f"guest_{gid[:8]}"
            st.session_state["user"] = GuestUser(guest_id)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="t-feature-card"><div class="t-feature-icon" style="background:#EFF6FF;">{icon_timeline()}</div><div class="t-feature-title">Track Over Time</div><div class="t-feature-text">Upload your lab PDF or enter values. Your biomarker timeline builds automatically over months and years.</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="t-feature-card"><div class="t-feature-icon" style="background:#F0FDF4;">{icon_chart()}</div><div class="t-feature-title">Detect Drift Early</div><div class="t-feature-text">Watch your markers change before they cross danger thresholds. Catch what doctors miss between appointments.</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="t-feature-card"><div class="t-feature-icon" style="background:#F5F3FF;">{icon_brain()}</div><div class="t-feature-title">Understand Everything</div><div class="t-feature-text">AI reads your entire biomarker history and explains it in plain language. No medical degree needed.</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="t-diabetes-card">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">{icon_drop()}<div class="t-diabetes-title">Diabetes Intelligence — Built In</div></div>
        <div class="t-diabetes-sub">India has 101 million diabetics and 136 million pre-diabetics. Most don't know their HbA1c is drifting until it's too late.</div>
        <div class="t-diabetes-grid">
            <div class="t-diabetes-stat"><div class="t-diabetes-num">101M</div><div class="t-diabetes-label">Diabetics in India</div></div>
            <div class="t-diabetes-stat"><div class="t-diabetes-num">136M</div><div class="t-diabetes-label">Pre-Diabetic</div></div>
            <div class="t-diabetes-stat"><div class="t-diabetes-num">0</div><div class="t-diabetes-label">Tools tracking drift</div></div>
        </div>
    </div>
    {FOOTER}
    """, unsafe_allow_html=True)
    st.stop()

# ══ MAIN APP ══════════════════════════════════════════════════════════════════
user = st.session_state["user"]
user_id = user.id

show_nav(user)

profiles_df = load_profiles_db(user_id)
tab1, tab2, tab3 = st.tabs(["  Log Test  ", "  My Timeline  ", "  Profiles  "])

# ══ TAB 1 — LOG TEST ══════════════════════════════════════════════════════════
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    if profiles_df.empty:
        st.markdown(f"""
        <div class="t-onboard">
            <div class="t-onboard-icon" style="background:#EFF6FF;">{icon_heartbeat()}</div>
            <div class="t-onboard-title">Welcome to Trace</div>
            <div class="t-onboard-sub">Get started in three simple steps</div>
            <div class="t-step"><div class="t-step-num">1</div><div class="t-step-text"><strong>Create your profile</strong> in the Profiles tab.</div></div>
            <div class="t-step"><div class="t-step-num">2</div><div class="t-step-text"><strong>Log your first test</strong> here. Upload a PDF or enter manually.</div></div>
            <div class="t-step"><div class="t-step-num">3</div><div class="t-step-text"><strong>See your timeline.</strong> AI reads your biomarker history and explains it.</div></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_form, col_side = st.columns([3, 2])
        with col_side:
            st.markdown('<div class="t-card">', unsafe_allow_html=True)
            st.markdown('<div class="t-section">Select Profile</div>', unsafe_allow_html=True)
            profile_names = profiles_df["name"].tolist() if "name" in profiles_df.columns else []
            selected_profile = st.selectbox("", profile_names, label_visibility="collapsed", key="log_profile")
            pr = profiles_df[profiles_df["name"]==selected_profile].iloc[0]
            gender = clean(pr.get("gender"), "Male")
            age = calculate_age(pr.get("dob"))
            conditions = clean(pr.get("conditions"), "None")
            diet = clean(pr.get("diet"), "Vegetarian")
            blood_group = clean(pr.get("blood_group"), "—")
            st.markdown(f"""
            <div style="background:#F8FAFC;border-radius:12px;padding:14px 16px;margin-top:10px;border:1px solid #E2E8F0;">
                <div style="font-size:14px;font-weight:800;color:#0F172A;margin-bottom:6px;">{selected_profile}</div>
                <div style="font-size:12px;color:#64748B;font-weight:500;line-height:1.9;">{gender} · {age} years · {blood_group}<br>{diet}<br>{conditions}</div>
                <div style="font-size:11px;color:#0EA5E9;margin-top:8px;font-weight:800;">Ranges calibrated for your profile</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="t-card" style="margin-top:12px;">', unsafe_allow_html=True)
            st.markdown('<div class="t-section">Upload PDF Report</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px;color:#94A3B8;margin-bottom:12px;font-weight:500;">AI reads your lab report and fills values automatically.</div>', unsafe_allow_html=True)
            uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="visible")
            if uploaded_pdf:
                if st.button("Extract from PDF →"):
                    with st.spinner("Reading your report..."):
                        pdf_text = extract_text_from_pdf(uploaded_pdf)
                        if not pdf_text.strip():
                            st.error("Could not read this PDF. Please enter values manually.")
                        else:
                            extracted = extract_values_with_ai(pdf_text, get_markers(gender, age), gender, age)
                            if extracted:
                                st.session_state["extracted_values"] = extracted
                                st.success(f"{len(extracted)} values found.")
                            else:
                                st.warning("Could not read values clearly. Please enter manually.")
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
                st.markdown(f'<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:12px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:13px;font-weight:700;color:#166634;">{len(extracted_vals)} values extracted — review and save below</div></div>', unsafe_allow_html=True)

            values = {}
            panel_colors = {"Complete Blood Count":"#EF4444","Thyroid Panel":"#7C3AED","Diabetes Panel":"#EA580C","Lipid Profile":"#0EA5E9","Liver Function":"#16A34A","Kidney Function":"#0891B2","Vitamins & Minerals":"#D97706","Hormones":"#DB2777","Inflammation":"#DC2626"}

            for panel_name, panel_markers in panels.items():
                pc = panel_colors.get(panel_name, "#0EA5E9")
                st.markdown(f'<div class="t-panel-head"><div style="width:8px;height:8px;border-radius:50%;background:{pc};flex-shrink:0;"></div>{panel_name}</div>', unsafe_allow_html=True)
                st.markdown('<div class="t-card" style="margin-bottom:12px;">', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                for i, (marker, mdata) in enumerate(panel_markers.items()):
                    with c1 if i%2==0 else c2:
                        dv = float(extracted_vals.get(marker, 0.0))
                        dv = min(max(dv, mdata["min"]), mdata["max"])
                        values[marker] = st.number_input(marker, min_value=mdata["min"], max_value=mdata["max"], value=dv, help=f"{MARKER_INFO.get(marker,'')} | Normal: {mdata['low']} – {mdata['high']}")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save Test →"):
                numeric_values = {k: float(v) for k, v in values.items() if v != 0.0}
                if save_test_db(user_id, selected_profile, test_date, gender, age, numeric_values):
                    st.session_state["extracted_values"] = {}
                    st.success(f"Test saved for {selected_profile} on {test_date}.")
                    st.balloons()
                else:
                    st.error("Could not save test. Please try again.")

# ══ TAB 2 — TIMELINE ══════════════════════════════════════════════════════════
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    if profiles_df.empty:
        st.markdown(f'<div class="t-onboard"><div class="t-onboard-icon" style="background:#F0FDF4;">{icon_chart()}</div><div class="t-onboard-title">No timeline yet</div><div class="t-onboard-sub">Create a profile and log your first test to see your biomarker story here.</div></div>', unsafe_allow_html=True)
    else:
        col_sel, _ = st.columns([2, 4])
        with col_sel:
            profile_names2 = profiles_df["name"].tolist() if "name" in profiles_df.columns else []
            selected_name = st.selectbox("", profile_names2, label_visibility="collapsed", key="timeline_profile")

        pr = profiles_df[profiles_df["name"]==selected_name].iloc[0]
        gender = clean(pr.get("gender"), "Male")
        age = calculate_age(pr.get("dob"))
        conditions = clean(pr.get("conditions"), "None")
        diet = clean(pr.get("diet"), "Vegetarian")
        blood_group = clean(pr.get("blood_group"), "—")
        markers = get_markers(gender, age)
        person_df = load_tests_db(user_id, selected_name)

        if person_df.empty:
            st.markdown('<div class="t-onboard"><div class="t-onboard-sub">No tests logged yet. Go to Log Test to add your first blood test.</div></div>', unsafe_allow_html=True)
        else:
            person_df["Date"] = pd.to_datetime(person_df["Date"])
            person_df = person_df.sort_values("Date")
            num_tests = len(person_df)
            analytics = compute_analytics(person_df, markers)

            sc = "#22C55E" if analytics["score"] >= 75 else "#F59E0B" if analytics["score"] >= 50 else "#EF4444"
            sb = "#F0FDF4" if analytics["score"] >= 75 else "#FFFBEB" if analytics["score"] >= 50 else "#FEF2F2"

            st.markdown(f"""
            <div class="t-score-card">
                <div class="t-score-circle" style="background:{sb};border-color:{sc};color:{sc};">{analytics["score"]}</div>
                <div>
                    <div class="t-score-title">{selected_name}'s Health Score</div>
                    <div class="t-score-sub">{analytics["normal"]} normal · {analytics["warning"]} drifting · {analytics["danger"]} critical<br>{num_tests} tests · {gender} · {age} years · {blood_group} · {diet}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1,c2,c3,c4,c5 = st.columns(5)
            for col, (num, color, label) in zip([c1,c2,c3,c4,c5], [(analytics["normal"],"#22C55E","Normal"),(analytics["warning"],"#F59E0B","Drifting"),(analytics["danger"],"#EF4444","Critical"),(analytics["improved"],"#0EA5E9","Improved"),(num_tests,"#7C3AED","Tests")]):
                with col:
                    st.markdown(f'<div class="t-stat"><div class="t-stat-num" style="color:{color};">{num}</div><div class="t-stat-label">{label}</div></div>', unsafe_allow_html=True)

            diabetes_intel = get_diabetes_intelligence(person_df, conditions)
            if diabetes_intel:
                rc = {"Normal":"#22C55E","Pre-Diabetic":"#F59E0B","Diabetic":"#EF4444"}.get(diabetes_intel["risk_level"],"#94A3B8")
                rb = {"Normal":"#F0FDF4","Pre-Diabetic":"#FFFBEB","Diabetic":"#FEF2F2"}.get(diabetes_intel["risk_level"],"#F8FAFC")
                traj = {"rising":"HbA1c is rising — monitor closely.","improving":"HbA1c is improving — great progress.","stable":"HbA1c is stable."}.get(diabetes_intel["trajectory"],"")
                ir = "Insulin resistance detected — HOMA-IR above 2.5." if diabetes_intel["insulin_resistance"] else "No insulin resistance detected."
                st.markdown(f"""
                <div class="t-card-amber" style="margin-top:8px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;gap:8px;">{icon_drop()}<div style="font-size:13px;font-weight:800;color:#92400E;">Diabetes Intelligence</div></div>
                        <span style="background:{rb};color:{rc};border:1px solid {rc};font-size:11px;font-weight:800;padding:4px 12px;border-radius:20px;">{diabetes_intel["risk_level"]}</span>
                    </div>
                    <div style="font-size:13px;color:#78350F;font-weight:500;line-height:1.8;">{traj}<br>{ir}</div>
                </div>
                """, unsafe_allow_html=True)

            alerts = get_trend_alerts(person_df, markers)
            if alerts:
                st.markdown('<div class="t-section">Trend Alerts</div>', unsafe_allow_html=True)
                for alert in alerts:
                    st.markdown(f'<div class="t-alert"><div class="t-alert-line"></div><div class="t-alert-text">{alert}</div></div>', unsafe_allow_html=True)

            if analytics["best_marker"] or analytics["worst_marker"]:
                st.markdown('<div class="t-section">Key Insights</div>', unsafe_allow_html=True)
                st.markdown('<div class="t-card">', unsafe_allow_html=True)
                if analytics["best_marker"]:
                    st.markdown(f'<div class="t-insight"><div class="t-insight-dot" style="background:#22C55E;"></div><div><div class="t-insight-label" style="color:#22C55E;">Strongest marker</div><div class="t-insight-text">{analytics["best_marker"]} — {analytics["best_val"]}</div></div></div>', unsafe_allow_html=True)
                if analytics["worst_marker"]:
                    st.markdown(f'<div class="t-insight"><div class="t-insight-dot" style="background:#F59E0B;"></div><div><div class="t-insight-label" style="color:#F59E0B;">Needs attention</div><div class="t-insight-text">{analytics["worst_marker"]} — {analytics["worst_val"]}</div></div></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="t-section">Your Health Story</div>', unsafe_allow_html=True)
            with st.spinner("Reading your biomarker story..."):
                ai_story = get_ai_analysis(selected_name, person_df, gender, age, conditions, diet)
            st.markdown(f'<div class="t-card-accent"><div class="t-ai-label">{icon_brain()} AI Analysis — {selected_name} · {gender} · {age}y · {diet}</div><div class="t-ai-text">{ai_story}</div></div><p class="t-disclaimer">For educational purposes only. Always consult your doctor for medical advice.</p>', unsafe_allow_html=True)

            wa_text = whatsapp_summary(selected_name, person_df, markers)
            wa_url = f"https://wa.me/?text={wa_text.replace(chr(10),'%0A').replace(' ','%20')}"
            st.markdown(f'<div class="t-share"><div class="t-share-text">Share your health summary with your doctor or family via WhatsApp</div><a href="{wa_url}" target="_blank" style="background:#22C55E;color:white;padding:10px 18px;border-radius:10px;text-decoration:none;font-size:12px;font-weight:800;white-space:nowrap;">Share on WhatsApp</a></div>', unsafe_allow_html=True)

            st.markdown('<div class="t-section">Detailed Biomarker Trends</div>', unsafe_allow_html=True)
            panels = {}
            for marker, mdata in markers.items():
                p = mdata["panel"]
                if p not in panels: panels[p] = {}
                panels[p][marker] = mdata

            panel_colors = {"Complete Blood Count":"#EF4444","Thyroid Panel":"#7C3AED","Diabetes Panel":"#EA580C","Lipid Profile":"#0EA5E9","Liver Function":"#16A34A","Kidney Function":"#0891B2","Vitamins & Minerals":"#D97706","Hormones":"#DB2777","Inflammation":"#DC2626"}

            for panel_name, panel_markers in panels.items():
                has_data = any(mk in person_df.columns and (person_df[mk]>0).any() for mk in panel_markers)
                if not has_data: continue
                pc = panel_colors.get(panel_name, "#0EA5E9")
                st.markdown(f'<div class="t-panel-head"><div style="width:8px;height:8px;border-radius:50%;background:{pc};"></div>{panel_name}</div>', unsafe_allow_html=True)

                for marker, mdata in panel_markers.items():
                    if marker not in person_df.columns: continue
                    series = person_df[marker]
                    sc2 = series.dropna(); sc2 = sc2[sc2 > 0]
                    if len(sc2) == 0: continue
                    latest = sc2.iloc[-1]
                    flag_text, flag_class = get_flag(latest, mdata)
                    trend_msg, trend_color = get_trend_msg(series, mdata)
                    trend_css = {"normal":"t-trend-normal","warning":"t-trend-warning","danger":"t-trend-danger","neutral":"t-trend-neutral"}.get(trend_color,"t-trend-neutral")
                    badge_css = {"normal":"t-badge-normal","danger":"t-badge-danger"}.get(flag_class,"t-badge-warning") if flag_class else ""
                    flag_html = f'<span class="t-badge {badge_css}">{latest} — {flag_text}</span>' if flag_text else ""
                    pct = bar_pct(latest, mdata) if flag_text else 50
                    bc = bar_color(flag_class) if flag_class else "#94A3B8"

                    st.markdown(f"""
                    <div class="t-marker">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div style="flex:1;">
                                <div class="t-marker-name">{marker}</div>
                                <div class="t-marker-info">{MARKER_INFO.get(marker,"")}</div>
                                <div class="t-trend {trend_css}">{trend_msg}</div>
                                <div class="t-marker-range">Normal: {mdata['low']} – {mdata['high']}</div>
                            </div>
                            <div style="margin-left:12px;flex-shrink:0;">{flag_html}</div>
                        </div>
                        <div class="t-bar-wrap"><div class="t-bar" style="width:{pct}%;background:{bc};"></div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if len(sc2) >= 2:
                        fig = go.Figure()
                        fig.add_hrect(y0=mdata["low"], y1=mdata["high"], fillcolor="rgba(34,197,94,0.06)", line_width=0)
                        fig.add_trace(go.Scatter(x=person_df["Date"], y=person_df[marker], mode="lines+markers", line=dict(color="#0EA5E9", width=2.5), marker=dict(size=7, color="#0EA5E9", line=dict(color="white", width=2)), fill="tozeroy", fillcolor="rgba(14,165,233,0.06)"))
                        fig.add_hline(y=mdata["high"], line_dash="dot", line_color="rgba(239,68,68,0.3)", line_width=1.5)
                        fig.add_hline(y=mdata["low"], line_dash="dot", line_color="rgba(239,68,68,0.3)", line_width=1.5)
                        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,0.8)", height=180, margin=dict(l=0,r=0,t=8,b=0), showlegend=False, xaxis=dict(showgrid=False, showline=False, tickfont=dict(color="#94A3B8", size=10)), yaxis=dict(showgrid=True, gridcolor="rgba(226,232,240,0.8)", showline=False, tickfont=dict(color="#94A3B8", size=10)))
                        st.plotly_chart(fig, use_container_width=True)
                    st.markdown("<br>", unsafe_allow_html=True)

            st.markdown('<div class="t-feedback"><div class="t-feedback-title">How did this feel?</div><div class="t-feedback-sub">Tell us what you felt, what confused you, or what you wish existed.</div></div>', unsafe_allow_html=True)
            rating = st.radio("", ["1","2","3","4","5"], horizontal=True, label_visibility="collapsed")
            feedback_text = st.text_area("", placeholder="What did you feel? What confused you? What do you wish Trace could do?", height=100, label_visibility="collapsed")
            feedback_email = st.text_input("", placeholder="Email — optional", label_visibility="collapsed")
            col_btn, _ = st.columns([1,2])
            with col_btn:
                if st.button("Send Feedback →"):
                    if not feedback_text.strip():
                        st.error("Please write something before sending.")
                    else:
                        save_feedback_db(user_id, selected_name, rating, feedback_text, feedback_email)
                        st.success("Received. Thank you so much.")

# ══ TAB 3 — PROFILES ══════════════════════════════════════════════════════════
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_new, col_existing = st.columns([2, 3])

    with col_new:
        st.markdown('<div class="t-card">', unsafe_allow_html=True)
        st.markdown('<div class="t-section">Create Profile</div>', unsafe_allow_html=True)
        st.markdown('<div class="t-label">Full Name</div>', unsafe_allow_html=True)
        new_name = st.text_input("", placeholder="e.g. Arman Khan", key="new_name", label_visibility="collapsed")
        st.markdown('<div class="t-label">Date of Birth</div>', unsafe_allow_html=True)
        new_dob = st.date_input("", value=date(2000,1,1), min_value=date(1920,1,1), max_value=date.today(), key="new_dob", label_visibility="collapsed")
        st.markdown('<div class="t-label">Gender</div>', unsafe_allow_html=True)
        new_gender = st.selectbox("", ["Male","Female","Other"], key="new_gender", label_visibility="collapsed")
        st.markdown('<div class="t-label">Blood Group</div>', unsafe_allow_html=True)
        new_blood = st.selectbox("", ["A+","A-","B+","B-","AB+","AB-","O+","O-","Unknown"], key="new_blood", label_visibility="collapsed")
        st.markdown('<div class="t-label">Known Conditions</div>', unsafe_allow_html=True)
        new_conditions = st.multiselect("", ["Diabetes","Thyroid Disorder","Hypertension","PCOS","Heart Disease","Kidney Disease","None"], default=["None"], key="new_conditions", label_visibility="collapsed")
        st.markdown('<div class="t-label">Diet Type</div>', unsafe_allow_html=True)
        new_diet = st.selectbox("", ["Vegetarian","Non-Vegetarian","Vegan","Eggetarian"], key="new_diet", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Profile →"):
            if not new_name:
                st.error("Please enter a name.")
            elif "name" in profiles_df.columns and new_name in profiles_df["name"].tolist():
                st.warning("A profile with this name already exists.")
            else:
                if save_profile_db(user_id, new_name, new_dob, new_gender, new_blood, ", ".join(new_conditions), new_diet):
                    st.success(f"Profile created for {new_name}.")
                    st.rerun()
                else:
                    st.error("Could not save profile. Please try again.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_existing:
        st.markdown('<div class="t-section">Your Profiles</div>', unsafe_allow_html=True)
        if profiles_df.empty:
            st.markdown('<div class="t-card" style="text-align:center;padding:32px;"><div style="font-size:14px;font-weight:800;color:#0F172A;margin-bottom:4px;">No profiles yet</div><div style="font-size:12px;color:#94A3B8;font-weight:500;">Create your first profile to get started</div></div>', unsafe_allow_html=True)
        else:
            for _, row in profiles_df.iterrows():
                a = calculate_age(row.get("dob"))
                conds = clean(row.get("conditions"), "None")
                diab_badge = '<span style="background:#FFF7ED;color:#EA580C;border:1px solid #FED7AA;font-size:10px;font-weight:800;padding:2px 8px;border-radius:10px;margin-left:6px;">Diabetes</span>' if "Diabetes" in conds else ""
                st.markdown(f"""
                <div class="t-profile-item">
                    <div class="t-profile-name">{row.get('name','')}{diab_badge}</div>
                    <div class="t-profile-info">{clean(row.get('gender'))} · {a} years · {clean(row.get('blood_group'),'—')}<br>{clean(row.get('diet'),'—')} · {conds}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="t-section">Account</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="t-card">
            <div style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:4px;">Signed in as</div>
            <div style="font-size:12px;color:#64748B;font-weight:500;">{user.email if hasattr(user, 'email') else 'Google Account'}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign Out →"):
            try:
                supabase.auth.sign_out()
            except:
                pass
            st.session_state["user"] = None
            st.rerun()

st.markdown(FOOTER, unsafe_allow_html=True)
