# -*- coding: utf-8 -*-
"""
MyLedger Falcon-Inspired Design System
Version: 2026-02-12 v6 - Enhanced UI/UX
"""

import streamlit as st

# 统一配色方案（Single source of truth）
MODERN_COLORS = [
    '#10B981', '#F97316', '#0EA5E9', '#6366F1', '#F59E0B',
    '#EC4899', '#8B5CF6', '#14B8A6', '#F43F5E'
]

def apply_custom_design():
    """Apply custom design system with enhanced components"""
    
    theme_vars = """
        --falcon-bg: #F9FAFB;
        --falcon-card: #FFFFFF;
        --falcon-primary: #10B981;
        --falcon-primary-soft: rgba(16, 185, 129, 0.08);
        --falcon-black: #0F172A;
        --falcon-text: #1E293B;
        --falcon-muted: #64748B;
        --falcon-border: #F1F5F9;
        --falcon-hover: #F8FAFC;
        --falcon-skeleton: linear-gradient(90deg, #F3F4F6 25%, #E5E7EB 50%, #F3F4F6 75%);
        --falcon-accent: #6366F1;
        --falcon-success: #10B981;
        --falcon-danger: #EF4444;
        --falcon-warning: #F59E0B;
    """
    
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            {theme_vars}
            --falcon-radius: 18px;
            --falcon-radius-sm: 12px;
            --falcon-radius-xs: 8px;
            --falcon-shadow-sm: 0 1px 3px rgba(0,0,0,0.02);
            --falcon-shadow-md: 0 4px 12px rgba(0,0,0,0.06);
            --falcon-shadow-lg: 0 8px 25px rgba(0,0,0,0.1);
            --falcon-transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        /* ========== Base ========== */
        .stApp {{
            background-color: var(--falcon-bg);
            font-family: 'Inter', "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--falcon-text);
            -webkit-font-smoothing: antialiased;
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

        /* ========== Sidebar ========== */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
            border-right: 1px solid var(--falcon-border) !important;
        }}
        
        [data-testid="stSidebar"] * {{
            color: var(--falcon-text) !important;
        }}

        /* Sidebar Navigation Radio */
        [data-testid="stSidebar"] div[role="radiogroup"] label {{
            display: flex !important;
            padding: 10px 16px !important;
            margin-bottom: 4px !important;
            border-radius: var(--falcon-radius-sm) !important;
            background: transparent !important;
            border: none !important;
            transition: var(--falcon-transition) !important;
            position: relative !important;
        }}
        
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: var(--falcon-primary-soft) !important;
        }}

        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] {{
            background: var(--falcon-primary-soft) !important;
            border: 1px solid rgba(16, 185, 129, 0.2) !important;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1) !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"]::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 3px;
            height: 60%;
            background: var(--falcon-primary);
            border-radius: 0 4px 4px 0;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] p {{
            color: #065F46 !important;
            font-weight: 600 !important;
        }}

        /* ========== Cards ========== */
        .u-card {{
            background: var(--falcon-card);
            padding: 24px;
            border-radius: var(--falcon-radius);
            border: 1px solid var(--falcon-border);
            margin-bottom: 20px;
            box-shadow: var(--falcon-shadow-sm);
            transition: var(--falcon-transition);
        }}
        
        .u-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--falcon-shadow-lg);
            border-color: rgba(99, 102, 241, 0.15);
        }}

        /* ========== Metric Card Tokens ========== */
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
            color: var(--falcon-warning);
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
            border-radius: var(--falcon-radius-xs);
            gap: 4px;
        }}
        .d-up {{ background-color: #F0FDF4; color: #10B981; }}
        .d-down {{ background-color: #FEF2F2; color: #EF4444; }}
        .d-n {{ background-color: var(--falcon-hover); color: var(--falcon-muted); }}

        .benchmark-tag {{
            font-size: 0.7rem;
            color: var(--falcon-muted);
            margin-left: 8px;
            font-weight: 500;
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

        /* ========== Tabs ========== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: var(--falcon-card);
            padding: 4px;
            border-radius: var(--falcon-radius-sm);
            border: 1px solid var(--falcon-border);
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: var(--falcon-radius-xs) !important;
            padding: 8px 20px !important;
            font-weight: 500 !important;
            transition: var(--falcon-transition) !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background: var(--falcon-hover) !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: var(--falcon-black) !important;
            color: white !important;
            font-weight: 600 !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none !important;
        }}

        /* ========== Buttons ========== */
        .stButton > button {{
            border-radius: var(--falcon-radius-sm) !important;
            font-weight: 600 !important;
            transition: var(--falcon-transition) !important;
            border: 1px solid var(--falcon-border) !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: var(--falcon-shadow-md) !important;
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #10B981, #059669) !important;
            border: none !important;
            color: white !important;
        }}

        /* ========== DataFrames ========== */
        [data-testid="stDataFrameResizable"] {{
            border-radius: var(--falcon-radius-sm) !important;
            overflow: hidden !important;
            border: 1px solid var(--falcon-border) !important;
        }}
        [data-testid="stDataFrame"] {{
            background-color: var(--falcon-card) !important;
        }}

        /* ========== Inputs ========== */
        .stSelectbox > div > div,
        .stNumberInput > div > div > input,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {{
            border-radius: var(--falcon-radius-sm) !important;
            border-color: var(--falcon-border) !important;
            transition: var(--falcon-transition) !important;
        }}
        .stSelectbox > div > div:focus-within,
        .stNumberInput > div > div > input:focus,
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: var(--falcon-primary) !important;
            box-shadow: 0 0 0 3px var(--falcon-primary-soft) !important;
        }}

        /* ========== Expander ========== */
        .streamlit-expanderHeader {{
            border-radius: var(--falcon-radius-sm) !important;
            font-weight: 600 !important;
        }}

        /* ========== Toast Notification ========== */
        @keyframes toast-in {{
            from {{ transform: translateX(120%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        @keyframes toast-out {{
            from {{ transform: translateX(0); opacity: 1; }}
            to {{ transform: translateX(120%); opacity: 0; }}
        }}
        .falcon-toast {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 99999;
            padding: 14px 24px;
            border-radius: var(--falcon-radius-sm);
            font-weight: 600;
            font-size: 0.9rem;
            backdrop-filter: blur(12px);
            animation: toast-in 0.4s ease-out, toast-out 0.4s ease-in 2.6s forwards;
            box-shadow: var(--falcon-shadow-lg);
        }}
        .falcon-toast.success {{
            background: rgba(16, 185, 129, 0.95);
            color: white;
        }}
        .falcon-toast.error {{
            background: rgba(239, 68, 68, 0.95);
            color: white;
        }}
        .falcon-toast.info {{
            background: rgba(99, 102, 241, 0.95);
            color: white;
        }}

        /* ========== Empty State ========== */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
        }}
        .empty-state .icon {{
            font-size: 3.5rem;
            margin-bottom: 16px;
            opacity: 0.7;
        }}
        .empty-state .title {{
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--falcon-black);
            margin-bottom: 8px;
            font-family: 'Outfit', sans-serif;
        }}
        .empty-state .desc {{
            font-size: 0.9rem;
            color: var(--falcon-muted);
            max-width: 320px;
            margin: 0 auto;
            line-height: 1.6;
        }}

        /* ========== Badge ========== */
        .falcon-badge {{
            display: inline-flex;
            align-items: center;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            gap: 4px;
        }}
        .falcon-badge.green {{ background: #F0FDF4; color: #059669; }}
        .falcon-badge.red {{ background: #FEF2F2; color: #DC2626; }}
        .falcon-badge.blue {{ background: #EFF6FF; color: #2563EB; }}
        .falcon-badge.orange {{ background: #FFFBEB; color: #D97706; }}
        .falcon-badge.purple {{ background: #F5F3FF; color: #7C3AED; }}
        .falcon-badge.gray {{ background: #F3F4F6; color: #6B7280; }}

        /* ========== Skeleton Loading ========== */
        @keyframes skeleton-loading {{
            0% {{ background-position: -200px 0; }}
            100% {{ background-position: calc(200px + 100%) 0; }}
        }}
        
        .skeleton {{
            background: var(--falcon-skeleton);
            background-size: 200px 100%;
            animation: skeleton-loading 1.5s ease-in-out infinite;
            border-radius: var(--falcon-radius-xs);
        }}
        .skeleton-text {{ height: 16px; margin-bottom: 8px; }}
        .skeleton-title {{ height: 32px; width: 60%; margin-bottom: 16px; }}
        .skeleton-card {{ height: 120px; border-radius: var(--falcon-radius); margin-bottom: 20px; }}
        .skeleton-chart {{ height: 300px; border-radius: var(--falcon-radius); }}

        /* ========== Misc ========== */
        .stSpinner > div {{
            border-color: var(--falcon-primary) transparent transparent transparent !important;
        }}
        
        .js-plotly-plot .plotly .modebar {{
            background-color: transparent !important;
        }}

        /* ========== Page Transition ========== */
        @keyframes page-fade-in {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .main .block-container {{
            animation: page-fade-in 0.35s ease-out;
        }}
        
        /* ========== Responsive ========== */
        @media (max-width: 768px) {{
            h2 {{ font-size: 1.4rem !important; }}
            .m-value {{ font-size: 1.8rem !important; }}
            .u-card {{ padding: 16px; margin-bottom: 12px; }}
        }}
    </style>
    """, unsafe_allow_html=True)


# ========== Component Functions ==========

def metric_card(label, value, delta=None, delta_up=True, is_masked=False, benchmark=None, subtitle=None):
    """Enhanced metric card component"""
    val_display = str(value)
    if is_masked:
        if "%" not in str(value):
            val_display = '<span class="privacy-masked">$ ••••••</span>'
    
    subtitle_html = ""
    if subtitle:
        display_sub = str(subtitle) if not is_masked else "••••• BTC"
        subtitle_html = f'<div class="m-subtitle">&#x1FA99; {display_sub}</div>'
    
    d_html = ""
    if delta:
        if delta_up is True:
            clz = "d-up"
            icon = "&#8599;"
        elif delta_up is False:
            clz = "d-down"
            icon = "&#8600;"
        else:
            clz = "d-n"
            icon = "&#8594;"
        
        bench_html = ""
        if benchmark:
            bench_html = f'<span class="benchmark-tag">vs {benchmark}</span>'
        
        d_html = f'<div class="m-delta {clz}"><span>{icon}</span> <span>{delta}</span>{bench_html}</div>'
    
    html = f"""<div class="u-card"><div class="m-label">{label}</div><div class="m-value">{val_display}</div>{subtitle_html}{d_html}</div>"""
    st.markdown(html, unsafe_allow_html=True)


def empty_state(icon="📭", title="暂无数据", description="", action_label=None):
    """
    Render an illustrated empty state placeholder
    
    Args:
        icon: Emoji icon
        title: Main title  
        description: Description text
        action_label: Optional action button label
    """
    action_html = ""
    if action_label:
        action_html = f'<div style="margin-top: 20px;"><span class="falcon-badge blue" style="font-size: 0.85rem; padding: 8px 16px; cursor: pointer;">{action_label}</span></div>'
    
    st.markdown(f"""
    <div class="empty-state">
        <div class="icon">{icon}</div>
        <div class="title">{title}</div>
        <div class="desc">{description}</div>
        {action_html}
    </div>
    """, unsafe_allow_html=True)


def badge(text, color="gray"):
    """
    Render an inline badge
    
    Args:
        text: Badge text
        color: green|red|blue|orange|purple|gray
    """
    return f'<span class="falcon-badge {color}">{text}</span>'


def toast(message, type="success"):
    """
    Show a toast notification
    
    Args:
        message: Notification message
        type: success|error|info
    """
    st.markdown(f'<div class="falcon-toast {type}">{message}</div>', unsafe_allow_html=True)


def stat_mini(label, value, change=None, change_up=True):
    """
    Render a compact stat display for sidebars
    
    Args:
        label: Stat label
        value: Main value
        change: Optional change text (e.g. "+2.5%")
        change_up: Whether change is positive
    """
    change_html = ""
    if change:
        color = "#10B981" if change_up else "#EF4444"
        arrow = "↑" if change_up else "↓"
        change_html = f'<span style="font-size: 0.75rem; color: {color}; font-weight: 600; margin-left: 6px;">{arrow} {change}</span>'
    
    st.markdown(f"""
    <div style="padding: 4px 0;">
        <div style="font-size: 0.7rem; color: var(--falcon-muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">{label}</div>
        <div style="font-size: 1.15rem; font-weight: 700; font-family: 'Outfit', sans-serif; color: var(--falcon-black); margin-top: 2px;">{value}{change_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ========== Skeleton Loaders ==========

def skeleton_card(count=1):
    """显示骨架屏卡片"""
    cards_html = ""
    for _ in range(count):
        cards_html += '<div class="skeleton skeleton-card"></div>'
    st.markdown(cards_html, unsafe_allow_html=True)


def skeleton_chart():
    """显示骨架屏图表"""
    st.markdown('<div class="skeleton skeleton-chart"></div>', unsafe_allow_html=True)


def skeleton_text(lines=3):
    """显示骨架屏文本"""
    text_html = '<div class="skeleton skeleton-title"></div>'
    for _ in range(lines):
        text_html += '<div class="skeleton skeleton-text"></div>'
    st.markdown(text_html, unsafe_allow_html=True)


def loading_placeholder(placeholder_type="card", count=1):
    """统一的加载占位组件"""
    if placeholder_type == "card":
        skeleton_card(count)
    elif placeholder_type == "chart":
        skeleton_chart()
    elif placeholder_type == "text":
        skeleton_text(count)


# ========== Layout Helpers ==========

def section_header(icon, title, description=None):
    """
    统一的分区标题组件（带分割线）
    
    Args:
        icon: Emoji 图标
        title: 标题文本
        description: 可选描述
    """
    desc_html = f"<span style='color: var(--falcon-muted); font-size: 0.85rem; font-weight: 500; margin-left: 12px;'>{description}</span>" if description else ""
    st.markdown(f"""<div style='margin: 2.5rem 0 1.5rem; display: flex; align-items: baseline; gap: 8px;'>
        <h3 style='margin: 0; font-size: 1.25rem; display: flex; align-items: center; gap: 8px;'><span>{icon}</span> <span>{title}</span></h3>
        {desc_html}
        <div style='flex: 1; height: 1px; background: linear-gradient(90deg, #E5E7EB, transparent); margin-left: 10px;'></div>
    </div>""", unsafe_allow_html=True)


def page_header(icon, title, description):
    """
    统一的页面顶部标题组件
    
    Args:
        icon: Emoji 图标
        title: 页面标题
        description: 页面简介
    """
    st.markdown(f"""
    <div style="margin-bottom: 2rem; animation: page-fade-in 0.4s ease-out;">
        <h2 style="margin: 0; display: flex; align-items: center; gap: 10px; font-size: 1.8rem;">
            <span>{icon}</span> <span>{title}</span>
        </h2>
        <p style="color: #64748B; font-size: 0.9rem; margin: 6px 0 0 0; font-weight: 500;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def divider():
    """统一的水平分割线"""
    st.markdown("""<div style='margin: 1.5rem 0; height: 1px; background: linear-gradient(90deg, transparent, #E5E7EB, transparent);'></div>""", unsafe_allow_html=True)


def sub_label(icon, text):
    """
    轻量级子标题（用于卡片/表单内部分区）
    
    Args:
        icon: Emoji 图标
        text: 标签文本
    """
    st.markdown(f"""<div style="font-size: 0.92rem; font-weight: 700; color: var(--falcon-black); font-family: 'Outfit', sans-serif; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span>{icon}</span><span>{text}</span>
    </div>""", unsafe_allow_html=True)
