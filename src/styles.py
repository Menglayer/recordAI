# -*- coding: utf-8 -*-
"""
MyLedger Falcon-Inspired Design System
Version: 2026-02-09 v5 - Dark Mode + Performance
"""

import streamlit as st

# 统一配色方案（Single source of truth）
MODERN_COLORS = [
    '#10B981', '#F97316', '#0EA5E9', '#6366F1', '#F59E0B',
    '#EC4899', '#8B5CF6', '#14B8A6', '#F43F5E'
]

def apply_custom_design(dark_mode=False):
    """Apply custom design with optional dark mode"""
    
    # Theme-aware CSS variables
    if dark_mode:
        theme_vars = """
            --falcon-bg: #0F172A;
            --falcon-card: #1E293B;
            --falcon-primary: #10B981;
            --falcon-black: #F8FAFC;
            --falcon-text: #E2E8F0;
            --falcon-muted: #94A3B8;
            --falcon-border: #334155;
            --falcon-hover: #334155;
            --falcon-skeleton: linear-gradient(90deg, #1E293B 25%, #334155 50%, #1E293B 75%);
        """
        sidebar_active_bg = "#10B981"
        sidebar_active_text = "#FFFFFF"
        card_shadow = "0 4px 20px rgba(0,0,0,0.3)"
    else:
        theme_vars = """
            --falcon-bg: #F9FAFB;
            --falcon-card: #FFFFFF;
            --falcon-primary: #10B981;
            --falcon-black: #0F172A;
            --falcon-text: #1E293B;
            --falcon-muted: #64748B;
            --falcon-border: #F1F5F9;
            --falcon-hover: #F8FAFC;
            --falcon-skeleton: linear-gradient(90deg, #F3F4F6 25%, #E5E7EB 50%, #F3F4F6 75%);
        """
        sidebar_active_bg = "#0F172A"
        sidebar_active_text = "#FFFFFF"
        card_shadow = "0 1px 3px rgba(0,0,0,0.02)"
    
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            {theme_vars}
            --falcon-radius: 18px;
        }}

        .stApp {{
            background-color: var(--falcon-bg);
            font-family: 'Inter', "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--falcon-text);
            -webkit-font-smoothing: antialiased;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}

        .block-container {{
            padding-top: 1.5rem !important;
            max-width: 1060px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}

        h1, h2, h3 {{
            font-family: 'Outfit', sans-serif;
            color: var(--falcon-black) !important;
            letter-spacing: -0.03em !important;
            font-weight: 700 !important;
        }}
        
        /* Streamlit 组件深色模式适配 */
        [data-testid="stSidebar"] {{
            background-color: var(--falcon-card) !important;
            border-right: 1px solid var(--falcon-border) !important;
        }}
        
        [data-testid="stSidebar"] * {{
            color: var(--falcon-text) !important;
        }}
        
        @media (max-width: 768px) {{
            h2 {{ font-size: 1.4rem !important; }}
            .m-value {{ font-size: 1.8rem !important; }}
        }}

        [data-testid="stSidebar"] div[role="radiogroup"] label {{
            display: flex !important;
            padding: 9px 16px !important;
            margin-bottom: 6px !important;
            border-radius: 12px !important;
            background: transparent !important;
            border: none !important;
            transition: all 0.2s ease !important;
        }}
        
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: var(--falcon-hover) !important;
        }}

        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] {{
            background: {sidebar_active_bg} !important;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12) !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] p {{
            color: {sidebar_active_text} !important;
        }}

        .privacy-masked {{
            filter: blur(8px);
            user-select: none;
            cursor: pointer;
            transition: filter 0.3s;
        }}
        .privacy-masked:hover {{
            filter: blur(4px);
        }}

        .u-card {{
            background: var(--falcon-card);
            padding: 24px;
            border-radius: var(--falcon-radius);
            border: 1px solid var(--falcon-border);
            margin-bottom: 20px;
            box-shadow: {card_shadow};
            transition: all 0.3s ease;
        }}
        
        .u-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}

        .m-label {{
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--falcon-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 10px;
        }}
        .m-value {{
            font-size: 2.3rem;
            font-weight: 700;
            color: var(--falcon-black);
            font-family: 'Outfit', sans-serif;
            line-height: 1.1;
        }}
        .m-subtitle {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #F59E0B;
            margin-top: 8px;
            font-family: 'Outfit', sans-serif;
        }}
        .m-delta {{
            display: inline-flex;
            align-items: center;
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 14px;
            padding: 4px 10px;
            border-radius: 8px;
            gap: 4px;
        }}
        .d-up {{ background-color: {'#064E3B' if dark_mode else '#F0FDF4'}; color: #10B981; }}
        .d-down {{ background-color: {'#7F1D1D' if dark_mode else '#FEF2F2'}; color: #EF4444; }}
        .d-n {{ background-color: var(--falcon-hover); color: var(--falcon-muted); }}

        .benchmark-tag {{
            font-size: 0.7rem;
            color: var(--falcon-muted);
            margin-left: 8px;
            font-weight: 500;
        }}

        [data-testid="stDataFrameResizable"] {{
            border-radius: 14px !important;
            overflow: hidden !important;
        }}
        
        /* 深色模式 DataFrame */
        [data-testid="stDataFrame"] {{
            background-color: var(--falcon-card) !important;
        }}
        
        /* ========== 骨架屏动画 ========== */
        @keyframes skeleton-loading {{
            0% {{ background-position: -200px 0; }}
            100% {{ background-position: calc(200px + 100%) 0; }}
        }}
        
        .skeleton {{
            background: var(--falcon-skeleton);
            background-size: 200px 100%;
            animation: skeleton-loading 1.5s ease-in-out infinite;
            border-radius: 8px;
        }}
        
        .skeleton-text {{
            height: 16px;
            margin-bottom: 8px;
        }}
        
        .skeleton-title {{
            height: 32px;
            width: 60%;
            margin-bottom: 16px;
        }}
        
        .skeleton-card {{
            height: 120px;
            border-radius: var(--falcon-radius);
            margin-bottom: 20px;
        }}
        
        .skeleton-chart {{
            height: 300px;
            border-radius: var(--falcon-radius);
        }}
        
        /* ========== 加载状态优化 ========== */
        .stSpinner > div {{
            border-color: var(--falcon-primary) transparent transparent transparent !important;
        }}
        
        /* Plotly 图表深色模式 */
        .js-plotly-plot .plotly .modebar {{
            background-color: transparent !important;
        }}
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


def skeleton_card(count=1):
    """显示骨架屏卡片（加载占位）"""
    cards_html = ""
    for _ in range(count):
        cards_html += '<div class="skeleton skeleton-card"></div>'
    st.markdown(cards_html, unsafe_allow_html=True)


def skeleton_chart():
    """显示骨架屏图表（加载占位）"""
    st.markdown('<div class="skeleton skeleton-chart"></div>', unsafe_allow_html=True)


def skeleton_text(lines=3):
    """显示骨架屏文本（加载占位）"""
    text_html = '<div class="skeleton skeleton-title"></div>'
    for _ in range(lines):
        text_html += '<div class="skeleton skeleton-text"></div>'
    st.markdown(text_html, unsafe_allow_html=True)


def loading_placeholder(placeholder_type="card", count=1):
    """
    统一的加载占位组件
    
    Args:
        placeholder_type: "card" | "chart" | "text"
        count: 显示数量（仅对 card 和 text 有效）
    """
    if placeholder_type == "card":
        skeleton_card(count)
    elif placeholder_type == "chart":
        skeleton_chart()
    elif placeholder_type == "text":
        skeleton_text(count)
