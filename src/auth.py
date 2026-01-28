"""
Authentication module
"""
import streamlit as st
from src import lang as L


def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Professional Login Screen
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="u-card" style='text-align: center; padding: 40px; margin-bottom: 0px;'>
                    <div style='background: #F8FAFC; width: 64px; height: 64px; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;'>
                        <span style='font-size: 32px;'>🔐</span>
                    </div>
                    <h2 style='margin-bottom: 8px; font-size: 1.8rem;'>{L.APP_TITLE.split(" - ")[0]}</h2>
                    <p style='color: var(--falcon-muted); margin-bottom: 32px; font-size: 0.95rem;'>请验证访问授权</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.text_input(
                "Access Key", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="键入密码并回车",
                label_visibility="collapsed"
            )
            
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.markdown("""
                    <div style='background-color: #FEF2F2; color: #DC2626; padding: 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; text-align: center; margin-top: 15px; border: 1px solid #FEE2E2;'>
                        ❌ 密码错误，请核对后重试
                    </div>
                """, unsafe_allow_html=True)
            
        return False

    if not st.session_state.get("password_correct", False):
        # Professional Login Screen (for re-entry)
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="u-card" style='text-align: center; padding: 40px; margin-bottom: 0px;'>
                    <div style='background: #F8FAFC; width: 64px; height: 64px; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;'>
                        <span style='font-size: 32px;'>🔐</span>
                    </div>
                    <h2 style='margin-bottom: 8px; font-size: 1.8rem;'>{L.APP_TITLE.split(" - ")[0]}</h2>
                    <p style='color: var(--falcon-muted); margin-bottom: 32px; font-size: 0.95rem;'>请验证访问授权</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.text_input(
                "Access Key", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="键入密码并回车",
                label_visibility="collapsed"
            )
            
            if not st.session_state["password_correct"]:
                st.markdown("""
                    <div style='background-color: #FEF2F2; color: #DC2626; padding: 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; text-align: center; margin-top: 15px; border: 1px solid #FEE2E2;'>
                        ❌ 密码错误，请核对后重试
                    </div>
                """, unsafe_allow_html=True)
        return False

    return True
