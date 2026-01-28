"""
Tips page - Help and usage instructions
"""
import streamlit as st
from src import lang as L


def show_tips_page():
    """Tips page"""
    
    st.markdown("---")
    st.header(L.TIPS_TITLE)
    
    st.markdown(L.TIPS_CONTENT)
