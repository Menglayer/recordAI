# -*- coding: utf-8 -*-
"""
MyLedger Falcon-Inspired Design System
Version: 2026-02-02 v4 - HTML Entities for stability
"""

import streamlit as st

def apply_custom_design():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --falcon-bg: #F9FAFB;
            --falcon-card: #FFFFFF;
            --falcon-primary: #10B981;
            --falcon-black: #0F172A;
            --falcon-text: #1E293B;
            --falcon-muted: #64748B;
            --falcon-border: #F1F5F9;
            --falcon-radius: 18px;
        }

        .stApp {
            background-color: var(--falcon-bg);
            font-family: 'Inter', "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--falcon-text);
            -webkit-font-smoothing: antialiased;
        }

        .block-container {
            padding-top: 1.5rem !important;
            max-width: 1060px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            color: var(--falcon-black) !important;
            letter-spacing: -0.03em !important;
            font-weight: 700 !important;
        }
        
        @media (max-width: 768px) {
            h2 { font-size: 1.4rem !important; }
            .m-value { font-size: 1.8rem !important; }
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label {
            display: flex !important;
            padding: 9px 16px !important;
            margin-bottom: 6px !important;
            border-radius: 12px !important;
            background: transparent !important;
            border: none !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] {
            background: #0F172A !important;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12) !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] p {
            color: #FFFFFF !important;
        }

        .privacy-masked {
            filter: blur(8px);
            user-select: none;
            cursor: pointer;
            transition: filter 0.3s;
        }
        .privacy-masked:hover {
            filter: blur(4px);
        }

        .u-card {
            background: var(--falcon-card);
            padding: 24px;
            border-radius: var(--falcon-radius);
            border: 1px solid #F1F5F9;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }

        .m-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--falcon-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 10px;
        }
        .m-value {
            font-size: 2.3rem;
            font-weight: 700;
            color: var(--falcon-black);
            font-family: 'Outfit', sans-serif;
            line-height: 1.1;
        }
        .m-subtitle {
            font-size: 1.1rem;
            font-weight: 600;
            color: #F59E0B;
            margin-top: 8px;
            font-family: 'Outfit', sans-serif;
        }
        .m-delta {
            display: inline-flex;
            align-items: center;
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 14px;
            padding: 4px 10px;
            border-radius: 8px;
            gap: 4px;
        }
        .d-up { background-color: #F0FDF4; color: #16A34A; }
        .d-down { background-color: #FEF2F2; color: #DC2626; }
        .d-n { background-color: #F8FAFB; color: #475569; }

        .benchmark-tag {
            font-size: 0.7rem;
            color: var(--falcon-muted);
            margin-left: 8px;
            font-weight: 500;
        }

        [data-testid="stDataFrameResizable"] {
            border-radius: 14px !important;
            overflow: hidden !important;
        }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, delta=None, delta_up=True, is_masked=False, benchmark=None, subtitle=None):
    # Prepare display value
    val_display = str(value)
    if is_masked:
        if "%" not in str(value):
            val_display = '<span class="privacy-masked">$ ••••••</span>'
    
    # Subtitle with coin icon (using HTML entity for safety)
    subtitle_html = ""
    if subtitle:
        # Coin icon: &#x1FA99;
        display_sub = str(subtitle) if not is_masked else "••••• BTC"
        subtitle_html = f'<div class="m-subtitle">&#x1FA99; {display_sub}</div>'
    
    # Delta indicator
    d_html = ""
    if delta:
        # Determine styling and icon based on delta_up
        if delta_up is True:
            clz = "d-up"
            icon = "&#8599;" # NE Arrow
        elif delta_up is False:
            clz = "d-down"
            icon = "&#8600;" # SE Arrow
        else:
            clz = "d-n"
            icon = "&#8594;" # Right Arrow
        
        bench_html = ""
        if benchmark:
            bench_html = f'<span class="benchmark-tag">vs {benchmark}</span>'
        
        d_html = f'<div class="m-delta {clz}"><span>{icon}</span> <span>{delta}</span>{bench_html}</div>'
    
    # Build final HTML - NO INDENTATION to avoid Markdown code block parsing
    html = f"""<div class="u-card"><div class="m-label">{label}</div><div class="m-value">{val_display}</div>{subtitle_html}{d_html}</div>"""
    
    st.markdown(html, unsafe_allow_html=True)
