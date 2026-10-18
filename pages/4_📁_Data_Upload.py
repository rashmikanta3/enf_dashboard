import io
import time
import numpy as np
import pandas as pd
import streamlit as st
from database import engine
import models
from utils.data_utils import get_templates
from utils.db_utils import fetch_distinct_options

from utils.auth_utils import render_login_sidebar

render_login_sidebar()

user = st.session_state.get("user")
if not user:
    st.warning("Please log in from the sidebar to access Data Upload.")
    st.stop()

if not user.get("can_access_data_upload"):
    st.error("⛔ Access Denied: You do not have permission to upload files.")
    st.stop()

st.title("📤 Data Upload Portal")

# Ensure all target tables exist
models.Base.metadata.create_all(bind=engine)

st.title("📁 Robust CSV Stream Ingestion Hub")
st.markdown("Download pre-verified templates below to guarantee column alignment, then stream your CSV file into the database.")

target_table = st.selectbox(
    "Select Target Dataset",
    ["Load Booking (load_bookings)", "Collection Settlement (collections)", "Target Allocation (targets)"]
)

templates = get_templates()
sample_df = templates[target_table]
csv_bytes = sample_df.to_csv(index=False).encode('utf-8')

st.download_button(
    label=f"📥 Download Exact CSV Template for {target_table.split(' ')[0]}",
    data=csv_bytes,
    file_name=f"sample_{target_table.split(' ')[0].lower()}_template.csv",
    mime="text/csv"
)

st.divider()

uploaded_file = st.file_uploader("Upload CSV File to Database", type=["csv"])

# ----------------- COMPREHENSIVE ALIAS DICTIONARY -----------------
HEADER_SYNONYMS = {
    # Load Booking & General
    "inspection": "inspection_date",
    "inspect_date": "inspection_date",
    "vcr": "vcr_no",
    "vcr_number": "vcr_no",
    "consumer_no": "scno",
    "consumer_name": "user_name",
    "name": "user_name",
    "load": "connected_load",
    "load_kw": "connected_load",
    
    # Collection Model Aliases (Maps standard names to collections table schema)
    "div": "div",
    "division": "div",
    "sub_div": "sub_div",
    "sub_division": "sub_div",
    "subdivision": "sub_div",
    "pr_number": "pr_no",
    "pr": "pr_no",
    "amount": "amount_paid",
    "paid_amount": "amount_paid",
    "collection_date": "collection_dat",
    "theft_type": "theft_typ",
    "connected_category": "connected_categor",
    "category": "connected_categor",
    "amount_collected_by": "amount_collected_b",
    "collected_by": "amount_collected_b",
    "mode": "mode_of_paymen",
    "mode_of_payment": "mode_of_paymen",
    
    # Target Model Aliases
    "target_load": "target_load_kw",
    "load_target": "target_load_kw",
    "target_collection": "target_collection_amount",
    "target_amount": "target_collection_amount",
    "target_dc": "target_dc_count",
    "dc_target": "target_dc_count"
}

# ----------------- STRICT DATASET VERIFICATION RULES -----------------
MANDATORY_COLUMNS = {
    "Load Booking (load_bookings)": [
        "vcr_no", "scno", "inspection_date", "circle", "division", 
        "sub_division", "section", "connected_load"
    ],
    "Collection Settlement (collections)": [
        "pr_no", "vcr_no", "scno", "circle", "div", 
        "sub_div", "section", "amount_paid"
    ],
    "Target Allocation (targets)": [
        "fy", "circle", "division", "sub_division", "section", 
        "target_load_kw", "target_collection_amount", "target_dc_count"
    ]
}

def normalize_column_name(col: str) -> str:
    """Strips whitespace, converts to lowercase and snake_case."""
    cleaned = (
        str(col).strip().lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace("/", "_")
        .replace("-", "_")
    )
    return HEADER_SYNONYMS.get(cleaned, cleaned)

def execute_copy_stream(cursor, sql_copy, string_buffer):
    """Executes high-speed PostgreSQL COPY streaming for psycopg2 and psycopg3."""
    if hasattr(cursor, "copy"):
        with cursor.copy(sql_copy) as copy:
            copy.write(string_buffer.getvalue())
    elif hasattr(cursor, "copy_expert"):
        string_buffer.seek(0)
        cursor.copy_expert(sql_copy, string_buffer)
    else:
        string_buffer.seek(0)
        cursor.execute(sql_copy)

def vectorized_fy_tagging(df, date_col):
    """Vectorized calculation of FY, Quarter, and Month using Pandas Datetime."""
    dt_series = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    df["month"] = dt_series.dt.strftime("%b").fillna("Oct")
    
    m = dt_series.dt.month.fillna(10).astype(int)
    y = dt_series.dt.year.fillna(2026).astype(int)
    
    q_num = np.where(m >= 4, ((m - 4) // 3) + 1, 4)
    df["qtr"] = "Q" + pd.Series(q_num, index=df.index).astype(str)
    
    fy_start = np.where(m >= 4, y, y - 1)
    fy_end = (fy_start + 1) % 100
    
    s_start = pd.Series(fy_start, index=df.index).astype(str)
    s_end = pd.Series(fy_end, index=df.index).astype(str).str.zfill(2)
    df["fy"] = s_start + "-" + s_end

# ----------------- UPLOAD & VERIFICATION LOGIC -----------------
if uploaded_file is not None:
    try:
        # Pre-flight check on headers
        uploaded_file.seek(0)
        preview_df = pd.read_csv(
            uploaded_file, 
            nrows=5, 
            dtype=str, 
            encoding="latin1", 
            encoding_errors="replace",
            on_bad_lines="skip"
        )
        uploaded_file.seek(0)

        # Normalize and alias uploaded column names
        normalized_uploaded_cols = [normalize_column_name(c) for c in preview_df.columns]
        
        # Verify against specific dataset mandatory rules
        expected_mandatory = MANDATORY_COLUMNS[target_table]
        missing_mandatory = [col for col in expected_mandatory if col not in normalized_uploaded_cols]

        if missing_mandatory:
            st.error(f"❌ **Column Verification Failed for {target_table.split(' ')[0]}!**")
            st.markdown(f"**Missing Required Column(s):** `{', '.join(missing_mandatory)}`")
            st.info(f"**Headers detected in your file:** `{', '.join(normalized_uploaded_cols)}`")
        else:
            st.success(f"✅ **{target_table.split(' ')[0]} CSV Verification Passed!** All required columns are present and aligned.")

            if "load" in target_table.lower():
                dest_table, conflict_col = "load_bookings", "vcr_no"
            elif "collection" in target_table.lower():
                dest_table, conflict_col = "collections", "pr_no"
            else:
                dest_table, conflict_col = "targets", None

            if st.button("🚀 Stream Ingest into Database"):
                start_time = time.time()
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                status_text.text("Connecting to database...")

                raw_conn = engine.raw_connection()
                try:
                    cursor = raw_conn.cursor()

                    # ----------------- 1. TARGET ALLOCATION VERIFIED UPSERT -----------------
                    if dest_table == "targets":
                        uploaded_file.seek(0)
                        df_target = pd.read_csv(
                            uploaded_file, 
                            dtype=str, 
                            encoding="latin1", 
                            encoding_errors="replace",
                            on_bad_lines="skip"
                        )
                        df_target.columns = [normalize_column_name(c) for c in df_target.columns]

                        # Clean whitespace
                        for c in df_target.select_dtypes(include="object").columns:
                            df_target[c] = (
                                df_target[c]
                                .str.replace('\xa0', ' ', regex=False)
                                .str.replace('"', '', regex=False)
                                .str.strip()
                            )

                        for c in ["target_load_kw", "target_collection_amount", "target_dc_count"]:
                            if c in df_target.columns:
                                df_target[c] = pd.to_numeric(
                                    df_target[c].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
                                ).fillna(0.0)

                        # Rollup generation across Section, Sub-Division, Division, Circle
                        levels = [
                            ('Section', 'section', ['circle', 'division', 'sub_division', 'section']),
                            ('Sub-Division', 'sub_division', ['circle', 'division', 'sub_division']),
                            ('Division', 'division', ['circle', 'division']),
                            ('Circle', 'circle', ['circle'])
                        ]

                        total_upserted = 0
                        for level_name, group_col, group_keys in levels:
                            agg = df_target.groupby(['fy'] + group_keys, as_index=False).agg({
                                'target_load_kw': 'sum',
                                'target_collection_amount': 'sum',
                                'target_dc_count': 'sum'
                            })
                            for _, r in agg.iterrows():
                                cursor.execute("""
                                    INSERT INTO targets (fy, entity_level, entity_name, circle, division, sub_division, section, target_load_kw, target_collection_amount, target_dc_count)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (fy, entity_level, entity_name) 
                                    DO UPDATE SET 
                                        target_load_kw = EXCLUDED.target_load_kw,
                                        target_collection_amount = EXCLUDED.target_collection_amount,
                                        target_dc_count = EXCLUDED.target_dc_count;
                                """, (
                                    r['fy'], level_name, r[group_col],
                                    r.get('circle'), r.get('division'), r.get('sub_division'), r.get('section'),
                                    r['target_load_kw'], r['target_collection_amount'], int(r['target_dc_count'])
                                ))
                                total_upserted += 1

                        raw_conn.commit()
                        progress_bar.progress(1.0)
                        status_text.empty()
                        st.balloons()
                        st.success(f"🎉 Target Ingestion Complete! Successfully verified, uploaded, and rolled up **{total_upserted:,}** targets across all jurisdictional tiers.")

                    # ----------------- 2. LOAD BOOKING & COLLECTION INGESTION -----------------
                    else:
                        CHUNK_SIZE = 50000
                        total_streamed = 0
                        total_inserted = 0
                        
                        uploaded_file.seek(0)
                        csv_iterator = pd.read_csv(
                            uploaded_file, 
                            chunksize=CHUNK_SIZE, 
                            dtype=str, 
                            encoding="latin1", 
                            encoding_errors="replace",
                            on_bad_lines="skip"
                        )

                        for chunk_idx, chunk in enumerate(csv_iterator):
                            status_text.text(f"Processing batch {chunk_idx + 1} ({total_streamed:,} rows processed)...")

                            # 1. Normalize headers
                            chunk.columns = [normalize_column_name(c) for c in chunk.columns]

                            # 2. Vectorized cleaning of stray quotes & non-breaking spaces
                            for col in chunk.select_dtypes(include="object").columns:
                                chunk[col] = (
                                    chunk[col]
                                    .str.replace('\xa0', ' ', regex=False)
                                    .str.replace('"', '', regex=False)
                                    .str.strip()
                                )

                            # 3. Clean scientific notation in vcr_no
                            if "vcr_no" in chunk.columns:
                                mask_e = chunk["vcr_no"].astype(str).str.contains(r"E\+", case=False, na=False)
                                if mask_e.any():
                                    chunk.loc[mask_e, "vcr_no"] = (
                                        pd.to_numeric(chunk.loc[mask_e, "vcr_no"], errors="coerce")
                                        .fillna(0)
                                        .astype("int64")
                                        .astype(str)
                                    )

                            # 4. In-chunk deduplication on primary key
                            if conflict_col and conflict_col in chunk.columns:
                                chunk = chunk.dropna(subset=[conflict_col]).drop_duplicates(subset=[conflict_col], keep="first")

                            # 5. Skip keys already existing in database
                            if conflict_col and conflict_col in chunk.columns and len(chunk) > 0:
                                keys = list(chunk[conflict_col].unique())
                                cursor.execute(
                                    f'SELECT "{conflict_col}" FROM {dest_table} WHERE "{conflict_col}" = ANY(%s);', 
                                    (keys,)
                                )
                                existing_keys = {r[0] for r in cursor.fetchall()}
                                if existing_keys:
                                    chunk = chunk[~chunk[conflict_col].isin(existing_keys)]

                            # 6. Auto-Tag FY, Quarter, Month if date column exists
                            date_col = next((c for c in ["inspection_date", "collection_dat", "dc_date"] if c in chunk.columns), None)
                            if date_col:
                                vectorized_fy_tagging(chunk, date_col)

                            # 7. Numeric conversion
                            for num_col in ["connected_load", "amount_paid", "outstanding_amount"]:
                                if num_col in chunk.columns:
                                    chunk[num_col] = pd.to_numeric(
                                        chunk[num_col].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
                                    ).fillna(0.0)

                            # 8. Stream records into final table
                            if len(chunk) > 0:
                                buffer = io.StringIO()
                                chunk.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
                                buffer.seek(0)

                                cols = list(chunk.columns)
                                columns_str = ", ".join([f'"{col}"' for col in cols])

                                copy_sql = f"COPY {dest_table} ({columns_str}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')"
                                execute_copy_stream(cursor, copy_sql, buffer)
                                raw_conn.commit()

                            total_streamed += CHUNK_SIZE
                            total_inserted += len(chunk)

                        elapsed = time.time() - start_time
                        skipped_count = max(0, total_streamed - total_inserted)
                        progress_bar.progress(1.0)
                        status_text.empty()
                        st.balloons()
                        st.success(
                            f"🎉 Ingestion Complete!\n\n"
                            f"- **Dataset:** {target_table}\n"
                            f"- **New Rows Inserted:** {total_inserted:,}\n"
                            f"- **Duplicates Skipped (Unique `{conflict_col}`):** {skipped_count:,}\n"
                            f"- **Total Time:** {elapsed:.2f} seconds"
                        )

                    cursor.close()
                    fetch_distinct_options.clear()
                except Exception as e:
                    raw_conn.rollback()
                    st.error(f"Ingestion failed: {e}")
                finally:
                    raw_conn.close()
    except Exception as err:
        st.error(f"Error reading CSV: {err}")