# ==============================================================================
# Core Engine: Data Visualization
#
# Author: Principal Engineer SME & Data Rendering Expert
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module is the centralized plotting engine for the VERITAS application.
# It is designed to create insightful, context-rich, and aesthetically pleasing
# visualizations that are not just informative but also guide the user to
# actionable conclusions.
#
# Architectural Principle:
# All plotting functions are decoupled from the Streamlit UI, taking clean
# DataFrames and parameters as input and returning Plotly Figure objects.
# They are built on a consistent, centrally managed theme.
# ==============================================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
import graphviz
from typing import Dict, List, Tuple

# Import the centralized settings for colors and configurations
from .. import settings

# --- Universal Helper ---
def create_empty_figure(message: str) -> go.Figure:
    """Creates a standardized empty figure with a message."""
    fig = go.Figure()
    fig.update_layout(
        xaxis={'visible': False}, yaxis={'visible': False},
        annotations=[{'text': message, 'xref': 'paper', 'yref': 'paper', 'showarrow': False, 'font': {'size': 16}}]
    )
    return fig

# --- Homepage & Strategic Plots ---
def plot_program_risk_matrix(df: pd.DataFrame) -> go.Figure:
    """Creates a strategic 2x2 risk matrix bubble chart for all programs."""
    if df.empty: return create_empty_figure("No program risk data available.")
    
    fig = px.scatter(
        df, x="days_to_milestone", y="dqs", size="active_deviations",
        color="risk_quadrant", text="program_id",
        hover_name="program_id",
        hover_data={"days_to_milestone": True, "dqs": ':.1f', "active_deviations": True, "risk_quadrant": False},
        color_discrete_map={
            "On Track": settings.COLORS.green, "Data Risk": settings.COLORS.orange,
            "Schedule Risk": settings.COLORS.lightblue, "High Priority": settings.COLORS.red
        },
        size_max=50
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(
        title="<b>Program Risk Matrix</b>",
        xaxis_title="Days to Next Milestone", yaxis_title="Data Quality Score (%)",
        xaxis=dict(autorange="reversed"),
        legend_title="Risk Quadrant",
    )
    return fig

def plot_pareto_chart(df: pd.DataFrame) -> go.Figure:
    """Creates a Pareto chart from a frequency DataFrame."""
    if df.empty: return create_empty_figure("Invalid data for Pareto chart.")
    df_sorted = df.sort_values(by='Frequency', ascending=False)
    df_sorted['cumulative_percentage'] = df_sorted['Frequency'].cumsum() / df_sorted['Frequency'].sum() * 100
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_sorted['Error Type'], y=df_sorted['Frequency'], name='Count', marker_color=settings.COLORS.orange))
    fig.add_trace(go.Scatter(x=df_sorted['Error Type'], y=df_sorted['cumulative_percentage'], name='Cumulative %', yaxis='y2', mode='lines+markers', line=dict(color=settings.COLORS.blue)))
    fig.update_layout(title='<b>Pareto Analysis of QC Failure Hotspots</b>', yaxis2=dict(overlaying='y', side='right', range=[0, 105]))
    return fig

# --- Statistical & QC Plots ---
def plot_historical_control_chart(df: pd.DataFrame, cqa: str, events_df: pd.DataFrame) -> go.Figure:
    """Creates a historical I-Chart with an overlay of deviation events."""
    if len(df) < 2: return create_empty_figure(f"Not enough data for {cqa}.")
    mean, std_dev = df[cqa].mean(), df[cqa].std()
    ucl, lcl = mean + 3 * std_dev, mean - 3 * std_dev

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['injection_time'], y=df[cqa], mode='lines+markers', name=cqa))
    fig.add_hline(y=mean, line_dash="dash", line_color=settings.COLORS.green, annotation_text="Mean")
    fig.add_hline(y=ucl, line_dash="dot", line_color=settings.COLORS.red, annotation_text="UCL (3σ)")
    fig.add_hline(y=lcl, line_dash="dot", line_color=settings.COLORS.red, annotation_text="LCL (3σ)")
    
    # Ultimate Feature: Overlay critical events for context
    for _, event in events_df.iterrows():
        if 'instrument' in event['title'].lower() and event['linked_record'] in df['instrument_id'].unique():
             fig.add_vline(x=df['injection_time'].median(), line_dash="longdash", line_color=settings.COLORS.gray, annotation_text=f"Event: {event['id']}")

    fig.update_layout(title=f"<b>Control Chart (I-Chart) for {cqa}</b>", xaxis_title="Date", yaxis_title="Value", showlegend=False, height=450)
    return fig

def plot_process_capability(df: pd.DataFrame, cqa: str, lsl: float, usl: float, cpk: float, cpk_target: float) -> go.Figure:
    """Displays a process capability histogram."""
    if cqa not in df.columns or df[cqa].dropna().empty: return create_empty_figure(f"No data for {cqa}.")
    
    title_color = settings.COLORS.green if cpk >= cpk_target else settings.COLORS.red
    fig = px.histogram(df, x=cqa, nbins=40, title=f"<b>Process Capability for {cqa} | Cpk: {cpk:.2f}</b>")
    if lsl is not None: fig.add_vline(x=lsl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="LSL")
    if usl is not None: fig.add_vline(x=usl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="USL")
    fig.add_vline(x=df[cqa].mean(), line_dash="dash", line_color=settings.COLORS.green, annotation_text="Mean")
    fig.update_layout(title_font_color=title_color, height=450)
    return fig

def plot_stability_trend(df: pd.DataFrame, assay: str, title: str, spec_limits: Dict, projection: Dict) -> go.Figure:
    """Plots a stability trend chart with confidence intervals."""
    if df.empty: return create_empty_figure(f"No data to plot for {assay}.")
    lsl, usl = spec_limits.lsl, spec_limits.usl
    
    fig = px.scatter(df, x='Timepoint (Months)', y=assay, color='lot_id', title=f"<b>{title}</b>")
    
    if projection and 'slope' in projection:
        fig.add_trace(go.Scatter(x=projection['pred_x'], y=projection['pred_y'], mode='lines', name='Regression Fit', line=dict(color=settings.COLORS.gray, dash='dash')))
    
    if lsl is not None: fig.add_hline(y=lsl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="LSL")
    if usl is not None: fig.add_hline(y=usl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="USL")
        
    fig.update_layout(xaxis_title="Timepoint (Months)", yaxis_title="Value", height=400)
    return fig

def plot_anova_results(df: pd.DataFrame, value_col: str, group_col: str, anova_results: dict) -> go.Figure:
    """Creates a box plot for ANOVA analysis, annotated with statistical results."""
    if df.empty: return create_empty_figure("Invalid data for ANOVA plot.")
    p_value = anova_results['p_value']
    title_text = f"<b>Distribution of {value_col} by {group_col} (p-value: {p_value:.4f})</b>"
    
    fig = px.box(df, x=group_col, y=value_col, points="all", color=group_col)
    fig.update_layout(title_text=title_text)
    return fig

def plot_qq(data: pd.Series) -> go.Figure:
    """Generates a Q-Q plot to test for normality."""
    if len(data.dropna()) < 3: return create_empty_figure("No data for Q-Q plot.")
    qq_data = stats.probplot(data.dropna(), dist="norm")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=qq_data[0][0], y=qq_data[0][1], mode='markers', name='Data Points'))
    fig.add_trace(go.Scatter(x=qq_data[0][0], y=qq_data[1][1] + qq_data[1][0]*qq_data[0][0], mode='lines', name='Normal Fit'))
    fig.update_layout(title="<b>Q-Q Plot for Normality Assessment</b>", xaxis_title="Theoretical Quantiles", yaxis_title="Sample Quantiles")
    return fig

def plot_ml_anomaly_results_3d(df: pd.DataFrame, cols: List[str], labels: np.ndarray) -> go.Figure:
    """Plots the results of an anomaly detection model in 3D."""
    if df.empty: return create_empty_figure("No data for anomaly plot.")
    df_plot = df.copy(); df_plot['Anomaly'] = labels
    df_plot['Anomaly'] = df_plot['Anomaly'].astype(str).replace({'1': 'Normal', '-1': 'Anomaly'})
    
    fig = px.scatter_3d(
        df_plot, x=cols[0], y=cols[1], z=cols[2], color='Anomaly',
        color_discrete_map={'Normal': settings.COLORS.blue, 'Anomaly': settings.COLORS.red},
        title=f"<b>Isolation Forest Anomaly Detection</b>", hover_data=df.columns
    )
    return fig

# --- Governance & Audit Plots ---
def plot_data_lineage_graph(df: pd.DataFrame, record_id: str) -> graphviz.Digraph:
    """Creates a Graphviz Digraph object for visual data lineage."""
    dot = graphviz.Digraph(comment=f'Lineage for {record_id}')
    dot.attr(rankdir='TB', splines='ortho')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor=settings.COLORS.lightcyan)
    
    record_df = df[df['Record ID'] == record_id].copy().sort_values('Timestamp', ascending=True)
    if record_df.empty: return dot
    
    # Create nodes for each event
    for i, (_, row) in enumerate(record_df.iterrows()):
        node_id = f'event_{i}'
        label = f"<{row['Action']}<br/><font point-size='10'>By: {row['User']}</font><br/><font point-size='9'>{row['Timestamp'].strftime('%Y-%m-%d %H:%M')}</font>>"
        dot.node(node_id, label)
        if i > 0:
            dot.edge(f'event_{i-1}', node_id)
            
    return dot
