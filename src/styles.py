# -*- coding: utf-8 -*-
"""
MyLedger Falcon-Inspired Design System
Added: Privacy mode support and mobile adaptations.
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

        /* 响应式容器 */
        .block-container {
            padding-top: 1.5rem !important;
            max-width: 1060px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* 标题适配 */
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

        /* 侧边栏按钮 */
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

        /* 隐私遮罩效果 */
        .privacy-masked {
            filter: blur(8px);
            user-select: none;
            cursor: pointer;
            transition: filter 0.3s;
        }
        .privacy-masked:hover {
            filter: blur(4px);
        }

        /* 统一卡片 */
        .u-card {
            background: var(--falcon-card);
            padding: 24px;
            border-radius: var(--falcon-radius);
            border: 1px solid #F1F5F9;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }

        /* 指标卡片 */
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

        /* 基准对比标签 */
        .benchmark-tag {
            font-size: 0.7rem;
            color: var(--falcon-muted);
            margin-left: 8px;
            font-weight: 500;
        }

        /* 移动端表格优化 */
        [data-testid="stDataFrameResizable"] {
            border-radius: 14px !important;
            overflow: hidden !important;
        }
    </style>
    """, unsafe_allow_html=True)

def metric_card(label, value, delta=None, delta_up=True, is_masked=False, benchmark=None):
    """极致优雅的指标卡片，支持隐私模式和基准对比"""
    val_display = value
    if is_masked:
        # 如果是隐私模式且不是百分比，则进行遮罩覆盖
        if "%" not in str(value):
            val_display = '<span class="privacy-masked">$ ••••••</span>'
    
    d_html = ""
    if delta:
        if isinstance(delta_up, bool):
            clz = "d-up" if delta_up else "d-down"
            icon = "↗" if delta_up else "↘"
        else:
            clz = "d-n"
            icon = "→"
        
        bench_html = ""
        if benchmark:
            bench_html = f'<span class="benchmark-tag">vs {benchmark}</span>'
            
        d_html = f'<div class="m-delta {clz}"><span>{icon}</span> <span>{delta}</span>{bench_html}</div>'
        
    st.markdown(f"""
    <div class="u-card">
        <div class="m-label">{label}</div>
        <div class="m-value">{val_display}</div>
        {d_html}
    </div>
    """, unsafe_allow_html=True)
