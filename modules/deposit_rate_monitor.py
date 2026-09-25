"""Công cụ giám sát lãi suất huy động."""

from __future__ import annotations

import numpy as np
import pandas as pd


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"

RATE_COLUMNS = {
    "1-3 tháng": "deposit_1_3m",
    "6-9 tháng": "deposit_6_9m",
    "12 tháng": "deposit_12m",
}

SEVERITY_RANK = {
    STATUS_NORMAL: 0,
    STATUS_WATCH: 1,
    STATUS_ALERT: 2,
}


def _rolling_quantile(
    series: pd.Series,
    quantile: float,
    window: int = 750,
    min_periods: int = 150,
) -> pd.Series:
    """Tính ngưỡng động từ các quan sát trước thời điểm hiện tại."""
    history = series.shift(1)
    return history.rolling(window=window, min_periods=min_periods).quantile(quantile)


def _rolling_zscore(
    series: pd.Series,
    window: int = 250,
    min_periods: int = 60,
) -> pd.Series:
    """Tính Z-score động từ các quan sát trước thời điểm hiện tại."""
    history = series.shift(1)
    mean = history.rolling(window=window, min_periods=min_periods).mean()
    std = history.rolling(window=window, min_periods=min_periods).std().replace(0, np.nan)
    return (series - mean) / std


def _classify_threshold(
    value: pd.Series,
    watch_threshold: pd.Series,
    alert_threshold: pd.Series,
) -> pd.Series:
    """Phân loại theo ngưỡng P95/P99."""
    status = pd.Series(STATUS_NORMAL, index=value.index, dtype="object")
    valid = value.notna() & watch_threshold.notna() & alert_threshold.notna()
    status.loc[valid & (value >= watch_threshold)] = STATUS_WATCH
    status.loc[valid & (value >= alert_threshold)] = STATUS_ALERT
    return status


def _classify_zscore(zscore: pd.Series) -> pd.Series:
    """Phân loại theo trị tuyệt đối Z-score."""
    magnitude = zscore.abs()
    status = pd.Series(STATUS_NORMAL, index=zscore.index, dtype="object")
    status.loc[magnitude >= 2.0] = STATUS_WATCH
    status.loc[magnitude >= 3.0] = STATUS_ALERT
    return status


def _worst_status(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Lấy trạng thái nghiêm trọng nhất theo từng dòng."""
    ranks = pd.concat(
        [frame[column].map(SEVERITY_RANK).rename(column) for column in columns],
        axis=1,
    )
    max_rank = ranks.max(axis=1)
    reverse_map = {rank: status for status, rank in SEVERITY_RANK.items()}
    return max_rank.map(reverse_map).fillna(STATUS_NORMAL)


def _rate_regime(
    current: pd.Series,
    p20: pd.Series,
    p80: pd.Series,
    p95: pd.Series,
) -> pd.Series:
    """Phân loại chế độ mặt bằng lãi suất theo phân phối lịch sử động."""
    regime = pd.Series("Chưa đủ dữ liệu", index=current.index, dtype="object")
    valid = current.notna() & p20.notna() & p80.notna() & p95.notna()
    regime.loc[valid & (current < p20)] = "Thấp"
    regime.loc[valid & (current >= p20) & (current < p80)] = "Bình thường"
    regime.loc[valid & (current >= p80) & (current < p95)] = "Cao"
    regime.loc[valid & (current >= p95)] = "Rất cao"
    return regime


def prepare_deposit_rate_data(deposit_data: pd.DataFrame) -> pd.DataFrame:
    """Tạo bộ chỉ báo giám sát từ dữ liệu lãi suất huy động."""
    required = ["date", *RATE_COLUMNS.values()]
    missing = [column for column in required if column not in deposit_data.columns]
    if missing:
        raise ValueError(f"Thiếu cột dữ liệu lãi suất huy động: {', '.join(missing)}")

    data = deposit_data[required].copy()
    data = data.sort_values("date").reset_index(drop=True)

    for label, column in RATE_COLUMNS.items():
        short_name = column.replace("deposit_", "")
        data[f"change_1obs_{short_name}_bps"] = data[column].diff().mul(100)
        data[f"change_5obs_{short_name}_bps"] = data[column].diff(5).mul(100)
        data[f"change_20obs_{short_name}_bps"] = data[column].diff(20).mul(100)

        absolute_change = data[f"change_20obs_{short_name}_bps"].abs()
        data[f"repricing_p95_{short_name}_bps"] = _rolling_quantile(absolute_change, 0.95)
        data[f"repricing_p99_{short_name}_bps"] = _rolling_quantile(absolute_change, 0.99)
        data[f"repricing_status_{short_name}"] = _classify_threshold(
            absolute_change,
            data[f"repricing_p95_{short_name}_bps"],
            data[f"repricing_p99_{short_name}_bps"],
        )

    data["spread_6_9m_1_3m_bps"] = (data["deposit_6_9m"] - data["deposit_1_3m"]).mul(100)
    data["spread_12m_1_3m_bps"] = (data["deposit_12m"] - data["deposit_1_3m"]).mul(100)
    data["spread_12m_6_9m_bps"] = (data["deposit_12m"] - data["deposit_6_9m"]).mul(100)

    data["spread_12m_1_3m_zscore"] = _rolling_zscore(data["spread_12m_1_3m_bps"])
    data["spread_status"] = _classify_zscore(data["spread_12m_1_3m_zscore"])

    data["rate_12m_zscore"] = _rolling_zscore(data["deposit_12m"])
    data["level_status"] = _classify_zscore(data["rate_12m_zscore"])

    data["rate_12m_p20"] = _rolling_quantile(data["deposit_12m"], 0.20)
    data["rate_12m_p80"] = _rolling_quantile(data["deposit_12m"], 0.80)
    data["rate_12m_p95"] = _rolling_quantile(data["deposit_12m"], 0.95)
    data["rate_regime"] = _rate_regime(
        data["deposit_12m"],
        data["rate_12m_p20"],
        data["rate_12m_p80"],
        data["rate_12m_p95"],
    )

    repricing_status_columns = [
        "repricing_status_1_3m",
        "repricing_status_6_9m",
        "repricing_status_12m",
    ]
    data["repricing_status"] = _worst_status(data, repricing_status_columns)
    data["overall_status"] = _worst_status(
        data,
        ["repricing_status", "level_status", "spread_status"],
    )

    change_columns = [
        "change_20obs_1_3m_bps",
        "change_20obs_6_9m_bps",
        "change_20obs_12m_bps",
    ]
    abs_changes = data[change_columns].abs()
    data["max_abs_change_20obs_bps"] = abs_changes.max(axis=1)

    daily_columns = [
        "change_1obs_1_3m_bps",
        "change_1obs_6_9m_bps",
        "change_1obs_12m_bps",
    ]
    daily_changes = data[daily_columns]
    abs_daily_changes = daily_changes.abs()
    data["max_abs_change_1obs_bps"] = abs_daily_changes.max(axis=1)

    daily_filled = abs_daily_changes.fillna(-np.inf)
    dominant_daily_column = daily_filled.idxmax(axis=1)
    no_daily_change = abs_daily_changes.isna().all(axis=1)
    dominant_daily_column = dominant_daily_column.mask(no_daily_change)
    dominant_map = {
        "change_1obs_1_3m_bps": "1-3 tháng",
        "change_1obs_6_9m_bps": "6-9 tháng",
        "change_1obs_12m_bps": "12 tháng",
    }
    data["dominant_repricing_tenor"] = dominant_daily_column.map(dominant_map)
    data["repricing_breadth"] = abs_daily_changes.gt(1e-10).sum(axis=1)

    return data


def summarize_deposit_rates(data: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt trạng thái mới nhất."""
    if data.empty:
        raise ValueError("Không có dữ liệu lãi suất huy động để tổng hợp.")

    row = data.iloc[-1]
    return {
        "date": row["date"],
        "deposit_1_3m": row["deposit_1_3m"],
        "deposit_6_9m": row["deposit_6_9m"],
        "deposit_12m": row["deposit_12m"],
        "change_5obs_12m_bps": row["change_5obs_12m_bps"],
        "change_20obs_12m_bps": row["change_20obs_12m_bps"],
        "spread_12m_1_3m_bps": row["spread_12m_1_3m_bps"],
        "rate_regime": row["rate_regime"],
        "rate_12m_zscore": row["rate_12m_zscore"],
        "level_status": row["level_status"],
        "spread_zscore": row["spread_12m_1_3m_zscore"],
        "spread_status": row["spread_status"],
        "repricing_status": row["repricing_status"],
        "overall_status": row["overall_status"],
        "repricing_breadth": int(row["repricing_breadth"]),
        "repricing_p95_12m_bps": row["repricing_p95_12m_bps"],
        "repricing_p99_12m_bps": row["repricing_p99_12m_bps"],
    }


def build_deposit_rate_window_summary(data: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt thống kê trong cửa sổ đang hiển thị."""
    if data.empty:
        return {
            "max_12m_rate": np.nan,
            "min_12m_rate": np.nan,
            "max_up_20obs_bps": np.nan,
            "max_down_20obs_bps": np.nan,
            "widest_spread_bps": np.nan,
            "narrowest_spread_bps": np.nan,
            "watch_days": 0,
            "alert_days": 0,
        }

    changes = data[
        ["change_20obs_1_3m_bps", "change_20obs_6_9m_bps", "change_20obs_12m_bps"]
    ]

    return {
        "max_12m_rate": float(data["deposit_12m"].max()),
        "min_12m_rate": float(data["deposit_12m"].min()),
        "max_up_20obs_bps": float(changes.max().max()),
        "max_down_20obs_bps": float(changes.min().min()),
        "widest_spread_bps": float(data["spread_12m_1_3m_bps"].max()),
        "narrowest_spread_bps": float(data["spread_12m_1_3m_bps"].min()),
        "watch_days": int(data["overall_status"].eq(STATUS_WATCH).sum()),
        "alert_days": int(data["overall_status"].eq(STATUS_ALERT).sum()),
    }


def build_deposit_rate_event_log(
    data: pd.DataFrame,
    max_events: int = 20,
) -> pd.DataFrame:
    """Tạo nhật ký các lần tín hiệu chuyển sang Theo dõi/Cảnh báo."""
    events: list[pd.DataFrame] = []

    for tenor, short_name in [("1-3 tháng", "1_3m"), ("6-9 tháng", "6_9m"), ("12 tháng", "12m")]:
        status_column = f"repricing_status_{short_name}"
        previous = data[status_column].shift(1)
        mask = data[status_column].ne(previous) & data[status_column].ne(STATUS_NORMAL)
        if mask.any():
            frame = data.loc[
                mask,
                [
                    "date",
                    f"change_20obs_{short_name}_bps",
                    f"repricing_p95_{short_name}_bps",
                    f"repricing_p99_{short_name}_bps",
                    status_column,
                ],
            ].copy()
            frame.columns = ["date", "value", "watch_threshold", "alert_threshold", "status"]
            frame["indicator"] = f"Điều chỉnh lãi suất {tenor} trong 20 quan sát"
            frame["unit"] = "bps"
            frame["value"] = frame["value"].abs()
            events.append(frame)

    for indicator, value_column, status_column in [
        ("Mặt bằng lãi suất 12 tháng", "rate_12m_zscore", "level_status"),
        ("Chênh lệch 12 tháng - 1-3 tháng", "spread_12m_1_3m_zscore", "spread_status"),
    ]:
        previous = data[status_column].shift(1)
        mask = data[status_column].ne(previous) & data[status_column].ne(STATUS_NORMAL)
        if mask.any():
            frame = data.loc[mask, ["date", value_column, status_column]].copy()
            frame.columns = ["date", "value", "status"]
            frame["watch_threshold"] = 2.0
            frame["alert_threshold"] = 3.0
            frame["indicator"] = indicator
            frame["unit"] = "σ"
            events.append(frame)

    if not events:
        return pd.DataFrame()

    result = pd.concat(events, ignore_index=True)
    result["severity_rank"] = result["status"].map(SEVERITY_RANK)
    return (
        result.sort_values(["date", "severity_rank"], ascending=[False, False])
        .head(max_events)
        .reset_index(drop=True)
    )


def build_deposit_rate_extremes(
    data: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Lấy các giai đoạn điều chỉnh lãi suất mạnh nhất."""
    if data.empty:
        return pd.DataFrame()

    return (
        data.dropna(subset=["max_abs_change_1obs_bps"])
        .loc[lambda frame: frame["max_abs_change_1obs_bps"] > 0]
        .sort_values("max_abs_change_1obs_bps", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
