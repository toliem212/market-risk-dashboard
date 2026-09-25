"""Hàm trình bày và định dạng dùng chung cho giao diện Streamlit."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH
from modules.limit_monitor import (
    STATUS_BREACH as LIMIT_STATUS_BREACH,
    STATUS_INVALID as LIMIT_STATUS_INVALID,
)
from modules.app_config import PERIOD_OPTIONS, PLOT_CONFIG

def format_number(value: float, decimals: int = 2) -> str:
    """Định dạng số theo quy ước Việt Nam."""
    if pd.isna(value):
        return "—"

    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(value: object) -> str:
    """Định dạng ngày DD/MM/YYYY."""
    if pd.isna(value):
        return "—"

    return pd.Timestamp(value).strftime("%d/%m/%Y")

def format_value(value: float, unit: str) -> str:
    """Định dạng giá trị theo đơn vị."""
    if pd.isna(value):
        return "—"

    decimals = 0 if unit in {"bps", "tỷ đồng", "triệu đồng", "VND/USD"} else 2
    number = format_number(value, decimals)

    return number if not unit else f"{number} {unit}"

def status_with_icon(status: str) -> str:
    """Thêm biểu tượng cho trạng thái."""
    if status == LIMIT_STATUS_BREACH:
        return f"🔴 {status}"

    if status == STATUS_ALERT:
        return f"🟠 {status}"

    if status == STATUS_WATCH:
        return f"🟡 {status}"

    if status == LIMIT_STATUS_INVALID:
        return f"⚪ {status}"

    return f"🟢 {STATUS_NORMAL}"

def classify_data_quality(quality_report: pd.DataFrame) -> str:
    """Phân loại trạng thái chất lượng dữ liệu."""
    flagged = quality_report[quality_report["Số trường hợp"] > 0]

    if flagged.empty:
        return STATUS_NORMAL

    critical = flagged[flagged["Mức độ"] == "Quan trọng"]

    if not critical.empty:
        return STATUS_ALERT

    return STATUS_WATCH

def apply_chart_layout(
    figure: go.Figure,
    y_title: str = "",
    height: int = 400,
    show_legend: bool = True,
) -> go.Figure:
    """Áp dụng bố cục chung cho biểu đồ."""
    bottom_margin = 75 if show_legend else 30

    figure.update_layout(
        height=height,
        margin={"l": 20, "r": 20, "t": 20, "b": bottom_margin},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 12, "color": "#4B5563"},
        hovermode="x unified",
        showlegend=show_legend,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.14,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "title": "",
            "showgrid": False,
            "zeroline": False,
            "tickformat": "%m/%Y",
        },
        yaxis={
            "title": y_title,
            "gridcolor": "#EDF0F2",
            "zeroline": False,
        },
    )

    return figure

def show_chart(
    title: str,
    figure: go.Figure,
    key: str,
) -> None:
    """Hiển thị biểu đồ Plotly với khóa Streamlit duy nhất."""
    st.markdown(f"#### {title}")
    st.plotly_chart(
        figure,
        width="stretch",
        config=PLOT_CONFIG,
        key=key,
    )

def select_period(key: str, default_label: str = "1 năm") -> int:
    """Chọn khoảng thời gian hiển thị."""
    labels = list(PERIOD_OPTIONS.keys())

    selected = st.radio(
        "Khoảng thời gian",
        options=labels,
        index=labels.index(default_label),
        horizontal=True,
        key=key,
    )

    return PERIOD_OPTIONS[selected]

