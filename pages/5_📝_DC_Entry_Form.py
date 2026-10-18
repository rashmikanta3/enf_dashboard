import streamlit as st
import pandas as pd
from sqlalchemy import text
from database import engine
from utils.data_utils import parse_date_fy_meta, format_inr
import models
from utils.auth_utils import render_login_sidebar

render_login_sidebar()

user = st.session_state.get("user")
if not user:
    st.warning("Please log in from the sidebar to access DC Entry.")
    st.stop()

if not user.get("can_access_dc_entry"):
    st.error("⛔ Access Denied: You do not have permission to access DC Entry.")
    st.stop()

st.title("📝 Disconnection (DC) Entry Form")
# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

st.markdown("Search a **VCR Number** to auto-populate consumer, section, and jurisdiction details, then record disconnection execution.")

# ----------------- SESSION STATE INITIALIZATION -----------------
if "dc_vcr_data" not in st.session_state:
    st.session_state["dc_vcr_data"] = {}
if "searched_vcr" not in st.session_state:
    st.session_state["searched_vcr"] = ""
if "existing_dc_records" not in st.session_state:
    st.session_state["existing_dc_records"] = []

# ----------------- 1. VCR NUMBER LOOKUP -----------------
col_vcr, col_btn = st.columns([3, 1])
vcr_query = col_vcr.text_input(
    "Enter VCR Number", 
    value=st.session_state["searched_vcr"],
    placeholder="e.g. 560822092601"
)
lookup_clicked = col_btn.button("🔍 Lookup VCR", use_container_width=True)

if lookup_clicked and vcr_query.strip():
    clean_vcr = vcr_query.strip()
    st.session_state["searched_vcr"] = clean_vcr
    
    with engine.connect() as conn:
        # 1. Check if VCR exists in load_bookings
        res = conn.execute(
            text("""
                SELECT vcr_no, scno, user_name, address, section, circle, division, sub_division 
                FROM load_bookings 
                WHERE vcr_no = :vcr 
                LIMIT 1
            """),
            {"vcr": clean_vcr}
        ).fetchone()

        # 2. Check if VCR already has prior DC records in disconnections table
        prior_dcs = conn.execute(
            text("""
                SELECT id, dc_date, dc_type, outstanding_amount, meter_reading, 
                       lineman_name, supervising_officer, remarks, created_at
                FROM disconnections 
                WHERE vcr_no = :vcr
                ORDER BY id DESC
            """),
            {"vcr": clean_vcr}
        ).fetchall()

        st.session_state["existing_dc_records"] = [dict(r._mapping) for r in prior_dcs]

        if res:
            st.session_state["dc_vcr_data"] = dict(res._mapping)
            if not st.session_state["existing_dc_records"]:
                st.success(f"✅ Record Found for Consumer: **{st.session_state['dc_vcr_data'].get('user_name', '')}** (No prior DC found)")
        else:
            st.session_state["dc_vcr_data"] = {}
            st.error(f"❌ VCR Number '{clean_vcr}' not found in Load Booking records.")

vcr_info = st.session_state["dc_vcr_data"]
active_circle = vcr_info.get("circle", "")
existing_dcs = st.session_state.get("existing_dc_records", [])

# ----------------- 2. DUPLICATE VCR / PRIOR DC ALERT -----------------
allow_entry = True

if existing_dcs:
    st.warning(f"⚠️ **Duplicate Alert:** This VCR Number (`{st.session_state['searched_vcr']}`) already has **{len(existing_dcs)}** recorded disconnection(s).")
    
    with st.expander("📋 View Previous Disconnection Details", expanded=True):
        # Format existing DC details in a clean table
        display_df = pd.DataFrame(existing_dcs)
        display_df['outstanding_amount'] = display_df['outstanding_amount'].apply(lambda x: f"₹{x:,.2f}")
        display_df = display_df.rename(columns={
            "id": "DC ID",
            "dc_date": "DC Date",
            "dc_type": "Type",
            "outstanding_amount": "Outstanding Dues",
            "meter_reading": "Meter Reading",
            "lineman_name": "Lineman / Officer",
            "remarks": "Remarks"
        })
        cols_to_show = ["DC ID", "DC Date", "Type", "Outstanding Dues", "Meter Reading", "Lineman / Officer", "Remarks"]
        st.dataframe(display_df[[c for c in cols_to_show if c in display_df.columns]], use_container_width=True)

    # Confirmation toggle to avoid accidental duplicate insertion
    confirm_duplicate = st.checkbox(
        "⚠️ Do you still want to add a subsequent / new DC entry for this VCR?",
        value=False,
        help="Check this box only if this is a valid subsequent disconnection (e.g. re-disconnection after temporary restoration)."
    )
    if not confirm_duplicate:
        allow_entry = False
        st.info("💡 To prevent duplicate entries, the form submission is locked. Check the box above to proceed.")

# ----------------- 3. CIRCLE-WISE OFFICERS FETCH -----------------
def get_circle_officers(circle_name):
    """Fetches standardized disconnecting officers for the selected circle."""
    if not circle_name:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT officer_name FROM disconnecting_officers WHERE circle = :c ORDER BY officer_name"),
            {"c": circle_name}
        ).fetchall()
        officers = [r[0] for r in rows if r[0]]

        if not officers:
            hist_rows = conn.execute(
                text("SELECT DISTINCT inspected_officer_name FROM load_bookings WHERE circle = :c AND inspected_officer_name IS NOT NULL ORDER BY inspected_officer_name"),
                {"c": circle_name}
            ).fetchall()
            officers = [r[0] for r in hist_rows if r[0]]

    return sorted(list(set(officers)))

circle_officers = get_circle_officers(active_circle) if active_circle else []

# ----------------- 4. DISCONNECTION ORDER FORM -----------------
st.divider()

with st.form("save_dc_form", clear_on_submit=False):
    st.subheader("Disconnection Execution Details")

    # Read-only Auto-Populated Consumer Details
    c1, c2 = st.columns(2)
    vcr_no = c1.text_input("VCR Number", value=vcr_info.get("vcr_no", st.session_state["searched_vcr"]), disabled=True)
    scno = c2.text_input("Consumer SCNO", value=vcr_info.get("scno", ""), disabled=True)

    c3, c4 = st.columns(2)
    consumer_name = c3.text_input("Consumer Name", value=vcr_info.get("user_name", ""), disabled=True)
    section_val = c4.text_input("Section", value=vcr_info.get("section", ""), disabled=True)

    addr_val = st.text_input("Address", value=vcr_info.get("address", ""), disabled=True)

    # Jurisdiction Display
    j1, j2, j3 = st.columns(3)
    j1.text_input("Circle", value=vcr_info.get("circle", "Unassigned"), disabled=True)
    j2.text_input("Division", value=vcr_info.get("division", "Unassigned"), disabled=True)
    j3.text_input("Sub-Division", value=vcr_info.get("sub_division", "Unassigned"), disabled=True)

    st.markdown("##### Fill Execution Parameters")

    # User-Editable Inputs
    f1, f2 = st.columns(2)
    dc_date = f1.date_input("Disconnection Date *")
    outstanding = f2.number_input("Outstanding Dues Amount (₹) *", min_value=0.0, step=100.0, value=0.0)

    f3, f4 = st.columns(2)
    reading = f3.text_input("Final Meter Reading (kWh)", placeholder="e.g. 1420.5")
    dc_type = f4.selectbox("Disconnection Type", ["Temporary", "Permanent"])

    st.markdown(f"**Executing Officer / Lineman ({active_circle or 'No Circle Selected'} Registry)**")
    
    officer_options = ["-- Select Existing Officer --"] + circle_officers + ["+ Add New Officer"]
    selected_officer_choice = st.selectbox("Designated Disconnecting Officer *", officer_options)

    new_officer_name = ""
    save_to_registry = False
    if selected_officer_choice == "+ Add New Officer" or not circle_officers:
        col_new1, col_new2 = st.columns([2, 1])
        new_officer_name = col_new1.text_input("Technician/Supervisor Name", placeholder="e.g. Er. Subhashree Mohapatra")
        save_to_registry = col_new2.checkbox("Save to Circle Registry for future use", value=True)

    remarks = st.text_input("Remarks / Reason", placeholder="e.g. Meter seal intact, disconnected from pole")

    # Form submit button is disabled if prior DC exists and user hasn't explicitly checked confirmation
    submit_dc = st.form_submit_button(
        "💾 Save Disconnection Order", 
        use_container_width=True,
        disabled=not allow_entry
    )

    if submit_dc:
        if not allow_entry:
            st.error("❌ Submission locked. Please confirm above if you intend to create a subsequent entry.")
            st.stop()

        # Determine final officer name
        if selected_officer_choice == "+ Add New Officer" or not circle_officers:
            final_officer = new_officer_name.strip()
        elif selected_officer_choice != "-- Select Existing Officer --":
            final_officer = selected_officer_choice.strip()
        else:
            final_officer = ""

        # Validation
        if not vcr_info.get("vcr_no"):
            st.error("❌ Please lookup and verify a valid VCR Number before submitting.")
        elif not final_officer:
            st.error("❌ Please select or enter the Disconnecting Officer.")
        else:
            date_str = dc_date.strftime("%d-%m-%Y")
            fy, qtr, m = parse_date_fy_meta(date_str)

            with engine.connect() as conn:
                # 1. Optionally register new officer for the circle
                if save_to_registry and final_officer and active_circle:
                    conn.execute(
                        text("""
                            INSERT INTO disconnecting_officers (circle, officer_name, designation)
                            VALUES (:c, :name, 'Executing Officer')
                            ON CONFLICT (circle, officer_name) DO NOTHING
                        """),
                        {"c": active_circle, "name": final_officer}
                    )

                # 2. Insert Disconnection record
                insert_dc_sql = """
                    INSERT INTO disconnections (
                        vcr_no, scno, consumer_name, address, section, 
                        circle, division, sub_division, dc_date, 
                        outstanding_amount, meter_reading, dc_type, 
                        lineman_name, supervising_officer, remarks, 
                        fy, qtr, month
                    ) VALUES (
                        :vcr, :scno, :cname, :addr, :sec, 
                        :circle, :div, :sub_div, :dc_date, 
                        :amt, :reading, :dc_type, 
                        :officer, :officer, :remarks, 
                        :fy, :qtr, :m
                    )
                """
                conn.execute(text(insert_dc_sql), {
                    "vcr": vcr_info.get("vcr_no"),
                    "scno": vcr_info.get("scno"),
                    "cname": vcr_info.get("user_name"),
                    "addr": vcr_info.get("address"),
                    "sec": vcr_info.get("section"),
                    "circle": vcr_info.get("circle"),
                    "div": vcr_info.get("division"),
                    "sub_div": vcr_info.get("sub_division"),
                    "dc_date": date_str,
                    "amt": outstanding,
                    "reading": reading,
                    "dc_type": dc_type,
                    "officer": final_officer,
                    "remarks": remarks,
                    "fy": fy,
                    "qtr": qtr,
                    "m": m
                })
                conn.commit()

            st.balloons()
            st.success(f"🎉 Disconnection Order for VCR **{vcr_info.get('vcr_no')}** ({vcr_info.get('user_name')}) saved successfully!")

            # Reset session state for next entry
            st.session_state["dc_vcr_data"] = {}
            st.session_state["searched_vcr"] = ""
            st.session_state["existing_dc_records"] = []