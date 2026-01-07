# -*- coding: utf-8 -*-
"""
MyLedger Falcon-Inspired Design System
Typography Focus: Refined Chinese fonts and balanced numeric weights.
"""

import streamlit as st

def apply_custom_design():
    """应用更柔和、更专业的 Falcon UI"""
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --falcon-bg: #F9FAFB;
            --falcon-card: #FFFFFF;
            --falcon-primary: #10B981; /* Default to USDT Green */
            --falcon-black: #0F172A;
            --falcon-text: #1E293B;
            --falcon-muted: #64748B;
            --falcon-border: #F1F5F9;
            --falcon-radius: 18px;
        }

        /* 全局字体平滑处理 */
        .stApp {
            background-color: var(--falcon-bg);
            /* 智能中英双字体栈：优先 HarmonyOS / 苹方 / 极简雅黑 */
            font-family: 'Inter', "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--falcon-text);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent !important;}

        .block-container {
            padding-top: 1.5rem !important;
            max-width: 1060px !important;
        }

        /* 标题风格：更有呼吸感的字体比例 */
        h1, h2, h3 {
            font-family: 'Outfit', "HarmonyOS Sans SC", sans-serif;
            color: var(--falcon-black) !important;
            letter-spacing: -0.03em !important;
            font-weight: 700 !important;
        }
        
        /* 侧边栏极致极简 */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #F1F5F9;
        }

        /* 侧边导航优化 */
        [data-testid="stSidebar"] div[role="radiogroup"] label {
            display: flex !important;
            padding: 9px 16px !important;
            margin-bottom: 6px !important;
            border-radius: 12px !important;
            background: transparent !important;
            border: none !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label p {
            color: #64748B !important;
            font-weight: 500 !important;
            font-size: 0.92rem !important;
            transition: color 0.2s;
        }

        /* 选中态：模拟 Falcon 的精致浮窗感 */
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] {
            background: #0F172A !important;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12) !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* 统一卡片 */
        .u-card {
            background: var(--falcon-card);
            padding: 24px;
            border-radius: var(--falcon-radius);
            border: 1px solid #F1F5F9;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }

        /* 指标显示优化：提升字间距与排版层次 */
        .m-box {
            display: block;
        }
        .m-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--falcon-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em; /* 增加高级感字间距 */
            margin-bottom: 10px;
        }
        .m-value {
            font-size: 2.3rem; /* 稍微减小避免笨重 */
            font-weight: 700; /* 从 800 降到 700 */
            color: var(--falcon-black);
            font-family: 'Outfit', sans-serif;
            line-height: 1.1;
            letter-spacing: -0.01em;
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
        .d-n { background-color: #F8FAFB; color: #475569; border: 1px solid #F1F5F9; }

        /* 侧边统计容器 */
        .side-stats {
            background: #F9FAFB;
            border-radius: 14px;
            padding: 14px;
            margin: 12px;
            border: 1px solid #F1F5F9;
        }
    </style>
    """, unsafe_allow_html=True)

def metric_card(label, value, delta=None, delta_up=True, help_text=None):
    """极致优雅的指标卡片"""
    d_html = ""
    if delta:
        if isinstance(delta_up, bool):
            clz = "d-up" if delta_up else "d-down"
            icon = "↗" if delta_up else "↘"
        else:
            clz = "d-n"
            icon = "→"
        d_html = f'<div class="m-delta {clz}"><span>{icon}</span> <span>{delta}</span></div>'
        
    st.markdown(f"""
    <div class="u-card">
        <div class="m-label">{label}</div>
        <div class="m-value">{value}</div>
        {d_html}
    </div>
    """, unsafe_allow_html=True)
