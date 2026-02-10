import streamlit as st
import pandas as pd
from src.database import get_journals
from src import lang as L

def render_journal_section(engine):
    """渲染复盘日记区域"""
    st.subheader(f"📝 {L.JOURNAL_TITLE}")
    
    try:
        journals_df = get_journals(engine, limit=20)
        
        if journals_df.empty:
            st.info("暂无复盘日记，请在数据录入页面添加。")
            return
            
        st.markdown("---")
        
        for _, row in journals_df.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 5])
                
                with col1:
                    # 日期样式
                    st.markdown(f"""
                    <div style="text-align: right; padding-right: 10px; border-right: 2px solid #e5e7eb;">
                        <div style="font-weight: 700; font-size: 1.1rem; color: #374151;">{row['date'].strftime('%m-%d')}</div>
                        <div style="font-size: 0.8rem; color: #9ca3af;">{row['date'].year}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 标签
                    if row['tags']:
                        tags = str(row['tags']).split(',')
                        st.markdown("<div style='text-align: right; margin-top: 8px;'>", unsafe_allow_html=True)
                        for tag in tags:
                             if tag.strip():
                                 st.markdown(f"<span style='background: #f3f4f6; color: #4b5563; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; display: inline-block; margin-bottom: 4px;'>{tag.strip()}</span>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    # 内容样式
                    content = str(row['content']).replace('\n', '<br>')
                    content = content.replace('{', '{{').replace('}', '}}')
                    
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <div style="font-family: 'Inter', sans-serif; line-height: 1.6; color: #E2E8F0;">
                            {content}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"加载日记失败: {e}")
