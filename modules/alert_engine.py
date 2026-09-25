"""Phát hiện bất thường và cảnh báo sớm từ dữ liệu thị trường."""

from __future__ import annotations

import numpy as np
import pandas as pd

STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"

SEVERITY_RANK = {STATUS_NORMAL: 0, STATUS_WATCH: 1, STATUS_ALERT: 2}
GROUP_ORDER = ["Ngoại hối", "Liên ngân hàng", "Lãi suất huy động"]
ZSCORE_WATCH_LEVEL = 2.0
ZSCORE_ALERT_LEVEL = 3.0
SHORT_WINDOW = 60
LONG_WINDOW = 250
SHORT_MIN_PERIODS = 30
LONG_MIN_PERIODS = 60


def rolling_zscore(series: pd.Series, window: int = SHORT_WINDOW, min_periods: int = SHORT_MIN_PERIODS) -> pd.Series:
    history = pd.to_numeric(series, errors="coerce").shift(1)
    mean = history.rolling(window=window, min_periods=min_periods).mean()
    std = history.rolling(window=window, min_periods=min_periods).std().replace(0, np.nan)
    return (pd.to_numeric(series, errors="coerce") - mean) / std


def rolling_quantile_thresholds(
    series: pd.Series,
    window: int = LONG_WINDOW,
    min_periods: int = LONG_MIN_PERIODS,
    watch_quantile: float = 0.95,
    alert_quantile: float = 0.99,
    ignore_zero: bool = False,
) -> tuple[pd.Series, pd.Series]:
    history = pd.to_numeric(series, errors="coerce").shift(1)
    if ignore_zero:
        history = history.where(history != 0)
    watch = history.rolling(window=window, min_periods=min_periods).quantile(watch_quantile)
    alert = history.rolling(window=window, min_periods=min_periods).quantile(alert_quantile)
    return watch, alert


def classify_signal(signal: pd.Series, watch_threshold: pd.Series, alert_threshold: pd.Series) -> pd.Series:
    status = pd.Series(STATUS_NORMAL, index=signal.index, dtype="object")
    valid = signal.notna() & watch_threshold.notna() & alert_threshold.notna()
    status.loc[valid & (signal >= watch_threshold)] = STATUS_WATCH
    status.loc[valid & (signal >= alert_threshold)] = STATUS_ALERT
    return status


def describe_zscore_rule(row: pd.Series) -> str:
    score = row.get("signed_score")
    if pd.isna(score):
        return "Chưa đủ dữ liệu lịch sử để đánh giá."
    absolute_score = abs(score)
    direction = "cao hơn" if score >= 0 else "thấp hơn"
    if row["status"] == STATUS_ALERT:
        return f"Chỉ báo {direction} nền lịch sử {absolute_score:.2f} độ lệch chuẩn, vượt ngưỡng cảnh báo 3σ."
    if row["status"] == STATUS_WATCH:
        return f"Chỉ báo {direction} nền lịch sử {absolute_score:.2f} độ lệch chuẩn, vượt ngưỡng theo dõi 2σ."
    return f"Độ lệch hiện tại là {absolute_score:.2f}σ, chưa vượt ngưỡng theo dõi."


def build_zscore_rule(
    dates: pd.Series,
    values: pd.Series,
    group: str,
    indicator: str,
    value_unit: str,
    scoring_values: pd.Series | None = None,
    window: int = SHORT_WINDOW,
    min_periods: int = SHORT_MIN_PERIODS,
) -> pd.DataFrame:
    if scoring_values is None:
        scoring_values = values
    zscore = rolling_zscore(scoring_values, window=window, min_periods=min_periods)
    signal = zscore.abs()
    watch = pd.Series(ZSCORE_WATCH_LEVEL, index=values.index, dtype="float64")
    alert = pd.Series(ZSCORE_ALERT_LEVEL, index=values.index, dtype="float64")
    status = classify_signal(signal, watch, alert)
    frame = pd.DataFrame({
        "date": dates,
        "group": group,
        "indicator": indicator,
        "value": values,
        "value_unit": value_unit,
        "signal_value": signal,
        "signal_unit": "σ",
        "watch_threshold": watch,
        "alert_threshold": alert,
        "status": status,
        "signed_score": zscore,
    })
    frame["severity_rank"] = frame["status"].map(SEVERITY_RANK)
    frame["reason"] = frame.apply(describe_zscore_rule, axis=1)
    return frame


def describe_quantile_rule(row: pd.Series) -> str:
    signal = row["signal_value"]
    watch = row["watch_threshold"]
    alert = row["alert_threshold"]
    if pd.isna(signal) or pd.isna(watch) or pd.isna(alert):
        return "Chưa đủ dữ liệu lịch sử để xác định ngưỡng."
    if row["status"] == STATUS_ALERT:
        return "Giá trị tín hiệu vượt bách phân vị 99% của phân phối lịch sử gần đây."
    if row["status"] == STATUS_WATCH:
        return "Giá trị tín hiệu vượt bách phân vị 95% của phân phối lịch sử gần đây."
    return "Giá trị hiện tại chưa vượt bách phân vị 95% của phân phối lịch sử gần đây."


def build_quantile_rule(
    dates: pd.Series,
    values: pd.Series,
    group: str,
    indicator: str,
    value_unit: str,
    use_absolute_value: bool = True,
    window: int = LONG_WINDOW,
    min_periods: int = LONG_MIN_PERIODS,
    ignore_zero: bool = False,
) -> pd.DataFrame:
    signal = values.abs() if use_absolute_value else values.copy()
    watch, alert = rolling_quantile_thresholds(
        signal,
        window=window,
        min_periods=min_periods,
        watch_quantile=0.95,
        alert_quantile=0.99,
        ignore_zero=ignore_zero,
    )
    status = classify_signal(signal, watch, alert)
    frame = pd.DataFrame({
        "date": dates,
        "group": group,
        "indicator": indicator,
        "value": values,
        "value_unit": value_unit,
        "signal_value": signal,
        "signal_unit": value_unit,
        "watch_threshold": watch,
        "alert_threshold": alert,
        "status": status,
    })
    frame["severity_rank"] = frame["status"].map(SEVERITY_RANK)
    frame["reason"] = frame.apply(describe_quantile_rule, axis=1)
    return frame


def build_rule_frames(fx_data: pd.DataFrame, interbank_data: pd.DataFrame, deposit_data: pd.DataFrame) -> list[pd.DataFrame]:
    rules = [
        build_zscore_rule(fx_data["date"], fx_data["daily_return_pct"], "Ngoại hối", "Biến động tỷ giá trong ngày", "%"),
        build_quantile_rule(fx_data["date"], fx_data["intraday_range_pct"], "Ngoại hối", "Biên độ tỷ giá trong ngày", "%", use_absolute_value=False),
        build_quantile_rule(fx_data["date"], fx_data["volatility_20d_pct"], "Ngoại hối", "Độ biến động tỷ giá 20 ngày", "%/năm", use_absolute_value=False),
        build_zscore_rule(interbank_data["date"], interbank_data["rate_on"], "Liên ngân hàng", "Mặt bằng lãi suất qua đêm", "%"),
        build_quantile_rule(interbank_data["date"], interbank_data["on_change_bps"], "Liên ngân hàng", "Thay đổi lãi suất qua đêm", "bps", use_absolute_value=True),
        build_quantile_rule(interbank_data["date"], interbank_data["spread_3m_on"], "Liên ngân hàng", "Chênh lệch 3 tháng - Qua đêm", "điểm %", use_absolute_value=True),
    ]
    turnover_values = interbank_data.get(
        "total_turnover_monitoring", interbank_data["total_turnover"]
    ).copy()
    if "turnover_placeholder_flag" in interbank_data.columns:
        turnover_values = turnover_values.mask(
            interbank_data["turnover_placeholder_flag"].fillna(False).astype(bool)
        )
    turnover_for_score = np.log1p(turnover_values.clip(lower=0))
    rules.append(build_zscore_rule(
        interbank_data["date"], turnover_values, "Liên ngân hàng",
        "Tổng doanh số liên ngân hàng", "tỷ đồng", scoring_values=turnover_for_score,
    ))
    deposit_change_20d_bps = deposit_data["deposit_12m"].diff(20).mul(100)
    rules.append(build_quantile_rule(
        deposit_data["date"], deposit_change_20d_bps, "Lãi suất huy động",
        "Thay đổi huy động 12 tháng trong 20 quan sát", "bps",
        use_absolute_value=True, window=500, min_periods=20, ignore_zero=True,
    ))
    return rules


def build_alert_snapshot(fx_data: pd.DataFrame, interbank_data: pd.DataFrame, deposit_data: pd.DataFrame) -> pd.DataFrame:
    latest_rows = []
    for frame in build_rule_frames(fx_data, interbank_data, deposit_data):
        valid = frame.dropna(subset=["date"])
        if not valid.empty:
            latest_rows.append(valid.iloc[[-1]])
    if not latest_rows:
        return pd.DataFrame()
    return pd.concat(latest_rows, ignore_index=True).sort_values(
        by=["severity_rank", "group", "indicator"], ascending=[False, True, True]
    ).reset_index(drop=True)


def build_alert_history(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    lookback_days: int = 730,
    max_events: int = 200,
) -> pd.DataFrame:
    events = []
    for frame in build_rule_frames(fx_data, interbank_data, deposit_data):
        ordered = frame.sort_values("date").reset_index(drop=True)
        previous = ordered["status"].shift(1)
        event_rows = ordered.loc[ordered["status"].ne(previous) & ordered["status"].ne(STATUS_NORMAL)].copy()
        if not event_rows.empty:
            events.append(event_rows)
    if not events:
        return pd.DataFrame()
    history = pd.concat(events, ignore_index=True)
    latest_date = history["date"].max()
    if pd.notna(latest_date):
        history = history[history["date"] >= latest_date - pd.Timedelta(days=lookback_days)]
    return history.sort_values(["date", "severity_rank"], ascending=[False, False]).head(max_events).reset_index(drop=True)


def worst_status(statuses: pd.Series) -> str:
    if statuses.empty:
        return STATUS_NORMAL
    max_rank = statuses.map(SEVERITY_RANK).max()
    return next((status for status, rank in SEVERITY_RANK.items() if rank == max_rank), STATUS_NORMAL)


def summarize_alerts(snapshot: pd.DataFrame) -> dict[str, object]:
    if snapshot.empty:
        return {
            "overall_status": STATUS_NORMAL,
            "open_count": 0,
            "watch_count": 0,
            "alert_count": 0,
            "total_indicators": 0,
            "group_status": {group: STATUS_NORMAL for group in GROUP_ORDER},
        }
    watch_count = int(snapshot["status"].eq(STATUS_WATCH).sum())
    alert_count = int(snapshot["status"].eq(STATUS_ALERT).sum())
    return {
        "overall_status": worst_status(snapshot["status"]),
        "open_count": watch_count + alert_count,
        "watch_count": watch_count,
        "alert_count": alert_count,
        "total_indicators": len(snapshot),
        "group_status": {
            group: worst_status(snapshot.loc[snapshot["group"] == group, "status"])
            for group in GROUP_ORDER
        },
    }
