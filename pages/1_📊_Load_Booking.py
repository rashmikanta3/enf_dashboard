import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.db_utils import run_aggregate_query
from utils.data_utils import FY_MONTHS
from utils.filter_utils import render_sidebar_filters

# Force wide layout and responsive container margins
st.set_page_config(page_title="Load Booking Performance", page_icon="📊", layout="wide")

# Custom CSS for modern KPI cards and full-width layout
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100% !important;
    }
    .kpi-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.15s ease-in-out;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: #475569;
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .kpi-value {
        color: #f8fafc;
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .kpi-sub {
        color: #64748b;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- CONFIG FOR QUICK IMAGE EXPORT -----------------
# Configures the Plotly camera button to save clean, high-resolution 1080p images for slide pasting
PLOTLY_SNAPSHOT_CONFIG = {
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'chart_snapshot',
        'height': 720,
        'width': 1280,
        'scale': 3  # Crisp DPI for pasting into PowerPoint
    }
}

# ----------------- HEADER & UNIT TOGGLE -----------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("📊 Load Booking Performance Dashboard")
with head_col2:
    unit_mode = st.radio(
        "Display Load Unit", 
        ["kW", "MW"], 
        horizontal=True, 
        index=0,
        help="Choose whether to display load figures in Kilowatts (kW) or Megawatts (MW)"
    )

unit_multiplier = 0.001 if unit_mode == "MW" else 1.0
unit_label = "MW" if unit_mode == "MW" else "kW"

# ----------------- 1. SIDEBAR FILTERS -----------------
where_stmt, sql_params, filters = render_sidebar_filters("load_bookings")

if filters["circle"] == "ALL":
    drill_col, target_level = "circle", "Circle"
elif filters["division"] == "ALL":
    drill_col, target_level = "division", "Division"
elif filters["sub_division"] == "ALL":
    drill_col, target_level = "sub_division", "Sub-Division"
else:
    drill_col, target_level = "section", "Section"

# ----------------- 2. KEY PERFORMANCE INDICATORS -----------------
kpi_sql = f"""
    SELECT 
        COUNT(id) AS total_cases,
        COALESCE(SUM(connected_load), 0.0) AS total_load,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'HOOK|BYPASS|CABLE|DIRECT' THEN connected_load ELSE 0.0 END), 0.0) AS load_dt,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'TAMPER|DAE|SEAL|METER' THEN connected_load ELSE 0.0 END), 0.0) AS load_dae,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'MISUSE|TARIFF|SUBMETER' THEN connected_load ELSE 0.0 END), 0.0) AS load_misuse
    FROM load_bookings
    WHERE {where_stmt}
"""
kpi_df = run_aggregate_query(kpi_sql, sql_params)
kpis = kpi_df.iloc[0] if not kpi_df.empty else None

tot_cases = int(kpis['total_cases']) if kpis is not None else 0
tot_load = (kpis['total_load'] * unit_multiplier) if kpis is not None else 0.0
load_dt = (kpis['load_dt'] * unit_multiplier) if kpis is not None else 0.0
load_dae = (kpis['load_dae'] * unit_multiplier) if kpis is not None else 0.0
load_misuse = (kpis['load_misuse'] * unit_multiplier) if kpis is not None else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #38bdf8;">
            <div class="kpi-title">Total Load Booked</div>
            <div class="kpi-value">{tot_load:,.2f} <span style="font-size:0.9rem; color:#38bdf8;">{unit_label}</span></div>
            <div class="kpi-sub">Across all inspected premises</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #818cf8;">
            <div class="kpi-title">Total Cases Booked</div>
            <div class="kpi-value">{tot_cases:,} <span style="font-size:0.9rem; color:#818cf8;">Nos</span></div>
            <div class="kpi-sub">Enforcement inspections</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #f97316;">
            <div class="kpi-title">DT Hooking / Bypass</div>
            <div class="kpi-value">{load_dt:,.2f} <span style="font-size:0.9rem; color:#f97316;">{unit_label}</span></div>
            <div class="kpi-sub">Direct line abstraction</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #eab308;">
            <div class="kpi-title">DAE / Meter Tamper</div>
            <div class="kpi-value">{load_dae:,.2f} <span style="font-size:0.9rem; color:#eab308;">{unit_label}</span></div>
            <div class="kpi-sub">Meter tampering & seals</div>
        </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #ec4899;">
            <div class="kpi-title">Tariff Misuse</div>
            <div class="kpi-value">{load_misuse:,.2f} <span style="font-size:0.9rem; color:#ec4899;">{unit_label}</span></div>
            <div class="kpi-sub">Unauthorized category usage</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# ----------------- 3. TARGET VS ACHIEVEMENT & ENHANCED DONUT CHART -----------------
target_fy_filter = "AND fy = ANY(:fys)" if filters["fys"] else ""

target_vs_achieve_sql = f"""
    WITH achieved AS (
        SELECT 
            COALESCE("{drill_col}", 'Unassigned') AS entity_name,
            COALESCE(SUM(connected_load), 0.0) AS achieved_load
        FROM load_bookings
        WHERE {where_stmt}
        GROUP BY "{drill_col}"
    ),
    target_agg AS (
        SELECT 
            entity_name,
            COALESCE(SUM(target_load_kw), 0.0) AS target_load
        FROM targets
        WHERE entity_level = '{target_level}'
        {target_fy_filter}
        GROUP BY entity_name
    )
    SELECT 
        COALESCE(a.entity_name, t.entity_name) AS entity,
        COALESCE(a.achieved_load, 0.0) AS achieved_kw,
        COALESCE(t.target_load, 0.0) AS target_kw
    FROM achieved a
    FULL OUTER JOIN target_agg t ON a.entity_name = t.entity_name
    WHERE COALESCE(a.entity_name, t.entity_name) IS NOT NULL
    ORDER BY achieved_kw DESC
    LIMIT 20
"""
tva_df = run_aggregate_query(target_vs_achieve_sql, sql_params)

category_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(connected_category), ''), 'DOMESTIC') AS category,
        COALESCE(SUM(connected_load), 0.0) AS load_kw,
        COUNT(id) AS case_count
    FROM load_bookings
    WHERE {where_stmt}
    GROUP BY COALESCE(NULLIF(TRIM(connected_category), ''), 'DOMESTIC')
    ORDER BY load_kw DESC
"""
cat_df = run_aggregate_query(category_sql, sql_params)

col_chart1, col_chart2 = st.columns([1.1, 0.9])

with col_chart1:
    if not tva_df.empty:
        tva_df['achieved_scaled'] = tva_df['achieved_kw'] * unit_multiplier
        tva_df['target_scaled'] = tva_df['target_kw'] * unit_multiplier

        fig_tva = go.Figure(data=[
            go.Bar(
                name=f'Achieved ({unit_label})', 
                x=tva_df['entity'], 
                y=tva_df['achieved_scaled'], 
                marker_color='#0284c7',
                text=tva_df['achieved_scaled'].apply(lambda v: f"{v:,.1f}"),
                textposition='auto'
            ),
            go.Bar(
                name=f'Target ({unit_label})', 
                x=tva_df['entity'], 
                y=tva_df['target_scaled'], 
                marker_color='#ea580c',
                text=tva_df['target_scaled'].apply(lambda v: f"{v:,.1f}"),
                textposition='auto'
            )
        ])
        fig_tva.update_layout(
            barmode='group',
            height=460,
            title=f"<b>Target vs Achievement</b> ({target_level}-wise Comparison)",
            xaxis_title=target_level,
            yaxis_title=f"Booked Load ({unit_label})",
            margin=dict(l=20, r=20, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_tva, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No target vs achievement records found for selected filter criteria.")

with col_chart2:
    if not cat_df.empty:
        cat_df['load_scaled'] = cat_df['load_kw'] * unit_multiplier
        cat_total = cat_df['load_scaled'].sum()

        fig_cat = px.pie(
            cat_df, 
            values="load_scaled", 
            names="category", 
            hole=0.55,
            title="<b>Category-Wise Load Booked</b>",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_cat.update_traces(
            textposition='outside', 
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>Booked Load: %{value:,.2f} " + unit_label + " (%{percent})<extra></extra>",
            marker=dict(line=dict(color='#0f172a', width=2))
        )
        fig_cat.update_layout(
            height=460,
            showlegend=False,
            margin=dict(l=30, r=30, t=50, b=30),
            annotations=[
                dict(
                    text=f"<b>{cat_total:,.1f}</b><br><span style='font-size:11px;color:#94a3b8;'>TOTAL {unit_label}</span>",
                    x=0.5, y=0.5, 
                    font_size=17, 
                    showarrow=False
                )
            ]
        )
        st.plotly_chart(fig_cat, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No category classification records available.")

st.divider()

# ----------------- 4. TOP 10 & BOTTOM 10 PERFORMERS -----------------
top_off_sql = f"""
    SELECT 
        COALESCE(inspected_officer_name, 'Unknown Officer') AS officer,
        COALESCE(SUM(connected_load), 0.0) AS total_load
    FROM load_bookings
    WHERE {where_stmt}
    GROUP BY inspected_officer_name
    ORDER BY total_load DESC
    LIMIT 10
"""
top_off_df = run_aggregate_query(top_off_sql, sql_params)

bottom_off_sql = f"""
    SELECT 
        COALESCE(inspected_officer_name, 'Unknown Officer') AS officer,
        COALESCE(SUM(connected_load), 0.0) AS total_load
    FROM load_bookings
    WHERE {where_stmt} AND inspected_officer_name IS NOT NULL
    GROUP BY inspected_officer_name
    HAVING SUM(connected_load) > 0
    ORDER BY total_load ASC
    LIMIT 10
"""
bottom_off_df = run_aggregate_query(bottom_off_sql, sql_params)

p_col1, p_col2 = st.columns(2)
with p_col1:
    if not top_off_df.empty:
        top_off_df['load_scaled'] = top_off_df['total_load'] * unit_multiplier
        fig_top = px.bar(
            top_off_df, 
            x="load_scaled", 
            y="officer", 
            orientation="h",
            title="🏆 <b>Top 10 Inspecting Officers by Booked Load</b>",
            labels={"load_scaled": f"Booked Load ({unit_label})", "officer": "Inspecting Officer"},
            color_discrete_sequence=['#10b981'],
            text=top_off_df['load_scaled'].apply(lambda v: f"{v:,.1f}")
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        fig_top.update_traces(textposition='outside')
        st.plotly_chart(fig_top, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

with p_col2:
    if not bottom_off_df.empty:
        bottom_off_df['load_scaled'] = bottom_off_df['total_load'] * unit_multiplier
        fig_bot = px.bar(
            bottom_off_df, 
            x="load_scaled", 
            y="officer", 
            orientation="h",
            title="⚠️ <b>Bottom 10 Performing Officers (Load > 0)</b>",
            labels={"load_scaled": f"Booked Load ({unit_label})", "officer": "Inspecting Officer"},
            color_discrete_sequence=['#ef4444'],
            text=bottom_off_df['load_scaled'].apply(lambda v: f"{v:,.1f}")
        )
        fig_bot.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        fig_bot.update_traces(textposition='outside')
        st.plotly_chart(fig_bot, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

st.divider()

# ----------------- 5. MULTI-LINE TIME TREND PROGRESSION -----------------
trend_sql = f"""
    SELECT 
        fy, 
        TRIM(month) AS month, 
        COALESCE(SUM(connected_load), 0.0) AS total_load
    FROM load_bookings
    WHERE {where_stmt} AND fy IS NOT NULL AND month IS NOT NULL
    GROUP BY fy, TRIM(month)
"""
trend_df = run_aggregate_query(trend_sql, sql_params)
if not trend_df.empty:
    trend_df['month_idx'] = trend_df['month'].apply(lambda m: FY_MONTHS.index(m) if m in FY_MONTHS else 99)
    trend_df = trend_df[trend_df['month_idx'] != 99].sort_values(['fy', 'month_idx'])
    trend_df['load_scaled'] = trend_df['total_load'] * unit_multiplier

    fig_trend = px.line(
        trend_df, 
        x="month", 
        y="load_scaled", 
        color="fy", 
        markers=True,
        title=f"📈 <b>Time-Wise Progress: Multi-FY Comparison</b> (Apr - Mar Sequence)",
        labels={"month": "Month", "load_scaled": f"Booked Load ({unit_label})", "fy": "Financial Year"}
    )
    fig_trend.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20))
    fig_trend.update_traces(line=dict(width=3), marker=dict(size=7))
    st.plotly_chart(fig_trend, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

st.divider()

# ----------------- 6. HIERARCHICAL DRILLDOWN CHART -----------------
st.subheader("🎇 Breakdown Comparison")

# Radio switch to toggle the view level
hierarchy_selection = st.radio(
    "Select Aggregation Level:",
    options=["Division", "Sub-Division", "Section"],
    horizontal=True,
    index=0
)

# Map human-readable option to table column name
level_col_map = {
    "Division": "division",
    "Sub-Division": "sub_division",
    "Section": "section"
}
selected_col = level_col_map[hierarchy_selection]

hierarchy_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM("{selected_col}"), ''), 'Unassigned') AS entity_name,
        COALESCE(SUM(connected_load), 0.0) AS total_load,
        COUNT(id) AS total_cases
    FROM load_bookings
    WHERE {where_stmt}
    GROUP BY "{selected_col}"
    ORDER BY total_load DESC
"""

hier_df = run_aggregate_query(hierarchy_sql, sql_params)

if not hier_df.empty:
    hier_df['load_scaled'] = hier_df['total_load'] * unit_multiplier

    fig_hier = px.bar(
        hier_df,
        x="entity_name",
        y="load_scaled",
        title=f"<b>{hierarchy_selection}-Wise Booked Load & Cases</b>",
        labels={
            "entity_name": hierarchy_selection,
            "load_scaled": f"Booked Load ({unit_label})"
        },
        hover_data={"total_cases": ":,"},
        color="load_scaled",
        color_continuous_scale="Blues",
        text=hier_df['load_scaled'].apply(lambda v: f"{v:,.1f}")
    )
    
    fig_hier.update_traces(
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Booked Load: %{y:,.2f} " + unit_label + "<br>Cases: %{customdata[0]:,}<extra></extra>"
    )
    
    fig_hier.update_layout(
        height=480,
        coloraxis_showscale=False,
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=50, b=80)
    )
    
    st.plotly_chart(fig_hier, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
else:
    st.info(f"No records available for the selected {hierarchy_selection} view.")