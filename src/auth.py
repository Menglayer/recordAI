"""
Authentication module
提供 Streamlit 应用的密码验证功能
"""
from typing import Callable
import streamlit as st
from src import lang as L


def _render_login_form(on_password_entered: Callable[[], None], show_error: bool = False) -> None:
    """
    渲染登录表单 UI
    
    Args:
        on_password_entered: 密码输入后的回调函数
        show_error: 是否显示错误提示
    """
    _, col_mid, _ = st.columns([1, 1.2, 1])
    with col_mid:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
        
        # 登录卡片
        st.markdown(f"""
            <div class="u-card" style='text-align: center; padding: 40px; margin-bottom: 0px;'>
                <div style='background: #F8FAFC; width: 64px; height: 64px; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;'>
                    <span style='font-size: 32px;'>🔐</span>
                </div>
                <h2 style='margin-bottom: 8px; font-size: 1.8rem;'>{L.APP_TITLE.split(" - ")[0]}</h2>
                <p style='color: var(--falcon-muted); margin-bottom: 32px; font-size: 0.95rem;'>请验证访问授权</p>
            </div>
        """, unsafe_allow_html=True)
        
        # 密码输入框
        st.text_input(
            "Access Key", 
            type="password", 
            on_change=on_password_entered, 
            key="password",
            placeholder="键入密码并回车",
            label_visibility="collapsed"
        )
        
        # 错误提示
        if show_error:
            st.markdown("""
                <div style='background-color: #FEF2F2; color: #DC2626; padding: 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; text-align: center; margin-top: 15px; border: 1px solid #FEE2E2;'>
                    ❌ 密码错误，请核对后重试
                </div>
            """, unsafe_allow_html=True)


def check_password() -> bool:
    """
    检查用户密码是否正确
    
    Returns:
        bool: True 如果密码正确，False 否则
    """

    def password_entered() -> None:
        """验证用户输入的密码"""
        entered_password = st.session_state.get("password", "")
        correct_password = st.secrets.get("PASSWORD", "admin123")
        
        if entered_password == correct_password:
            st.session_state["password_correct"] = True
            # 清除密码状态，避免明文存储
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # 首次访问，尚未验证
    if "password_correct" not in st.session_state:
        _render_login_form(password_entered, show_error=False)
        return False

    # 密码错误，需要重新输入
    if not st.session_state.get("password_correct", False):
        _render_login_form(password_entered, show_error=True)
        return False

    # 密码正确
    return True
