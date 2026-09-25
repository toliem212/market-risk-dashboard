"""
Funding Pressure Monitor
========================

Mô-đun theo dõi áp lực nguồn vốn và thanh khoản thị trường từ dữ liệu
lãi suất liên ngân hàng và lãi suất huy động.

Nguyên tắc:
- Căn chỉnh hai nguồn dữ liệu theo thời gian bằng merge_asof.
- Chỉ dùng quan sát huy động gần nhất tại hoặc trước ngày liên ngân hàng.
- Không dùng dữ liệu tương lai để lấp cho quá khứ.
- Chuẩn hóa các thành phần bằng rolling Z-score chỉ từ dữ liệu quá khứ.
- Chỉ số tổng hợp được hiệu chỉnh bằng percentile lịch sử động.
- Đây là chỉ báo market/funding pressure tham khảo, không phải LCR, NSFR,
  liquidity gap hay hạn mức thanh khoản nội bộ của một ngân hàng.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.alert_engine import (
    STATUS_ALERT,
    STATUS_NORMAL,
    STATUS_WATCH,
)


# =============================================================================
# CẤU HÌNH
# =============================================================================

ZSCORE_WINDOW = 250
ZSCORE_MIN_PERIODS = 60
PRESSURE_WINDOW = 500
PRESSURE_MIN_PERIODS = 120
WATCH_QUANTILE = 0.95
ALERT_QUANTILE = 0.99
DEPOSIT_TOLERANCE_DAYS = 7


# =============================================================================
# HÀM THỐNG KÊ
# =============================================================================


def rolling_zscore(
    series: pd.Series,
    window: int = ZSCORE_WINDOW,
    min_periods: int = ZSCORE_MIN_PERIODS,
) -> pd.Series:
    """Tính rolling Z-score chỉ từ các quan sát trước thời điểm hiện tại."""
    history = series.shift(1)

    rolling_mean = history.rolling(
        window=window,
        min_periods=min_periods,
    ).mean()

    rolling_std = (
        history.rolling(
            window=window,
            min_periods=min_periods,
        )
        .std()
        .replace(0, np.nan)
    )

    return (series - rolling_mean) / rolling_std


def rolling_quantile(
    series: pd.Series,
    quantile: float,
    window: int = PRESSURE_WINDOW,
    min_periods: int = PRESSURE_MIN_PERIODS,
) -> pd.Series:
    """Tính percentile động, loại quan sát hiện tại khỏi cửa sổ hiệu chỉnh."""
    return (
        series.shift(1)
        .rolling(
            window=window,
            min_periods=min_periods,
        )
        .quantile(quantile)
    )


def positive_component(series: pd.Series, cap: float = 4.0) -> pd.Series:
    """Giữ phần Z-score dương vì giá trị dương đại diện cho áp lực tăng."""
    return series.clip(lower=0, upper=cap)


# =============================================================================
# CĂN CHỈNH VÀ TẠO CHỈ BÁO
# =============================================================================


def align_funding_data(
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    tolerance_days: int = DEPOSIT_TOLERANCE_DAYS,
) -> pd.DataFrame:
    """
    Ghép dữ liệu liên ngân hàng với dữ liệu huy động gần nhất trước đó.

    merge_asof(direction="backward") bảo đảm không sử dụng dữ liệu tương lai.
    """
    interbank_columns = [
        "date",
        "rate_on",
        "rate_1w",
        "rate_1m",
        "rate_3m",
        "total_turnover",
    ]
    for optional_column in ["total_turnover_monitoring", "turnover_placeholder_flag"]:
        if optional_column in interbank_data.columns:
            interbank_columns.append(optional_column)

    deposit_columns = [
        "date",
        "deposit_1_3m",
        "deposit_6_9m",
        "deposit_12m",
    ]

    left = (
        interbank_data[interbank_columns]
        .dropna(subset=["date"])
        .sort_values("date")
        .copy()
    )

    right = (
        deposit_data[deposit_columns]
        .dropna(subset=["date"])
        .sort_values("date")
        .copy()
    )

    right = right.rename(columns={"date": "deposit_date"})

    aligned = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on="deposit_date",
        direction="backward",
        tolerance=pd.Timedelta(days=tolerance_days),
    )

    aligned["deposit_data_age_days"] = (
        aligned["date"] - aligned["deposit_date"]
    ).dt.days

    return aligned


def build_funding_pressure_data(
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> pd.DataFrame:
    """Tính các biến giám sát và Funding Pressure Index."""
    data = align_funding_data(
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )

    data["spread_1m_vs_deposit_1_3m"] = (
        data["rate_1m"] - data["deposit_1_3m"]
    )

    data["spread_3m_vs_deposit_1_3m"] = (
        data["rate_3m"] - data["deposit_1_3m"]
    )

    data["deposit_curve_12m_minus_1_3m"] = (
        data["deposit_12m"] - data["deposit_1_3m"]
    )

    data["on_change_5d_bps"] = data["rate_on"].diff(5).mul(100)
    data["deposit_12m_change_20d_bps"] = data["deposit_12m"].diff(20).mul(100)

    turnover_for_monitoring = data.get(
        "total_turnover_monitoring", data["total_turnover"]
    )
    if "turnover_placeholder_flag" in data.columns:
        turnover_for_monitoring = turnover_for_monitoring.mask(
            data["turnover_placeholder_flag"].fillna(False).astype(bool)
        )
    data["total_turnover_monitoring"] = turnover_for_monitoring
    log_turnover = np.log1p(turnover_for_monitoring.clip(lower=0))

    data["z_on_level"] = rolling_zscore(data["rate_on"])
    data["z_funding_spread"] = rolling_zscore(
        data["spread_3m_vs_deposit_1_3m"]
    )
    data["z_deposit_change"] = rolling_zscore(
        data["deposit_12m_change_20d_bps"]
    )
    data["z_turnover"] = rolling_zscore(log_turnover)

    component_columns = [
        "pressure_on_level",
        "pressure_funding_spread",
        "pressure_deposit_change",
        "pressure_turnover",
    ]

    data["pressure_on_level"] = positive_component(
        data["z_on_level"]
    )
    data["pressure_funding_spread"] = positive_component(
        data["z_funding_spread"]
    )
    data["pressure_deposit_change"] = positive_component(
        data["z_deposit_change"]
    )
    data["pressure_turnover"] = positive_component(
        data["z_turnover"]
    )

    data["available_components"] = data[component_columns].notna().sum(axis=1)

    data["funding_pressure_index"] = data[component_columns].mean(
        axis=1,
        skipna=True,
    )

    data.loc[
        data["available_components"] < 3,
        "funding_pressure_index",
    ] = np.nan

    data["watch_threshold"] = rolling_quantile(
        data["funding_pressure_index"],
        WATCH_QUANTILE,
    )

    data["alert_threshold"] = rolling_quantile(
        data["funding_pressure_index"],
        ALERT_QUANTILE,
    )

    data["status"] = STATUS_NORMAL

    valid = (
        data["funding_pressure_index"].notna()
        & data["watch_threshold"].notna()
        & data["alert_threshold"].notna()
    )

    watch_mask = valid & (
        data["funding_pressure_index"] >= data["watch_threshold"]
    )

    alert_mask = valid & (
        data["funding_pressure_index"] >= data["alert_threshold"]
    )

    data.loc[watch_mask, "status"] = STATUS_WATCH
    data.loc[alert_mask, "status"] = STATUS_ALERT

    return data


# =============================================================================
# TÓM TẮT VÀ LỊCH SỬ
# =============================================================================


def latest_valid_row(data: pd.DataFrame) -> pd.Series | None:
    """Lấy quan sát mới nhất có đủ dữ liệu để đánh giá chỉ số tổng hợp."""
    valid = data.dropna(
        subset=[
            "funding_pressure_index",
            "watch_threshold",
            "alert_threshold",
        ]
    )

    if valid.empty:
        return None

    return valid.iloc[-1]


def summarize_funding_pressure(
    pressure_data: pd.DataFrame,
) -> dict[str, object]:
    """Tạo snapshot trạng thái mới nhất cho dashboard."""
    latest = latest_valid_row(pressure_data)

    if latest is None:
        return {
            "status": STATUS_NORMAL,
            "date": pd.NaT,
            "index": np.nan,
            "watch_threshold": np.nan,
            "alert_threshold": np.nan,
            "spread_1m": np.nan,
            "spread_3m": np.nan,
            "deposit_change_20d_bps": np.nan,
            "on_rate": np.nan,
            "deposit_12m": np.nan,
            "deposit_age_days": np.nan,
        }

    return {
        "status": latest["status"],
        "date": latest["date"],
        "index": latest["funding_pressure_index"],
        "watch_threshold": latest["watch_threshold"],
        "alert_threshold": latest["alert_threshold"],
        "spread_1m": latest["spread_1m_vs_deposit_1_3m"],
        "spread_3m": latest["spread_3m_vs_deposit_1_3m"],
        "deposit_change_20d_bps": latest["deposit_12m_change_20d_bps"],
        "on_rate": latest["rate_on"],
        "deposit_12m": latest["deposit_12m"],
        "deposit_age_days": latest["deposit_data_age_days"],
    }


def build_pressure_components_snapshot(
    pressure_data: pd.DataFrame,
) -> pd.DataFrame:
    """Tạo bảng phân rã thành phần áp lực tại quan sát mới nhất."""
    latest = latest_valid_row(pressure_data)

    if latest is None:
        return pd.DataFrame()

    rows = [
        {
            "component": "Mặt bằng lãi suất qua đêm",
            "raw_value": latest["rate_on"],
            "raw_unit": "%",
            "zscore": latest["z_on_level"],
            "pressure_score": latest["pressure_on_level"],
        },
        {
            "component": "Chênh lệch 3M liên ngân hàng - huy động 1-3M",
            "raw_value": latest["spread_3m_vs_deposit_1_3m"],
            "raw_unit": "điểm %",
            "zscore": latest["z_funding_spread"],
            "pressure_score": latest["pressure_funding_spread"],
        },
        {
            "component": "Thay đổi huy động 12M trong 20 quan sát",
            "raw_value": latest["deposit_12m_change_20d_bps"],
            "raw_unit": "bps",
            "zscore": latest["z_deposit_change"],
            "pressure_score": latest["pressure_deposit_change"],
        },
        {
            "component": "Doanh số liên ngân hàng",
            "raw_value": latest.get("total_turnover_monitoring", latest["total_turnover"]),
            "raw_unit": "tỷ đồng",
            "zscore": latest["z_turnover"],
            "pressure_score": latest["pressure_turnover"],
        },
    ]

    return pd.DataFrame(rows)


def build_pressure_events(
    pressure_data: pd.DataFrame,
    max_events: int = 50,
) -> pd.DataFrame:
    """Lấy các ngày chỉ số áp lực đạt mức Theo dõi hoặc Cảnh báo."""
    events = pressure_data[
        pressure_data["status"].isin(
            [STATUS_WATCH, STATUS_ALERT]
        )
    ].copy()

    if events.empty:
        return pd.DataFrame()

    events["severity_rank"] = events["status"].map(
        {
            STATUS_NORMAL: 0,
            STATUS_WATCH: 1,
            STATUS_ALERT: 2,
        }
    )

    events = (
        events.sort_values(
            ["date", "severity_rank", "funding_pressure_index"],
            ascending=[False, False, False],
        )
        .head(max_events)
        .reset_index(drop=True)
    )

    return events
