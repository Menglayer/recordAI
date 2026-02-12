"""
Dashboard Journal Section
复盘日记展示组件
"""
import streamlit as st
import pandas as pd
from src.database import get_journals
from src import lang as L
from src import styles as S


def render_journal_section(engine):
    """渲染复盘日记区域"""
    st.subheader(f"📝 {L.JOURNAL_TITLE}")
    
    try:
        journals_df = get_journals(engine, limit=20)
        
        if journals_df.empty:
            S.empty_state(
                "📝", "暂无复盘日记",
                "前往「数据录入 → 复盘日记」记录您的投资思考"
            )
            return
        
        for idx, row in journals_df.iterrows():
            date_str = row['date'].strftime('%m-%d')
            year_str = str(row['date'].year)
            content = str(row['content']).replace('\n', '<br>')
            content = content.replace('{', '{{').replace('}', '}}')
            
            # Build tags HTML
            tags_html = ""
            if row['tags']:
                tags = [t.strip() for t in str(row['tags']).split(',') if t.strip()]
                tags_html = " ".join([S.badge(tag, "blue") for tag in tags])
            
            st.markdown(f"""
            <div class="u-card" style="padding: 20px; display: flex; gap: 20px;">
                <div style="min-width: 60px; text-align: center; border-right: 2px solid #E5E7EB; padding-right: 16px;">
                    <div style="font-weight: 800; font-size: 1.3rem; color: #0F172A; font-family: 'Outfit', sans-serif;">{date_str}</div>
                    <div style="font-size: 0.75rem; color: #64748B;">{year_str}</div>
                    <div style="margin-top: 8px;">{tags_html}</div>
                </div>
                <div style="flex: 1;">
                    <div style="font-size: 0.9rem; line-height: 1.8; color: #374151;">{content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"加载日记失败: {e}")
