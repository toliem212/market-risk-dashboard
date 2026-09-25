"""Công cụ giám sát thị trường tiền tệ liên ngân hàng."""

from __future__ import annotations

import numpy as np
import pandas as pd


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"

REQUIRED_COLUMNS = [
    "date",
    "rate_on",
    "rate_1w",
    "rate_2w",
    "rate_1m",
    "rate_3m",
    "turnover_on",
    "turnover_1w",
    "turnover_2w",
    "turnover_1m",
    "turnover_3m",
    "total_turnover",
]

SEVERITY_RANK = {
    STATUS_NORMAL: 0,
    STATUS_WATCH: 1,
    STATUS_ALERT: 2,
}


def _rolling_quantile(
    series: pd.Series,
    quantile: float,
    window: int,
    min_periods: int,
    ignore_zero: bool = False,
) -> pd.Series:
    """Tính rolling quantile chỉ từ các quan sát trước thời điểm hiện tại."""
    history = series.shift(1)
    if ignore_zero:
        history = history.where(history > 0)

    return history.rolling(window=window, min_periods=min_periods).quantile(quantile)


def _rolling_zscore(
    series: pd.Series,
    window: int,
    min_periods: int,
) -> pd.Series:
    """Tính Z-score động từ dữ liệu lịch sử trước thời điểm hiện tại."""
    history = series.shift(1)
    mean = history.rolling(window=window, min_periods=min_periods).mean()
    std = history.rolling(window=window, min_periods=min_periods).std().replace(0, np.nan)
    return (series - mean) / std


def _classify_threshold(
    value: pd.Series,
    watch_threshold: pd.Series,
    alert_threshold: pd.Series,
) -> pd.Series:
    """Phân loại tín hiệu theo hai ngưỡng động."""
    status = pd.Series(STATUS_NORMAL, index=value.index, dtype="object")
    valid = value.notna() & watch_threshold.notna() & alert_threshold.notna()
    status.loc[valid & (value >= watch_threshold)] = STATUS_WATCH
    status.loc[valid & (value >= alert_threshold)] = STATUS_ALERT
    return status


def _classify_zscore(zscore: pd.Series) -> pd.Series:
    """Phân loại mức độ bất thường theo trị tuyệt đối của Z-score."""
    magnitude = zscore.abs()
    status = pd.Series(STATUS_NORMAL, index=zscore.index, dtype="object")
    status.loc[magnitude >= 2.0] = STATUS_WATCH
    status.loc[magnitude >= 3.0] = STATUS_ALERT
    return status


def _worst_status(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Lấy trạng thái nghiêm trọng nhất theo từng ngày."""
    ranks = pd.DataFrame(
        {column: frame[column].map(SEVERITY_RANK) for column in columns},
        index=frame.index,
    )
    max_rank = ranks.max(axis=1)
    reverse_rank = {rank: status for status, rank in SEVERITY_RANK.items()}
    return max_rank.map(reverse_rank)


def prepare_money_market_data(
    interbank_data: pd.DataFrame,
    threshold_window: int = 500,
    threshold_min_periods: int = 120,
    zscore_window: int = 60,
    zscore_min_periods: int = 30,
) -> pd.DataFrame:
    """Tạo bộ chỉ tiêu giám sát thị trường tiền tệ liên ngân hàng."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in interbank_data.columns
    ]
    if missing_columns:
        raise ValueError(
            "Dữ liệu liên ngân hàng thiếu các cột: " + ", ".join(missing_columns)
        )

    data = interbank_data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    rate_columns = ["rate_on", "rate_1w", "rate_2w", "rate_1m", "rate_3m"]
    tenor_labels = ["on", "1w", "2w", "1m", "3m"]

    for column, label in zip(rate_columns, tenor_labels):
        data[f"change_{label}_bps"] = data[column].diff().mul(100)

    data["abs_on_change_bps"] = data["change_on_bps"].abs()
    data["on_change_p95_bps"] = _rolling_quantile(
        data["abs_on_change_bps"], 0.95, threshold_window, threshold_min_periods
    )
    data["on_change_p99_bps"] = _rolling_quantile(
        data["abs_on_change_bps"], 0.99, threshold_window, threshold_min_periods
    )
    data["on_change_status"] = _classify_threshold(
        data["abs_on_change_bps"],
        data["on_change_p95_bps"],
        data["on_change_p99_bps"],
    )

    data["on_level_zscore"] = _rolling_zscore(
        data["rate_on"], zscore_window, zscore_min_periods
    )
    data["on_level_status"] = _classify_zscore(data["on_level_zscore"])
    data["on_volatility_20d_bps"] = data["change_on_bps"].rolling(20).std()

    data["spread_1w_on_bps"] = (data["rate_1w"] - data["rate_on"]).mul(100)
    data["spread_2w_on_bps"] = (data["rate_2w"] - data["rate_on"]).mul(100)
    data["spread_1m_on_bps"] = (data["rate_1m"] - data["rate_on"]).mul(100)
    data["spread_3m_on_bps"] = (data["rate_3m"] - data["rate_on"]).mul(100)

    inversion_columns = []
    for label in ["1w", "2w", "1m", "3m"]:
        column = f"inversion_on_{label}_bps"
        spread_column = f"spread_{label}_on_bps"
        data[column] = (-data[spread_column]).clip(lower=0)
        inversion_columns.append(column)

    data["max_curve_inversion_bps"] = data[inversion_columns].max(axis=1)
    data["curve_inversion_p95_bps"] = _rolling_quantile(
        data["max_curve_inversion_bps"],
        0.95,
        threshold_window,
        30,
        ignore_zero=True,
    )
    data["curve_inversion_p99_bps"] = _rolling_quantile(
        data["max_curve_inversion_bps"],
        0.99,
        threshold_window,
        30,
        ignore_zero=True,
    )
    data["curve_status"] = _classify_threshold(
        data["max_curve_inversion_bps"],
        data["curve_inversion_p95_bps"],
        data["curve_inversion_p99_bps"],
    )

    data["curve_range_bps"] = (
        data[rate_columns].max(axis=1) - data[rate_columns].min(axis=1)
    ).mul(100)

    if "turnover_placeholder_flag" in data.columns:
        placeholder_mask = data["turnover_placeholder_flag"].fillna(False).astype(bool)
    else:
        turnover_columns = [
            "turnover_on", "turnover_1w", "turnover_2w", "turnover_1m", "turnover_3m"
        ]
        placeholder_mask = data[turnover_columns].eq(13).all(axis=1)

    monitoring_turnover = data.get("total_turnover_monitoring", data["total_turnover"]).copy()
    monitoring_turnover = monitoring_turnover.mask(placeholder_mask)
    data["total_turnover_monitoring"] = monitoring_turnover

    log_turnover = np.log1p(monitoring_turnover.clip(lower=0))
    data["turnover_zscore"] = _rolling_zscore(
        log_turnover, zscore_window, zscore_min_periods
    )
    data["turnover_status"] = _classify_zscore(data["turnover_zscore"])
    data["turnover_on_share_pct"] = (
        data["turnover_on"].div(monitoring_turnover).mul(100)
    ).mask(placeholder_mask)

    status_columns = [
        "on_change_status",
        "on_level_status",
        "curve_status",
        "turnover_status",
    ]
    data["monitoring_status"] = _worst_status(data, status_columns)

    return data


def summarize_money_market(data: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt trạng thái mới nhất của thị trường liên ngân hàng."""
    if data.empty:
        return {}

    latest = data.iloc[-1]
    turnover_rows = data.dropna(subset=["total_turnover_monitoring", "turnover_zscore"])
    latest_turnover = turnover_rows.iloc[-1] if not turnover_rows.empty else None

    summary = {
        "date": latest["date"],
        "rate_on": latest["rate_on"],
        "rate_1w": latest["rate_1w"],
        "rate_1m": latest["rate_1m"],
        "rate_3m": latest["rate_3m"],
        "on_change_bps": latest["change_on_bps"],
        "on_volatility_20d_bps": latest["on_volatility_20d_bps"],
        "on_change_p95_bps": latest["on_change_p95_bps"],
        "on_change_p99_bps": latest["on_change_p99_bps"],
        "on_change_status": latest["on_change_status"],
        "on_level_zscore": latest["on_level_zscore"],
        "on_level_status": latest["on_level_status"],
        "spread_1w_on_bps": latest["spread_1w_on_bps"],
        "spread_1m_on_bps": latest["spread_1m_on_bps"],
        "spread_3m_on_bps": latest["spread_3m_on_bps"],
        "max_curve_inversion_bps": latest["max_curve_inversion_bps"],
        "curve_inversion_p95_bps": latest["curve_inversion_p95_bps"],
        "curve_inversion_p99_bps": latest["curve_inversion_p99_bps"],
        "curve_status": latest["curve_status"],
        "monitoring_status": latest["monitoring_status"],
    }

    if latest_turnover is None:
        summary.update(
            {
                "turnover_date": pd.NaT,
                "total_turnover": np.nan,
                "turnover_on_share_pct": np.nan,
                "turnover_zscore": np.nan,
                "turnover_status": STATUS_NORMAL,
            }
        )
    else:
        summary.update(
            {
                "turnover_date": latest_turnover["date"],
                "total_turnover": latest_turnover["total_turnover_monitoring"],
                "turnover_on_share_pct": latest_turnover["turnover_on_share_pct"],
                "turnover_zscore": latest_turnover["turnover_zscore"],
                "turnover_status": latest_turnover["turnover_status"],
            }
        )

    return summary


def build_money_market_event_log(
    data: pd.DataFrame,
    max_events: int = 100,
) -> pd.DataFrame:
    """Tạo nhật ký các tín hiệu bất thường của thị trường liên ngân hàng."""
    events: list[pd.DataFrame] = []

    def append_events(
        mask: pd.Series,
        indicator: str,
        value_column: str,
        unit: str,
        watch_column: str | None,
        alert_column: str | None,
        status_column: str,
    ) -> None:
        selected = data.loc[mask].copy()
        if selected.empty:
            return

        event = pd.DataFrame(
            {
                "date": selected["date"],
                "indicator": indicator,
                "value": selected[value_column],
                "unit": unit,
                "status": selected[status_column],
            }
        )
        event["watch_threshold"] = (
            selected[watch_column] if watch_column else 2.0
        )
        event["alert_threshold"] = (
            selected[alert_column] if alert_column else 3.0
        )
        events.append(event)

    append_events(
        data["on_change_status"] != STATUS_NORMAL,
        "Biến động O/N trong ngày",
        "change_on_bps",
        "bps",
        "on_change_p95_bps",
        "on_change_p99_bps",
        "on_change_status",
    )
    append_events(
        data["on_level_status"] != STATUS_NORMAL,
        "Mặt bằng O/N bất thường",
        "on_level_zscore",
        "σ",
        None,
        None,
        "on_level_status",
    )
    append_events(
        data["curve_status"] != STATUS_NORMAL,
        "Đảo chiều cấu trúc kỳ hạn",
        "max_curve_inversion_bps",
        "bps",
        "curve_inversion_p95_bps",
        "curve_inversion_p99_bps",
        "curve_status",
    )
    append_events(
        data["turnover_status"] != STATUS_NORMAL,
        "Doanh số giao dịch bất thường",
        "turnover_zscore",
        "σ",
        None,
        None,
        "turnover_status",
    )

    if not events:
        return pd.DataFrame()

    result = pd.concat(events, ignore_index=True)
    result["severity_rank"] = result["status"].map(SEVERITY_RANK)
    return (
        result.sort_values(["date", "severity_rank"], ascending=[False, False])
        .head(max_events)
        .reset_index(drop=True)
    )


def build_money_market_extremes(
    data: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Lấy các phiên có biến động O/N lớn nhất theo trị tuyệt đối."""
    if data.empty:
        return pd.DataFrame()

    return (
        data.dropna(subset=["change_on_bps"])
        .assign(abs_change=lambda frame: frame["change_on_bps"].abs())
        .nlargest(top_n, "abs_change")
        .drop(columns="abs_change")
        .sort_values("change_on_bps", key=lambda series: series.abs(), ascending=False)
        .reset_index(drop=True)
    )


def build_money_market_window_summary(data: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt các cực trị trong khoảng thời gian đang xem."""
    if data.empty:
        return {
            "max_on_rate": np.nan,
            "min_on_rate": np.nan,
            "max_up_bps": np.nan,
            "max_down_bps": np.nan,
            "max_inversion_bps": np.nan,
            "watch_days": 0,
            "alert_days": 0,
        }

    return {
        "max_on_rate": data["rate_on"].max(),
        "min_on_rate": data["rate_on"].min(),
        "max_up_bps": data["change_on_bps"].max(),
        "max_down_bps": data["change_on_bps"].min(),
        "max_inversion_bps": data["max_curve_inversion_bps"].max(),
        "watch_days": int(data["monitoring_status"].eq(STATUS_WATCH).sum()),
        "alert_days": int(data["monitoring_status"].eq(STATUS_ALERT).sum()),
    }
