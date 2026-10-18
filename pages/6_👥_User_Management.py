import streamlit as st
import pandas as pd
from sqlalchemy import text
from database import engine
from utils.auth_utils import hash_password, verify_password, render_login_sidebar

st.set_page_config(page_title="User Management & Password", page_icon="👥", layout="wide")

# Render authentication sidebar
render_login_sidebar()

current_user = st.session_state.get("user")
if not current_user:
    st.warning("⚠️ Please log in from the sidebar to access this page.")
    st.stop()

st.title("👥 User Management & Security")
st.write(f"Logged in as: **{current_user.get('full_name') or current_user.get('username')}** (`{current_user.get('role', 'member')}`)")

is_admin = current_user.get("role") == "admin"

# Organize into tabs
if is_admin:
    tab_pwd, tab_create, tab_manage = st.tabs(["🔑 Change My Password", "➕ Create New User", "📋 Manage Users & Reset Passwords"])
else:
    tab_pwd, = st.tabs(["🔑 Change My Password"])

# -------------------------------------------------------------
# TAB 1: SELF-SERVICE CHANGE PASSWORD (AVAILABLE TO ALL USERS)
# -------------------------------------------------------------
with tab_pwd:
    st.subheader("Update Your Password")
    with st.form("form_change_my_password", clear_on_submit=True):
        col_p1, col_p2 = st.columns(2)
        old_pwd = col_p1.text_input("Current Password *", type="password")
        new_pwd = col_p2.text_input("New Password *", type="password")
        confirm_pwd = col_p2.text_input("Confirm New Password *", type="password")

        btn_update = st.form_submit_button("Update Password", use_container_width=True)

        if btn_update:
            if not old_pwd or not new_pwd or not confirm_pwd:
                st.error("❌ All fields are required.")
            elif new_pwd != confirm_pwd:
                st.error("❌ New password and confirmation do not match.")
            elif len(new_pwd) < 6:
                st.error("❌ New password must be at least 6 characters long.")
            else:
                # Retrieve current password hash from DB
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT password_hash FROM team_users WHERE username = :u AND is_active = TRUE"),
                        {"u": current_user["username"]}
                    ).fetchone()

                if not row or not verify_password(row[0], old_pwd):
                    st.error("❌ Current password is incorrect.")
                else:
                    new_hash = hash_password(new_pwd)
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE team_users SET password_hash = :h, updated_at = CURRENT_TIMESTAMP WHERE username = :u"),
                            {"h": new_hash, "u": current_user["username"]}
                        )
                    st.success("✅ Password updated successfully! Please use your new password next time you log in.")

# -------------------------------------------------------------
# TAB 2: CREATE NEW USER (ADMIN ONLY)
# -------------------------------------------------------------
if is_admin:
    with tab_create:
        st.subheader("Register a New Team Member")

        with st.form("form_create_user", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("Username *", placeholder="e.g. jeypore_operator")
            new_fullname = c2.text_input("Full Name *", placeholder="e.g. Rajesh Kumar Mohanty")

            p1, p2 = st.columns(2)
            user_pwd = p1.text_input("Initial Password *", type="password")
            user_role = p2.selectbox("Role *", ["operator", "lineman", "supervisor", "admin"])

            st.markdown("##### Jurisdiction Scope (Optional)")
            j1, j2, j3, j4 = st.columns(4)
            u_circle = j1.text_input("Circle", placeholder="e.g. JEYPORE")
            u_division = j2.text_input("Division", placeholder="e.g. JED JEYPORE")
            u_subdiv = j3.text_input("Sub-Division", placeholder="e.g. JEYPORE SDO-II")
            u_sec = j4.text_input("Section", placeholder="e.g. ESO RANDHAPALLI")

            st.markdown("##### Feature Access Permissions")
            perm1, perm2 = st.columns(2)
            acc_dc = perm1.checkbox("Allow Access to DC Entry Form (`5_📝_DC_Entry_Form.py`)", value=True)
            acc_upload = perm2.checkbox("Allow Access to Data Upload Portal", value=False)

            btn_create = st.form_submit_button("➕ Register User", use_container_width=True)

            if btn_create:
                uname_clean = new_username.strip().lower()
                if not uname_clean or not new_fullname.strip() or not user_pwd:
                    st.error("❌ Username, Full Name, and Password are required.")
                elif len(user_pwd) < 6:
                    st.error("❌ Password must be at least 6 characters long.")
                else:
                    try:
                        hashed = hash_password(user_pwd)
                        insert_query = text("""
                            INSERT INTO team_users (
                                username, full_name, password_hash, role,
                                circle, division, sub_division, section,
                                can_access_dc_entry, can_access_data_upload, is_active
                            ) VALUES (
                                :uname, :fname, :pwd, :role,
                                :circle, :div, :subdiv, :sec,
                                :acc_dc, :acc_upload, TRUE
                            )
                        """)
                        with engine.begin() as conn:
                            conn.execute(insert_query, {
                                "uname": uname_clean,
                                "fname": new_fullname.strip(),
                                "pwd": hashed,
                                "role": user_role,
                                "circle": u_circle.strip() or None,
                                "div": u_division.strip() or None,
                                "subdiv": u_subdiv.strip() or None,
                                "sec": u_sec.strip() or None,
                                "acc_dc": acc_dc,
                                "acc_upload": acc_upload
                            })
                        st.success(f"🎉 User **{uname_clean}** created successfully!")
                    except Exception as e:
                        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                            st.error(f"❌ Username '{uname_clean}' is already taken.")
                        else:
                            st.error(f"❌ Database error: {e}")

# -------------------------------------------------------------
# TAB 3: MANAGE USERS & ADMIN RESET PASSWORD (ADMIN ONLY)
# -------------------------------------------------------------
if is_admin:
    with tab_manage:
        st.subheader("All Registered Users")

        with engine.connect() as conn:
            users_df = pd.read_sql(
                text("""
                    SELECT id, username, full_name, role, circle, division, 
                           can_access_dc_entry, can_access_data_upload, is_active, created_at
                    FROM team_users
                    ORDER BY id ASC
                """),
                conn
            )

        if not users_df.empty:
            st.dataframe(users_df, use_container_width=True)

            st.divider()
            st.subheader("🔑 Admin Password Reset")
            st.caption("Reset any user's password directly without knowing their current password.")

            with st.form("form_admin_reset_pwd"):
                user_list = users_df["username"].tolist()
                target_user = st.selectbox("Select User to Reset", user_list)
                admin_new_pwd = st.text_input("Set New Password", type="password")

                btn_admin_reset = st.form_submit_button("Reset User Password")

                if btn_admin_reset:
                    if not admin_new_pwd or len(admin_new_pwd) < 6:
                        st.error("❌ Password must be at least 6 characters.")
                    else:
                        new_h = hash_password(admin_new_pwd)
                        with engine.begin() as conn:
                            conn.execute(
                                text("UPDATE team_users SET password_hash = :h, updated_at = CURRENT_TIMESTAMP WHERE username = :u"),
                                {"h": new_h, "u": target_user}
                            )
                        st.success(f"✅ Password for user **{target_user}** reset successfully!")
        else:
            st.info("No users registered yet.")