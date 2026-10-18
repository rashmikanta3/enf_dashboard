import pandas as pd
import streamlit as st
from sqlalchemy import text
from database import engine

@st.cache_data(ttl=600)
def fetch_distinct_options(table_name, column_name, filters=None):
    where_parts = [f'"{column_name}" IS NOT NULL']
    params = {}
    if filters:
        for idx, (col, val) in enumerate(filters.items()):
            if val and val != "ALL":
                where_parts.append(f'"{col}" = :p_{idx}')
                params[f'p_{idx}'] = val

    sql = f'SELECT DISTINCT "{column_name}" FROM {table_name} WHERE {" AND ".join(where_parts)} ORDER BY "{column_name}"'
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df[column_name].tolist()

def run_aggregate_query(sql_query, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(sql_query), conn, params=params or {})