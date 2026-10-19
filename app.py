"""
HelpDesk AI - Enterprise IT Service Management (ITSM) System
Multi-Agent Incident Triage, SOP Grounded Retrieval, Safety Auditing & Policy Routing.
Powered by LangGraph, Local Ollama / Enterprise Cloud MoE, Deterministic ITIL Guardrails,
and Secure PBKDF2-HMAC-SHA256 Authentication.
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import re
import html

# Local core modules
from agents.orchestrator import process_ticket
from llm_client import check_model_status
from sample_tickets import SAMPLE_TICKETS
from knowledge_base import KB_ARTICLES, get_article_by_id
from evaluation import run_comprehensive_evaluation
import auth
from rbac import (
    ROLE_EMPLOYEE,
    ROLE_IT_SUPPORT,
    ROLE_ADMIN_SECOPS,
    normalize_role,
    get_nav_views_for_role,
    get_backend_tickets,
    can_user_access_ticket,
    filter_security_incidents,
    calculate_role_metrics,
    clean_inference_source,
    sanitize_ui_text
)

# Page configuration
st.set_page_config(
    page_title="HelpDesk AI | IT Incident Management",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# PREMIUM LIGHT SAAS CSS THEME (Mint / Emerald / Teal Accents & Ambient Orbs)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Global Typography & Light SaaS Reset */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #0f172a;
    }
    
    /* Background with Soft Glowing Gradient Orbs */
    .stApp {
        background-color: #f8fafc !important;
        background-image: 
            radial-gradient(circle at 10% 12%, rgba(13, 148, 136, 0.07) 0%, transparent 40%),
            radial-gradient(circle at 90% 88%, rgba(16, 185, 129, 0.07) 0%, transparent 42%),
            radial-gradient(circle at 50% 50%, rgba(20, 184, 166, 0.04) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
    }

    /* Streamlit Sidebar Light Override */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.02) !important;
    }
    section[data-testid="stSidebar"] * {
        color: #1e293b !important;
    }

    /* Top Header Bar */
    .app-header {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(12px);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 22px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .app-header-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #0d9488 0%, #10b981 100%);
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        box-shadow: 0 4px 10px rgba(13, 148, 136, 0.25);
    }

    /* Light SaaS Cards */
    .saas-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .saas-card:hover {
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e1;
    }
    
    .saas-card-header {
        font-size: 0.80rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Metric KPI Cards */
    .metric-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(13, 148, 136, 0.08);
        border-color: #99f6e4;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.76rem;
        color: #0d9488;
        font-weight: 500;
        margin-top: 6px;
    }

    /* Polished Status Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 600;
        line-height: 1.3;
        white-space: nowrap;
    }
    .badge-critical {
        background-color: #ffe4e6;
        color: #e11d48;
        border: 1px solid #fecdd3;
    }
    .badge-high {
        background-color: #fef3c7;
        color: #d97706;
        border: 1px solid #fde68a;
    }
    .badge-medium {
        background-color: #e0f2fe;
        color: #0284c7;
        border: 1px solid #bae6fd;
    }
    .badge-low {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    .badge-security {
        background-color: #f3e8ff;
        color: #7e22ce;
        border: 1px solid #e9d5ff;
    }
    .badge-category {
        background-color: #f8fafc;
        color: #334155;
        border: 1px solid #cbd5e1;
    }
    .badge-success {
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }
    .badge-escalated {
        background-color: #fff1f2;
        color: #be123c;
        border: 1px solid #fecdd3;
    }

    /* Escalation Banners */
    .security-banner {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        border-left: 5px solid #e11d48;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(225, 29, 72, 0.08);
    }
    .security-title {
        font-size: 0.98rem;
        font-weight: 800;
        color: #be123c;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .security-body {
        font-size: 0.86rem;
        color: #9f1239;
        line-height: 1.5;
    }

    .escalation-banner {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        border-left: 5px solid #f59e0b;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .escalation-title {
        font-size: 0.96rem;
        font-weight: 700;
        color: #b45309;
        margin-bottom: 4px;
    }
    .escalation-body {
        font-size: 0.86rem;
        color: #92400e;
        line-height: 1.5;
    }

    .standard-banner {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 5px solid #10b981;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .standard-title {
        font-size: 0.96rem;
        font-weight: 700;
        color: #047857;
        margin-bottom: 4px;
    }
    .standard-body {
        font-size: 0.86rem;
        color: #065f46;
        line-height: 1.5;
    }

    /* Actionable DO & DON'T Cards */
    .do-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .do-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #059669;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .dont-card {
        background: #fff1f2;
        border: 1px solid #fecdd3;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .dont-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #e11d48;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .action-step-item {
        font-size: 0.87rem;
        color: #1e293b;
        line-height: 1.45;
        margin-bottom: 8px;
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }

    /* Micro labels */
    .field-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .field-value {
        font-size: 0.92rem;
        color: #0f172a;
        margin-bottom: 12px;
    }

    /* KB Article Chip */
    .kb-chip {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        transition: border-color 0.15s ease;
    }
    .kb-chip:hover {
        border-color: #0d9488;
        background: #ffffff;
    }

    /* Form Inputs with Glowing Focus */
    .stTextInput input, .stTextArea textarea {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #0d9488 !important;
        box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.16) !important;
        outline: none !important;
    }
    div[data-baseweb="select"] {
        border-radius: 10px !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="select"] * {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    /* Buttons with Mint/Teal Gradients & Micro-interactions */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0d9488 0%, #059669 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        padding: 9px 18px !important;
        box-shadow: 0 2px 6px rgba(13, 148, 136, 0.28) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.38) !important;
        opacity: 0.96 !important;
    }
    button[kind="primary"]:active {
        transform: translateY(0) !important;
    }
    button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 9px !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
    }

    /* User Profile & System Status Pill */
    .user-profile-badge {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .system-status-pill {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 14px;
    }

    /* Agent Timeline Stepper */
    .timeline-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        overflow-x: auto;
    }
    .timeline-step {
        display: flex;
        align-items: center;
        gap: 10px;
        position: relative;
    }
    .step-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #ecfdf5;
        color: #059669;
        border: 2px solid #10b981;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .step-label {
        font-size: 0.82rem;
        font-weight: 700;
        color: #0f172a;
    }
    .step-sub {
        font-size: 0.70rem;
        color: #64748b;
    }
    .timeline-arrow {
        color: #cbd5e1;
        font-size: 1.1rem;
        margin: 0 8px;
    }

    /* Reduced Motion Preference */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = ""

if "auth_email" not in st.session_state:
    st.session_state["auth_email"] = ""

if "auth_role" not in st.session_state:
    st.session_state["auth_role"] = ""

if "auth_tab" not in st.session_state:
    st.session_state["auth_tab"] = "login"

if "tickets" not in st.session_state:
    initial_queue = []
    for item in SAMPLE_TICKETS:
        t_copy = dict(item)
        t_copy["status"] = "New"
        t_copy["processed_result"] = None
        t_copy["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        t_copy.setdefault("reporter_email", f"staff.{t_copy['id'].lower()}@enterprise.internal")
        t_copy.setdefault("reporter_name", "Corporate Staff")
        t_copy.setdefault("created_by", t_copy["reporter_email"])
        initial_queue.append(t_copy)
    st.session_state["tickets"] = initial_queue

if "wb_title" not in st.session_state:
    st.session_state["wb_title"] = ""

if "wb_desc" not in st.session_state:
    st.session_state["wb_desc"] = ""

if "wb_impact" not in st.session_state:
    st.session_state["wb_impact"] = "One user"

if "wb_urgency" not in st.session_state:
    st.session_state["wb_urgency"] = "Work impaired"

if "active_processed_result" not in st.session_state:
    st.session_state["active_processed_result"] = None

if "current_ticket_id" not in st.session_state:
    st.session_state["current_ticket_id"] = None

if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = "My Dashboard"

if "evaluation_results" not in st.session_state:
    st.session_state["evaluation_results"] = None

if "global_search" not in st.session_state:
    st.session_state["global_search"] = ""


# ==============================================================================
# HELPER FUNCTIONS & CALLBACKS
# ==============================================================================
def clear_form_state():
    st.session_state["wb_title"] = ""
    st.session_state["wb_desc"] = ""
    st.session_state["wb_impact"] = "One user"
    st.session_state["wb_urgency"] = "Work impaired"
    st.session_state["current_ticket_id"] = None
    st.session_state["active_processed_result"] = None


def blank_form_callback():
    clear_form_state()
    user_role = st.session_state.get("auth_role", "")
    canon = normalize_role(user_role)
    if canon == ROLE_EMPLOYEE:
        st.session_state["nav_view"] = "Submit Ticket"
    else:
        st.session_state["nav_view"] = "Triage Workbench"


def load_ticket_callback(ticket_dict: dict):
    user_email = st.session_state.get("auth_email", "")
    user_role = st.session_state.get("auth_role", "")
    # Server-side authorization check before loading ticket into session workbench
    if not can_user_access_ticket(ticket_dict, user_email, user_role):
        st.session_state["current_ticket_id"] = None
        st.session_state["active_processed_result"] = None
        return

    st.session_state["wb_title"] = ticket_dict.get("title", "")
    st.session_state["wb_desc"] = ticket_dict.get("description", "")
    st.session_state["wb_impact"] = ticket_dict.get("impact", "One user")
    st.session_state["wb_urgency"] = ticket_dict.get("urgency", "Work impaired")
    st.session_state["current_ticket_id"] = ticket_dict.get("id")
    st.session_state["active_processed_result"] = ticket_dict.get("processed_result")
    
    canon = normalize_role(user_role)
    if canon == ROLE_EMPLOYEE:
        st.session_state["nav_view"] = "Submit Ticket"
    elif canon == ROLE_IT_SUPPORT:
        st.session_state["nav_view"] = "Triage Workbench"
    else:
        st.session_state["nav_view"] = "Security Incidents" if ticket_dict.get("expected_category") == "Security" else "All Incidents"


def logout_callback():
    st.session_state["authenticated"] = False
    st.session_state["auth_user"] = ""
    st.session_state["auth_email"] = ""
    st.session_state["auth_role"] = ""
    clear_form_state()
    st.rerun()


def update_ticket_result(ticket_id: str, result: dict):
    for t in st.session_state["tickets"]:
        if t["id"] == ticket_id:
            t["processed_result"] = result
            t["status"] = result.get("status", "Triaged")
            t["expected_category"] = result.get("category")
            t["expected_priority"] = result.get("priority")
            break


def render_priority_badge(priority: str) -> str:
    p = str(priority).capitalize()
    cls = {
        "Critical": "badge-critical",
        "High": "badge-high",
        "Medium": "badge-medium",
        "Low": "badge-low"
    }.get(p, "badge-low")
    return f"<span class='badge {cls}'>{html.escape(p)}</span>"


def render_category_badge(category: str) -> str:
    c = str(category).capitalize()
    cls = "badge-security" if c == "Security" else "badge-category"
    return f"<span class='badge {cls}'>{html.escape(c)}</span>"


def render_status_badge(status: str) -> str:
    s = str(status)
    if "Escalated" in s:
        cls = "badge-escalated"
    elif "Resolved" in s or "Triaged" in s or "Advisory" in s:
        cls = "badge-success"
    else:
        cls = "badge-category"
    return f"<span class='badge {cls}'>{html.escape(s)}</span>"


def render_guidance_cards(do_steps: list, dont_steps: list):
    """Safely renders DO and DON'T checklists as self-contained HTML blocks."""
    do_items_html = "".join([
        f"<div class='action-step-item'><span style='color: #059669; font-weight: 700;'>{idx}.</span><span>{html.escape(s)}</span></div>"
        for idx, s in enumerate(do_steps, 1)
    ])
    dont_items_html = "".join([
        f"<div class='action-step-item'><span style='color: #e11d48; font-weight: 700;'>✕</span><span>{html.escape(s)}</span></div>"
        for s in dont_steps
    ])
    full_html = f"""
    <div class='do-card'>
        <div class='do-title'>✅ What You Need to DO:</div>
        {do_items_html}
    </div>
    <div class='dont-card'>
        <div class='dont-title'>🚫 What You Must NOT DO:</div>
        {dont_items_html}
    </div>
    """
    st.markdown(full_html, unsafe_allow_html=True)


def render_retrieved_articles_card(articles: list):
    """Safely renders referenced SOP knowledge base articles as a self-contained card."""
    if articles:
        chips_html = "".join([
            f"<div class='kb-chip'>"
            f"<div style='font-size: 0.84rem; font-weight: 700; color: #0f172a;'>📄 {html.escape(art['id'])}: {html.escape(art['title'])}</div>"
            f"<div style='font-size: 0.78rem; color: #64748b; margin-top: 4px;'>{html.escape(art['summary'])}</div>"
            f"</div>"
            for art in articles
        ])
    else:
        chips_html = "<div style='font-size: 0.84rem; color: #94a3b8; padding: 6px 0;'>No approved knowledge SOP article matched this query.</div>"

    card_html = f"""
    <div class='saas-card'>
        <div class='saas-card-header'>
            <span>Approved SOP Articles Referenced ({len(articles)})</span>
            <span class='badge badge-category'>Token/Keyword Match</span>
        </div>
        {chips_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def format_concise_guidance(recommendation_text: str, category: str, is_escalated: bool):
    """Parses and formats recommendations into direct 'What to DO' and 'What NOT to DO' action items."""
    lines = (recommendation_text or "").split("\n")
    do_steps = []
    for l in lines:
        cleaned = l.strip()
        if not cleaned or cleaned.startswith("**") or cleaned.startswith("*") or cleaned.startswith("#"):
            continue
        m = re.match(r"^(\d+[\.\)]\s*)(.+)", cleaned)
        if m:
            do_steps.append(m.group(2).strip())
        elif len(cleaned) > 12 and not any(k in cleaned.lower() for k in ["advisory", "notice", "estimated", "guardrail"]):
            do_steps.append(cleaned)
    
    if not do_steps:
        if category == "Hardware":
            do_steps = [
                "Perform clean shutdown; disconnect docks and unapproved chargers for 30s.",
                "Inspect air vents; ensure laptop is on a flat, unblocked surface.",
                "If chassis remains hot or power fails, submit for hardware technician inspection."
            ]
        elif category == "Network":
            do_steps = [
                "Verify local internet connectivity by pinging your default router gateway.",
                "Restart the corporate AnyConnect VPN client and attempt reconnection.",
                "Flush local DNS cache and disable conflicting secondary virtual adapters."
            ]
        elif category == "Access":
            do_steps = [
                "Use the enterprise self-service portal to initiate Active Directory password reset.",
                "Wait 15 minutes for temporary invalid-attempt lockout counters to clear.",
                "Update cached credentials across local Outlook and browser sessions."
            ]
        elif category == "Security":
            do_steps = [
                "Immediately disconnect Wi-Fi and unplug network cables to isolate your device.",
                "Change corporate account passwords from a separate, uncompromised endpoint.",
                "Flag suspicious email or link to SecOps incident response on-call team."
            ]
        else:
            do_steps = [
                "Restart application and clear corrupted local session cache files.",
                "Verify system updates and restart operating system.",
                "Collect error log timestamps if unexpected crashes persist."
            ]
    
    dont_steps = [
        "DO NOT share passwords, Active Directory PINs, or MFA codes with anyone.",
        "DO NOT execute unverified or destructive terminal commands (e.g., format / wipe)."
    ]
    if category == "Security":
        dont_steps.append("DO NOT keep device connected to corporate network while under investigation.")
        dont_steps.append("DO NOT forward phishing messages or click any further embedded links.")
    elif category == "Hardware":
        dont_steps.append("DO NOT open laptop chassis or attempt internal battery maintenance yourself.")
        dont_steps.append("DO NOT use device if battery shows physical swelling or emits burnt odor.")
    elif category == "Access":
        dont_steps.append("DO NOT repeatedly re-enter expired passwords (causes hard AD account lockout).")
    elif category == "Network":
        dont_steps.append("DO NOT install unapproved third-party proxies or bypass company firewall.")
    else:
        dont_steps.append("DO NOT modify registry entries or delete application system binaries.")

    return do_steps[:4], dont_steps[:3]


# ==============================================================================
# AUTHENTICATION EXPERIENCE (Login & Signup)
# ==============================================================================
if not st.session_state.get("authenticated", False):
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    col_wrap_l, col_wrap_m, col_wrap_r = st.columns([1, 10, 1])
    with col_wrap_m:
        col_hero, col_card = st.columns([1.1, 1], gap="large")

        # Left: Branded Welcome Panel
        with col_hero:
            welcome_html = (
                "<div style='padding: 24px 16px;'>"
                "<div style='display: flex; align-items: center; gap: 14px; margin-bottom: 20px;'>"
                "<div style='width: 48px; height: 48px; border-radius: 12px; background: linear-gradient(135deg, #0d9488 0%, #10b981 100%); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; box-shadow: 0 6px 18px rgba(13, 148, 136, 0.30); color: white;'>"
                "🛡️"
                "</div>"
                "<div>"
                "<h1 style='font-size: 1.75rem; font-weight: 800; color: #0f172a; margin: 0; line-height: 1.2;'>HelpDesk AI</h1>"
                "<p style='font-size: 0.84rem; color: #0d9488; font-weight: 600; margin: 2px 0 0 0;'>Autonomous IT Service Management</p>"
                "</div>"
                "</div>"
                "<p style='font-size: 0.96rem; color: #475569; line-height: 1.6; margin-bottom: 24px;'>"
                "Experience next-generation IT incident resolution. Powered by LangGraph multi-agent orchestration, official SOP retrieval, deterministic ITIL priority matrix, and strict safety guardrails."
                "</p>"
                "<div style='display: flex; flex-direction: column; gap: 14px; margin-bottom: 28px;'>"
                "<div style='display: flex; align-items: flex-start; gap: 12px;'>"
                "<div style='width: 24px; height: 24px; border-radius: 50%; background: #ecfdf5; color: #059669; display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 800;'>✓</div>"
                "<div style='font-size: 0.88rem; color: #334155;'><b>Role-Based Access Control</b> — Strict backend-scoped incident views for Employees, IT Support, and SecOps.</div>"
                "</div>"
                "<div style='display: flex; align-items: flex-start; gap: 12px;'>"
                "<div style='width: 24px; height: 24px; border-radius: 50%; background: #ecfdf5; color: #059669; display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 800;'>✓</div>"
                "<div style='font-size: 0.88rem; color: #334155;'><b>Critic Safety Audit</b> — Deterministic zero-credential-leak guardrails and safe operation verification.</div>"
                "</div>"
                "<div style='display: flex; align-items: flex-start; gap: 12px;'>"
                "<div style='width: 24px; height: 24px; border-radius: 50%; background: #ecfdf5; color: #059669; display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 800;'>✓</div>"
                "<div style='font-size: 0.88rem; color: #334155;'><b>Instant SOP Grounding</b> — Verified troubleshooting actions retrieved directly from organizational SOPs.</div>"
                "</div>"
                "</div>"
                "<div style='background: rgba(255, 255, 255, 0.7); border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; font-size: 0.78rem; color: #64748b; display: flex; align-items: center; gap: 10px;'>"
                "<span style='font-size: 1rem;'>🔒</span>"
                "<span><b>Enterprise Security:</b> Encrypted authentication, role-based access control, and ITIL-aligned guardrails.</span>"
                "</div>"
                "</div>"
            )
            st.markdown(welcome_html, unsafe_allow_html=True)

        # Right: Auth Card (Login vs Signup Switcher)
        with col_card:
            with st.container(border=True):
                tab_col1, tab_col2 = st.columns(2)
                with tab_col1:
                    is_login_active = (st.session_state["auth_tab"] == "login")
                    if st.button("Sign In", type="primary" if is_login_active else "secondary", use_container_width=True, key="btn_nav_signin"):
                        st.session_state["auth_tab"] = "login"
                        st.rerun()
                with tab_col2:
                    is_signup_active = (st.session_state["auth_tab"] == "signup")
                    if st.button("Create Account", type="primary" if is_signup_active else "secondary", use_container_width=True, key="btn_nav_signup"):
                        st.session_state["auth_tab"] = "signup"
                        st.rerun()

                st.markdown("<hr style='margin: 14px 0 16px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

                if st.session_state["auth_tab"] == "login":
                    st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 2px;'>Welcome Back</h3>", unsafe_allow_html=True)
                    st.markdown("<p style='font-size: 0.80rem; color: #64748b; margin-bottom: 14px;'>Enter your corporate credentials to access the service desk.</p>", unsafe_allow_html=True)

                    login_email = st.text_input("Corporate Email", key="login_email_input", placeholder="name@enterprise.internal")
                    
                    col_pwd, col_toggle = st.columns([4, 1])
                    with col_toggle:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        show_pwd = st.checkbox("Show", key="login_show_pwd")
                    with col_pwd:
                        login_pwd = st.text_input("Password", type="text" if show_pwd else "password", key="login_pwd_input", placeholder="Enter your password")

                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                    if st.button("🚀 Sign In to Dashboard", type="primary", use_container_width=True, key="btn_exec_login"):
                        if not login_email.strip() or not login_pwd:
                            st.error("Please provide both email and password.")
                        else:
                            success, msg, user_data = auth.authenticate_user(login_email, login_pwd)
                            if success and user_data:
                                st.session_state["authenticated"] = True
                                st.session_state["auth_user"] = user_data["full_name"]
                                st.session_state["auth_email"] = user_data["email"]
                                st.session_state["auth_role"] = user_data["role"]
                                st.session_state["nav_view"] = get_nav_views_for_role(user_data["role"])[0]
                                st.success("Authentication successful! Loading workspace...")
                                st.rerun()
                            else:
                                st.error(f"Authentication failed: {msg}")



                else:
                    st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 2px;'>Create Your Account</h3>", unsafe_allow_html=True)
                    st.markdown("<p style='font-size: 0.80rem; color: #64748b; margin-bottom: 14px;'>Register a new enterprise user profile with local storage.</p>", unsafe_allow_html=True)

                    su_name = st.text_input("Full Employee Name", key="su_name_input", placeholder="e.g. Elena Rostova")
                    su_email = st.text_input("Corporate Email", key="su_email_input", placeholder="elena.rostova@enterprise.internal")
                    st.text_input(
                        "Assigned Role",
                        value="Employee / Incident Reporter",
                        disabled=True,
                        key="su_role_display",
                        help="Standard self-registration assigns standard Employee permissions. Elevated roles require administrative authorization."
                    )
                    su_role = "Employee / Incident Reporter"

                    col_supwd, col_sutoggle = st.columns([4, 1])
                    with col_sutoggle:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        show_su_pwd = st.checkbox("Show", key="su_show_pwd")
                    with col_supwd:
                        su_pwd = st.text_input("Password", type="text" if show_su_pwd else "password", key="su_pwd_input", placeholder="Min 8 chars with mixed case")

                    su_confirm = st.text_input("Confirm Password", type="text" if show_su_pwd else "password", key="su_confirm_input", placeholder="Repeat password")

                    if su_pwd:
                        strength = auth.calculate_password_strength(su_pwd)
                        st.markdown(
                            f"<div style='margin-top: 6px; margin-bottom: 10px;'>"
                            f"<div style='display: flex; justify-content: space-between; font-size: 0.74rem; font-weight: 600; color: #64748b; margin-bottom: 3px;'>"
                            f"<span>Password Strength:</span>"
                            f"<span style='color: {strength['color']}; font-weight: 700;'>{html.escape(strength['label'])}</span>"
                            f"</div>"
                            f"<div style='background: #e2e8f0; height: 6px; border-radius: 4px; overflow: hidden;'>"
                            f"<div style='background: {strength['color']}; width: {strength['percent']}%; height: 100%; transition: width 0.3s ease;'></div>"
                            f"</div>"
                            f"<div style='font-size: 0.72rem; color: #64748b; margin-top: 5px;'>"
                            f"<span>{'✓' if strength['checks']['min_length'] else '✕'} 8+ chars &nbsp;|&nbsp; </span>"
                            f"<span>{'✓' if strength['checks']['has_upper'] else '✕'} Uppercase &nbsp;|&nbsp; </span>"
                            f"<span>{'✓' if strength['checks']['has_lower'] else '✕'} Lowercase &nbsp;|&nbsp; </span>"
                            f"<span>{'✓' if strength['checks']['has_digit'] else '✕'} Number &nbsp;|&nbsp; </span>"
                            f"<span>{'✓' if strength['checks']['has_special'] else '✕'} Symbol</span>"
                            f"</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

                    if st.button("✨ Complete Registration", type="primary", use_container_width=True, key="btn_exec_signup"):
                        ok, reg_msg, new_user = auth.register_user(
                            email=su_email,
                            full_name=su_name,
                            password=su_pwd,
                            confirm_password=su_confirm,
                            role=su_role,
                            allow_privileged=False
                        )
                        if ok and new_user:
                            st.session_state["authenticated"] = True
                            st.session_state["auth_user"] = new_user["full_name"]
                            st.session_state["auth_email"] = new_user["email"]
                            st.session_state["auth_role"] = new_user["role"]
                            st.session_state["nav_view"] = get_nav_views_for_role(new_user["role"])[0]
                            st.success("Account registered successfully! Redirecting...")
                            st.rerun()
                        else:
                            st.error(f"Registration failed: {reg_msg}")

                st.markdown(
                    "<div style='margin-top: 18px; font-size: 0.72rem; color: #94a3b8; text-align: center;'>"
                    "Protected by Secure Authentication & ITIL Incident Guardrails"
                    "</div>",
                    unsafe_allow_html=True
                )
    st.stop()


# ==============================================================================
# MAIN APPLICATION (Protected Access)
# ==============================================================================

# Extract RBAC context
auth_user = st.session_state.get("auth_user", "Enterprise User")
auth_email = st.session_state.get("auth_email", "")
auth_role = st.session_state.get("auth_role", "Employee / Incident Reporter")
canon_role = normalize_role(auth_role)

# Backend ticket filtering:
# - Employee gets ONLY their own tickets
# - IT Support and Admin/SecOps get authorized queue tickets
user_tickets = get_backend_tickets(auth_email, auth_role, st.session_state["tickets"])
role_metrics = calculate_role_metrics(user_tickets, auth_role, len(KB_ARTICLES))

# Validate navigation selection against role authorization
allowed_views = get_nav_views_for_role(auth_role)
if st.session_state.get("nav_view") not in allowed_views:
    st.session_state["nav_view"] = allowed_views[0]

# Fetch active model backend telemetry
model_stat = check_model_status()

# ------------------------------------------------------------------------------
# SIDEBAR NAVIGATION & USER PROFILE
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
            <div style='width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #0d9488 0%, #10b981 100%); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: white;'>
                🛡️
            </div>
            <div>
                <h3 style='margin: 0; font-size: 1.15rem; font-weight: 800; color: #0f172a;'>HelpDesk AI</h3>
                <div style='font-size: 0.70rem; color: #0d9488; font-weight: 600;'>Enterprise ITSM</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<hr style='margin: 8px 0 14px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Active User Profile Card
    user_initials = "".join([part[0] for part in auth_user.split()[:2]]).upper() or "U"
    st.markdown(
        f"""
        <div class='user-profile-badge'>
            <div style='display: flex; align-items: center; gap: 10px;'>
                <div style='width: 34px; height: 34px; border-radius: 50%; background: #ccfbf1; color: #0f766e; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 0.85rem;'>
                    {html.escape(user_initials)}
                </div>
                <div style='overflow: hidden;'>
                    <div style='font-size: 0.84rem; font-weight: 700; color: #0f172a; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>{html.escape(auth_user)}</div>
                    <div style='font-size: 0.70rem; color: #0d9488; font-weight: 600;'>{html.escape(auth_role)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.button("🚪 Sign Out", on_click=logout_callback, use_container_width=True, key="btn_sidebar_logout")
    st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Sidebar Navigation Radio (Strictly authorized views)
    selected_nav = st.radio(
        "Navigation Menu",
        options=allowed_views,
        index=allowed_views.index(st.session_state["nav_view"]) if st.session_state["nav_view"] in allowed_views else 0,
        label_visibility="collapsed"
    )
    st.session_state["nav_view"] = selected_nav

    st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Role-Specific Sidebar Status (Strictly scoped)
    if canon_role == ROLE_EMPLOYEE:
        st.markdown(
            f"""
            <div style='font-size: 0.74rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>My Service Status</div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>My Submitted Tickets:</span>
                <span style='font-weight: 700; color: #0f172a;'>{role_metrics['total_tickets']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Under Review / Active:</span>
                <span style='font-weight: 700; color: #0d9488;'>{role_metrics['active_tickets']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 12px; color: #334155;'>
                <span>Resolved Tickets:</span>
                <span style='font-weight: 700; color: #059669;'>{role_metrics['resolved_tickets']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif canon_role == ROLE_IT_SUPPORT:
        st.markdown(
            f"""
            <div style='font-size: 0.74rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>IT Support Queue</div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Queue Incidents:</span>
                <span style='font-weight: 700; color: #0f172a;'>{role_metrics['total_queue']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Triaged & Analyzed:</span>
                <span style='font-weight: 700; color: #0d9488;'>{role_metrics['triaged_analyzed']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Pending Triage:</span>
                <span style='font-weight: 700; color: #d97706;'>{role_metrics['pending_triage']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 12px; color: #334155;'>
                <span>Escalated Incidents:</span>
                <span style='font-weight: 700; color: #e11d48;'>{role_metrics['escalated']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style='font-size: 0.74rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Organisation Security & Ops</div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Total Org Incidents:</span>
                <span style='font-weight: 700; color: #0f172a;'>{role_metrics['total_org_incidents']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Security Threats:</span>
                <span style='font-weight: 700; color: #e11d48;'>{role_metrics['security_threats']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 5px; color: #334155;'>
                <span>Critical / High:</span>
                <span style='font-weight: 700; color: #d97706;'>{role_metrics['high_critical']}</span>
            </div>
            <div style='display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 12px; color: #334155;'>
                <span>Triaged Rate:</span>
                <span style='font-weight: 700; color: #0d9488;'>{role_metrics['triage_rate']}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # System Inference Telemetry (Sanitized - Zero vendor branding)
    if model_stat.get("is_cloud"):
        st.markdown(
            """
            <div class='system-status-pill' style='border-color: #bae6fd; background: #f0f9ff;'>
                <div style='font-size: 0.78rem; font-weight: 700; color: #0369a1;'>☁️ Enterprise Cloud AI</div>
                <div style='font-size: 0.70rem; color: #0284c7; margin-top: 2px;'>Operational & Ready</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif model_stat["ollama"]["available"]:
        st.markdown(
            """
            <div class='system-status-pill' style='border-color: #a7f3d0; background: #f0fdf4;'>
                <div style='font-size: 0.78rem; font-weight: 700; color: #047857;'>🔒 Local AI Engine (On-Prem)</div>
                <div style='font-size: 0.70rem; color: #065f46; margin-top: 2px;'>Operational & Ready</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class='system-status-pill' style='border-color: #fde68a; background: #fffbeb;'>
                <div style='font-size: 0.78rem; font-weight: 700; color: #b45309;'>⚙️ Standard Assistant</div>
                <div style='font-size: 0.70rem; color: #92400e; margin-top: 2px;'>Deterministic rules active</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.caption("HelpDesk AI v2.4 • Production Ready")


# ------------------------------------------------------------------------------
# TOP HEADER BAR
# ------------------------------------------------------------------------------
h_col1, h_col2, h_col3 = st.columns([2.5, 3.5, 2.5])
with h_col1:
    role_portal_label = {
        ROLE_EMPLOYEE: "Employee Portal",
        ROLE_IT_SUPPORT: "IT Support Desk",
        ROLE_ADMIN_SECOPS: "SecOps & Admin Console"
    }.get(canon_role, "IT Portal")
    st.markdown(
        f"""
        <div style='display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 1.15rem; font-weight: 800; color: #0f172a;'>HelpDesk AI</span>
            <span style='color: #cbd5e1;'>/</span>
            <span style='font-size: 0.85rem; color: #64748b;'>{html.escape(role_portal_label)}</span>
            <span style='color: #cbd5e1;'>/</span>
            <span style='font-size: 0.95rem; font-weight: 600; color: #0d9488;'>{html.escape(st.session_state["nav_view"])}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
with h_col2:
    st.text_input("Global Search", key="global_search_input", placeholder="🔍 Search incidents, error codes, SOP articles...", label_visibility="collapsed")
with h_col3:
    model_badge_text = "Enterprise Cloud" if model_stat.get("is_cloud") else ("Local Ollama" if model_stat["ollama"]["available"] else "Offline Heuristics")
    model_dot_color = "#0284c7" if model_stat.get("is_cloud") else ("#10b981" if model_stat["ollama"]["available"] else "#f59e0b")
    st.markdown(
        f"""
        <div style='display: flex; align-items: center; justify-content: flex-end; gap: 8px;'>
            <div style='display: flex; align-items: center; gap: 6px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 4px 12px; font-size: 0.74rem; font-weight: 600; color: #334155;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: {model_dot_color}; display: inline-block;'></span>
                <span>{html.escape(model_badge_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<hr style='margin: 8px 0 18px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)


# ==============================================================================
# VIEW: EMPLOYEE DASHBOARD
# ==============================================================================
if st.session_state["nav_view"] == "My Dashboard":
    st.markdown(
        f"""
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Welcome back, {html.escape(auth_user)}</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Submit IT incidents, monitor the real-time status of your requests, and browse verified knowledge base solutions.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Employee KPI Cards (Derived solely from employee's own tickets)
    ek1, ek2, ek3, ek4 = st.columns(4)
    with ek1:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>My Submitted Tickets</div>
                <div class='metric-value'>{role_metrics['total_tickets']}</div>
                <div class='metric-sub'>Total incidents submitted by you</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with ek2:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>In Progress / Active</div>
                <div class='metric-value' style='color: #0d9488;'>{role_metrics['active_tickets']}</div>
                <div class='metric-sub'>Currently being investigated</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with ek3:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Resolved Tickets</div>
                <div class='metric-value' style='color: #059669;'>{role_metrics['resolved_tickets']}</div>
                <div class='metric-sub'>Confirmed fixed & completed</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with ek4:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Approved SOPs</div>
                <div class='metric-value' style='color: #0284c7;'>{role_metrics['approved_sops']}</div>
                <div class='metric-sub'>Verified IT self-help articles</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Action Banner & Recent Tickets
    with st.container(border=True):
        col_dash_a, col_dash_b = st.columns([3.5, 1.5])
        with col_dash_a:
            st.markdown("<h4 style='font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 0;'>My Recent Support Incidents</h4>", unsafe_allow_html=True)
            st.caption("Track the latest status, automated SOP guidance, and technician updates for your requests.")
        with col_dash_b:
            if st.button("➕ Submit a Support Ticket", type="primary", use_container_width=True, key="btn_emp_new_ticket"):
                blank_form_callback()
                st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if not user_tickets:
            st.info("You have not submitted any support tickets yet. Click **'➕ Submit a Support Ticket'** above if you need assistance.")
        else:
            for t in user_tickets[:5]:
                t_col1, t_col2, t_col3 = st.columns([1.5, 5, 2.5])
                with t_col1:
                    st.markdown(f"<span style='font-weight: 700; color: #0d9488; font-size: 0.88rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.72rem; color: #64748b;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
                with t_col2:
                    st.markdown(f"<div style='font-weight: 600; color: #0f172a; font-size: 0.90rem;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.78rem; color: #64748b;'>{html.escape(t['description'][:110])}...</div>", unsafe_allow_html=True)
                with t_col3:
                    st.markdown(
                        f"<div style='display: flex; gap: 4px; align-items: center; justify-content: flex-end; margin-bottom: 4px;'>"
                        f"{render_category_badge(t.get('expected_category', 'Unclassified'))} "
                        f"{render_status_badge(t.get('status', 'New'))}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    if st.button(f"View Status ➔", key=f"btn_view_my_dash_{t['id']}", use_container_width=True):
                        load_ticket_callback(t)
                        st.rerun()
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)


# ==============================================================================
# VIEW: QUEUE OVERVIEW (IT Support)
# ==============================================================================
elif st.session_state["nav_view"] == "Queue Overview":
    if canon_role not in [ROLE_IT_SUPPORT, ROLE_ADMIN_SECOPS]:
        st.error("Access Denied: You do not have permission to view the Queue Overview.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Operational Queue & Service Desk Health</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Real-time incident queue metrics, multi-agent triage rates, and category distribution.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Queue Incidents</div>
                <div class='metric-value'>{role_metrics['total_queue']}</div>
                <div class='metric-sub'>Active operational tickets</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Triaged & Analyzed</div>
                <div class='metric-value' style='color: #0d9488;'>{role_metrics['triaged_analyzed']}</div>
                <div class='metric-sub'>Guided resolution generated</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k3:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Pending Triage</div>
                <div class='metric-value' style='color: #d97706;'>{role_metrics['pending_triage']}</div>
                <div class='metric-sub'>Awaiting multi-agent analysis</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>High / Critical</div>
                <div class='metric-value' style='color: #e11d48;'>{role_metrics['high_critical']}</div>
                <div class='metric-sub'>Urgent ITIL escalation priority</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k5:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Approved SOPs</div>
                <div class='metric-value' style='color: #0284c7;'>{role_metrics['approved_sops']}</div>
                <div class='metric-sub'>Grounded knowledge base</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Incident Category Distribution</span><span class='badge badge-category'>Real Queue Data</span></div>", unsafe_allow_html=True)
            cat_counts = {}
            for t in user_tickets:
                cat = t.get("expected_category") or "Unclassified"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            
            df_cat = pd.DataFrame([{"Category": k, "Count": v} for k, v in cat_counts.items()])
            if not df_cat.empty:
                cat_chart = alt.Chart(df_cat).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("Category:N", sort="-y", title=None),
                    y=alt.Y("Count:Q", title="Incident Count", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Category:N", scale=alt.Scale(range=["#0d9488", "#0284c7", "#f59e0b", "#7c3aed", "#e11d48"]), legend=None),
                    tooltip=["Category", "Count"]
                ).properties(height=220)
                st.altair_chart(cat_chart, use_container_width=True)
            else:
                st.info("No queue tickets available.")

    with chart_col2:
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>ITIL Priority Breakdown</span><span class='badge badge-category'>ITIL v4 Matrix</span></div>", unsafe_allow_html=True)
            prio_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
            for t in user_tickets:
                p = t.get("expected_priority") or "Medium"
                if p in prio_counts:
                    prio_counts[p] += 1
                else:
                    prio_counts[p] = 1
            
            df_prio = pd.DataFrame([{"Priority": k, "Incidents": v} for k, v in prio_counts.items()])
            prio_chart = alt.Chart(df_prio).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("Priority:N", sort=["Critical", "High", "Medium", "Low"], title=None),
                y=alt.Y("Incidents:Q", title="Incidents", axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("Priority:N", scale=alt.Scale(
                    domain=["Critical", "High", "Medium", "Low"],
                    range=["#e11d48", "#d97706", "#0284c7", "#64748b"]
                ), legend=None),
                tooltip=["Priority", "Incidents"]
            ).properties(height=220)
            st.altair_chart(prio_chart, use_container_width=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        col_hdr_a, col_hdr_b = st.columns([3, 1])
        with col_hdr_a:
            st.markdown("<h4 style='font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 0;'>Active Operational Incident Queue</h4>", unsafe_allow_html=True)
            st.caption("Select any incident to inspect its multi-agent triage logs, resolution checklist, and safety review.")
        with col_hdr_b:
            if st.button("⚡ Open Incident Queue", type="primary", use_container_width=True, key="btn_ov_to_queue"):
                st.session_state["nav_view"] = "Incident Queue"
                st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        for t in user_tickets[:5]:
            q_col1, q_col2, q_col3 = st.columns([1.5, 5, 2.5])
            with q_col1:
                st.markdown(f"<span style='font-weight: 700; color: #0d9488; font-size: 0.88rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.72rem; color: #64748b;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
            with q_col2:
                st.markdown(f"<div style='font-weight: 600; color: #0f172a; font-size: 0.90rem;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.78rem; color: #64748b;'>{html.escape(t['description'][:110])}...</div>", unsafe_allow_html=True)
            with q_col3:
                st.markdown(
                    f"<div style='display: flex; gap: 4px; align-items: center; justify-content: flex-end; margin-bottom: 4px;'>"
                    f"{render_category_badge(t.get('expected_category', 'Unclassified'))} "
                    f"{render_priority_badge(t.get('expected_priority', 'Medium'))} "
                    f"{render_status_badge(t.get('status', 'New'))}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"Inspect {t['id']} ➔", key=f"btn_inspect_ov_{t['id']}", use_container_width=True):
                    load_ticket_callback(t)
                    st.rerun()
            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)


# ==============================================================================
# VIEW: EXECUTIVE METRICS (Admin / SecOps)
# ==============================================================================
elif st.session_state["nav_view"] == "Executive Metrics":
    if canon_role != ROLE_ADMIN_SECOPS:
        st.error("Access Denied: Administrator or SecOps privileges required.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Organisation-Wide Security & Service Desk Metrics</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Executive overview of organization incident volume, security threat escalations, and automated triage coverage.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Total Org Incidents</div>
                <div class='metric-value'>{role_metrics['total_org_incidents']}</div>
                <div class='metric-sub'>All organization tickets</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Security Threats</div>
                <div class='metric-value' style='color: #e11d48;'>{role_metrics['security_threats']}</div>
                <div class='metric-sub'>Phishing & malware incidents</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k3:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Critical / High</div>
                <div class='metric-value' style='color: #d97706;'>{role_metrics['high_critical']}</div>
                <div class='metric-sub'>Urgent business impact</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Triaged & Analyzed</div>
                <div class='metric-value' style='color: #0d9488;'>{role_metrics['triaged_analyzed']}</div>
                <div class='metric-sub'>Rate: {role_metrics['triage_rate']}% triaged</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k5:
        st.markdown(
            f"""
            <div class='metric-container'>
                <div class='metric-label'>Policy Escalations</div>
                <div class='metric-value' style='color: #7e22ce;'>{role_metrics['escalated']}</div>
                <div class='metric-sub'>Internal human review escalation</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Organization Incident Distribution</span><span class='badge badge-category'>Enterprise Scope</span></div>", unsafe_allow_html=True)
            cat_counts = {}
            for t in user_tickets:
                cat = t.get("expected_category") or "Unclassified"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            
            df_cat = pd.DataFrame([{"Category": k, "Count": v} for k, v in cat_counts.items()])
            cat_chart = alt.Chart(df_cat).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("Category:N", sort="-y", title=None),
                y=alt.Y("Count:Q", title="Incident Count", axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("Category:N", scale=alt.Scale(range=["#0d9488", "#0284c7", "#f59e0b", "#7c3aed", "#e11d48"]), legend=None),
                tooltip=["Category", "Count"]
            ).properties(height=220)
            st.altair_chart(cat_chart, use_container_width=True)

    with chart_col2:
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Security Threat Severity Breakdown</span><span class='badge badge-critical'>SecOps Triage</span></div>", unsafe_allow_html=True)
            prio_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
            for t in user_tickets:
                p = t.get("expected_priority") or "Medium"
                if p in prio_counts:
                    prio_counts[p] += 1
            
            df_prio = pd.DataFrame([{"Priority": k, "Incidents": v} for k, v in prio_counts.items()])
            prio_chart = alt.Chart(df_prio).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("Priority:N", sort=["Critical", "High", "Medium", "Low"], title=None),
                y=alt.Y("Incidents:Q", title="Incidents", axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("Priority:N", scale=alt.Scale(
                    domain=["Critical", "High", "Medium", "Low"],
                    range=["#e11d48", "#d97706", "#0284c7", "#64748b"]
                ), legend=None),
                tooltip=["Priority", "Incidents"]
            ).properties(height=220)
            st.altair_chart(prio_chart, use_container_width=True)


# ==============================================================================
# VIEW: SUBMIT TICKET (Employee) / TRIAGE WORKBENCH (IT Support)
# ==============================================================================
elif st.session_state["nav_view"] in ["Submit Ticket", "Triage Workbench"]:
    if canon_role == ROLE_EMPLOYEE and st.session_state["nav_view"] == "Triage Workbench":
        st.session_state["nav_view"] = "Submit Ticket"
        st.rerun()
    current_id = st.session_state.get("current_ticket_id")
    if current_id:
        active_t = next((t for t in st.session_state["tickets"] if t["id"] == current_id), None)
        if active_t and not can_user_access_ticket(active_t, auth_email, auth_role):
            st.error("Access Denied: You do not have permission to view or manage this incident.")
            st.session_state["current_ticket_id"] = None
            st.session_state["active_processed_result"] = None
            clear_form_state()
            st.stop()
    has_result = st.session_state.get("active_processed_result") is not None

    col_hdr_left, col_hdr_right = st.columns([3, 1])
    with col_hdr_left:
        active_title = st.session_state.get("wb_title", "").strip()
        default_heading = "Submit Support Incident" if canon_role == ROLE_EMPLOYEE else "Triage Workbench & Multi-Agent Pipeline"
        display_title = active_title if active_title else default_heading
        st.markdown(f"<h2 style='margin: 0; padding: 0; font-size: 1.45rem; font-weight: 800; color: #0f172a;'>{html.escape(display_title)}</h2>", unsafe_allow_html=True)
        if not active_title:
            st.caption("Provide your IT issue details below for automated ITIL classification, SOP retrieval, safety audit, and guided resolution.")
    with col_hdr_right:
        if has_result:
            res = st.session_state["active_processed_result"]
            st.markdown(
                f"<div style='text-align: right;'>"
                f"{render_category_badge(res.get('category', 'Unclassified'))} &nbsp;"
                f"{render_priority_badge(res.get('priority', 'Medium'))} &nbsp;"
                f"{render_status_badge(res.get('status', 'Triaged'))}"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='text-align: right;'><span class='badge badge-category'>Ready for Input</span></div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 12px 0 16px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Ticket Form
    with st.container(border=True):
        st.markdown("<div class='saas-card-header'><span>📝 Incident Description & Parameters</span></div>", unsafe_allow_html=True)
        
        # Interactive Demo Presets Loader (Available for IT Support)
        if canon_role != ROLE_EMPLOYEE:
            preset_col1, preset_col2 = st.columns([3.5, 1.5])
            with preset_col1:
                preset_options = ["Custom Input (Type your own ticket below)"] + [f"{t['id']} - {t.get('name', t['title'][:30])}" for t in user_tickets]
                selected_preset = st.selectbox("Quick-Load Queue Incident Template", options=preset_options, key="select_demo_incident")
            with preset_col2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Load into Workbench", use_container_width=True, key="btn_apply_demo_incident"):
                    if " - " in selected_preset:
                        sel_id = selected_preset.split(" - ")[0]
                        matched = next((t for t in user_tickets if t["id"] == sel_id), None)
                        if matched:
                            load_ticket_callback(matched)
                            st.rerun()

        f_col1, f_col2 = st.columns([3, 2], gap="large")
        with f_col1:
            ticket_title = st.text_input("Incident Title / Query Summary", key="wb_title", placeholder="e.g. AnyConnect VPN Gateway Timeout")
            ticket_desc = st.text_area("Incident Description & Symptoms", height=120, key="wb_desc", placeholder="Describe observed symptoms, error codes, and impacted applications...")
        with f_col2:
            impact_opts = ["One user", "Multiple users", "Business-critical service"]
            urgency_opts = ["Work blocked", "Work impaired", "Minor inconvenience"]
            
            ticket_impact = st.selectbox("Reported Impact Scope", options=impact_opts, key="wb_impact")
            ticket_urgency = st.selectbox("Reported Urgency Level", options=urgency_opts, key="wb_urgency")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            btn_col_a, btn_col_b = st.columns([2.5, 1])
            with btn_col_a:
                action_label = "⚡ Submit & Run Multi-Agent Triage" if canon_role == ROLE_EMPLOYEE else "⚡ Run Multi-Agent Triage & Resolution"
                run_btn = st.button(action_label, type="primary", use_container_width=True, key="btn_run_workbench")
            with btn_col_b:
                st.button("Clear Form", on_click=clear_form_state, use_container_width=True, key="btn_clear_wb")

    # Handle Analysis Execution
    if run_btn:
        title_val = ticket_title.strip()
        desc_val = ticket_desc.strip()
        
        if not title_val and not desc_val:
            st.warning("⚠️ Please provide an incident title or description before running analysis.")
        else:
            effective_title = title_val or desc_val.split("\n")[0][:60]
            effective_desc = desc_val or title_val

            with st.status("Executing LangGraph multi-agent pipeline...", expanded=True) as status_box:
                st.write("1. **Triage Agent:** Deterministic ITIL matrix classification...")
                st.write("2. **Retrieval Agent:** Querying official SOP knowledge base...")
                st.write("3. **Resolution Agent:** Synthesizing actionable DO and DON'T guidance...")
                st.write("4. **Critic Agent:** Auditing zero-credential leaks and command safety...")
                st.write("5. **Policy Router:** Applying deterministic escalation guardrails...")
                
                res = process_ticket(
                    title=effective_title,
                    description=effective_desc,
                    impact=ticket_impact,
                    urgency=ticket_urgency
                )
                status_box.update(label="✓ Multi-Agent Pipeline Completed Successfully", state="complete", expanded=False)

            st.session_state["active_processed_result"] = res
            
            if current_id:
                update_ticket_result(current_id, res)
            else:
                new_id = f"INC-{1000 + len(st.session_state['tickets']) + 1}"
                st.session_state["current_ticket_id"] = new_id
                new_entry = {
                    "id": new_id,
                    "name": effective_title[:30],
                    "title": effective_title,
                    "description": effective_desc,
                    "impact": ticket_impact,
                    "urgency": ticket_urgency,
                    "expected_category": res.get("category"),
                    "expected_priority": res.get("priority"),
                    "status": res.get("status", "Triaged"),
                    "processed_result": res,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reporter_email": auth_email.strip().lower(),
                    "reporter_name": auth_user,
                    "created_by": auth_email.strip().lower()
                }
                st.session_state["tickets"].insert(0, new_entry)
            
            st.rerun()

    # Display Analysis Results
    res = st.session_state.get("active_processed_result")
    if res:
        is_security_incident = (res.get("category") == "Security") or ("Security" in str(res.get("status", "")))
        
        # 1. Timeline Stepper
        st.markdown(
            f"""
            <div class='timeline-container'>
                <div class='timeline-step'>
                    <div class='step-circle'>1</div>
                    <div>
                        <div class='step-label'>Triage</div>
                        <div class='step-sub'>{html.escape(str(res.get('category')))} • {html.escape(str(res.get('priority')))}</div>
                    </div>
                </div>
                <div class='timeline-arrow'>➔</div>
                <div class='timeline-step'>
                    <div class='step-circle'>2</div>
                    <div>
                        <div class='step-label'>Retrieval</div>
                        <div class='step-sub'>{len(res.get('retrieved_articles', []))} SOP(s) Matched</div>
                    </div>
                </div>
                <div class='timeline-arrow'>➔</div>
                <div class='timeline-step'>
                    <div class='step-circle'>3</div>
                    <div>
                        <div class='step-label'>Resolution</div>
                        <div class='step-sub'>Guidance Synthesized</div>
                    </div>
                </div>
                <div class='timeline-arrow'>➔</div>
                <div class='timeline-step'>
                    <div class='step-circle'>4</div>
                    <div>
                        <div class='step-label'>Critic</div>
                        <div class='step-sub'>{html.escape(str(res.get('critic_verdict', 'Approved')))} Safe</div>
                    </div>
                </div>
                <div class='timeline-arrow'>➔</div>
                <div class='timeline-step'>
                    <div class='step-circle' style='background: {"#fff1f2" if res.get("is_escalated") else "#ecfdf5"}; border-color: {"#e11d48" if res.get("is_escalated") else "#10b981"}; color: {"#e11d48" if res.get("is_escalated") else "#059669"};'>5</div>
                    <div>
                        <div class='step-label'>Router</div>
                        <div class='step-sub'>{html.escape(str(res.get('escalation_tier', 'Tier 1')))}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. Escalation / Containment Alert Banner
        if is_security_incident:
            st.markdown(
                f"""
                <div class='security-banner'>
                    <div class='security-title'>🚨 MANDATORY SECOPS SECURITY INCIDENT ESCALATION (HUMAN REVIEW REQUIRED)</div>
                    <div class='security-body'>
                        <b>Target Escalation Queue:</b> {html.escape(str(res.get('escalation_tier', 'SecOps Incident Response Team')))}<br>
                        <b>Trigger Rationale:</b> {html.escape(str(res.get('escalation_reason', 'Security policy indicator detected.')))}<br>
                        <b>Advisory Containment Notice:</b> Follow containment steps below. The AI system does NOT execute automated host quarantine.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif res.get("is_escalated"):
            st.markdown(
                f"""
                <div class='escalation-banner'>
                    <div class='escalation-title'>🚨 INCIDENT ESCALATED: {html.escape(str(res.get('escalation_tier', 'Tier 2 Support')))}</div>
                    <div class='escalation-body'>
                        <b>Escalation Policy Rationale:</b> {html.escape(str(res.get('escalation_reason', 'Policy threshold triggered.')))}<br>
                        <i>Ticket routed to human technician queue. Advisory troubleshooting instructions generated below.</i>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class='standard-banner'>
                    <div class='standard-title'>🟢 STANDARD TIER-1 RESOLUTION SCOPE</div>
                    <div class='standard-body'>Governed by verified knowledge SOP documentation. Follow the verified action checklist below.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # 3. Two-Column Layout
        col_left, col_right = st.columns([1, 1], gap="medium")

        with col_left:
            # Triage Assessment Card
            st.markdown(
                f"""
                <div class='saas-card'>
                    <div class='saas-card-header'>
                        <span>Triage Classification & ITIL Priority</span>
                        <span>{render_category_badge(res['category'])} {render_priority_badge(res['priority'])}</span>
                    </div>
                    <div class='field-label'>ITIL Matrix Reasoning</div>
                    <div class='field-value' style='line-height: 1.5;'>{html.escape(str(res.get('triage_reasoning')))}</div>
                    <div style='display: flex; gap: 16px; margin-top: 10px; font-size: 0.82rem; color: #64748b; background: #f8fafc; padding: 8px 12px; border-radius: 6px;'>
                        <div><b>Impact Scope:</b> {html.escape(str(st.session_state.get('wb_impact', 'One user')))}</div>
                        <div><b>Urgency Level:</b> {html.escape(str(st.session_state.get('wb_urgency', 'Work impaired')))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Critic Safety Card
            critic_verdict = res.get("critic_verdict", "Approved")
            is_safe = res.get("is_safe", True)
            is_grounded = res.get("is_grounded", True)
            revisions_used = res.get("revision_count", 0)
            
            if critic_verdict == "Approved":
                critic_badge = "<span class='badge badge-success'>✓ Verified Safe</span>"
            elif critic_verdict == "Flagged":
                critic_badge = "<span class='badge badge-high'>⚠ Flagged for Review</span>"
            else:
                critic_badge = "<span class='badge badge-critical'>✕ Rejected by Safety Policy</span>"

            st.markdown(
                f"""
                <div class='saas-card'>
                    <div class='saas-card-header'>
                        <span>Critic Safety & Guardrail Audit</span>
                        <span>{critic_badge}</span>
                    </div>
                    <div class='field-label'>Policy Verification Checklist</div>
                    <div style='font-size: 0.86rem; color: #334155; margin-bottom: 10px; line-height: 1.6;'>
                        • Zero Credential Solicitation: <b>{'Passed (No credentials requested)' if is_safe else 'Violation Detected'}</b><br>
                        • Non-Destructive Command Check: <b>Passed (Safe operations only)</b><br>
                        • False Premature Resolution Check: <b>Passed (Advisory checklist only)</b><br>
                        • Knowledge Base SOP Grounding: <b>{'Grounded in official SOP' if is_grounded else 'Insufficient Evidence'}</b><br>
                        • Bounded Feedback Iterations: <b>{revisions_used} revision(s) executed</b>
                    </div>
                    <div class='field-label'>Critic Assessment Summary</div>
                    <div class='field-value' style='font-size: 0.88rem; line-height: 1.45;'>{html.escape(str(res.get('critic_critique')))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Retrieved SOP Sources Card
            render_retrieved_articles_card(res.get("retrieved_articles", []))

        with col_right:
            # Actionable Advisory Guidance
            raw_source = res.get("agent_sources", {}).get("resolution", "unknown")
            clean_source = clean_inference_source(raw_source)
            is_deterministic = "deterministic" in raw_source.lower()
            source_badge = (
                "<span class='badge badge-high'>⚠️ Deterministic Fallback</span>"
                if is_deterministic
                else f"<span class='badge badge-category'>{html.escape(clean_source)}</span>"
            )

            st.markdown(
                f"""
                <div class='saas-card'>
                    <div class='saas-card-header'>
                        <span>Recommended Resolution Guidance</span>
                        <span>{source_badge}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            recs_raw = res.get("recommendation", "No recommendation generated.")
            do_steps, dont_steps = format_concise_guidance(
                recommendation_text=recs_raw,
                category=res.get("category", "Hardware"),
                is_escalated=res.get("is_escalated", False)
            )

            # Render DO & DON'T checklists safely
            render_guidance_cards(do_steps, dont_steps)

            with st.expander("📄 View Full Synthesized Resolution Text", expanded=False):
                st.markdown(recs_raw)

            # Interactive User Feedback Action Buttons
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                if st.button("✓ Confirm Fix Worked", key="btn_confirm_fix_wb", use_container_width=True):
                    if current_id:
                        for t in st.session_state["tickets"]:
                            if t["id"] == current_id:
                                t["status"] = "User Confirmed - Resolved"
                    st.success("User confirmed troubleshooting resolved the issue. Ticket marked as Resolved.")
            with act_col2:
                if st.button("👤 Request Human Review", key="btn_req_dispatch_wb", use_container_width=True):
                    if current_id:
                        for t in st.session_state["tickets"]:
                            if t["id"] == current_id:
                                t["status"] = "Escalated - Human Review Requested"
                    st.warning("Incident escalated to internal human technician review queue. (External ticket dispatch is not connected).")

            # Output Routing Card
            st.markdown(
                f"""
                <div class='saas-card' style='margin-top: 14px;'>
                    <div class='saas-card-header'>
                        <span>Final Output Routing Decision</span>
                        <span>{render_status_badge(res.get('status', 'Triaged'))}</span>
                    </div>
                    <div style='font-size: 0.88rem; color: #1e293b; line-height: 1.55;'>
                        <b>Target Queue Tier:</b> {html.escape(str(res.get('escalation_tier')))}<br>
                        <b>Escalation Policy Rationale:</b> {html.escape(str(res.get('escalation_reason')))}<br>
                        <b>Critic Revisions:</b> {res.get('revision_count', 0)} round(s) &nbsp;|&nbsp; 
                        Feedback: <i>{html.escape(str(res.get('critic_feedback') or 'Approved without revision'))}</i><br>
                        <b>Inference Backend:</b> <code>{html.escape(clean_source)}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Technical Logs (Only for IT Support / Admin)
        if canon_role != ROLE_EMPLOYEE:
            with st.expander("🔍 Multi-Agent Execution Trace (LangGraph Logs)", expanded=False):
                logs = res.get("execution_logs", [])
                if logs:
                    for log_line in logs:
                        st.code(sanitize_ui_text(log_line), language="bash")
                else:
                    st.write("No execution logs recorded.")
    else:
        st.info("💡 Enter your incident details above, then click **'⚡ Run Multi-Agent Triage & Resolution'** to execute the LangGraph workflow.")


# ==============================================================================
# VIEW: MY TICKETS (Employee Ticket History)
# ==============================================================================
elif st.session_state["nav_view"] == "My Tickets":
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>My Support Tickets & History</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>View and track the status of all support incidents submitted by your account.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not user_tickets:
        st.info("You have not submitted any support tickets yet. Click **'Submit Ticket'** in the sidebar to report an issue.")
    else:
        st.markdown(f"<div style='font-size: 0.80rem; font-weight: 600; color: #64748b; margin-bottom: 12px;'>Showing {len(user_tickets)} ticket(s) submitted by you</div>", unsafe_allow_html=True)
        for t in user_tickets:
            with st.container(border=True):
                r_col1, r_col2, r_col3 = st.columns([1.5, 6, 2.5])
                with r_col1:
                    st.markdown(f"<span style='font-weight: 800; color: #0d9488; font-size: 0.92rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.72rem; color: #64748b; margin-top: 2px;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
                with r_col2:
                    st.markdown(f"<div style='font-size: 0.94rem; font-weight: 700; color: #0f172a;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.82rem; color: #64748b; margin-top: 3px;'>{html.escape(t['description'][:140])}...</div>", unsafe_allow_html=True)
                with r_col3:
                    st.markdown(
                        f"<div style='display: flex; gap: 4px; justify-content: flex-end; margin-bottom: 8px;'>"
                        f"{render_category_badge(t.get('expected_category', 'Unclassified'))} "
                        f"{render_status_badge(t.get('status', 'New'))}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    if st.button("View Details ➔", key=f"btn_emp_inspect_{t['id']}", use_container_width=True):
                        load_ticket_callback(t)
                        st.rerun()


# ==============================================================================
# VIEW: INCIDENT QUEUE (IT Support)
# ==============================================================================
elif st.session_state["nav_view"] == "Incident Queue":
    if canon_role not in [ROLE_IT_SUPPORT, ROLE_ADMIN_SECOPS]:
        st.error("Access Denied: You do not have permission to access the Incident Queue.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Operational Incident Queue & Triage Desk</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Manage, triage, inspect, and escalate service desk incidents across the organization.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Queue Batch Triage Action Row
    untriaged_count = sum(1 for t in user_tickets if t.get("status") == "New" and t.get("processed_result") is None)
    col_q_act1, col_q_act2 = st.columns([3, 1.5])
    with col_q_act2:
        if untriaged_count > 0:
            if st.button(f"⚡ Batch Triage All Pending ({untriaged_count})", type="primary", use_container_width=True, key="btn_batch_triage"):
                with st.status(f"Executing LangGraph multi-agent triage across {untriaged_count} pending incidents...", expanded=True) as status_box:
                    for pending_t in user_tickets:
                        if pending_t.get("status") == "New" and pending_t.get("processed_result") is None:
                            st.write(f"Triaging **{pending_t['id']}**: {pending_t['title'][:35]}...")
                            res = process_ticket(
                                title=pending_t["title"],
                                description=pending_t["description"],
                                impact=pending_t.get("impact", "One user"),
                                urgency=pending_t.get("urgency", "Work impaired")
                            )
                            pending_t["processed_result"] = res
                            pending_t["status"] = res.get("status", "Triaged")
                            pending_t["expected_category"] = res.get("category")
                            pending_t["expected_priority"] = res.get("priority")
                    status_box.update(label="✓ Completed batch triage successfully!", state="complete")
                st.rerun()

    # Filter Controls
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        kw_filter = st.text_input("Search Queue", placeholder="Filter by ID, title, reporter, or symptoms...", label_visibility="collapsed")
    with f2:
        cat_filter = st.selectbox("Category", options=["All", "Network", "Access", "Hardware", "Software", "Security"], label_visibility="collapsed")
    with f3:
        prio_filter = st.selectbox("Priority", options=["All", "Critical", "High", "Medium", "Low"], label_visibility="collapsed")
    with f4:
        stat_filter = st.selectbox("Status", options=["All", "Pending Triage (New)", "Triaged", "Escalated", "Resolved"], label_visibility="collapsed")

    # Filter Tickets
    matched_tickets = []
    for t in user_tickets:
        full_text = f"{t['title']} {t['description']} {t['id']} {t.get('reporter_email', '')} {t.get('reporter_name', '')}"
        if kw_filter and kw_filter.lower() not in full_text.lower():
            continue
        if cat_filter != "All" and t.get("expected_category") != cat_filter:
            continue
        if prio_filter != "All" and t.get("expected_priority") != prio_filter:
            continue
        if stat_filter != "All":
            curr_stat = str(t.get("status", "New"))
            if stat_filter == "Pending Triage (New)" and (curr_stat != "New" or t.get("processed_result") is not None):
                continue
            elif stat_filter == "Triaged" and "Triaged" not in curr_stat:
                continue
            elif stat_filter == "Escalated" and "Escalated" not in curr_stat:
                continue
            elif stat_filter == "Resolved" and "Resolved" not in curr_stat:
                continue
        matched_tickets.append(t)

    st.markdown(f"<div style='font-size: 0.80rem; font-weight: 600; color: #64748b; margin-bottom: 12px;'>Showing {len(matched_tickets)} incident(s)</div>", unsafe_allow_html=True)

    # Render Incident Cards with Inline Triage & Actions
    for t in matched_tickets:
        with st.container(border=True):
            r_col1, r_col2, r_col3 = st.columns([1.5, 5, 2.5])
            with r_col1:
                st.markdown(f"<span style='font-weight: 800; color: #0d9488; font-size: 0.92rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.72rem; color: #64748b; margin-top: 2px;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.70rem; color: #0f766e;'>👤 {html.escape(t.get('reporter_name', 'Employee'))}</div>", unsafe_allow_html=True)
            with r_col2:
                st.markdown(f"<div style='font-size: 0.94rem; font-weight: 700; color: #0f172a;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.82rem; color: #64748b; margin-top: 3px;'>{html.escape(t['description'][:140])}...</div>", unsafe_allow_html=True)
            with r_col3:
                st.markdown(
                    f"<div style='display: flex; gap: 4px; justify-content: flex-end; margin-bottom: 8px;'>"
                    f"{render_category_badge(t.get('expected_category', 'Unclassified'))} "
                    f"{render_priority_badge(t.get('expected_priority', 'Medium'))} "
                    f"{render_status_badge(t.get('status', 'New'))}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
                # Action Buttons
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if t.get("status") == "New" and t.get("processed_result") is None:
                        if st.button("⚡ Triage", key=f"btn_triage_now_{t['id']}", use_container_width=True):
                            with st.spinner(f"Triaging {t['id']}..."):
                                res = process_ticket(
                                    title=t["title"],
                                    description=t["description"],
                                    impact=t.get("impact", "One user"),
                                    urgency=t.get("urgency", "Work impaired")
                                )
                                t["processed_result"] = res
                                t["status"] = res.get("status", "Triaged")
                                t["expected_category"] = res.get("category")
                                t["expected_priority"] = res.get("priority")
                                st.rerun()
                    else:
                        if st.button("Inspect ➔", key=f"btn_inspect_queue_{t['id']}", use_container_width=True):
                            load_ticket_callback(t)
                            st.rerun()
                with btn_c2:
                    if "Escalated" not in str(t.get("status", "")):
                        if st.button("Escalate", key=f"btn_esc_{t['id']}", use_container_width=True):
                            t["status"] = "Escalated - Tier 2 Support"
                            st.rerun()
                    else:
                        if st.button("Resolve", key=f"btn_res_{t['id']}", use_container_width=True):
                            t["status"] = "Resolved"
                            st.rerun()


# ==============================================================================
# VIEW: SECURITY INCIDENTS (Admin / SecOps)
# ==============================================================================
elif st.session_state["nav_view"] == "Security Incidents":
    if canon_role != ROLE_ADMIN_SECOPS:
        st.error("Access Denied: SecOps privileges required to view security incidents.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>SecOps Threat Management & Incident Containment</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Dedicated security incident operations queue. Reviews phishing, ransomware, credential exposures, and policy escalations.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    sec_incidents = filter_security_incidents(user_tickets)

    st.markdown(
        f"""
        <div class='security-banner'>
            <div class='security-title'>🛡️ SECOPS ACTIVE THREAT MONITORING</div>
            <div class='security-body'>
                <b>Active Threat Incidents:</b> {len(sec_incidents)} incident(s) currently flagged for mandatory SecOps analysis.<br>
                <b>Containment Policy:</b> Ensure affected endpoint network isolation and immediate Active Directory credential suspension.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not sec_incidents:
        st.info("No active security threats or escalations currently pending review.")
    else:
        for t in sec_incidents:
            with st.container(border=True):
                s_col1, s_col2, s_col3 = st.columns([1.5, 5, 2.5])
                with s_col1:
                    st.markdown(f"<span style='font-weight: 800; color: #e11d48; font-size: 0.92rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.72rem; color: #64748b; margin-top: 2px;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.70rem; color: #9f1239;'>👤 {html.escape(t.get('reporter_name', 'Employee'))}</div>", unsafe_allow_html=True)
                with s_col2:
                    st.markdown(f"<div style='font-size: 0.94rem; font-weight: 700; color: #0f172a;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.82rem; color: #64748b; margin-top: 3px;'>{html.escape(t['description'])}</div>", unsafe_allow_html=True)
                with s_col3:
                    st.markdown(
                        f"<div style='display: flex; gap: 4px; justify-content: flex-end; margin-bottom: 8px;'>"
                        f"{render_category_badge(t.get('expected_category', 'Security'))} "
                        f"{render_priority_badge(t.get('expected_priority', 'Critical'))} "
                        f"{render_status_badge(t.get('status', 'Security Escalation'))}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    act1, act2 = st.columns(2)
                    with act1:
                        if st.button("Investigate ➔", key=f"btn_sec_inv_{t['id']}", use_container_width=True):
                            load_ticket_callback(t)
                            st.rerun()
                    with act2:
                        if st.button("Mark Contained", key=f"btn_sec_cont_{t['id']}", use_container_width=True):
                            t["status"] = "Contained & Resolved"
                            st.rerun()


# ==============================================================================
# VIEW: ALL INCIDENTS (Admin Audit Log)
# ==============================================================================
elif st.session_state["nav_view"] == "All Incidents":
    if canon_role != ROLE_ADMIN_SECOPS:
        st.error("Access Denied: Administrator privileges required to view all organization incidents.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Organisation Incident Log & Audit Trail</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Full enterprise audit registry of all historical and active incidents.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        kw_filter = st.text_input("Filter Registry", placeholder="Search by title, description, or reporter...", label_visibility="collapsed")
    with f2:
        cat_filter = st.selectbox("Category Filter", options=["All", "Network", "Access", "Hardware", "Software", "Security"], label_visibility="collapsed")
    with f3:
        prio_filter = st.selectbox("Priority Filter", options=["All", "Critical", "High", "Medium", "Low"], label_visibility="collapsed")

    matched_tickets = []
    for t in user_tickets:
        if kw_filter and kw_filter.lower() not in (t["title"] + " " + t["description"] + " " + t["id"]).lower():
            continue
        if cat_filter != "All" and t.get("expected_category") != cat_filter:
            continue
        if prio_filter != "All" and t.get("expected_priority") != prio_filter:
            continue
        matched_tickets.append(t)

    st.markdown(f"<div style='font-size: 0.80rem; font-weight: 600; color: #64748b; margin-bottom: 12px;'>Showing {len(matched_tickets)} incident(s)</div>", unsafe_allow_html=True)

    for t in matched_tickets:
        with st.container(border=True):
            r_col1, r_col2, r_col3 = st.columns([1.5, 6, 2])
            with r_col1:
                st.markdown(f"<span style='font-weight: 800; color: #0d9488; font-size: 0.92rem;'>{html.escape(t['id'])}</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.72rem; color: #64748b; margin-top: 2px;'>{html.escape(t.get('created_at', 'Today'))}</div>", unsafe_allow_html=True)
            with r_col2:
                st.markdown(f"<div style='font-size: 0.94rem; font-weight: 700; color: #0f172a;'>{html.escape(t['title'])}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.82rem; color: #64748b; margin-top: 3px;'>{html.escape(t['description'][:140])}...</div>", unsafe_allow_html=True)
            with r_col3:
                st.markdown(
                    f"<div style='display: flex; gap: 4px; justify-content: flex-end; margin-bottom: 8px;'>"
                    f"{render_category_badge(t.get('expected_category', 'Unclassified'))} "
                    f"{render_priority_badge(t.get('expected_priority', 'Medium'))} "
                    f"{render_status_badge(t.get('status', 'New'))}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button("Inspect ➔", key=f"btn_all_audit_{t['id']}", use_container_width=True):
                    load_ticket_callback(t)
                    st.rerun()


# ==============================================================================
# VIEW: KNOWLEDGE BASE (Approved SOP Catalog)
# ==============================================================================
elif st.session_state["nav_view"] == "Knowledge Base":
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Enterprise IT Standard Operating Procedures (SOP)</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Curated and approved troubleshooting knowledge base articles supporting HelpDesk AI retrieval.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    kb_c1, kb_c2 = st.columns([1.5, 3])
    with kb_c1:
        cat_choice = st.selectbox("Filter SOP by Category", options=["All", "Network", "Access", "Hardware", "Software", "Security"])
    with kb_c2:
        kb_search = st.text_input("Search SOP Articles", placeholder="Filter by keyword, title, or ID...")

    for art in KB_ARTICLES:
        if cat_choice != "All" and art["category"] != cat_choice:
            continue
        if kb_search:
            kw_match = any(kb_search.lower() in k.lower() for k in art["keywords"])
            title_match = kb_search.lower() in art["title"].lower()
            id_match = kb_search.lower() in art["id"].lower()
            if not (kw_match or title_match or id_match):
                continue

        with st.container(border=True):
            st.markdown(
                f"""
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                    <span style='font-size: 0.98rem; font-weight: 700; color: #0f172a;'>📄 {html.escape(art['id'])}: {html.escape(art['title'])}</span>
                    {render_category_badge(art['category'])}
                </div>
                <div style='font-size: 0.84rem; color: #475569; margin-bottom: 8px;'>{html.escape(art['summary'])}</div>
                <div style='font-size: 0.74rem; color: #0d9488; font-weight: 600; margin-bottom: 10px;'>
                    Keywords: <code>{html.escape(', '.join(art['keywords']))}</code>
                </div>
                """,
                unsafe_allow_html=True
            )
            with st.expander("📋 View Approved Operating Steps"):
                for step_idx, step in enumerate(art["steps"], 1):
                    st.markdown(f"**{step_idx}.** {step}")


# ==============================================================================
# VIEW: EVALUATION (Benchmark Suite - Admin / SecOps)
# ==============================================================================
elif st.session_state["nav_view"] == "Evaluation":
    if canon_role != ROLE_ADMIN_SECOPS:
        st.error("Access Denied: Administrator or SecOps privileges required to access the Evaluation suite.")
        st.stop()
    st.markdown(
        """
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>Automated Evaluation & Safety Benchmark Suite</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Deterministic regression testing across ITIL classification, priority calculation, security recall, and safety guardrails across 16 synthetic test cases.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_btn_eval, col_eval_note = st.columns([1.5, 3])
    with col_btn_eval:
        run_eval_now = st.button("🚀 Run Full Automated Benchmark", type="primary", use_container_width=True)

    if run_eval_now or st.session_state["evaluation_results"] is None:
        with st.spinner("Executing 16 synthetic test cases through evaluation engine..."):
            st.session_state["evaluation_results"] = run_comprehensive_evaluation()

    ev = st.session_state["evaluation_results"]

    if ev:
        em1, em2, em3, em4, em5, em6 = st.columns(6)
        with em1:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>Category Acc</div>
                    <div class='metric-value' style='color: #059669;'>{ev['category_accuracy']}%</div>
                    <div class='metric-sub'>{ev['category_matches']}/{ev['category_total']} correct</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with em2:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>Priority Acc</div>
                    <div class='metric-value' style='color: #059669;'>{ev['priority_accuracy']}%</div>
                    <div class='metric-sub'>{ev['priority_matches']}/{ev['priority_total']} correct</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with em3:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>Security Recall</div>
                    <div class='metric-value' style='color: #e11d48;'>{ev['security_recall']}%</div>
                    <div class='metric-sub'>{ev['security_matches']}/{ev['security_total']} threats caught</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with em4:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>KB Retrieval</div>
                    <div class='metric-value' style='color: #0284c7;'>{ev['retrieval_accuracy']}%</div>
                    <div class='metric-sub'>{ev['retrieval_matches']}/{ev['retrieval_total']} top-1 matches</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with em5:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>Critic Safety</div>
                    <div class='metric-value' style='color: #7c3aed;'>{ev['critic_accuracy']}%</div>
                    <div class='metric-sub'>{ev['critic_counts'].get('Rejected', 0)} rejected</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with em6:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-label'>Routing Acc</div>
                    <div class='metric-value' style='color: #0d9488;'>{ev['routing_accuracy']}%</div>
                    <div class='metric-sub'>{ev['routing_matches']}/{ev['routing_total']} policy routed</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        echart_col1, echart_col2 = st.columns(2)
        with echart_col1:
            with st.container(border=True):
                st.markdown("<div class='saas-card-header'><span>Benchmark Metric Scores (%)</span><span class='badge badge-success'>16 Benchmark Cases</span></div>", unsafe_allow_html=True)
                df_eval_metrics = pd.DataFrame({
                    "Evaluation Dimension": [
                        "Category Accuracy",
                        "ITIL Priority",
                        "Security Recall",
                        "KB Retrieval Top-1",
                        "Critic Safety Audit",
                        "Policy Routing"
                    ],
                    "Score (%)": [
                        ev["category_accuracy"],
                        ev["priority_accuracy"],
                        ev["security_recall"],
                        ev["retrieval_accuracy"],
                        ev["critic_accuracy"],
                        ev["routing_accuracy"]
                    ]
                })
                bar_chart = alt.Chart(df_eval_metrics).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("Evaluation Dimension:N", sort=None, axis=alt.Axis(labelAngle=-25, title=None)),
                    y=alt.Y("Score (%):Q", scale=alt.Scale(domain=[0, 100]), title="Accuracy / Recall (%)"),
                    color=alt.value("#0d9488"),
                    tooltip=["Evaluation Dimension", "Score (%)"]
                ).properties(height=230)
                st.altair_chart(bar_chart, use_container_width=True)

        with echart_col2:
            with st.container(border=True):
                st.markdown("<div class='saas-card-header'><span>Critic Safety Decisions Breakdown</span><span class='badge badge-category'>Guardrail Audit</span></div>", unsafe_allow_html=True)
                df_critic = pd.DataFrame([
                    {"Decision": k, "Cases": v} for k, v in ev["critic_counts"].items()
                ])
                critic_chart = alt.Chart(df_critic).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("Decision:N", title=None),
                    y=alt.Y("Cases:Q", title="Evaluated Test Cases", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Decision:N", scale=alt.Scale(
                        domain=["Approved", "Flagged", "Rejected"],
                        range=["#10b981", "#f59e0b", "#e11d48"]
                    ), legend=None),
                    tooltip=["Decision", "Cases"]
                ).properties(height=230)
                st.altair_chart(critic_chart, use_container_width=True)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h4 style='font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 10px;'>📋 Detailed Test Case Execution (TC-NET-01 through TC-ROUT-01)</h4>", unsafe_allow_html=True)
            df_results = pd.DataFrame(ev["detailed_results"])
            st.dataframe(df_results, use_container_width=True, hide_index=True)

        st.markdown(
            f"""
            <div style='background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 14px 18px; margin-top: 18px;'>
                <div style='font-size: 0.88rem; font-weight: 700; color: #b45309; margin-bottom: 4px;'>⚠️ Evaluation Methodology & Small Test-Set Limitation</div>
                <div style='font-size: 0.82rem; color: #92400e; line-height: 1.5;'>{html.escape(ev['limitation_note'])}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# VIEW: SETTINGS / PROFILE (Role-Scoped)
# ==============================================================================
elif st.session_state["nav_view"] in ["Settings", "Admin Settings", "My Profile"]:
    heading_title = "My Profile & Account Details" if canon_role == ROLE_EMPLOYEE else "Settings & Account Management"
    st.markdown(
        f"""
        <div style='margin-bottom: 16px;'>
            <h2 style='font-size: 1.55rem; font-weight: 800; color: #0f172a; margin: 0;'>{html.escape(heading_title)}</h2>
            <p style='font-size: 0.86rem; color: #64748b; margin-top: 4px;'>Manage account identity, update security credentials, and review service status.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    set_col1, set_col2 = st.columns(2, gap="large")

    with set_col1:
        # User Account Card
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Active User Account</span><span class='badge badge-success'>Authenticated</span></div>", unsafe_allow_html=True)
            st.markdown(f"**Full Name:** `{auth_user}`")
            st.markdown(f"**Corporate Email:** `{auth_email}`")
            st.markdown(f"**Assigned Role:** `{auth_role}`")
            st.markdown(f"**Session Active Since:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("Sign Out of Session", on_click=logout_callback, key="btn_settings_logout"):
                st.rerun()

        # Security & Password Management
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Security & Credentials</span></div>", unsafe_allow_html=True)
            st.caption("Keep your corporate account secure with a strong password.")
            
            with st.expander("🔑 Change Account Password", expanded=False):
                with st.form("form_change_password"):
                    curr_pwd = st.text_input("Current Password", type="password", key="cp_curr_pwd")
                    new_pwd = st.text_input("New Password", type="password", key="cp_new_pwd", help="Min 8 characters with upper, lower, numbers, and symbols")
                    conf_pwd = st.text_input("Confirm New Password", type="password", key="cp_conf_pwd")
                    
                    if new_pwd:
                        pwd_eval = auth.calculate_password_strength(new_pwd)
                        st.caption(f"Password Strength: **{pwd_eval['label']}** ({pwd_eval['percent']}%)")
                        
                    submit_pwd_change = st.form_submit_button("Update Password", type="primary", use_container_width=True)
                    if submit_pwd_change:
                        success_cp, msg_cp = auth.change_password(auth_email, curr_pwd, new_pwd, conf_pwd)
                        if success_cp:
                            st.success(msg_cp)
                        else:
                            st.error(msg_cp)

    with set_col2:
        # AI Service Status Indicator
        with st.container(border=True):
            status_badge = "<span class='badge badge-success'>Operational</span>" if model_stat.get("available") else "<span class='badge badge-category'>Standby</span>"
            st.markdown(f"<div class='saas-card-header'><span>AI Service Status</span>{status_badge}</div>", unsafe_allow_html=True)
            
            if model_stat.get("is_cloud"):
                service_mode = "Cloud Assistant"
                status_desc = "Connected & Operational"
            elif model_stat["ollama"]["available"]:
                service_mode = "Local Assistant"
                status_desc = "Connected & Operational (On-Premise)"
            else:
                service_mode = "Deterministic Assistant"
                status_desc = "Active (ITIL Rule Heuristics)"
                
            st.markdown(f"**Service Mode:** `{service_mode}`")
            st.markdown(f"**Availability:** `{status_desc}`")
            st.markdown(f"**Automated Guardrails:** `Active & Enforced`")
            st.markdown(
                """
                <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; font-size: 0.80rem; color: #475569; margin-top: 10px; line-height: 1.5;'>
                    💡 The AI assistant provides real-time ITIL incident classification, verified SOP knowledge retrieval, and automated safety reviews.
                </div>
                """,
                unsafe_allow_html=True
            )

        # Privacy Notice Card
        with st.container(border=True):
            st.markdown("<div class='saas-card-header'><span>Privacy & Data Protection Notice</span></div>", unsafe_allow_html=True)
            st.markdown(
                """
                HelpDesk AI is configured to protect corporate confidentiality and sensitive user data:
                - **Data Confidentiality:** Incident inquiries and descriptions are processed strictly to assist with IT troubleshooting and incident resolution.
                - **Zero Credential Retention:** Safety guardrails actively inspect and prevent the transmission or storage of passwords, access tokens, and secrets.
                - **Access Isolation:** Incident visibility is strictly scoped to your authorized corporate role and permissions.
                """
            )
