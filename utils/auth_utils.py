import hashlib
import os
import pandas as pd
from sqlalchemy import text
from utils.db_utils import engine
import streamlit as st

def hash_password(password: str) -> str:
    """Hash password with a random 16-byte salt using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pwd_hash}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a provided plaintext password against the stored salt$hash."""
    try:
        salt, pwd_hash = stored_hash.split('$')
        check_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return pwd_hash == check_hash
    except Exception:
        return False

def authenticate_user(username: str, password: str):
    sql = text("SELECT * FROM team_users WHERE username = :username AND is_active = TRUE")
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"username": username.strip()})
    
    if df.empty:
        return None
    
    user_row = df.iloc[0].to_dict()
    if verify_password(user_row["password_hash"], password):
        # Omit password hash before storing in session state
        user_row.pop("password_hash", None)
        return user_row
    return None

def render_login_sidebar():
    if "user" not in st.session_state:
        st.session_state["user"] = None

    if st.session_state["user"] is None:
        st.sidebar.subheader("🔐 Team Login")
        uname = st.sidebar.text_input("Username", key="login_user")
        pwd = st.sidebar.text_input("Password", type="password", key="login_pwd")
        if st.sidebar.button("Login"):
            user = authenticate_user(uname, pwd)
            if user:
                st.session_state["user"] = user
                st.sidebar.success(f"Logged in as {user['full_name']}")
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials or account inactive.")
    else:
        u = st.session_state["user"]
        st.sidebar.write(f"Logged in: **{u['full_name']}** (`{u['role']}`)")
        if st.sidebar.button("Logout"):
            st.session_state["user"] = None
            st.rerun()
