"""Phân rã biến động thị trường theo các yếu tố quan sát được."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH


ROLLING_WINDOW = 250
MIN_PERIODS = 60
INTENSITY_WINDOW = 500
INTENSITY_MIN_PERIODS = 120
WATCH_QUANTILE = 0.95
ALERT_QUANTILE = 0.99

FACTOR_DEFINITIONS = {
    "fx_return_pct": {
        "label": "USD/VND",
        "unit": "%",
    },
    "on_change_bps": {
        "label": "Lãi suất O/N",
        "unit": "bps",
    },
    "curve_change_bps": {
        "label": "Độ dốc 3M - O/N",
        "unit": "bps",
    },
    "turnover_log_change_pct": {
        "label": "Doanh số liên ngân hàng",
        "unit": "% log",
    },
    "deposit_12m_change_bps": {
        "label": "Lãi suất huy động 12 tháng",
        "unit": "bps",
    },
}

FACTOR_COLUMNS = list(FACTOR_DEFINITIONS.keys())


def rolling_robust_score(
    series: pd.Series,
    window: int = ROLLING_WINDOW,
    min_periods: int = MIN_PERIODS,
) -> pd.Series:
    """Chuẩn hóa biến động bằng median/IQR lịch sử, không dùng quan sát hiện tại."""
    history = pd.to_numeric(series, errors="coerce").shift(1)

    median = history.rolling(window, min_periods=min_periods).median()
    q25 = history.rolling(window, min_periods=min_periods).quantile(0.25)
    q75 = history.rolling(window, min_periods=min_periods).quantile(0.75)
    robust_scale = (q75 - q25) / 1.349

    fallback_scale = history.rolling(window, min_periods=min_periods).std()
    scale = robust_scale.where(robust_scale.abs() > 1e-12, fallback_scale)
    scale = scale.replace(0, np.nan)

    return (series - median) / scale


def rolling_quantile(
    series: pd.Series,
    quantile: float,
    window: int = INTENSITY_WINDOW,
    min_periods: int = INTENSITY_MIN_PERIODS,
) -> pd.Series:
    """Tính bách phân vị động từ các quan sát trước ngày hiện tại."""
    return (
        series.shift(1)
        .rolling(window=window, min_periods=min_periods)
        .quantile(quantile)
    )


def classify_score(score: float) -> str:
    """Phân loại mức bất thường của một yếu tố theo trị tuyệt đối của điểm chuẩn hóa."""
    if pd.isna(score):
        return STATUS_NORMAL

    magnitude = abs(float(score))

    if magnitude >= 3.0:
        return STATUS_ALERT

    if magnitude >= 2.0:
        return STATUS_WATCH

    return STATUS_NORMAL


def classify_intensity(
    intensity: float,
    watch_threshold: float,
    alert_threshold: float,
) -> str:
    """Phân loại cường độ biến động tổng hợp theo phân phối lịch sử."""
    if pd.isna(intensity) or pd.isna(watch_threshold) or pd.isna(alert_threshold):
        return STATUS_NORMAL

    if intensity >= alert_threshold:
        return STATUS_ALERT

    if intensity >= watch_threshold:
        return STATUS_WATCH

    return STATUS_NORMAL


def _align_market_data(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> pd.DataFrame:
    """Căn chỉnh FX, liên ngân hàng và huy động trên cùng trục thời gian."""
    fx = (
        fx_data[["date", "daily_return_pct"]]
        .dropna(subset=["date"])
        .sort_values("date")
        .rename(columns={"daily_return_pct": "fx_return_pct"})
        .copy()
    )

    interbank_columns = ["date", "rate_on", "rate_3m", "total_turnover"]
    for optional_column in ["total_turnover_monitoring", "turnover_placeholder_flag"]:
        if optional_column in interbank_data.columns:
            interbank_columns.append(optional_column)

    interbank = (
        interbank_data[interbank_columns]
        .dropna(subset=["date"])
        .sort_values("date")
        .copy()
    )

    interbank["on_change_bps"] = interbank["rate_on"].diff().mul(100)
    interbank["curve_spread_pct"] = interbank["rate_3m"] - interbank["rate_on"]
    interbank["curve_change_bps"] = interbank["curve_spread_pct"].diff().mul(100)

    turnover_for_monitoring = interbank.get(
        "total_turnover_monitoring", interbank["total_turnover"]
    )
    if "turnover_placeholder_flag" in interbank.columns:
        turnover_for_monitoring = turnover_for_monitoring.mask(
            interbank["turnover_placeholder_flag"].fillna(False).astype(bool)
        )
    log_turnover = np.log1p(turnover_for_monitoring.clip(lower=0))
    interbank["turnover_log_change_pct"] = log_turnover.diff().mul(100)

    deposit = (
        deposit_data[["date", "deposit_12m"]]
        .dropna(subset=["date"])
        .sort_values("date")
        .copy()
    )
    deposit["deposit_12m_change_bps"] = deposit["deposit_12m"].diff().mul(100)
    deposit = deposit.rename(columns={"date": "deposit_date"})

    aligned = fx.merge(
        interbank[
            [
                "date",
                "on_change_bps",
                "curve_change_bps",
                "turnover_log_change_pct",
            ]
        ],
        on="date",
        how="inner",
    )

    aligned = pd.merge_asof(
        aligned.sort_values("date"),
        deposit[["deposit_date", "deposit_12m_change_bps"]],
        left_on="date",
        right_on="deposit_date",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    aligned["deposit_data_age_days"] = (
        aligned["date"] - aligned["deposit_date"]
    ).dt.days

    return aligned.reset_index(drop=True)


def build_market_factor_attribution_data(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> pd.DataFrame:
    """Tạo bộ dữ liệu phân rã cường độ biến động thị trường theo từng yếu tố."""
    data = _align_market_data(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )

    score_columns = []
    absolute_score_columns = []

    for factor in FACTOR_COLUMNS:
        score_column = f"{factor}_score"
        absolute_column = f"{factor}_abs_score"

        data[score_column] = rolling_robust_score(data[factor])
        data[absolute_column] = data[score_column].abs().clip(upper=8.0)

        score_columns.append(score_column)
        absolute_score_columns.append(absolute_column)

    data["available_factors"] = data[absolute_score_columns].notna().sum(axis=1)
    data["market_move_intensity"] = data[absolute_score_columns].mean(axis=1, skipna=True)
    data.loc[data["available_factors"] < 3, "market_move_intensity"] = np.nan

    total_absolute_score = data[absolute_score_columns].sum(axis=1, min_count=1)

    for factor in FACTOR_COLUMNS:
        contribution_column = f"{factor}_contribution_pct"
        absolute_column = f"{factor}_abs_score"

        data[contribution_column] = (
            data[absolute_column]
            .div(total_absolute_score.replace(0, np.nan))
            .mul(100)
        )

    contribution_columns = [
        f"{factor}_contribution_pct" for factor in FACTOR_COLUMNS
    ]

    factor_lookup = {
        f"{factor}_contribution_pct": FACTOR_DEFINITIONS[factor]["label"]
        for factor in FACTOR_COLUMNS
    }

    data["dominant_factor_column"] = pd.Series(pd.NA, index=data.index, dtype="object")
    valid_contribution = total_absolute_score.gt(0)
    data.loc[valid_contribution, "dominant_factor_column"] = (
        data.loc[valid_contribution, contribution_columns].idxmax(axis=1)
    )
    data["dominant_factor"] = data["dominant_factor_column"].map(factor_lookup)
    data["dominant_contribution_pct"] = data[contribution_columns].max(axis=1)

    data["watch_threshold"] = rolling_quantile(
        data["market_move_intensity"],
        WATCH_QUANTILE,
    )
    data["alert_threshold"] = rolling_quantile(
        data["market_move_intensity"],
        ALERT_QUANTILE,
    )

    data["status"] = [
        classify_intensity(intensity, watch, alert)
        for intensity, watch, alert in zip(
            data["market_move_intensity"],
            data["watch_threshold"],
            data["alert_threshold"],
        )
    ]

    return data


def build_attribution_snapshot(
    attribution_data: pd.DataFrame,
    selected_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Tạo bảng phân rã theo yếu tố tại một ngày được chọn."""
    if attribution_data.empty:
        return pd.DataFrame()

    data = attribution_data.dropna(subset=["date"]).sort_values("date")

    if selected_date is None:
        row = data.iloc[-1]
    else:
        selected_date = pd.Timestamp(selected_date)
        eligible = data[data["date"] <= selected_date]

        if eligible.empty:
            return pd.DataFrame()

        row = eligible.iloc[-1]

    rows = []

    for factor in FACTOR_COLUMNS:
        definition = FACTOR_DEFINITIONS[factor]
        value = row.get(factor, np.nan)
        score = row.get(f"{factor}_score", np.nan)
        contribution = row.get(f"{factor}_contribution_pct", np.nan)

        if pd.isna(value):
            direction = "—"
        elif value > 0:
            direction = "Tăng"
        elif value < 0:
            direction = "Giảm"
        else:
            direction = "Không đổi"

        rows.append(
            {
                "date": row["date"],
                "factor": definition["label"],
                "value": value,
                "unit": definition["unit"],
                "direction": direction,
                "score": score,
                "abs_score": abs(score) if pd.notna(score) else np.nan,
                "contribution_pct": contribution,
                "status": classify_score(score),
            }
        )

    snapshot = pd.DataFrame(rows)
    return snapshot.sort_values("contribution_pct", ascending=False).reset_index(drop=True)


def summarize_market_factor_attribution(
    attribution_data: pd.DataFrame,
    selected_date: pd.Timestamp | None = None,
) -> dict[str, object]:
    """Tóm tắt cường độ biến động và yếu tố chi phối tại ngày được chọn."""
    if attribution_data.empty:
        return {
            "date": pd.NaT,
            "dominant_factor": "—",
            "dominant_contribution_pct": np.nan,
            "market_move_intensity": np.nan,
            "watch_threshold": np.nan,
            "alert_threshold": np.nan,
            "status": STATUS_NORMAL,
            "available_factors": 0,
        }

    data = attribution_data.dropna(subset=["date"]).sort_values("date")

    if selected_date is not None:
        eligible = data[data["date"] <= pd.Timestamp(selected_date)]
        if eligible.empty:
            return summarize_market_factor_attribution(pd.DataFrame())
        row = eligible.iloc[-1]
    else:
        row = data.iloc[-1]

    factor_statuses = [
        classify_score(row.get(f"{factor}_score", np.nan))
        for factor in FACTOR_COLUMNS
    ]
    status_rank = {STATUS_NORMAL: 0, STATUS_WATCH: 1, STATUS_ALERT: 2}
    factor_status = max(factor_statuses, key=lambda status: status_rank[status])
    composite_status = row.get("status", STATUS_NORMAL)
    overall_status = max(
        [factor_status, composite_status],
        key=lambda status: status_rank[status],
    )

    return {
        "date": row["date"],
        "dominant_factor": row.get("dominant_factor", "—"),
        "dominant_contribution_pct": row.get("dominant_contribution_pct", np.nan),
        "market_move_intensity": row.get("market_move_intensity", np.nan),
        "watch_threshold": row.get("watch_threshold", np.nan),
        "alert_threshold": row.get("alert_threshold", np.nan),
        "status": overall_status,
        "composite_status": composite_status,
        "factor_status": factor_status,
        "available_factors": int(row.get("available_factors", 0)),
    }


def build_dominant_factor_summary(
    attribution_data: pd.DataFrame,
    lookback: int = 250,
) -> pd.DataFrame:
    """Tổng hợp tần suất từng yếu tố là yếu tố chi phối trong cửa sổ quan sát."""
    if attribution_data.empty:
        return pd.DataFrame()

    data = (
        attribution_data.dropna(
            subset=["market_move_intensity", "dominant_factor"]
        )
        .tail(lookback)
        .copy()
    )

    if data.empty:
        return pd.DataFrame()

    rows = []

    for label in [definition["label"] for definition in FACTOR_DEFINITIONS.values()]:
        subset = data[data["dominant_factor"] == label]

        contribution_columns = [
            column
            for column, factor_label in {
                f"{factor}_contribution_pct": definition["label"]
                for factor, definition in FACTOR_DEFINITIONS.items()
            }.items()
            if factor_label == label
        ]

        contribution_column = contribution_columns[0] if contribution_columns else None
        average_contribution = (
            subset[contribution_column].mean()
            if contribution_column is not None and not subset.empty
            else np.nan
        )

        rows.append(
            {
                "factor": label,
                "dominant_days": int(len(subset)),
                "dominant_share_pct": float(len(subset) / len(data) * 100),
                "average_contribution_pct": average_contribution,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("dominant_days", ascending=False)
        .reset_index(drop=True)
    )


def build_extreme_attribution_events(
    attribution_data: pd.DataFrame,
    lookback: int = 1000,
    limit: int = 15,
) -> pd.DataFrame:
    """Lấy các ngày có cường độ biến động tổng hợp lớn nhất."""
    if attribution_data.empty:
        return pd.DataFrame()

    columns = [
        "date",
        "market_move_intensity",
        "watch_threshold",
        "alert_threshold",
        "status",
        "dominant_factor",
        "dominant_contribution_pct",
        "available_factors",
    ]

    return (
        attribution_data.dropna(subset=["market_move_intensity"])
        .tail(lookback)
        .sort_values("market_move_intensity", ascending=False)
        .head(limit)[columns]
        .reset_index(drop=True)
    )
