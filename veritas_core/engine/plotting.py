# ==============================================================================
# Core Engine: Data Visualization
#
# Author: Principal Engineer SME & Data Rendering Expert
# Last Updated: 2025-07-20
#
# Description:
# This module is the centralized plotting engine for the VERITAS application,
# providing pure, non-UI functions to create insightful, context-rich, and
# aesthetically pleasing visualizations using Plotly and Graphviz. Functions are
# decoupled from the Streamlit UI, taking DataFrames and parameters as input and
# returning Plotly Figure or Graphviz Digraph objects, built on a consistent theme.
# ==============================================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
import graphviz
from typing import Dict, List, Tuple, Optional

# Import the centralized settings for colors and configurations
from .. import settings

# --- Universal Helper ---

def create_empty_figure(message: str) -> go.Figure:
    """
    Create a standardized empty Plotly figure with a message.

    Args:
        message (str): Message to display on the empty figure.

    Returns:
        go.Figure: Empty Plotly figure with the specified message.

    Raises:
        ValueError: If message is empty or not a string.
        TypeError: If Plotly figure creation fails.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")
    
    try:
        fig = go.Figure()
        fig.update_layout(
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': message,
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 16}
            }]
        )
        return fig
    except Exception as e:
        raise TypeError(f"Failed to create empty figure: {str(e)}")

# --- Homepage & Strategic Plots ---

def plot_program_risk_matrix(df: pd.DataFrame) -> go.Figure:
    """
    Create a 2x2 risk matrix bubble chart for program risk data.

    Args:
        df (pd.DataFrame): DataFrame with 'program_id', 'days_to_milestone', 'dqs',
            'active_deviations', and 'risk_quadrant' columns.

    Returns:
        go.Figure: Plotly scatter plot of the risk matrix.

    Raises:
        ValueError: If required columns are missing or data is invalid.
        TypeError: If df is not a DataFrame or settings.COLORS is invalid.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    required_cols = ['program_id', 'days_to_milestone', 'dqs', 'active_deviations', 'risk_quadrant']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    if df.empty:
        return create_empty_figure("No program risk data available.")
    if not all(df[col].dtype in [np.float64, np.int64] for col in ['days_to_milestone', 'dqs', 'active_deviations']):
        raise ValueError("Columns 'days_to_milestone', 'dqs', and 'active_deviations' must be numeric")

    try:
        color_map = {
            "On Track": settings.COLORS.green,
            "Data Risk": settings.COLORS.orange,
            "Schedule Risk": settings.COLORS.lightblue,
            "High Priority": settings.COLORS.red
        }
        fig = px.scatter(
            df,
            x="days_to_milestone",
            y="dqs",
            size="active_deviations",
            color="risk_quadrant",
            text="program_id",
            hover_name="program_id",
            hover_data={"days_to_milestone": True, "dqs": ':.1f', "active_deviations": True, "risk_quadrant": False},
            color_discrete_map=color_map,
            size_max=50
        )
        fig.update_traces(textposition='top center')
        fig.update_layout(
            title="<b>Program Risk Matrix</b>",
            xaxis_title="Days to Next Milestone",
            yaxis_title="Data Quality Score (%)",
            xaxis=dict(autorange="reversed"),
            legend_title="Risk Quadrant"
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot risk matrix: {str(e)}")

def plot_pareto_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a Pareto chart from a frequency DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with 'Error Type' and 'Frequency' columns.

    Returns:
        go.Figure: Plotly Pareto chart with bars and cumulative percentage line.

    Raises:
        ValueError: If required columns are missing or data is invalid.
        TypeError: If df is not a DataFrame or settings.COLORS is invalid.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    required_cols = ['Error Type', 'Frequency']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    if df.empty:
        return create_empty_figure("Invalid data for Pareto chart.")
    if not np.issubdtype(df['Frequency'].dtype, np.number):
        raise ValueError("Frequency column must be numeric")

    try:
        df_sorted = df.sort_values(by='Frequency', ascending=False)
        total_freq = df_sorted['Frequency'].sum()
        if total_freq == 0:
            return create_empty_figure("No valid frequency data for Pareto chart.")
        df_sorted['cumulative_percentage'] = df_sorted['Frequency'].cumsum() / total_freq * 100

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_sorted['Error Type'],
            y=df_sorted['Frequency'],
            name='Count',
            marker_color=settings.COLORS.orange
        ))
        fig.add_trace(go.Scatter(
            x=df_sorted['Error Type'],
            y=df_sorted['cumulative_percentage'],
            name='Cumulative %',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color=settings.COLORS.blue)
        ))
        fig.update_layout(
            title='<b>Pareto Analysis of QC Failure Hotspots</b>',
            yaxis2=dict(overlaying='y', side='right', range=[0, 105])
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot Pareto chart: {str(e)}")

# --- Statistical & QC Plots ---

def plot_historical_control_chart(df: pd.DataFrame, cqa: str, events_df: pd.DataFrame) -> go.Figure:
    """
    Create a historical I-Chart with an overlay of deviation events.

    Args:
        df (pd.DataFrame): DataFrame with 'injection_time', 'instrument_id', and cqa columns.
        cqa (str): Critical Quality Attribute column to plot (e.g., 'purity').
        events_df (pd.DataFrame): DataFrame with 'id', 'title', 'linked_record', and 'timestamp' columns.

    Returns:
        go.Figure: Plotly control chart with event overlays.

    Raises:
        ValueError: If required columns are missing or data is invalid.
        TypeError: If df or events_df is not a DataFrame or cqa is not a string.
    """
    if not isinstance(df, pd.DataFrame) or not isinstance(events_df, pd.DataFrame):
        raise TypeError("df and events_df must be pandas DataFrames")
    if not isinstance(cqa, str):
        raise TypeError("cqa must be a string")
    required_cols = ['injection_time', 'instrument_id', cqa]
    event_cols = ['id', 'title', 'linked_record', 'timestamp']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    if not all(col in events_df.columns for col in event_cols):
        raise ValueError(f"events_df must contain columns: {event_cols}")
    if len(df) < 2:
        return create_empty_figure(f"Not enough data for {cqa}.")
    if not np.issubdtype(df[cqa].dtype, np.number):
        raise ValueError(f"{cqa} column must be numeric")
    if not np.issubdtype(df['injection_time'].dtype, np.datetime64):
        raise ValueError("injection_time column must be datetime")

    try:
        mean, std_dev = df[cqa].mean(), df[cqa].std()
        ucl, lcl = mean + 3 * std_dev, mean - 3 * std_dev

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['injection_time'],
            y=df[cqa],
            mode='lines+markers',
            name=cqa
        ))
        fig.add_hline(y=mean, line_dash="dash", line_color=settings.COLORS.green, annotation_text="Mean")
        fig.add_hline(y=ucl, line_dash="dot", line_color=settings.COLORS.red, annotation_text="UCL (3σ)")
        fig.add_hline(y=lcl, line_dash="dot", line_color=settings.COLORS.red, annotation_text="LCL (3σ)")

        for _, event in events_df.iterrows():
            if 'instrument' in event['title'].lower() and event['linked_record'] in df['instrument_id'].unique():
                if pd.api.types.is_datetime64_any_dtype(event['timestamp']):
                    fig.add_vline(
                        x=event['timestamp'],
                        line_dash="longdash",
                        line_color=settings.COLORS.gray,
                        annotation_text=f"Event: {event['id']}"
                    )

        fig.update_layout(
            title=f"<b>Control Chart (I-Chart) for {cqa}</b>",
            xaxis_title="Date",
            yaxis_title="Value",
            showlegend=False,
            height=450
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot control chart: {str(e)}")

def plot_process_capability(df: pd.DataFrame, cqa: str, lsl: float, usl: float, cpk: float, cpk_target: float) -> go.Figure:
    """
    Create a process capability histogram.

    Args:
        df (pd.DataFrame): DataFrame with cqa column.
        cqa (str): Critical Quality Attribute column to plot (e.g., 'purity').
        lsl (float): Lower specification limit.
        usl (float): Upper specification limit.
        cpk (float): Process capability index.
        cpk_target (float): Target Cpk value.

    Returns:
        go.Figure: Plotly histogram with specification limits and mean.

    Raises:
        ValueError: If cqa is missing, data is invalid, or lsl >= usl.
        TypeError: If df is not a DataFrame, cqa is not a string, or lsl/usl/cpk/cpk_target are not numeric.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(cqa, str):
        raise TypeError("cqa must be a string")
    if cqa not in df.columns:
        raise ValueError(f"DataFrame must contain column: {cqa}")
    if df[cqa].dropna().empty:
        return create_empty_figure(f"No data for {cqa}.")
    if not np.issubdtype(df[cqa].dtype, np.number):
        raise ValueError(f"{cqa} column must be numeric")
    if not all(isinstance(x, (int, float)) for x in [lsl, usl, cpk, cpk_target]):
        raise TypeError("lsl, usl, cpk, and cpk_target must be numeric")
    if lsl >= usl:
        raise ValueError("Lower specification limit must be less than upper specification limit")

    try:
        title_color = settings.COLORS.green if cpk >= cpk_target else settings.COLORS.red
        fig = px.histogram(df, x=cqa, nbins=40, title=f"<b>Process Capability for {cqa} | Cpk: {cpk:.2f}</b>")
        if lsl is not None:
            fig.add_vline(x=lsl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="LSL")
        if usl is not None:
            fig.add_vline(x=usl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="USL")
        fig.add_vline(x=df[cqa].mean(), line_dash="dash", line_color=settings.COLORS.green, annotation_text="Mean")
        fig.update_layout(title_font_color=title_color, height=450)
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot process capability: {str(e)}")

def plot_stability_trend(df: pd.DataFrame, assay: str, title: str, spec_limits: Dict, projection: Dict) -> go.Figure:
    """
    Create a stability trend chart with confidence intervals.

    Args:
        df (pd.DataFrame): DataFrame with 'lot_id', 'timepoint_months', and assay columns.
        assay (str): Assay column to plot (e.g., 'purity').
        title (str): Plot title.
        spec_limits (Dict): Dictionary with 'lsl' and 'usl' keys for specification limits.
        projection (Dict): Dictionary with 'slope', 'pred_x', and 'pred_y' for regression fit.

    Returns:
        go.Figure: Plotly scatter plot with regression and specification lines.

    Raises:
        ValueError: If required columns or spec_limits keys are missing, or data is invalid.
        TypeError: If df is not a DataFrame, assay or title is not a string, or inputs are invalid.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(assay, str) or not isinstance(title, str):
        raise TypeError("assay and title must be strings")
    if not isinstance(spec_limits, dict) or not isinstance(projection, dict):
        raise TypeError("spec_limits and projection must be dictionaries")
    required_cols = ['lot_id', 'timepoint_months', assay]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    if df.empty:
        return create_empty_figure(f"No data to plot for {assay}.")
    if not all(key in spec_limits for key in ['lsl', 'usl']):
        raise ValueError("spec_limits must contain 'lsl' and 'usl' keys")

    try:
        lsl, usl = spec_limits['lsl'], spec_limits['usl']
        fig = px.scatter(df, x='timepoint_months', y=assay, color='lot_id', title=f"<b>{title}</b>")

        if projection and all(key in projection for key in ['slope', 'pred_x', 'pred_y']):
            fig.add_trace(go.Scatter(
                x=projection['pred_x'],
                y=projection['pred_y'],
                mode='lines',
                name='Regression Fit',
                line=dict(color=settings.COLORS.gray, dash='dash')
            ))

        if lsl is not None:
            fig.add_hline(y=lsl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="LSL")
        if usl is not None:
            fig.add_hline(y=usl, line_dash="solid", line_color=settings.COLORS.red, annotation_text="USL")

        fig.update_layout(xaxis_title="Timepoint (Months)", yaxis_title="Value", height=400)
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot stability trend: {str(e)}")

def plot_anova_results(df: pd.DataFrame, value_col: str, group_col: str, anova_results: Dict) -> go.Figure:
    """
    Create a box plot for ANOVA analysis with statistical results.

    Args:
        df (pd.DataFrame): DataFrame with value_col and group_col.
        value_col (str): Column name of the values to analyze.
        group_col (str): Column name of the grouping variable.
        anova_results (Dict): Dictionary with 'p_value' key from ANOVA test.

    Returns:
        go.Figure: Plotly box plot with p-value annotation.

    Raises:
        ValueError: If required columns or anova_results keys are missing, or data is invalid.
        TypeError: If df is not a DataFrame, columns are not strings, or anova_results is not a dict.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(value_col, str) or not isinstance(group_col, str):
        raise TypeError("value_col and group_col must be strings")
    if not isinstance(anova_results, dict):
        raise TypeError("anova_results must be a dictionary")
    if not all(col in df.columns for col in [value_col, group_col]):
        raise ValueError(f"DataFrame must contain columns: {value_col}, {group_col}")
    if df.empty:
        return create_empty_figure("Invalid data for ANOVA plot.")
    if 'p_value' not in anova_results:
        raise ValueError("anova_results must contain 'p_value' key")

    try:
        p_value = anova_results['p_value']
        title_text = f"<b>Distribution of {value_col} by {group_col} (p-value: {p_value:.4f})</b>"
        fig = px.box(df, x=group_col, y=value_col, points="all", color=group_col)
        fig.update_layout(title_text=title_text)
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot ANOVA results: {str(e)}")

def plot_qq(data: pd.Series) -> go.Figure:
    """
    Generate a Q-Q plot to test for normality.

    Args:
        data (pd.Series): Data series to plot.

    Returns:
        go.Figure: Plotly Q-Q plot with data points and normal fit line.

    Raises:
        ValueError: If data is empty or non-numeric.
        TypeError: If data is not a pandas Series.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("data must be a pandas Series")
    data_clean = data.dropna()
    if data_clean.empty:
        raise ValueError("Data series is empty after dropping NaN values")
    if not np.issubdtype(data_clean.dtype, np.number):
        raise ValueError("Data series must be numeric")
    if len(data_clean) < 3:
        return create_empty_figure("Not enough data for Q-Q plot.")

    try:
        qq_data = stats.probplot(data_clean, dist="norm")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=qq_data[0][0],
            y=qq_data[0][1],
            mode='markers',
            name='Data Points'
        ))
        fig.add_trace(go.Scatter(
            x=qq_data[0][0],
            y=qq_data[1][1] + qq_data[1][0] * qq_data[0][0],
            mode='lines',
            name='Normal Fit'
        ))
        fig.update_layout(
            title="<b>Q-Q Plot for Normality Assessment</b>",
            xaxis_title="Theoretical Quantiles",
            yaxis_title="Sample Quantiles"
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot Q-Q plot: {str(e)}")

def plot_ml_anomaly_results_3d(df: pd.DataFrame, cols: List[str], labels: np.ndarray) -> go.Figure:
    """
    Create a 3D scatter plot of anomaly detection results.

    Args:
        df (pd.DataFrame): DataFrame with columns specified in cols.
        cols (List[str]): Exactly three column names for x, y, z axes.
        labels (np.ndarray): Array of labels (-1 for anomalies, 1 for inliers).

    Returns:
        go.Figure: Plotly 3D scatter plot of anomaly detection results.

    Raises:
        ValueError: If cols is not exactly 3, columns are missing, or labels length mismatches.
        TypeError: If df is not a DataFrame, cols is not a list of strings, or labels is not a numpy array.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
        raise TypeError("cols must be a list of strings")
    if len(cols) != 3:
        raise ValueError("cols must contain exactly three column names")
    if not all(c in df.columns for c in cols):
        raise ValueError(f"DataFrame must contain columns: {cols}")
    if df.empty:
        return create_empty_figure("No data for anomaly plot.")
    if not all(np.issubdtype(df[c].dtype, np.number) for c in cols):
        raise ValueError("All columns in cols must be numeric")
    if not isinstance(labels, np.ndarray):
        raise TypeError("labels must be a numpy array")
    if len(labels) != len(df):
        raise ValueError("labels length must match DataFrame length")

    try:
        df_plot = df.copy()
        df_plot['Anomaly'] = labels
        df_plot['Anomaly'] = df_plot['Anomaly'].astype(str).replace({'1': 'Normal', '-1': 'Anomaly'})
        
        fig = px.scatter_3d(
            df_plot,
            x=cols[0],
            y=cols[1],
            z=cols[2],
            color='Anomaly',
            color_discrete_map={'Normal': settings.COLORS.blue, 'Anomaly': settings.COLORS.red},
            title=f"<b>Isolation Forest Anomaly Detection</b>",
            hover_data=df.columns
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Failed to plot anomaly results: {str(e)}")

# --- Governance & Audit Plots ---

def plot_data_lineage_graph(df: pd.DataFrame, record_id: str) -> graphviz.Digraph:
    """
    Create a Graphviz Digraph for visual data lineage.

    Args:
        df (pd.DataFrame): DataFrame with 'record_id', 'timestamp', 'user', and 'action' columns.
        record_id (str): Record ID to filter the lineage.

    Returns:
        graphviz.Digraph: Graphviz Digraph object for data lineage.

    Raises:
        ValueError: If required columns are missing or record_id is empty.
        TypeError: If df is not a DataFrame or record_id is not a string.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")
    required_cols = ['record_id', 'timestamp', 'user', 'action']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        raise ValueError("timestamp column must be datetime")

    try:
        dot = graphviz.Digraph(comment=f'Lineage for {record_id}')
        dot.attr(rankdir='TB', splines='ortho')
        dot.attr('node', shape='box', style='rounded,filled', fillcolor=settings.COLORS.lightcyan)

        record_df = df[df['record_id'] == record_id].copy().sort_values('timestamp', ascending=True)
        if record_df.empty:
            dot.node('empty', 'No lineage data available')
            return dot

        for i, (_, row) in enumerate(record_df.iterrows()):
            node_id = f'event_{i}'
            label = f"<{row['action']}<br/><font point-size='10'>By: {row['user']}</font><br/><font point-size='9'>{row['timestamp'].strftime('%Y-%m-%d %H:%M')}</font>>"
            dot.node(node_id, label)
            if i > 0:
                dot.edge(f'event_{i-1}', node_id)

        return dot
    except Exception as e:
        dot = graphviz.Digraph(comment=f'Lineage for {record_id}')
        dot.node('error', f'Failed to plot lineage: {str(e)}')
        return dot
