import pandas as pd
import io


FY_MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

def parse_date_fy_meta(dt_val):
    if not dt_val or pd.isna(dt_val):
        return "2026-27", "Q3", "Oct"
    try:
        dt = pd.to_datetime(dt_val, dayfirst=True)
        m = dt.month
        y = dt.year
        if m >= 4:
            fy = f"{y}-{str(y+1)[-2:]}"
            q = f"Q{((m - 4) // 3) + 1}"
        else:
            fy = f"{y-1}-{str(y)[-2:]}"
            q = "Q4"
        return fy, q, dt.strftime("%b")
    except Exception:
        return "2026-27", "Q3", "Oct"

def get_templates():
    return {
        "Load Booking (load_bookings)": pd.DataFrame({
            "vcr_no": ["560822092601", "560822092602"],
            "scno": ["321102005432", "321102008891"],
            "inspection_date": ["12-10-2026", "13-10-2026"],
            "circle": ["BERHAMPUR", "JEYPORE"],
            "division": ["BED BERHAMPUR", "JED JEYPORE"],
            "sub_division": ["CITY SUBDIV", "BORIGUMA"],
            "section": ["SECTION-1", "BORIGUMA SEC"],
            "inspected_officer_name": ["Er. Rajesh Kumar", "Er. Amit Patel"],
            "user_name": ["Ramesh Sahoo", "Pooja Das"],
            "address": ["Plot 42, Main Rd", "Near Market Square"],
            "defect_name": ["DIRECT HOOKING", "DAE TAMPER"],
            "connected_category": ["DOMESTIC", "COMMERCIAL"],
            "connected_load": [4.5, 2.0]
        }),
        "Collection Settlement (collections)": pd.DataFrame({
            "pr_no": ["PR-99201", "PR-99202"],
            "vcr_no": ["560822092601", "560822092602"],
            "scno": ["321102005432", "321102008891"],
            "circle": ["BERHAMPUR", "JEYPORE"],
            "div": ["BED BERHAMPUR", "JED JEYPORE"],
            "sub_div": ["CITY SUBDIV", "BORIGUMA"],
            "section": ["SECTION-1", "BORIGUMA SEC"],
            "inspected_officer_name": ["Er. Rajesh Kumar", "Er. Amit Patel"],
            "user_name": ["Ramesh Sahoo", "Pooja Das"],
            "status": ["Closed", "Closed"],
            "theft_typ": ["Hooking", "Tamper"],
            "defect_name": ["DIRECT HOOKING", "DAE TAMPER"],
            "connected_categor": ["DOMESTIC", "COMMERCIAL"],
            "amount_paid": [12500.0, 8400.0],
            "collection_dat": ["15-10-2026", "16-10-2026"],
            "mode_of_paymen": ["UPI", "NEFT"],
            "amount_collected_b": ["Cashier A", "Cashier B"]
        }),
        "Target Allocation (targets)": pd.DataFrame({
            "fy": ["2026-27", "2026-27"],
            "circle": ["BERHAMPUR", "JEYPORE"],
            "division": ["BED BERHAMPUR", "JED JEYPORE"],
            "sub_division": ["CITY SUBDIV", "BORIGUMA"],
            "section": ["SECTION-1", "BORIGUMA SEC"],
            "target_load_kw": [150.0, 200.0],
            "target_collection_amount": [500000.0, 800000.0],
            "target_dc_count": [40, 60]
        })
    }
def format_inr(val: float) -> str:
    """
    Formats numerical amounts into Indian numbering denominations (Lakh and Crore):
    - Below 1 Lakh: ₹ XX,XXX
    - 1 Lakh to < 1 Crore: ₹ X.XX L
    - 1 Crore and above: ₹ X.XX Cr
    """
    if val is None or val == 0:
        return "₹ 0"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    
    if abs_val >= 10_000_000:  # 1 Crore = 100 Lakhs
        return f"{sign}₹ {abs_val / 10_000_000:.2f} Cr"
    elif abs_val >= 100_000:   # 1 Lakh = 100,000
        return f"{sign}₹ {abs_val / 100_000:.2f} L"
    else:
        return f"{sign}₹ {abs_val:,.2f}"
