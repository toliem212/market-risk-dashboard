"""Công cụ giám sát rủi ro thị trường cho USD/VND."""

from __future__ import annotations

import numpy as np
import pandas as pd


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"

REGIME_LOW = "Thấp"
REGIME_NORMAL = "Bình thường"
REGIME_HIGH = "Cao"
REGIME_VERY_HIGH = "Rất cao"


REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "daily_return_pct",
    "intraday_range_pct",
    "volatility_20d_pct",
    "volatility_60d_pct",
]


def _rolling_quantile(
    series: pd.Series,
    quantile: float,
    window: int,
    min_periods: int,
) -> pd.Series:
    """Tính rolling quantile chỉ từ các quan sát trước thời điểm hiện tại."""
    return (
        series.shift(1)
        .rolling(window=window, min_periods=min_periods)
        .quantile(quantile)
    )


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


def _classify_volatility_regime(
    volatility: pd.Series,
    p20: pd.Series,
    p80: pd.Series,
    p95: pd.Series,
) -> pd.Series:
    """Phân loại chế độ biến động theo phân phối động của volatility 20 ngày."""
    regime = pd.Series(REGIME_NORMAL, index=volatility.index, dtype="object")
    valid = volatility.notna() & p20.notna() & p80.notna() & p95.notna()

    regime.loc[valid & (volatility < p20)] = REGIME_LOW
    regime.loc[valid & (volatility >= p80)] = REGIME_HIGH
    regime.loc[valid & (volatility >= p95)] = REGIME_VERY_HIGH

    return regime


def prepare_fx_risk_data(
    fx_data: pd.DataFrame,
    threshold_window: int = 500,
    min_periods: int = 120,
) -> pd.DataFrame:
    """Tạo bộ chỉ tiêu giám sát ngoại hối từ dữ liệu USD/VND."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in fx_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Dữ liệu USD/VND thiếu các cột: " + ", ".join(missing_columns)
        )

    data = fx_data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    data["return_5d_pct"] = data["close"].pct_change(5).mul(100)
    data["return_20d_pct"] = data["close"].pct_change(20).mul(100)
    data["abs_return_pct"] = data["daily_return_pct"].abs()

    rolling_peak = data["close"].rolling(window=250, min_periods=20).max()
    data["drawdown_250d_pct"] = data["close"].div(rolling_peak).sub(1).mul(100)

    data["return_p95"] = _rolling_quantile(
        data["abs_return_pct"], 0.95, threshold_window, min_periods
    )
    data["return_p99"] = _rolling_quantile(
        data["abs_return_pct"], 0.99, threshold_window, min_periods
    )
    data["range_p95"] = _rolling_quantile(
        data["intraday_range_pct"], 0.95, threshold_window, min_periods
    )
    data["range_p99"] = _rolling_quantile(
        data["intraday_range_pct"], 0.99, threshold_window, min_periods
    )

    data["vol20_p20"] = _rolling_quantile(
        data["volatility_20d_pct"], 0.20, threshold_window, min_periods
    )
    data["vol20_p80"] = _rolling_quantile(
        data["volatility_20d_pct"], 0.80, threshold_window, min_periods
    )
    data["vol20_p95"] = _rolling_quantile(
        data["volatility_20d_pct"], 0.95, threshold_window, min_periods
    )

    data["move_status"] = _classify_threshold(
        data["abs_return_pct"], data["return_p95"], data["return_p99"]
    )
    data["range_status"] = _classify_threshold(
        data["intraday_range_pct"], data["range_p95"], data["range_p99"]
    )
    data["volatility_regime"] = _classify_volatility_regime(
        data["volatility_20d_pct"],
        data["vol20_p20"],
        data["vol20_p80"],
        data["vol20_p95"],
    )

    return data


def summarize_fx_risk(data: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt trạng thái mới nhất của USD/VND."""
    if data.empty:
        return {}

    latest = data.iloc[-1]

    return {
        "date": latest["date"],
        "close": latest["close"],
        "return_1d_pct": latest["daily_return_pct"],
        "return_5d_pct": latest["return_5d_pct"],
        "return_20d_pct": latest["return_20d_pct"],
        "intraday_range_pct": latest["intraday_range_pct"],
        "volatility_20d_pct": latest["volatility_20d_pct"],
        "volatility_60d_pct": latest["volatility_60d_pct"],
        "drawdown_250d_pct": latest["drawdown_250d_pct"],
        "move_status": latest["move_status"],
        "range_status": latest["range_status"],
        "volatility_regime": latest["volatility_regime"],
        "return_p95": latest["return_p95"],
        "return_p99": latest["return_p99"],
        "range_p95": latest["range_p95"],
        "range_p99": latest["range_p99"],
        "vol20_p80": latest["vol20_p80"],
        "vol20_p95": latest["vol20_p95"],
    }


def build_fx_event_log(
    data: pd.DataFrame,
    max_events: int = 100,
) -> pd.DataFrame:
    """Tạo danh sách các ngày vượt ngưỡng biến động hoặc biên độ."""
    events: list[pd.DataFrame] = []

    move_events = data.loc[
        data["move_status"] != STATUS_NORMAL,
        [
            "date",
            "daily_return_pct",
            "abs_return_pct",
            "return_p95",
            "return_p99",
            "move_status",
        ],
    ].copy()

    if not move_events.empty:
        move_events["indicator"] = "Biến động tỷ giá ngày"
        move_events["value"] = move_events["daily_return_pct"]
        move_events["signal"] = move_events["abs_return_pct"]
        move_events["watch_threshold"] = move_events["return_p95"]
        move_events["alert_threshold"] = move_events["return_p99"]
        move_events["status"] = move_events["move_status"]
        events.append(
            move_events[
                [
                    "date",
                    "indicator",
                    "value",
                    "signal",
                    "watch_threshold",
                    "alert_threshold",
                    "status",
                ]
            ]
        )

    range_events = data.loc[
        data["range_status"] != STATUS_NORMAL,
        [
            "date",
            "intraday_range_pct",
            "range_p95",
            "range_p99",
            "range_status",
        ],
    ].copy()

    if not range_events.empty:
        range_events["indicator"] = "Biên độ trong ngày"
        range_events["value"] = range_events["intraday_range_pct"]
        range_events["signal"] = range_events["intraday_range_pct"]
        range_events["watch_threshold"] = range_events["range_p95"]
        range_events["alert_threshold"] = range_events["range_p99"]
        range_events["status"] = range_events["range_status"]
        events.append(
            range_events[
                [
                    "date",
                    "indicator",
                    "value",
                    "signal",
                    "watch_threshold",
                    "alert_threshold",
                    "status",
                ]
            ]
        )

    if not events:
        return pd.DataFrame(
            columns=[
                "date",
                "indicator",
                "value",
                "signal",
                "watch_threshold",
                "alert_threshold",
                "status",
            ]
        )

    return (
        pd.concat(events, ignore_index=True)
        .sort_values(["date", "status"], ascending=[False, True])
        .head(max_events)
        .reset_index(drop=True)
    )


def build_extreme_move_table(
    data: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Lấy các phiên có biến động tuyệt đối lớn nhất trong mẫu được chọn."""
    if data.empty:
        return pd.DataFrame()

    columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "daily_return_pct",
        "intraday_range_pct",
        "volatility_20d_pct",
        "drawdown_250d_pct",
    ]

    return (
        data.dropna(subset=["daily_return_pct"])
        .assign(abs_return_pct=lambda frame: frame["daily_return_pct"].abs())
        .nlargest(top_n, "abs_return_pct")
        [columns]
        .reset_index(drop=True)
    )


def build_fx_window_summary(data: pd.DataFrame) -> dict[str, object]:
    """Tổng hợp thống kê cho khoảng thời gian đang hiển thị."""
    if data.empty:
        return {
            "max_up_pct": np.nan,
            "max_down_pct": np.nan,
            "max_range_pct": np.nan,
            "min_drawdown_pct": np.nan,
            "watch_days": 0,
            "alert_days": 0,
        }

    watch_days = int(
        (
            data[["move_status", "range_status"]]
            .eq(STATUS_WATCH)
            .any(axis=1)
        ).sum()
    )
    alert_days = int(
        (
            data[["move_status", "range_status"]]
            .eq(STATUS_ALERT)
            .any(axis=1)
        ).sum()
    )

    return {
        "max_up_pct": data["daily_return_pct"].max(),
        "max_down_pct": data["daily_return_pct"].min(),
        "max_range_pct": data["intraday_range_pct"].max(),
        "min_drawdown_pct": data["drawdown_250d_pct"].min(),
        "watch_days": watch_days,
        "alert_days": alert_days,
    }
