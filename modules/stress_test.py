"""Kiểm tra sức chịu đựng theo các yếu tố thị trường."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH

PRESET_SCENARIOS = {
    "Căng thẳng vừa": {
        "fx_shock_pct": 0.50,
        "on_shock_bps": 100.0,
        "rate_1w_shock_bps": 75.0,
        "rate_1m_shock_bps": 75.0,
        "rate_3m_shock_bps": 50.0,
        "deposit_12m_shock_bps": 25.0,
    },
    "Căng thẳng mạnh": {
        "fx_shock_pct": 1.00,
        "on_shock_bps": 200.0,
        "rate_1w_shock_bps": 150.0,
        "rate_1m_shock_bps": 125.0,
        "rate_3m_shock_bps": 100.0,
        "deposit_12m_shock_bps": 50.0,
    },
    "Cú sốc đảo chiều": {
        "fx_shock_pct": -1.00,
        "on_shock_bps": -150.0,
        "rate_1w_shock_bps": -125.0,
        "rate_1m_shock_bps": -100.0,
        "rate_3m_shock_bps": -75.0,
        "deposit_12m_shock_bps": -50.0,
    },
}


def get_preset_scenario(name: str) -> dict[str, float]:
    if name not in PRESET_SCENARIOS:
        raise KeyError(f"Không tồn tại kịch bản: {name}")
    return PRESET_SCENARIOS[name].copy()


def historical_abs_thresholds(
    series: pd.Series,
    watch_quantile: float = 0.95,
    alert_quantile: float = 0.99,
    exclude_zero: bool = False,
    minimum_observations: int = 20,
) -> tuple[float, float, int]:
    sample = pd.to_numeric(series, errors="coerce").dropna().abs()
    if exclude_zero:
        nonzero = sample[sample > 0]
        if len(nonzero) >= minimum_observations:
            sample = nonzero
    if len(sample) < minimum_observations:
        return np.nan, np.nan, len(sample)
    return float(sample.quantile(watch_quantile)), float(sample.quantile(alert_quantile)), len(sample)


def classify_stress_magnitude(shock_value: float, watch_threshold: float, alert_threshold: float) -> str:
    if pd.isna(watch_threshold) or pd.isna(alert_threshold):
        return STATUS_NORMAL
    magnitude = abs(float(shock_value))
    if magnitude >= alert_threshold:
        return STATUS_ALERT
    if magnitude >= watch_threshold:
        return STATUS_WATCH
    return STATUS_NORMAL


def describe_stress(
    shock_value: float,
    watch_threshold: float,
    alert_threshold: float,
    sample_size: int,
    signal_unit: str,
) -> str:
    if pd.isna(watch_threshold) or pd.isna(alert_threshold):
        return f"Chưa đủ dữ liệu lịch sử để xác định ngưỡng tham chiếu (số quan sát khả dụng: {sample_size})."
    magnitude = abs(float(shock_value))
    if magnitude >= alert_threshold:
        return f"Độ lớn cú sốc {magnitude:.2f} {signal_unit} bằng hoặc vượt bách phân vị 99% lịch sử ({alert_threshold:.2f} {signal_unit})."
    if magnitude >= watch_threshold:
        return f"Độ lớn cú sốc {magnitude:.2f} {signal_unit} bằng hoặc vượt bách phân vị 95% lịch sử ({watch_threshold:.2f} {signal_unit})."
    return f"Độ lớn cú sốc {magnitude:.2f} {signal_unit} thấp hơn bách phân vị 95% lịch sử ({watch_threshold:.2f} {signal_unit})."


def build_stress_row(
    factor: str,
    current_value: float,
    shock_value: float,
    stressed_value: float,
    value_unit: str,
    shock_unit: str,
    historical_changes: pd.Series,
    exclude_zero: bool = False,
    minimum_observations: int = 20,
) -> dict[str, object]:
    watch, alert, sample_size = historical_abs_thresholds(
        historical_changes, exclude_zero=exclude_zero, minimum_observations=minimum_observations
    )
    return {
        "factor": factor,
        "current_value": float(current_value),
        "value_unit": value_unit,
        "shock_value": float(shock_value),
        "shock_unit": shock_unit,
        "stressed_value": float(stressed_value),
        "watch_threshold": watch,
        "alert_threshold": alert,
        "reference_sample_size": sample_size,
        "status": classify_stress_magnitude(shock_value, watch, alert),
        "reason": describe_stress(shock_value, watch, alert, sample_size, shock_unit),
    }


def run_stress_test(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    fx_shock_pct: float = 0.0,
    on_shock_bps: float = 0.0,
    rate_1w_shock_bps: float = 0.0,
    rate_1m_shock_bps: float = 0.0,
    rate_3m_shock_bps: float = 0.0,
    deposit_12m_shock_bps: float = 0.0,
) -> pd.DataFrame:
    latest_fx = fx_data.iloc[-1]
    latest_mm = interbank_data.iloc[-1]
    latest_dep = deposit_data.iloc[-1]
    rows = [
        build_stress_row("USD/VND", latest_fx["close"], fx_shock_pct, latest_fx["close"] * (1 + fx_shock_pct / 100), "VND/USD", "%", fx_data["daily_return_pct"]),
        build_stress_row("Lãi suất qua đêm", latest_mm["rate_on"], on_shock_bps, latest_mm["rate_on"] + on_shock_bps / 100, "%", "bps", interbank_data["rate_on"].diff().mul(100)),
        build_stress_row("Lãi suất 1 tuần", latest_mm["rate_1w"], rate_1w_shock_bps, latest_mm["rate_1w"] + rate_1w_shock_bps / 100, "%", "bps", interbank_data["rate_1w"].diff().mul(100)),
        build_stress_row("Lãi suất 1 tháng", latest_mm["rate_1m"], rate_1m_shock_bps, latest_mm["rate_1m"] + rate_1m_shock_bps / 100, "%", "bps", interbank_data["rate_1m"].diff().mul(100)),
        build_stress_row("Lãi suất 3 tháng", latest_mm["rate_3m"], rate_3m_shock_bps, latest_mm["rate_3m"] + rate_3m_shock_bps / 100, "%", "bps", interbank_data["rate_3m"].diff().mul(100)),
        build_stress_row("Huy động 12 tháng", latest_dep["deposit_12m"], deposit_12m_shock_bps, latest_dep["deposit_12m"] + deposit_12m_shock_bps / 100, "%", "bps", deposit_data["deposit_12m"].diff().mul(100), exclude_zero=True, minimum_observations=10),
    ]
    return pd.DataFrame(rows)


def summarize_stress_results(results: pd.DataFrame) -> dict[str, object]:
    if results.empty:
        return {"overall_status": STATUS_NORMAL, "normal_count": 0, "watch_count": 0, "alert_count": 0}
    normal = int(results["status"].eq(STATUS_NORMAL).sum())
    watch = int(results["status"].eq(STATUS_WATCH).sum())
    alert = int(results["status"].eq(STATUS_ALERT).sum())
    overall = STATUS_ALERT if alert else STATUS_WATCH if watch else STATUS_NORMAL
    return {"overall_status": overall, "normal_count": normal, "watch_count": watch, "alert_count": alert}


def build_interbank_curve(results: pd.DataFrame) -> pd.DataFrame:
    factors = [("Qua đêm", "Lãi suất qua đêm"), ("1 tuần", "Lãi suất 1 tuần"), ("1 tháng", "Lãi suất 1 tháng"), ("3 tháng", "Lãi suất 3 tháng")]
    rows = []
    for tenor, factor in factors:
        matching = results[results["factor"] == factor]
        if matching.empty:
            continue
        row = matching.iloc[0]
        rows.append({"tenor": tenor, "current_rate": row["current_value"], "stressed_rate": row["stressed_value"]})
    return pd.DataFrame(rows)
