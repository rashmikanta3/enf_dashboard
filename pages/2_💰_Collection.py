import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from utils.db_utils import run_aggregate_query
from utils.data_utils import FY_MONTHS, format_inr
from utils.filter_utils import render_sidebar_filters

# Force wide layout and responsive container margins
st.set_page_config(page_title="Penal Collection Performance", page_icon="💰", layout="wide")

# Modern CSS for KPI cards matching Load Booking style
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

PLOTLY_SNAPSHOT_CONFIG = {
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'collection_snapshot',
        'height': 720,
        'width': 1280,
        'scale': 3
    }
}

st.title("💰 Penal Collection Performance Dashboard")

# 1. Unified sidebar filters
where_stmt, sql_params, filters = render_sidebar_filters(
    "collections", 
    div_col_name="div", 
    sub_div_col_name="sub_div"
)

# Determine dynamic drill-down hierarchy level
if filters["circle"] == "ALL":
    drill_col, target_level = "circle", "Circle"
elif filters["division"] == "ALL":
    drill_col, target_level = "div", "Division"
elif filters["sub_division"] == "ALL":
    drill_col, target_level = "sub_div", "Sub-Division"
else:
    drill_col, target_level = "section", "Section"

# 2. Key Performance Indicators with breakdown
kpi_sql = f"""
    SELECT 
        COUNT(id) AS number_of_mr,
        COALESCE(SUM(amount_paid), 0.0) AS total_collected,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'HOOK|BYPASS|CABLE|DIRECT' THEN amount_paid ELSE 0.0 END), 0.0) AS coll_dt,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'TAMPER|DAE|SEAL|METER' THEN amount_paid ELSE 0.0 END), 0.0) AS coll_dae,
        COALESCE(SUM(CASE WHEN UPPER(COALESCE(defect_name, '')) ~ 'MISUSE|TARIFF|SUBMETER' THEN amount_paid ELSE 0.0 END), 0.0) AS coll_misuse
    FROM collections
    WHERE {where_stmt}
"""
kpi_df = run_aggregate_query(kpi_sql, sql_params)
kpis = kpi_df.iloc[0] if not kpi_df.empty else None

tot_mr = int(kpis['number_of_mr']) if kpis is not None else 0
tot_amt = float(kpis['total_collected']) if kpis is not None else 0.0
avg_mr = (tot_amt / tot_mr) if tot_mr > 0 else 0.0
coll_dt = float(kpis['coll_dt']) if kpis is not None else 0.0
coll_dae = float(kpis['coll_dae']) if kpis is not None else 0.0
coll_misuse = float(kpis['coll_misuse']) if kpis is not None else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #38bdf8;">
            <div class="kpi-title">Total Collected</div>
            <div class="kpi-value">{format_inr(tot_amt)}</div>
            <div class="kpi-sub">Total penal collection</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #818cf8;">
            <div class="kpi-title">Money Receipts</div>
            <div class="kpi-value">{tot_mr:,} <span style="font-size:0.85rem; color:#818cf8;">MRs</span></div>
            <div class="kpi-sub">Avg: {format_inr(avg_mr)}/MR</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #f97316;">
            <div class="kpi-title">DT Hooking / Bypass</div>
            <div class="kpi-value">{format_inr(coll_dt)}</div>
            <div class="kpi-sub">Direct line recovery</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #eab308;">
            <div class="kpi-title">DAE / Meter Tamper</div>
            <div class="kpi-value">{format_inr(coll_dae)}</div>
            <div class="kpi-sub">Tamper & seal penalties</div>
        </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #ec4899;">
            <div class="kpi-title">Tariff Misuse</div>
            <div class="kpi-value">{format_inr(coll_misuse)}</div>
            <div class="kpi-sub">Category regularization</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# 3. Target vs Achievement & Defect-Wise Collection Pie Chart
target_fy_filter = "AND fy = ANY(:fys)" if filters["fys"] else ""

col_tva_sql = f"""
    WITH achieved AS (
        SELECT 
            COALESCE("{drill_col}", 'Unassigned') AS entity_name,
            COALESCE(SUM(amount_paid), 0.0) AS achieved_amt
        FROM collections
        WHERE {where_stmt}
        GROUP BY "{drill_col}"
    ),
    target_agg AS (
        SELECT 
            entity_name,
            COALESCE(SUM(target_collection_amount), 0.0) AS target_amt
        FROM targets
        WHERE entity_level = '{target_level}'
        {target_fy_filter}
        GROUP BY entity_name
    )
    SELECT 
        COALESCE(a.entity_name, t.entity_name) AS entity,
        COALESCE(a.achieved_amt, 0.0) AS achieved,
        COALESCE(t.target_amt, 0.0) AS target
    FROM achieved a
    FULL OUTER JOIN target_agg t ON a.entity_name = t.entity_name
    WHERE COALESCE(a.entity_name, t.entity_name) IS NOT NULL
    ORDER BY achieved DESC
    LIMIT 20
"""
col_tva_df = run_aggregate_query(col_tva_sql, sql_params)

defect_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(defect_name), ''), 'Other / Unspecified') AS defect,
        COALESCE(SUM(amount_paid), 0.0) AS amount,
        COUNT(id) AS mr_count
    FROM collections
    WHERE {where_stmt}
    GROUP BY COALESCE(NULLIF(TRIM(defect_name), ''), 'Other / Unspecified')
    ORDER BY amount DESC
"""
defect_df = run_aggregate_query(defect_sql, sql_params)

col1, col2 = st.columns([1.1, 0.9])
with col1:
    if not col_tva_df.empty:
        col_tva_df['achieved_lakh'] = col_tva_df['achieved'] / 100_000
        col_tva_df['target_lakh'] = col_tva_df['target'] / 100_000
        col_tva_df['achieved_label'] = col_tva_df['achieved'].apply(format_inr)
        col_tva_df['target_label'] = col_tva_df['target'].apply(format_inr)

        fig_col_tva = go.Figure(data=[
            go.Bar(
                name='Collected',
                x=col_tva_df['entity'],
                y=col_tva_df['achieved_lakh'],
                customdata=col_tva_df['achieved_label'],
                hovertemplate="<b>%{x}</b><br>Collected: %{customdata}<extra></extra>",
                marker_color='#0284c7'
            ),
            go.Bar(
                name='Target',
                x=col_tva_df['entity'],
                y=col_tva_df['target_lakh'],
                customdata=col_tva_df['target_label'],
                hovertemplate="<b>%{x}</b><br>Target: %{customdata}<extra></extra>",
                marker_color='#ea580c'
            )
        ])
        fig_col_tva.update_layout(
            barmode='group',
            height=460,
            title=f"<b>Collection Target vs Achievement</b> ({target_level}-wise)",
            xaxis_title=target_level,
            yaxis_title="Amount (₹ in Lakhs)",
            margin=dict(l=20, r=20, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_col_tva, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No collection target data found for current filters.")

with col2:
    if not defect_df.empty:
        defect_df['amount_lakh'] = defect_df['amount'] / 100_000
        defect_df['amount_label'] = defect_df['amount'].apply(format_inr)

        fig_defect = px.pie(
            defect_df,
            values="amount",
            names="defect",
            hole=0.55,
            title="<b>Defect-Wise Collection Distribution</b>",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_defect.update_traces(
            textposition='outside',
            textinfo='percent+label',
            customdata=defect_df['amount_label'],
            hovertemplate="<b>%{label}</b><br>Collected: %{customdata} (%{percent})<extra></extra>",
            marker=dict(line=dict(color='#0f172a', width=2))
        )
        fig_defect.update_layout(
            height=460,
            showlegend=False,
            margin=dict(l=30, r=30, t=50, b=30),
            annotations=[
                dict(
                    text=f"<b>{format_inr(tot_amt)}</b><br><span style='font-size:11px;color:#94a3b8;'>TOTAL COLLECTION</span>",
                    x=0.5, y=0.5,
                    font_size=15,
                    showarrow=False
                )
            ]
        )
        st.plotly_chart(fig_defect, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No defect collection records available.")

st.divider()

# 4. Radio Toggle for Division, Sub-Division, and Section Breakdown
st.subheader("📊 Hierarchy-Wise Collection Breakdown")

hierarchy_selection = st.radio(
    "Select Aggregation Level:",
    options=["Division", "Sub-Division", "Section"],
    horizontal=True,
    index=0
)

level_col_map = {
    "Division": "div",
    "Sub-Division": "sub_div",
    "Section": "section"
}
selected_col = level_col_map[hierarchy_selection]

hier_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM("{selected_col}"), ''), 'Unassigned') AS entity_name,
        COALESCE(SUM(amount_paid), 0.0) AS total_collected,
        COUNT(id) AS total_mr
    FROM collections
    WHERE {where_stmt}
    GROUP BY "{selected_col}"
    ORDER BY total_collected DESC
"""
hier_df = run_aggregate_query(hier_sql, sql_params)

if not hier_df.empty:
    hier_df['amount_lakh'] = hier_df['total_collected'] / 100_000
    hier_df['amount_label'] = hier_df['total_collected'].apply(format_inr)

    fig_hier = px.bar(
        hier_df,
        x="entity_name",
        y="amount_lakh",
        title=f"<b>{hierarchy_selection}-Wise Collection & Receipts</b>",
        labels={
            "entity_name": hierarchy_selection,
            "amount_lakh": "Amount (₹ in Lakhs)"
        },
        color="amount_lakh",
        color_continuous_scale="Teal",
        custom_data=["amount_label", "total_mr"]
    )
    fig_hier.update_traces(
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Amount: %{customdata[0]}<br>MRs: %{customdata[1]:,}<extra></extra>"
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

st.divider()

# 5. Team-Wise Collection Report
# ----------------- 5. COLLECTOR / TEAM-WISE COLLECTION REPORT -----------------
team_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(amount_collected_b), ''), 'Unassigned') AS team,
        COALESCE(SUM(amount_paid), 0.0) AS total_collected,
        COUNT(id) AS mr_count
    FROM collections
    WHERE {where_stmt}
    GROUP BY COALESCE(NULLIF(TRIM(amount_collected_b), ''), 'Unassigned')
    ORDER BY total_collected DESC
"""
team_df = run_aggregate_query(team_sql, sql_params)

if not team_df.empty:
    team_df['amount_lakh'] = team_df['total_collected'] / 100_000
    team_df['amount_label'] = team_df['total_collected'].apply(format_inr)

    fig_team = px.bar(
        team_df,
        x="team",
        y="amount_lakh",
        title="👥 <b>Collection Performance by Collector (amount_collected_b)</b>",
        labels={"team": "Collector / Team", "amount_lakh": "Amount (₹ in Lakhs)"},
        color="amount_lakh",
        color_continuous_scale="Purples",
        custom_data=["amount_label", "mr_count"]
    )
    fig_team.update_traces(
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Collected: %{customdata[0]}<br>Total MRs: %{customdata[1]:,}<extra></extra>"
    )
    fig_team.update_layout(
        height=450,
        coloraxis_showscale=False,
        xaxis_tickangle=-30,
        margin=dict(l=20, r=20, t=50, b=70)
    )
    st.plotly_chart(fig_team, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

# 6. Top 10 & Bottom 5 Collecting Officers
top_col_sql = f"""
    SELECT 
        COALESCE(amount_collected_b, inspected_officer_name, 'Official Collector') AS collector,
        COALESCE(SUM(amount_paid), 0.0) AS amount
    FROM collections
    WHERE {where_stmt}
    GROUP BY COALESCE(amount_collected_b, inspected_officer_name, 'Official Collector')
    ORDER BY amount DESC
    LIMIT 10
"""
top_col_df = run_aggregate_query(top_col_sql, sql_params)

bottom_col_sql = f"""
    SELECT 
        COALESCE(amount_collected_b, inspected_officer_name, 'Official Collector') AS collector,
        COALESCE(SUM(amount_paid), 0.0) AS amount
    FROM collections
    WHERE {where_stmt} 
      AND COALESCE(amount_collected_b, inspected_officer_name) IS NOT NULL
    GROUP BY COALESCE(amount_collected_b, inspected_officer_name, 'Official Collector')
    HAVING SUM(amount_paid) > 0
    ORDER BY amount ASC
    LIMIT 5
"""
bottom_col_df = run_aggregate_query(bottom_col_sql, sql_params)

p_col1, p_col2 = st.columns(2)
with p_col1:
    if not top_col_df.empty:
        top_col_df['amount_lakh'] = top_col_df['amount'] / 100_000
        top_col_df['amount_formatted'] = top_col_df['amount'].apply(format_inr)

        fig_top = px.bar(
            top_col_df,
            x="amount_lakh",
            y="collector",
            orientation="h",
            title="🏆 <b>Top 10 Collecting Officers</b>",
            labels={"amount_lakh": "Amount (₹ in Lakhs)", "collector": "Collector"},
            color_discrete_sequence=['#10b981'],
            custom_data=["amount_formatted"]
        )
        fig_top.update_traces(
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>Collected: %{customdata[0]}<extra></extra>"
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_top, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

with p_col2:
    if not bottom_col_df.empty:
        bottom_col_df['amount_lakh'] = bottom_col_df['amount'] / 100_000
        bottom_col_df['amount_formatted'] = bottom_col_df['amount'].apply(format_inr)

        fig_bot = px.bar(
            bottom_col_df,
            x="amount_lakh",
            y="collector",
            orientation="h",
            title="⚠️ <b>Bottom 5 Collecting Officers (Amount > 0)</b>",
            labels={"amount_lakh": "Amount (₹ in Lakhs)", "collector": "Collector"},
            color_discrete_sequence=['#ef4444'],
            custom_data=["amount_formatted"]
        )
        fig_bot.update_traces(
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>Collected: %{customdata[0]}<extra></extra>"
        )
        fig_bot.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_bot, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

st.divider()

# 7. Multi-Line Time Trend Progression
trend_sql = f"""
    SELECT 
        fy, 
        TRIM(month) AS month, 
        COALESCE(SUM(amount_paid), 0.0) AS total_collected
    FROM collections
    WHERE {where_stmt} AND fy IS NOT NULL AND month IS NOT NULL
    GROUP BY fy, TRIM(month)
"""
trend_df = run_aggregate_query(trend_sql, sql_params)
if not trend_df.empty:
    trend_df['month_idx'] = trend_df['month'].apply(lambda m: FY_MONTHS.index(m) if m in FY_MONTHS else 99)
    trend_df = trend_df[trend_df['month_idx'] != 99].sort_values(['fy', 'month_idx'])

    trend_df['total_collected_lakh'] = trend_df['total_collected'] / 100_000
    trend_df['amount_formatted'] = trend_df['total_collected'].apply(format_inr)

    fig_trend = px.line(
        trend_df,
        x="month",
        y="total_collected_lakh",
        color="fy",
        markers=True,
        title="📈 <b>Time-Wise Collection: Multi-FY Progression</b> (Apr - Mar)",
        labels={"month": "Month", "total_collected_lakh": "Collected (₹ in Lakhs)", "fy": "Financial Year"},
        custom_data=["amount_formatted"]
    )
    fig_trend.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate="Month: %{x}<br>Collection: %{customdata[0]}<extra></extra>"
    )
    fig_trend.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_trend, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)