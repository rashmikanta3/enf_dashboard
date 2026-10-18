import streamlit as st
from utils.db_utils import fetch_distinct_options
from utils.data_utils import FY_MONTHS
from datetime import date

def get_current_fy() -> str:
    today = date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    end_year_short = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year_short}"  # Returns e.g. "2026-27"

def render_sidebar_filters(table_name: str, div_col_name: str = "division", sub_div_col_name: str = "sub_division"):
    """
    Renders standardized cascading filters in the sidebar:
    Circle -> Division -> Sub-Division -> Section -> Financial Year -> Quarter -> Month
    
    Returns:
        where_stmt (str): SQL WHERE clause (e.g. "1=1 AND circle = :circle ...")
        sql_params (dict): Parameter dictionary for SQLAlchemy text() execution
        filter_state (dict): Selected values (circle, division, etc.) for UI headings
    """
    st.sidebar.subheader("Filters")

    # 1. Geographic Hierarchy
    circles = fetch_distinct_options(table_name, "circle")
    sel_circle = st.sidebar.selectbox("Circle", ["ALL"] + circles)

    divisions = fetch_distinct_options(table_name, div_col_name, {"circle": sel_circle})
    sel_div = st.sidebar.selectbox("Division", ["ALL"] + divisions)

    subdivisions = fetch_distinct_options(table_name, sub_div_col_name, {"circle": sel_circle, div_col_name: sel_div})
    sel_subdiv = st.sidebar.selectbox("Sub-Division", ["ALL"] + subdivisions)

    sections = fetch_distinct_options(table_name, "section", {"circle": sel_circle, div_col_name: sel_div, sub_div_col_name: sel_subdiv})
    sel_sec = st.sidebar.selectbox("Section", ["ALL"] + sections)

    st.sidebar.markdown("---")

    # 2. Time Hierarchy (FY, Quarter, Month)
    all_fys = fetch_distinct_options(table_name, "fy")
    current_fy = get_current_fy()
    if not all_fys:
        all_fys = ["2026-27","2025-26","2025-24"]
    sel_fys = st.sidebar.multiselect("Financial Year", options=all_fys, default= current_fy if all_fys else [])

    quarters_list = ["ALL", "Q1", "Q2", "Q3", "Q4"]
    sel_qtr = st.sidebar.selectbox("Quarter", quarters_list)

    quarter_month_map = {
        "Q1": ["Apr", "May", "Jun"],
        "Q2": ["Jul", "Aug", "Sep"],
        "Q3": ["Oct", "Nov", "Dec"],
        "Q4": ["Jan", "Feb", "Mar"]
    }
    available_months = ["ALL"] + (quarter_month_map.get(sel_qtr, FY_MONTHS) if sel_qtr != "ALL" else FY_MONTHS)
    sel_month = st.sidebar.selectbox("Month", available_months)

    # 3. Build SQL Condition
    where_clauses = ["1=1"]
    sql_params = {}

    if sel_circle != "ALL":
        where_clauses.append("circle = :circle")
        sql_params["circle"] = sel_circle
    if sel_div != "ALL":
        where_clauses.append(f'"{div_col_name}" = :division')
        sql_params["division"] = sel_div
    if sel_subdiv != "ALL":
        where_clauses.append(f'"{sub_div_col_name}" = :sub_division')
        sql_params["sub_division"] = sel_subdiv
    if sel_sec != "ALL":
        where_clauses.append("section = :section")
        sql_params["section"] = sel_sec

    if sel_fys:
        where_clauses.append("fy = ANY(:fys)")
        sql_params["fys"] = sel_fys
    if sel_qtr != "ALL":
        where_clauses.append("TRIM(qtr) = :qtr")
        sql_params["qtr"] = sel_qtr
    if sel_month != "ALL":
        where_clauses.append("TRIM(month) = :month")
        sql_params["month"] = sel_month

    where_stmt = " AND ".join(where_clauses)
    
    filter_state = {
        "circle": sel_circle,
        "division": sel_div,
        "sub_division": sel_subdiv,
        "section": sel_sec,
        "fys": sel_fys,
        "qtr": sel_qtr,
        "month": sel_month
    }

    return where_stmt, sql_params, filter_state