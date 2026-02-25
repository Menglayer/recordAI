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
            
            # Tags row (only if tags exist)
            tags_row = ""
            if tags_html:
                tags_row = f'<div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #F1F5F9;">{tags_html}</div>'
            
            st.markdown(f"""
            <div class="u-card" style="padding: 0; overflow: hidden; display: flex; align-items: stretch;">
                <div style="width: 100px; min-width: 100px; background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px 12px; border-right: 1px solid #E5E7EB; position: relative;">
                    <div style="position: absolute; left: 0; top: 20%; height: 60%; width: 3px; background: linear-gradient(180deg, #10B981, #059669); border-radius: 0 4px 4px 0;"></div>
                    <div style="font-weight: 800; font-size: 1.4rem; color: #0F172A; font-family: 'Outfit', sans-serif; line-height: 1;">{date_str}</div>
                    <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px; font-weight: 500;">{year_str}</div>
                </div>
                <div style="flex: 1; padding: 20px 24px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 0.88rem; line-height: 1.9; color: #374151;">{content}</div>
                    {tags_row}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"加载日记失败: {e}")

