"""Biểu đồ Plotly dùng trong các phân hệ giám sát."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH
from modules.app_config import (
    COLOR_BLUE, COLOR_GREEN, COLOR_GREY, COLOR_LIGHT_BLUE,
    COLOR_ORANGE, COLOR_RED, COLOR_YELLOW,
)
from modules.limit_monitor import (
    STATUS_BREACH as LIMIT_STATUS_BREACH,
    STATUS_INVALID as LIMIT_STATUS_INVALID,
)
from modules.market_factor_attribution import FACTOR_DEFINITIONS
from modules.risk_heatmap import HEATMAP_COLUMNS, status_to_score
from modules.ui_helpers import apply_chart_layout

def create_fx_line_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ tỷ giá USD/VND."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["close"],
            mode="lines",
            line={"color": COLOR_ORANGE, "width": 2.2},
            customdata=np.column_stack([data["daily_return_pct"]]),
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Đóng cửa: %{y:,.0f}<br>"
                "Thay đổi: %{customdata[0]:+.2f}%"
                "<extra></extra>"
            ),
        )
    )

    return apply_chart_layout(
        figure,
        y_title="VND/USD",
        height=390,
        show_legend=False,
    )

def create_interbank_rate_chart(
    data: pd.DataFrame,
    include_two_week: bool = True,
) -> go.Figure:
    """Tạo biểu đồ lãi suất liên ngân hàng."""
    figure = go.Figure()

    series = [
        ("rate_on", "Qua đêm (O/N)", COLOR_ORANGE),
        ("rate_1w", "1 tuần (1W)", COLOR_BLUE),
    ]

    if include_two_week:
        series.append(("rate_2w", "2 tuần (2W)", COLOR_LIGHT_BLUE))

    series.extend(
        [
            ("rate_1m", "1 tháng (1M)", COLOR_GREEN),
            ("rate_3m", "3 tháng (3M)", COLOR_YELLOW),
        ]
    )

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{label}: %{{y:.2f}}%"
                    "<extra></extra>"
                ),
            )
        )

    return apply_chart_layout(
        figure,
        y_title="%",
        height=390,
        show_legend=True,
    )

def create_fx_candlestick_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ nến USD/VND."""
    figure = go.Figure()

    figure.add_trace(
        go.Candlestick(
            x=data["date"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            increasing_line_color=COLOR_GREEN,
            decreasing_line_color=COLOR_RED,
            name="USD/VND",
        )
    )

    figure.update_layout(xaxis_rangeslider_visible=False)

    return apply_chart_layout(
        figure,
        y_title="VND/USD",
        height=480,
        show_legend=False,
    )

def create_fx_return_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ thay đổi tỷ giá."""
    colors = np.where(
        data["daily_return_pct"] >= 0,
        COLOR_GREEN,
        COLOR_RED,
    )

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["date"],
            y=data["daily_return_pct"],
            marker_color=colors,
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Thay đổi: %{y:+.2f}%"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="%",
        height=390,
        show_legend=False,
    )

def create_fx_volatility_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ độ biến động tỷ giá."""
    figure = go.Figure()

    series = [
        ("volatility_20d_pct", "20 ngày", COLOR_ORANGE),
        ("volatility_60d_pct", "60 ngày", COLOR_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.9},
            )
        )

    return apply_chart_layout(
        figure,
        y_title="% quy đổi năm",
        height=390,
        show_legend=True,
    )

def create_fx_threshold_chart(data: pd.DataFrame) -> go.Figure:
    """Mức thay đổi tỷ giá ngày và ngưỡng bách phân vị động."""
    colors = np.where(data["daily_return_pct"] >= 0, COLOR_GREEN, COLOR_RED)
    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["date"],
            y=data["daily_return_pct"],
            name="Thay đổi ngày",
            marker_color=colors,
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Thay đổi: %{y:+.3f}%"
                "<extra></extra>"
            ),
        )
    )

    for column, name, color, dash in [
        ("return_p95", "+P95", COLOR_YELLOW, "dash"),
        ("return_p99", "+P99", COLOR_RED, "dot"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=name,
                line={"color": color, "width": 1.5, "dash": dash},
            )
        )
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=-data[column],
                mode="lines",
                name=f"-{name[1:]}",
                line={"color": color, "width": 1.5, "dash": dash},
            )
        )

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="%",
        height=420,
        show_legend=True,
    )

def create_fx_drawdown_chart(data: pd.DataFrame) -> go.Figure:
    """Mức giảm của USD/VND so với đỉnh trong 250 quan sát."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["drawdown_250d_pct"],
            mode="lines",
            fill="tozeroy",
            name="Mức giảm từ đỉnh 250 ngày",
            line={"color": COLOR_RED, "width": 1.8},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Mức giảm từ đỉnh: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="%",
        height=420,
        show_legend=False,
    )

def create_fx_volatility_regime_chart(data: pd.DataFrame) -> go.Figure:
    """Độ biến động 20 ngày và các ngưỡng trạng thái biến động."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["volatility_20d_pct"],
            mode="lines",
            name="Độ biến động 20 ngày",
            line={"color": COLOR_BLUE, "width": 2},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["vol20_p80"],
            mode="lines",
            name="P80",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["vol20_p95"],
            mode="lines",
            name="P95",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dot"},
        )
    )

    return apply_chart_layout(
        figure,
        y_title="% quy đổi năm",
        height=420,
        show_legend=True,
    )

def create_fx_range_threshold_chart(data: pd.DataFrame) -> go.Figure:
    """Biên độ trong ngày và ngưỡng bách phân vị động."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["intraday_range_pct"],
            mode="lines",
            name="Biên độ trong ngày",
            line={"color": COLOR_ORANGE, "width": 1.8},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["range_p95"],
            mode="lines",
            name="P95",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["range_p99"],
            mode="lines",
            name="P99",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dot"},
        )
    )

    return apply_chart_layout(
        figure,
        y_title="%",
        height=420,
        show_legend=True,
    )

def create_interbank_spread_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ chênh lệch kỳ hạn."""
    figure = go.Figure()

    series = [
        ("spread_1m_on", "1M - O/N", COLOR_ORANGE),
        ("spread_3m_on", "3M - O/N", COLOR_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
            )
        )

    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#AAB0B6",
    )

    return apply_chart_layout(
        figure,
        y_title="Điểm phần trăm",
        height=390,
        show_legend=True,
    )

def create_interbank_turnover_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ doanh số liên ngân hàng."""
    figure = go.Figure()
    turnover = data.get("total_turnover_monitoring", data["total_turnover"])

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=turnover,
            mode="lines",
            fill="tozeroy",
            line={"color": COLOR_ORANGE, "width": 1.6},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Doanh số: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=390,
        show_legend=False,
    )

def create_on_change_threshold_chart(data: pd.DataFrame) -> go.Figure:
    """Biến động O/N trong ngày và các ngưỡng lịch sử động."""
    colors = np.where(data["change_on_bps"] >= 0, COLOR_RED, COLOR_GREEN)
    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["date"],
            y=data["change_on_bps"],
            name="Thay đổi O/N",
            marker_color=colors,
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Thay đổi O/N: %{y:+.0f} bps"
                "<extra></extra>"
            ),
        )
    )

    for column, name, color, dash in [
        ("on_change_p95_bps", "P95", COLOR_YELLOW, "dash"),
        ("on_change_p99_bps", "P99", COLOR_RED, "dot"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=f"+{name}",
                line={"color": color, "width": 1.5, "dash": dash},
            )
        )
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=-data[column],
                mode="lines",
                name=f"-{name}",
                line={"color": color, "width": 1.5, "dash": dash},
            )
        )

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="bps",
        height=420,
        show_legend=True,
    )

def create_on_level_zscore_chart(data: pd.DataFrame) -> go.Figure:
    """Z-score động của mặt bằng lãi suất O/N."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["on_level_zscore"],
            mode="lines",
            name="Z-score O/N",
            line={"color": COLOR_BLUE, "width": 1.9},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Z-score: %{y:+.2f}σ"
                "<extra></extra>"
            ),
        )
    )

    for level, color, dash in [
        (2, COLOR_YELLOW, "dash"),
        (3, COLOR_RED, "dot"),
        (-2, COLOR_YELLOW, "dash"),
        (-3, COLOR_RED, "dot"),
    ]:
        figure.add_hline(y=level, line_color=color, line_dash=dash, line_width=1.2)

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="Độ lệch chuẩn (σ)",
        height=420,
        show_legend=False,
    )

def create_money_market_curve_chart(data: pd.DataFrame) -> go.Figure:
    """Chênh lệch lãi suất các kỳ hạn so với O/N."""
    figure = go.Figure()

    series = [
        ("spread_1w_on_bps", "1W - O/N", COLOR_ORANGE),
        ("spread_2w_on_bps", "2W - O/N", COLOR_LIGHT_BLUE),
        ("spread_1m_on_bps", "1M - O/N", COLOR_GREEN),
        ("spread_3m_on_bps", "3M - O/N", COLOR_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.7},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{label}: %{{y:+.0f}} bps"
                    "<extra></extra>"
                ),
            )
        )

    figure.add_hline(y=0, line_color="#AAB0B6", line_dash="dash")

    return apply_chart_layout(
        figure,
        y_title="bps",
        height=420,
        show_legend=True,
    )

def create_turnover_zscore_chart(data: pd.DataFrame) -> go.Figure:
    """Mức bất thường của tổng doanh số liên ngân hàng."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["turnover_zscore"],
            mode="lines",
            name="Z-score doanh số",
            line={"color": COLOR_ORANGE, "width": 1.9},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Z-score: %{y:+.2f}σ"
                "<extra></extra>"
            ),
        )
    )

    for level, color, dash in [
        (2, COLOR_YELLOW, "dash"),
        (3, COLOR_RED, "dot"),
        (-2, COLOR_YELLOW, "dash"),
        (-3, COLOR_RED, "dot"),
    ]:
        figure.add_hline(y=level, line_color=color, line_dash=dash, line_width=1.2)

    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="Độ lệch chuẩn (σ)",
        height=420,
        show_legend=False,
    )

def create_deposit_rate_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ lãi suất huy động."""
    figure = go.Figure()

    series = [
        ("deposit_1_3m", "1-3 tháng", COLOR_ORANGE),
        ("deposit_6_9m", "6-9 tháng", COLOR_GREEN),
        ("deposit_12m", "12 tháng", COLOR_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 2},
            )
        )

    return apply_chart_layout(
        figure,
        y_title="%",
        height=450,
        show_legend=True,
    )

def create_deposit_change_chart(data: pd.DataFrame) -> go.Figure:
    """Biến động lãi suất huy động trong 20 quan sát."""
    figure = go.Figure()

    series = [
        ("change_20obs_1_3m_bps", "1-3 tháng", COLOR_ORANGE),
        ("change_20obs_6_9m_bps", "6-9 tháng", COLOR_GREEN),
        ("change_20obs_12m_bps", "12 tháng", COLOR_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{label}: %{{y:+.0f}} bps"
                    "<extra></extra>"
                ),
            )
        )

    figure.add_hline(y=0, line_color="#AAB0B6")
    return apply_chart_layout(figure, y_title="bps", height=420, show_legend=True)

def create_deposit_repricing_threshold_chart(data: pd.DataFrame) -> go.Figure:
    """Tốc độ điều chỉnh kỳ hạn 12 tháng so với ngưỡng lịch sử."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["change_20obs_12m_bps"].abs(),
            mode="lines",
            name="|Δ 20 quan sát|",
            line={"color": COLOR_BLUE, "width": 1.9},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "|Δ|: %{y:.0f} bps"
                "<extra></extra>"
            ),
        )
    )

    for column, label, color, dash in [
        ("repricing_p95_12m_bps", "P95", COLOR_YELLOW, "dash"),
        ("repricing_p99_12m_bps", "P99", COLOR_RED, "dot"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.4, "dash": dash},
            )
        )

    return apply_chart_layout(figure, y_title="bps", height=420, show_legend=True)

def create_deposit_spread_chart(data: pd.DataFrame) -> go.Figure:
    """Chênh lệch lãi suất giữa các nhóm kỳ hạn huy động."""
    figure = go.Figure()

    series = [
        ("spread_6_9m_1_3m_bps", "6-9M - 1-3M", COLOR_ORANGE),
        ("spread_12m_1_3m_bps", "12M - 1-3M", COLOR_BLUE),
        ("spread_12m_6_9m_bps", "12M - 6-9M", COLOR_GREEN),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{label}: %{{y:+.0f}} bps"
                    "<extra></extra>"
                ),
            )
        )

    figure.add_hline(y=0, line_color="#AAB0B6", line_dash="dash")
    return apply_chart_layout(figure, y_title="bps", height=420, show_legend=True)

def create_deposit_spread_zscore_chart(data: pd.DataFrame) -> go.Figure:
    """Mức bất thường của chênh lệch 12 tháng - 1-3 tháng."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["spread_12m_1_3m_zscore"],
            mode="lines",
            name="Z-score chênh lệch kỳ hạn",
            line={"color": COLOR_ORANGE, "width": 1.9},
        )
    )

    for level, color, dash in [
        (2, COLOR_YELLOW, "dash"),
        (3, COLOR_RED, "dot"),
        (-2, COLOR_YELLOW, "dash"),
        (-3, COLOR_RED, "dot"),
    ]:
        figure.add_hline(y=level, line_color=color, line_dash=dash, line_width=1.2)

    figure.add_hline(y=0, line_color="#AAB0B6")
    return apply_chart_layout(
        figure,
        y_title="Độ lệch chuẩn (σ)",
        height=420,
        show_legend=False,
    )

def create_deposit_level_regime_chart(data: pd.DataFrame) -> go.Figure:
    """Mặt bằng lãi suất 12 tháng và các phân vị lịch sử động."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["deposit_12m"],
            mode="lines",
            name="12 tháng",
            line={"color": COLOR_BLUE, "width": 2.0},
        )
    )

    for column, label, color, dash in [
        ("rate_12m_p20", "P20", COLOR_LIGHT_BLUE, "dash"),
        ("rate_12m_p80", "P80", COLOR_YELLOW, "dash"),
        ("rate_12m_p95", "P95", COLOR_RED, "dot"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.3, "dash": dash},
            )
        )

    return apply_chart_layout(figure, y_title="%", height=420, show_legend=True)

def create_bond_yield_curve_chart(comparison: pd.DataFrame) -> go.Figure:
    """So sánh đường cong lợi suất mới nhất với ngày dữ liệu liền trước."""
    figure = go.Figure()

    if "previous_yield_pct" in comparison.columns:
        previous = comparison.dropna(subset=["previous_yield_pct"])
        if not previous.empty:
            figure.add_trace(
                go.Scatter(
                    x=previous["tenor_years"],
                    y=previous["previous_yield_pct"],
                    mode="lines+markers",
                    name="Ngày liền trước",
                    line={"color": COLOR_LIGHT_BLUE, "width": 1.8, "dash": "dash"},
                    marker={"size": 7},
                )
            )

    figure.add_trace(
        go.Scatter(
            x=comparison["tenor_years"],
            y=comparison["current_yield_pct"],
            mode="lines+markers",
            name="Mới nhất",
            line={"color": COLOR_ORANGE, "width": 2.4},
            marker={"size": 8},
        )
    )

    figure = apply_chart_layout(
        figure,
        y_title="Lợi suất (%)",
        height=430,
        show_legend=True,
    )
    figure.update_xaxes(title="Kỳ hạn còn lại (năm)")
    return figure

def create_bond_curve_change_chart(snapshot: pd.DataFrame) -> go.Figure:
    """Biến động lợi suất theo kỳ hạn tại ngày dữ liệu mới nhất."""
    colors = np.where(snapshot["yield_change_bps"] >= 0, COLOR_RED, COLOR_GREEN)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=snapshot["tenor_years"],
            y=snapshot["yield_change_bps"],
            marker_color=colors,
            hovertemplate=(
                "Kỳ hạn: %{x:g} năm<br>"
                "Thay đổi: %{y:+.1f} bps"
                "<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line_color="#AAB0B6")
    figure = apply_chart_layout(
        figure,
        y_title="bps",
        height=390,
        show_legend=False,
    )
    figure.update_xaxes(title="Kỳ hạn còn lại (năm)")
    return figure

def create_bond_tenor_history_chart(data: pd.DataFrame) -> go.Figure:
    """Lịch sử lợi suất của một kỳ hạn."""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["yield_pct"],
            mode="lines",
            line={"color": COLOR_BLUE, "width": 2},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Lợi suất: %{y:.3f}%"
                "<extra></extra>"
            ),
        )
    )
    return apply_chart_layout(
        figure,
        y_title="Lợi suất (%)",
        height=390,
        show_legend=False,
    )

def create_bond_move_threshold_chart(data: pd.DataFrame) -> go.Figure:
    """So sánh độ lớn biến động lợi suất với ngưỡng lịch sử động."""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["yield_change_bps"].abs(),
            mode="lines",
            name="|Δ lợi suất|",
            line={"color": COLOR_BLUE, "width": 1.8},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["watch_threshold_bps"],
            mode="lines",
            name="P95",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["alert_threshold_bps"],
            mode="lines",
            name="P99",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dash"},
        )
    )
    return apply_chart_layout(
        figure,
        y_title="bps",
        height=390,
        show_legend=True,
    )

def create_stress_curve_chart(curve: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ đường cong lãi suất trước và sau cú sốc."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=curve["tenor"],
            y=curve["current_rate"],
            mode="lines+markers",
            name="Hiện tại",
            line={"color": COLOR_BLUE, "width": 2},
        )
    )

    figure.add_trace(
        go.Scatter(
            x=curve["tenor"],
            y=curve["stressed_rate"],
            mode="lines+markers",
            name="Sau cú sốc",
            line={"color": COLOR_RED, "width": 2},
        )
    )

    return apply_chart_layout(
        figure,
        y_title="%",
        height=400,
        show_legend=True,
    )

def create_historical_stress_score_chart(
    timeline: pd.DataFrame,
    selected_date: pd.Timestamp | None = None,
) -> go.Figure:
    """Tạo biểu đồ điểm stress lịch sử và các ngưỡng phân vị."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=timeline["date"],
            y=timeline["stress_score"],
            mode="lines",
            name="Điểm stress lịch sử",
            line={"color": COLOR_BLUE, "width": 1.5},
        )
    )

    figure.add_trace(
        go.Scatter(
            x=timeline["date"],
            y=timeline["p95_score"],
            mode="lines",
            name="P95",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
        )
    )

    figure.add_trace(
        go.Scatter(
            x=timeline["date"],
            y=timeline["p99_score"],
            mode="lines",
            name="P99",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dash"},
        )
    )

    if selected_date is not None:
        selected = timeline[timeline["date"] == pd.Timestamp(selected_date)]
        if not selected.empty:
            figure.add_trace(
                go.Scatter(
                    x=selected["date"],
                    y=selected["stress_score"],
                    mode="markers",
                    name="Kịch bản được chọn",
                    marker={"color": COLOR_ORANGE, "size": 11, "symbol": "diamond"},
                )
            )

    return apply_chart_layout(
        figure,
        y_title="Điểm bách phân vị",
        height=410,
        show_legend=True,
    )

def create_loss_distribution_chart(
    loss_data: pd.DataFrame,
    unit: str,
    historical_var: float,
    historical_es: float,
    parametric_var: float,
) -> go.Figure:
    """Tạo phân phối lỗ và các mốc VaR/ES."""
    figure = go.Figure()

    figure.add_trace(
        go.Histogram(
            x=loss_data["loss"],
            nbinsx=60,
            name="Phân phối lỗ/lãi",
            marker_color=COLOR_LIGHT_BLUE,
            opacity=0.80,
            hovertemplate=(
                "Lỗ/lãi: %{x:,.2f}<br>"
                "Số quan sát: %{y}"
                "<extra></extra>"
            ),
        )
    )

    if pd.notna(historical_var):
        figure.add_vline(
            x=historical_var,
            line_color=COLOR_RED,
            line_width=2,
            annotation_text="VaR mô phỏng lịch sử",
            annotation_position="top",
        )

    if pd.notna(historical_es):
        figure.add_vline(
            x=historical_es,
            line_color=COLOR_ORANGE,
            line_width=2,
            line_dash="dash",
            annotation_text="ES mô phỏng lịch sử",
            annotation_position="top",
        )

    if pd.notna(parametric_var):
        figure.add_vline(
            x=parametric_var,
            line_color=COLOR_BLUE,
            line_width=2,
            line_dash="dot",
            annotation_text="VaR tham số",
            annotation_position="bottom",
        )

    figure.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 35, "b": 45},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
        xaxis={"title": unit, "gridcolor": "#EDF0F2"},
        yaxis={"title": "Số quan sát", "gridcolor": "#EDF0F2"},
    )

    return figure

def create_rolling_var_chart(
    rolling_data: pd.DataFrame,
    unit: str,
) -> go.Figure:
    """Tạo biểu đồ lỗ thực tế và VaR theo cửa sổ trượt."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=rolling_data["date"],
            y=rolling_data["loss"],
            mode="lines",
            name="Lỗ/lãi thực tế",
            line={"color": COLOR_GREY, "width": 1.2},
        )
    )

    figure.add_trace(
        go.Scatter(
            x=rolling_data["date"],
            y=rolling_data["rolling_var"],
            mode="lines",
            name="VaR theo cửa sổ trượt",
            line={"color": COLOR_RED, "width": 2},
        )
    )

    exceptions = rolling_data[rolling_data["exception"]]

    if not exceptions.empty:
        figure.add_trace(
            go.Scatter(
                x=exceptions["date"],
                y=exceptions["loss"],
                mode="markers",
                name="Vượt VaR",
                marker={"color": COLOR_ORANGE, "size": 8, "symbol": "x"},
            )
        )

    return apply_chart_layout(
        figure,
        y_title=unit,
        height=430,
        show_legend=True,
    )

def create_cumulative_exception_chart(
    cumulative_data: pd.DataFrame,
) -> go.Figure:
    """Tạo biểu đồ số lần vượt VaR tích lũy so với mức kỳ vọng."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=cumulative_data["date"],
            y=cumulative_data["actual_cumulative"],
            mode="lines",
            name="Vượt VaR thực tế",
            line={"color": COLOR_RED, "width": 2},
        )
    )

    figure.add_trace(
        go.Scatter(
            x=cumulative_data["date"],
            y=cumulative_data["expected_cumulative"],
            mode="lines",
            name="Mức kỳ vọng",
            line={"color": COLOR_BLUE, "width": 2, "dash": "dash"},
        )
    )

    return apply_chart_layout(
        figure,
        y_title="Số lần vượt VaR tích lũy",
        height=400,
        show_legend=True,
    )

def create_funding_spread_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ chênh lệch liên ngân hàng so với huy động 1-3 tháng."""
    figure = go.Figure()

    series = [
        (
            "spread_1m_vs_deposit_1_3m",
            "1M liên ngân hàng - huy động 1-3M",
            COLOR_ORANGE,
        ),
        (
            "spread_3m_vs_deposit_1_3m",
            "3M liên ngân hàng - huy động 1-3M",
            COLOR_BLUE,
        ),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{label}: %{{y:+.2f}} điểm %"
                    "<extra></extra>"
                ),
            )
        )

    figure.add_hline(y=0, line_dash="dash", line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="Điểm phần trăm",
        height=410,
        show_legend=True,
    )

def create_funding_pressure_index_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ chỉ số áp lực nguồn vốn và ngưỡng lịch sử động."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["funding_pressure_index"],
            mode="lines",
            name="Chỉ số áp lực nguồn vốn",
            line={"color": COLOR_BLUE, "width": 2.2},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "Chỉ số: %{y:.2f}<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["watch_threshold"],
            mode="lines",
            name="Ngưỡng theo dõi (P95)",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "P95: %{y:.2f}<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["alert_threshold"],
            mode="lines",
            name="Ngưỡng cảnh báo (P99)",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dash"},
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                "P99: %{y:.2f}<extra></extra>"
            ),
        )
    )

    return apply_chart_layout(
        figure,
        y_title="Chỉ số chuẩn hóa",
        height=410,
        show_legend=True,
    )

def create_funding_component_chart(components: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ phân rã các thành phần của chỉ số áp lực nguồn vốn."""
    figure = go.Figure()

    if components.empty:
        return figure

    figure.add_trace(
        go.Bar(
            x=components["component"],
            y=components["pressure_score"],
            marker_color=COLOR_ORANGE,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Điểm áp lực: %{y:.2f}<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=410,
        margin={"l": 20, "r": 20, "t": 20, "b": 120},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 12, "color": "#4B5563"},
        showlegend=False,
        xaxis={
            "title": "",
            "showgrid": False,
            "tickangle": -20,
            "automargin": True,
        },
        yaxis={
            "title": "Điểm áp lực chuẩn hóa",
            "gridcolor": "#EDF0F2",
            "zeroline": False,
        },
    )

    return figure

def create_repricing_balance_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ RSA và RSL theo nhóm kỳ hạn tái định giá."""
    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["rsa"],
            name="RSA",
            marker_color=COLOR_BLUE,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "RSA: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["rsl"],
            name="RSL",
            marker_color=COLOR_ORANGE,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "RSL: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(barmode="group")

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=430,
        show_legend=True,
    )

def create_repricing_gap_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ chênh lệch kỳ định lại lãi suất và chênh lệch lũy kế."""
    colors = np.where(
        data["repricing_gap"] >= 0,
        COLOR_GREEN,
        COLOR_RED,
    )

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["repricing_gap"],
            name="Chênh lệch kỳ định lại lãi suất",
            marker_color=colors,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Chênh lệch: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=data["bucket"],
            y=data["cumulative_gap"],
            mode="lines+markers",
            name="Chênh lệch lũy kế",
            line={
                "color": COLOR_BLUE,
                "width": 2.2,
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Chênh lệch lũy kế: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#AAB0B6",
    )

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=430,
        show_legend=True,
    )

def create_irrbb_shock_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ cú sốc lãi suất theo nhóm kỳ hạn."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["bucket"],
            y=data["shock_bps"],
            mode="lines+markers",
            name="Cú sốc",
            line={
                "color": COLOR_RED,
                "width": 2.2,
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Cú sốc: %{y:+.0f} bps"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#AAB0B6",
    )

    return apply_chart_layout(
        figure,
        y_title="bps",
        height=390,
        show_legend=False,
    )

def create_irrbb_sensitivity_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ xấp xỉ tác động đến NII và EVE theo nhóm kỳ hạn."""
    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["nii_impact"],
            name="ΔNII xấp xỉ",
            marker_color=COLOR_GREEN,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "ΔNII: %{y:+,.1f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["eve_proxy_impact"],
            name="ΔEVE xấp xỉ",
            marker_color=COLOR_BLUE,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "ΔEVE xấp xỉ: %{y:+,.1f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(barmode="group")
    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#AAB0B6",
    )

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=410,
        show_legend=True,
    )

def create_liquidity_flow_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ dòng tiền vào và dòng tiền ra sau cú sốc."""
    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["stressed_inflow"],
            name="Dòng tiền vào",
            marker_color=COLOR_GREEN,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Dòng tiền vào: %{y:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=-data["stressed_outflow"],
            name="Dòng tiền ra",
            marker_color=COLOR_RED,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Dòng tiền ra: %{customdata:,.0f} tỷ đồng"
                "<extra></extra>"
            ),
            customdata=data["stressed_outflow"],
        )
    )

    figure.update_layout(barmode="relative")
    figure.add_hline(y=0, line_color="#AAB0B6")

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=410,
        show_legend=True,
    )

def create_liquidity_gap_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ chênh lệch dòng tiền thanh khoản và chênh lệch lũy kế."""
    figure = go.Figure()

    colors = np.where(
        data["stressed_net_flow"] >= 0,
        COLOR_GREEN,
        COLOR_RED,
    )

    figure.add_trace(
        go.Bar(
            x=data["bucket"],
            y=data["stressed_net_flow"],
            name="Chênh lệch dòng tiền thanh khoản",
            marker_color=colors,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Chênh lệch dòng tiền thanh khoản: %{y:+,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=data["bucket"],
            y=data["stressed_cumulative_gap"],
            mode="lines+markers",
            name="Chênh lệch lũy kế",
            line={"color": COLOR_BLUE, "width": 2.2},
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Cumulative Gap: %{y:+,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#AAB0B6",
    )

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=410,
        show_legend=True,
    )

def create_liquidity_position_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ trạng thái thanh khoản sau khi cộng đệm thanh khoản."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["end_day"],
            y=data["liquidity_position"],
            mode="lines+markers",
            name="Trạng thái thanh khoản",
            line={"color": COLOR_ORANGE, "width": 2.4},
            customdata=data["bucket"],
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "Ngày cuối nhóm kỳ hạn: %{x:.0f}<br>"
                "Trạng thái thanh khoản: %{y:+,.0f} tỷ đồng"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color=COLOR_RED,
    )

    figure.update_xaxes(title="Ngày")

    return apply_chart_layout(
        figure,
        y_title="Tỷ đồng",
        height=410,
        show_legend=False,
    )

def create_limit_utilization_chart(data: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ mức sử dụng hạn mức."""
    plot_data = (
        data.dropna(subset=["utilization_pct"])
        .sort_values("utilization_pct", ascending=True)
        .copy()
    )

    color_map = {
        STATUS_NORMAL: COLOR_GREEN,
        STATUS_WATCH: COLOR_YELLOW,
        STATUS_ALERT: COLOR_ORANGE,
        LIMIT_STATUS_BREACH: COLOR_RED,
        LIMIT_STATUS_INVALID: COLOR_GREY,
    }

    colors = [
        color_map.get(status, COLOR_GREY)
        for status in plot_data["status"]
    ]

    labels = (
        plot_data["book"].astype(str)
        + " · "
        + plot_data["metric"].astype(str)
    )

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=plot_data["utilization_pct"],
            y=labels,
            orientation="h",
            marker_color=colors,
            customdata=np.column_stack(
                [
                    plot_data["current_value"],
                    plot_data["limit_value"],
                    plot_data["unit"],
                    plot_data["status"],
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Mức sử dụng: %{x:.1f}%<br>"
                "Giá trị hiện tại: %{customdata[0]:,.2f} %{customdata[2]}<br>"
                "Hạn mức: %{customdata[1]:,.2f} %{customdata[2]}<br>"
                "Trạng thái: %{customdata[3]}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_vline(
        x=80,
        line_dash="dot",
        line_color=COLOR_YELLOW,
        annotation_text="80%",
        annotation_position="top",
    )

    figure.add_vline(
        x=90,
        line_dash="dot",
        line_color=COLOR_ORANGE,
        annotation_text="90%",
        annotation_position="top",
    )

    figure.add_vline(
        x=100,
        line_dash="dash",
        line_color=COLOR_RED,
        annotation_text="100%",
        annotation_position="top",
    )

    figure.update_layout(
        height=max(380, 58 * len(plot_data) + 140),
        margin={"l": 20, "r": 20, "t": 25, "b": 45},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={
            "family": "Arial",
            "size": 12,
            "color": "#4B5563",
        },
        showlegend=False,
        xaxis={
            "title": "% sử dụng hạn mức",
            "gridcolor": "#EDF0F2",
            "zeroline": False,
            "range": [
                0,
                max(
                    110,
                    float(plot_data["utilization_pct"].max()) * 1.12
                    if not plot_data.empty
                    else 110,
                ),
            ],
        },
        yaxis={
            "title": "",
            "showgrid": False,
            "automargin": True,
        },
    )

    return figure

def create_risk_heatmap_chart(matrix: pd.DataFrame) -> go.Figure:
    """Tạo ma trận nhiệt trạng thái rủi ro theo nhóm và khía cạnh giám sát."""
    if matrix.empty:
        return go.Figure()

    scores = matrix[HEATMAP_COLUMNS].map(status_to_score)
    labels = matrix[HEATMAP_COLUMNS].copy()

    colorscale = [
        [0.0000, "#E5E7EB"],
        [0.1666, "#E5E7EB"],
        [0.1667, "#DFF3E7"],
        [0.4999, "#DFF3E7"],
        [0.5000, "#FFF0C2"],
        [0.8332, "#FFF0C2"],
        [0.8333, "#F8D7DA"],
        [1.0000, "#F8D7DA"],
    ]

    figure = go.Figure(
        data=go.Heatmap(
            z=scores.to_numpy(),
            x=HEATMAP_COLUMNS,
            y=matrix["Nhóm rủi ro"],
            text=labels.to_numpy(),
            texttemplate="%{text}",
            zmin=-1,
            zmax=2,
            colorscale=colorscale,
            showscale=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{x}: %{text}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=max(390, 64 * len(matrix) + 100),
        margin={"l": 20, "r": 20, "t": 20, "b": 70},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 12, "color": "#4B5563"},
        xaxis={
            "title": "",
            "side": "top",
            "showgrid": False,
            "tickangle": -15,
        },
        yaxis={
            "title": "",
            "showgrid": False,
            "autorange": "reversed",
        },
    )

    return figure

def create_factor_contribution_chart(snapshot: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ tỷ trọng cường độ biến động theo yếu tố."""
    if snapshot.empty:
        return go.Figure()

    plot_data = snapshot.sort_values("contribution_pct", ascending=True).copy()
    color_map = {
        STATUS_NORMAL: COLOR_GREEN,
        STATUS_WATCH: COLOR_YELLOW,
        STATUS_ALERT: COLOR_RED,
    }
    colors = [color_map.get(status, COLOR_GREY) for status in plot_data["status"]]

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=plot_data["contribution_pct"],
            y=plot_data["factor"],
            orientation="h",
            marker_color=colors,
            customdata=np.column_stack(
                [
                    plot_data["value"],
                    plot_data["unit"],
                    plot_data["score"],
                    plot_data["direction"],
                    plot_data["status"],
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Tỷ trọng cường độ: %{x:.1f}%<br>"
                "Biến động: %{customdata[0]:+.2f} %{customdata[1]}<br>"
                "Điểm chuẩn hóa: %{customdata[2]:+.2f}σ<br>"
                "Chiều: %{customdata[3]}<br>"
                "Mức độ: %{customdata[4]}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=390,
        margin={"l": 20, "r": 20, "t": 20, "b": 45},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 12, "color": "#4B5563"},
        showlegend=False,
        xaxis={
            "title": "% cường độ chuẩn hóa",
            "range": [0, 100],
            "gridcolor": "#EDF0F2",
            "zeroline": False,
        },
        yaxis={"title": "", "showgrid": False, "automargin": True},
    )
    return figure

def create_factor_contribution_history_chart(
    attribution_data: pd.DataFrame,
    lookback: int,
) -> go.Figure:
    """Tạo biểu đồ tỷ trọng cường độ theo thời gian."""
    data = attribution_data.dropna(subset=["market_move_intensity"]).tail(lookback).copy()
    figure = go.Figure()

    factor_colors = [
        COLOR_ORANGE,
        COLOR_BLUE,
        COLOR_GREEN,
        COLOR_YELLOW,
        COLOR_LIGHT_BLUE,
    ]

    for (factor, definition), color in zip(FACTOR_DEFINITIONS.items(), factor_colors):
        figure.add_trace(
            go.Bar(
                x=data["date"],
                y=data[f"{factor}_contribution_pct"],
                name=definition["label"],
                marker_color=color,
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    f"{definition['label']}: %{{y:.1f}}%"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(barmode="stack")
    return apply_chart_layout(
        figure,
        y_title="% cường độ chuẩn hóa",
        height=430,
        show_legend=True,
    )

def create_market_move_intensity_chart(
    attribution_data: pd.DataFrame,
    lookback: int,
) -> go.Figure:
    """Tạo biểu đồ cường độ biến động tổng hợp và ngưỡng lịch sử."""
    data = attribution_data.dropna(subset=["market_move_intensity"]).tail(lookback).copy()
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["market_move_intensity"],
            mode="lines",
            name="Cường độ biến động",
            line={"color": COLOR_BLUE, "width": 2.1},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["watch_threshold"],
            mode="lines",
            name="P95",
            line={"color": COLOR_YELLOW, "width": 1.5, "dash": "dash"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["alert_threshold"],
            mode="lines",
            name="P99",
            line={"color": COLOR_RED, "width": 1.5, "dash": "dash"},
        )
    )

    return apply_chart_layout(
        figure,
        y_title="Điểm chuẩn hóa",
        height=410,
        show_legend=True,
    )

def create_dominant_factor_frequency_chart(summary: pd.DataFrame) -> go.Figure:
    """Tạo biểu đồ tần suất yếu tố chi phối."""
    if summary.empty:
        return go.Figure()

    plot_data = summary.sort_values("dominant_days", ascending=True)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=plot_data["dominant_days"],
            y=plot_data["factor"],
            orientation="h",
            marker_color=COLOR_BLUE,
            customdata=plot_data["dominant_share_pct"],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Số phiên chi phối: %{x:.0f}<br>"
                "Tỷ trọng số phiên: %{customdata:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=360,
        margin={"l": 20, "r": 20, "t": 20, "b": 45},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 12, "color": "#4B5563"},
        showlegend=False,
        xaxis={
            "title": "Số phiên",
            "gridcolor": "#EDF0F2",
            "zeroline": False,
        },
        yaxis={"title": "", "showgrid": False, "automargin": True},
    )
    return figure

def create_confidence_ladder_chart(
    ladder: pd.DataFrame,
    unit: str,
) -> go.Figure:
    """So sánh VaR và ES tại nhiều mức tin cậy."""
    figure = go.Figure()

    series = [
        ("Mô phỏng lịch sử", "var", "VaR lịch sử", COLOR_BLUE),
        ("Mô phỏng lịch sử", "es", "ES lịch sử", COLOR_RED),
        ("Tham số", "var", "VaR tham số", COLOR_LIGHT_BLUE),
        ("Tham số", "es", "ES tham số", COLOR_ORANGE),
    ]

    for method, column, label, color in series:
        subset = ladder[ladder["method"] == method].copy()
        figure.add_trace(
            go.Bar(
                x=subset["confidence"].map(lambda value: f"{value * 100:g}%"),
                y=subset[column],
                name=label,
                marker_color=color,
                hovertemplate=(
                    "%{x}<br>"
                    + label
                    + ": %{y:,.2f} "
                    + unit
                    + "<extra></extra>"
                ),
            )
        )

    figure.update_layout(barmode="group")
    return apply_chart_layout(
        figure,
        y_title=unit,
        height=410,
        show_legend=True,
    )

def create_rolling_tail_chart(
    data: pd.DataFrame,
    unit: str,
) -> go.Figure:
    """Hiển thị VaR và ES theo cửa sổ trượt."""
    figure = go.Figure()

    series = [
        ("historical_var", "VaR lịch sử", COLOR_BLUE),
        ("historical_es", "ES lịch sử", COLOR_RED),
        ("parametric_var", "VaR tham số", COLOR_LIGHT_BLUE),
    ]

    for column, label, color in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.8},
                hovertemplate=(
                    "<b>%{x|%d/%m/%Y}</b><br>"
                    + label
                    + ": %{y:,.2f} "
                    + unit
                    + "<extra></extra>"
                ),
            )
        )

    return apply_chart_layout(
        figure,
        y_title=unit,
        height=420,
        show_legend=True,
    )

def create_tail_ratio_chart(data: pd.DataFrame) -> go.Figure:
    """Hiển thị mức độ nặng của đuôi phân phối và chênh lệch mô hình."""
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["tail_loss_ratio"],
            mode="lines",
            name="ES / VaR",
            line={"color": COLOR_RED, "width": 1.8},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["model_var_ratio"],
            mode="lines",
            name="VaR tham số / VaR lịch sử",
            line={"color": COLOR_BLUE, "width": 1.8},
        )
    )
    figure.add_hline(y=1.0, line_dash="dash", line_color=COLOR_GREY)

    return apply_chart_layout(
        figure,
        y_title="Lần",
        height=400,
        show_legend=True,
    )

def create_tail_volatility_chart(data: pd.DataFrame, unit: str) -> go.Figure:
    """Hiển thị độ biến động của chuỗi lỗ và các ngưỡng chế độ."""
    figure = go.Figure()

    series = [
        ("rolling_volatility", "Độ biến động", COLOR_BLUE, 2.0),
        ("volatility_p50", "P50", COLOR_GREY, 1.2),
        ("volatility_p75", "P75", COLOR_YELLOW, 1.2),
        ("volatility_p90", "P90", COLOR_RED, 1.2),
    ]

    for column, label, color, width in series:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[column],
                mode="lines",
                name=label,
                line={"color": color, "width": width},
            )
        )

    return apply_chart_layout(
        figure,
        y_title=unit,
        height=400,
        show_legend=True,
    )

