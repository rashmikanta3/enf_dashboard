import streamlit as st
import models  # Initializes database tables and unique indexes

st.set_page_config(
    page_title="Utility Vigilance & DC Portal",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Power Utility Vigilance & Disconnection Portal")
st.markdown("""
Welcome to the Performance Monitoring and Ingestion Portal.

### Navigation Overview
- **📊 Load Booking Dashboard**: Target vs. Achievement, Defect Breakdown, and Multi-FY progression.
- **💰 Collection Dashboard**: Penal assessment collections, money receipt analysis, and collector ranks.
- **✂️ Disconnection Monitoring**: Dues recovery monitoring and executive enforcement tracking.
- **📁 Data Upload Hub**: Fast streaming CSV uploader with duplicate skipping (`vcr_no`, `pr_no`) and target rollup.
- **📝 DC Entry Form**: Real-time VCR lookup and disconnection order creation.
- **👥  User Management**: Change password

👈 *Select a module from the sidebar to begin.*
""")