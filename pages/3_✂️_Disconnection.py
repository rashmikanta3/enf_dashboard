import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from utils.db_utils import run_aggregate_query
from utils.data_utils import FY_MONTHS, format_inr
from utils.filter_utils import render_sidebar_filters

# Force wide layout and responsive container margins
st.set_page_config(page_title="Disconnection Performance", page_icon="✂️", layout="wide")

# Modern CSS for KPI cards matching Load Booking & Collection
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
        'filename': 'disconnection_snapshot',
        'height': 720,
        'width': 1280,
        'scale': 3
    }
}

st.title("✂️ Disconnection (DC) Monitoring Dashboard")

# 1. Sidebar Filters
where_stmt, sql_params, filters = render_sidebar_filters("disconnections")

if filters["circle"] == "ALL":
    drill_col, target_level = "circle", "Circle"
elif filters["division"] == "ALL":
    drill_col, target_level = "division", "Division"
elif filters["sub_division"] == "ALL":
    drill_col, target_level = "sub_division", "Sub-Division"
else:
    drill_col, target_level = "section", "Section"

# 2. Modern KPI Cards
dc_kpi_sql = f"""
    SELECT 
        COUNT(id) AS total_dc,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt,
        COUNT(CASE WHEN UPPER(COALESCE(dc_type, '')) = 'TEMPORARY' THEN 1 END) AS temp_dc,
        COUNT(CASE WHEN UPPER(COALESCE(dc_type, '')) = 'PERMANENT' THEN 1 END) AS perm_dc
    FROM disconnections
    WHERE {where_stmt}
"""
dc_kpi = run_aggregate_query(dc_kpi_sql, sql_params)
kpis = dc_kpi.iloc[0] if not dc_kpi.empty else None

tot_dc = int(kpis['total_dc']) if kpis is not None else 0
tot_dc_amt = float(kpis['total_amt']) if kpis is not None else 0.0
temp_dc = int(kpis['temp_dc']) if kpis is not None else 0
perm_dc = int(kpis['perm_dc']) if kpis is not None else 0
avg_dc = (tot_dc_amt / tot_dc) if tot_dc > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #ef4444;">
            <div class="kpi-title">Total Disconnections</div>
            <div class="kpi-value">{tot_dc:,} <span style="font-size:0.85rem; color:#ef4444;">Nos</span></div>
            <div class="kpi-sub">Total executed disconnections</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #f97316;">
            <div class="kpi-title">Outstanding Dues</div>
            <div class="kpi-value">{format_inr(tot_dc_amt)}</div>
            <div class="kpi-sub">Avg: {format_inr(avg_dc)}/DC</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #38bdf8;">
            <div class="kpi-title">Temporary DC</div>
            <div class="kpi-value">{temp_dc:,} <span style="font-size:0.85rem; color:#38bdf8;">Nos</span></div>
            <div class="kpi-sub">Eligible for reconnection</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #a855f7;">
            <div class="kpi-title">Permanent DC</div>
            <div class="kpi-value">{perm_dc:,} <span style="font-size:0.85rem; color:#a855f7;">Nos</span></div>
            <div class="kpi-sub">Final service cut-offs</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# 3. Target vs Achievement & DC Type Breakdown
target_fy_filter = "AND fy = ANY(:fys)" if filters["fys"] else ""

dc_tva_sql = f"""
    WITH achieved AS (
        SELECT 
            COALESCE("{drill_col}", 'Unassigned') AS entity_name,
            COUNT(id) AS achieved_count
        FROM disconnections
        WHERE {where_stmt}
        GROUP BY "{drill_col}"
    ),
    target_agg AS (
        SELECT 
            entity_name,
            COALESCE(SUM(target_dc_count), 0) AS target_count
        FROM targets
        WHERE entity_level = '{target_level}'
        {target_fy_filter}
        GROUP BY entity_name
    )
    SELECT 
        COALESCE(a.entity_name, t.entity_name) AS entity,
        COALESCE(a.achieved_count, 0) AS achieved,
        COALESCE(t.target_count, 0) AS target
    FROM achieved a
    FULL OUTER JOIN target_agg t ON a.entity_name = t.entity_name
    WHERE COALESCE(a.entity_name, t.entity_name) IS NOT NULL
    ORDER BY achieved DESC
    LIMIT 20
"""
dc_tva_df = run_aggregate_query(dc_tva_sql, sql_params)

type_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(dc_type), ''), 'Unspecified') AS dc_type,
        COUNT(id) AS total_count,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt}
    GROUP BY COALESCE(NULLIF(TRIM(dc_type), ''), 'Unspecified')
    ORDER BY total_count DESC
"""
type_df = run_aggregate_query(type_sql, sql_params)

col_chart1, col_chart2 = st.columns([1.1, 0.9])
with col_chart1:
    if not dc_tva_df.empty:
        fig_dc_tva = go.Figure(data=[
            go.Bar(
                name='Executed DC', 
                x=dc_tva_df['entity'], 
                y=dc_tva_df['achieved'], 
                marker_color='#dc2626',
                text=dc_tva_df['achieved'].apply(lambda v: f"{v:,}"),
                textposition='auto'
            ),
            go.Bar(
                name='Target DC', 
                x=dc_tva_df['entity'], 
                y=dc_tva_df['target'], 
                marker_color='#ea580c',
                text=dc_tva_df['target'].apply(lambda v: f"{v:,}"),
                textposition='auto'
            )
        ])
        fig_dc_tva.update_layout(
            barmode='group',
            height=460,
            title=f"<b>Disconnection Target vs Achievement</b> ({target_level}-wise)",
            xaxis_title=target_level,
            yaxis_title="Count of DCs",
            margin=dict(l=20, r=20, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_dc_tva, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No disconnection target data found for current filters.")

with col_chart2:
    if not type_df.empty:
        type_df['amt_label'] = type_df['total_amt'].apply(format_inr)
        fig_type = px.pie(
            type_df,
            values="total_count",
            names="dc_type",
            hole=0.55,
            title="<b>DC Type Breakdown (Temp vs Perm)</b>",
            color_discrete_sequence=['#ef4444', '#38bdf8', '#a855f7']
        )
        fig_type.update_traces(
            textposition='outside',
            textinfo='percent+label',
            customdata=type_df['amt_label'],
            hovertemplate="<b>%{label}</b><br>Count: %{value:,} (%{percent})<br>Outstanding: %{customdata}<extra></extra>",
            marker=dict(line=dict(color='#0f172a', width=2))
        )
        fig_type.update_layout(
            height=460,
            showlegend=False,
            margin=dict(l=30, r=30, t=50, b=30),
            annotations=[
                dict(
                    text=f"<b>{tot_dc:,}</b><br><span style='font-size:11px;color:#94a3b8;'>TOTAL DCS</span>",
                    x=0.5, y=0.5,
                    font_size=16,
                    showarrow=False
                )
            ]
        )
        st.plotly_chart(fig_type, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)
    else:
        st.info("No DC type records available.")

st.divider()

# 4. Radio Switch for Division, Sub-Division, and Section Breakdown
st.subheader("📊 Hierarchy-Wise Disconnection Breakdown")

hierarchy_selection = st.radio(
    "Select Aggregation Level:",
    options=["Division", "Sub-Division", "Section"],
    horizontal=True,
    index=0
)

level_col_map = {
    "Division": "division",
    "Sub-Division": "sub_division",
    "Section": "section"
}
selected_col = level_col_map[hierarchy_selection]

hier_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM("{selected_col}"), ''), 'Unassigned') AS entity_name,
        COUNT(id) AS total_dcs,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt}
    GROUP BY "{selected_col}"
    ORDER BY total_dcs DESC
"""
hier_df = run_aggregate_query(hier_sql, sql_params)

if not hier_df.empty:
    hier_df['amt_label'] = hier_df['total_amt'].apply(format_inr)

    fig_hier = px.bar(
        hier_df,
        x="entity_name",
        y="total_dcs",
        title=f"<b>{hierarchy_selection}-Wise Disconnections & Outstanding Dues</b>",
        labels={
            "entity_name": hierarchy_selection,
            "total_dcs": "Total Disconnections"
        },
        color="total_dcs",
        color_continuous_scale="Reds",
        custom_data=["amt_label"],
        text=hier_df['total_dcs'].apply(lambda v: f"{v:,}")
    )
    fig_hier.update_traces(
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Disconnections: %{y:,}<br>Outstanding Dues: %{customdata[0]}<extra></extra>"
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

# 5. Team-Wise DC Report (Supervising Officer / Squad)
team_sql = f"""
    SELECT 
        COALESCE(NULLIF(TRIM(supervising_officer), ''), 'Unassigned Squad') AS team,
        COUNT(id) AS total_dcs,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt}
    GROUP BY COALESCE(NULLIF(TRIM(supervising_officer), ''), 'Unassigned Squad')
    ORDER BY total_dcs DESC
"""
team_df = run_aggregate_query(team_sql, sql_params)

if not team_df.empty:
    team_df['amt_label'] = team_df['total_amt'].apply(format_inr)

    fig_team = px.bar(
        team_df,
        x="team",
        y="total_dcs",
        title="👥 <b>Team / Supervising Officer DC Performance</b>",
        labels={"team": "Team / Supervising Officer", "total_dcs": "Disconnections Executed"},
        color="total_dcs",
        color_continuous_scale="Oranges",
        custom_data=["amt_label"],
        text=team_df['total_dcs'].apply(lambda v: f"{v:,}")
    )
    fig_team.update_traces(
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>Disconnections: %{y:,}<br>Outstanding Dues: %{customdata[0]}<extra></extra>"
    )
    fig_team.update_layout(
        height=450,
        coloraxis_showscale=False,
        xaxis_tickangle=-30,
        margin=dict(l=20, r=20, t=50, b=70)
    )
    st.plotly_chart(fig_team, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

st.divider()

# 6. Officers & Linemen Performance (Top 10 & Bottom 5)
top_off_sql = f"""
    SELECT 
        COALESCE(lineman_name, supervising_officer, 'Unknown Lineman') AS officer,
        COUNT(id) AS total_dcs,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt}
    GROUP BY COALESCE(lineman_name, supervising_officer, 'Unknown Lineman')
    ORDER BY total_dcs DESC
    LIMIT 10
"""
top_off_df = run_aggregate_query(top_off_sql, sql_params)

bot_off_sql = f"""
    SELECT 
        COALESCE(lineman_name, supervising_officer, 'Unknown Lineman') AS officer,
        COUNT(id) AS total_dcs,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt} AND COALESCE(lineman_name, supervising_officer) IS NOT NULL
    GROUP BY COALESCE(lineman_name, supervising_officer, 'Unknown Lineman')
    HAVING COUNT(id) > 0
    ORDER BY total_dcs ASC
    LIMIT 5
"""
bot_off_df = run_aggregate_query(bot_off_sql, sql_params)

p_col1, p_col2 = st.columns(2)
with p_col1:
    if not top_off_df.empty:
        top_off_df['amt_label'] = top_off_df['total_amt'].apply(format_inr)
        fig_top = px.bar(
            top_off_df,
            x="total_dcs",
            y="officer",
            orientation="h",
            title="🏆 <b>Top 10 Executing Linemen / Officers</b>",
            labels={"total_dcs": "Total Disconnections", "officer": "Lineman / Officer"},
            color_discrete_sequence=['#ef4444'],
            custom_data=["amt_label"],
            text=top_off_df['total_dcs'].apply(lambda v: f"{v:,}")
        )
        fig_top.update_traces(
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>Disconnections: %{x:,}<br>Outstanding: %{customdata[0]}<extra></extra>"
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_top, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

with p_col2:
    if not bot_off_df.empty:
        bot_off_df['amt_label'] = bot_off_df['total_amt'].apply(format_inr)
        fig_bot = px.bar(
            bot_off_df,
            x="total_dcs",
            y="officer",
            orientation="h",
            title="⚠️ <b>Bottom 5 Executing Linemen (DC > 0)</b>",
            labels={"total_dcs": "Total Disconnections", "officer": "Lineman / Officer"},
            color_discrete_sequence=['#f97316'],
            custom_data=["amt_label"],
            text=bot_off_df['total_dcs'].apply(lambda v: f"{v:,}")
        )
        fig_bot.update_traces(
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>Disconnections: %{x:,}<br>Outstanding: %{customdata[0]}<extra></extra>"
        )
        fig_bot.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_bot, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)

st.divider()

# 7. Multi-Line Time Trend Progression
trend_sql = f"""
    SELECT 
        fy, 
        TRIM(month) AS month, 
        COUNT(id) AS total_dcs,
        COALESCE(SUM(outstanding_amount), 0.0) AS total_amt
    FROM disconnections
    WHERE {where_stmt} AND fy IS NOT NULL AND month IS NOT NULL
    GROUP BY fy, TRIM(month)
"""
trend_df = run_aggregate_query(trend_sql, sql_params)
if not trend_df.empty:
    trend_df['month_idx'] = trend_df['month'].apply(lambda m: FY_MONTHS.index(m) if m in FY_MONTHS else 99)
    trend_df = trend_df[trend_df['month_idx'] != 99].sort_values(['fy', 'month_idx'])
    trend_df['amt_label'] = trend_df['total_amt'].apply(format_inr)

    fig_trend = px.line(
        trend_df,
        x="month",
        y="total_dcs",
        color="fy",
        markers=True,
        title="📈 <b>Time-Wise Disconnections: Multi-FY Progression</b> (Apr - Mar)",
        labels={"month": "Month", "total_dcs": "Disconnections Count", "fy": "Financial Year"},
        custom_data=["amt_label"]
    )
    fig_trend.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate="Month: %{x}<br>Disconnections: %{y:,}<br>Outstanding: %{customdata[0]}<extra></extra>"
    )
    fig_trend.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_trend, use_container_width=True, config=PLOTLY_SNAPSHOT_CONFIG)