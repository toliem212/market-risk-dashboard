
"""
Value at Risk and Expected Shortfall Engine
===========================================

Mô-đun ước lượng VaR và Expected Shortfall cho các yếu tố rủi ro thị trường.

Phạm vi:
- Ngoại hối USD/VND với quy mô phơi nhiễm giả định.
- Lãi suất liên ngân hàng với độ nhạy P&L giả định theo 1 điểm cơ bản.

Các phương pháp:
- Historical Simulation.
- Parametric Normal.
- Rolling Historical VaR.

Kết quả phục vụ minh họa phương pháp định lượng, không đại diện cho VaR
của một ngân hàng hoặc một danh mục giao dịch thực tế.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd


METHOD_HISTORICAL = "Historical Simulation"
METHOD_PARAMETRIC = "Parametric Normal"

POSITION_LONG_USD = "Long USD"
POSITION_SHORT_USD = "Short USD"

RATE_FACTORS = {
    "Lãi suất qua đêm": "rate_on",
    "Lãi suất 1 tháng": "rate_1m",
    "Lãi suất 3 tháng": "rate_3m",
}


def clean_loss_series(losses: pd.Series) -> pd.Series:
    """Chuẩn hóa chuỗi lỗ và loại bỏ giá trị không hợp lệ."""
    numeric = pd.to_numeric(losses, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    return numeric.dropna()


def build_fx_loss_series(
    fx_data: pd.DataFrame,
    exposure_billion_vnd: float,
    position: str = POSITION_LONG_USD,
) -> pd.DataFrame:
    """
    Chuyển biến động USD/VND thành chuỗi lỗ giả định.

    exposure_billion_vnd là giá trị phơi nhiễm quy đổi theo tỷ đồng.
    Với Long USD: USD/VND tăng tạo lãi, giảm tạo lỗ.
    Với Short USD: dấu P&L đảo ngược.
    """
    direction = 1.0 if position == POSITION_LONG_USD else -1.0

    result = fx_data[["date", "daily_return_pct"]].copy()
    result["factor_change"] = result["daily_return_pct"]
    result["loss"] = (
        -direction
        * result["daily_return_pct"].div(100)
        * float(exposure_billion_vnd)
    )
    result["loss_unit"] = "tỷ đồng"

    return result.dropna(subset=["date", "loss"]).reset_index(drop=True)


def build_rate_loss_series(
    interbank_data: pd.DataFrame,
    factor_name: str,
    sensitivity_million_vnd_per_bp: float,
) -> pd.DataFrame:
    """
    Chuyển thay đổi lãi suất thành chuỗi lỗ giả định.

    sensitivity_million_vnd_per_bp là mức thay đổi P&L, tính bằng triệu đồng,
    khi lãi suất tăng 1 bp. Giá trị dương nghĩa là lãi suất tăng tạo lỗ.
    """
    if factor_name not in RATE_FACTORS:
        raise KeyError(f"Yếu tố lãi suất không hợp lệ: {factor_name}")

    column = RATE_FACTORS[factor_name]
    rate_change_bps = interbank_data[column].diff().mul(100)

    result = interbank_data[["date"]].copy()
    result["factor_change"] = rate_change_bps
    result["loss"] = rate_change_bps * float(sensitivity_million_vnd_per_bp)
    result["loss_unit"] = "triệu đồng"

    return result.dropna(subset=["date", "loss"]).reset_index(drop=True)


def historical_var_es(
    losses: pd.Series,
    confidence_level: float,
) -> dict[str, float]:
    """Tính Historical VaR và Expected Shortfall."""
    sample = clean_loss_series(losses)

    if sample.empty:
        return {"var": np.nan, "es": np.nan, "mean": np.nan, "std": np.nan}

    var_value = float(sample.quantile(confidence_level))
    tail = sample[sample >= var_value]
    es_value = float(tail.mean()) if not tail.empty else var_value

    return {
        "var": max(var_value, 0.0),
        "es": max(es_value, var_value, 0.0),
        "mean": float(sample.mean()),
        "std": float(sample.std(ddof=1)),
    }


def parametric_var_es(
    losses: pd.Series,
    confidence_level: float,
) -> dict[str, float]:
    """Tính VaR và Expected Shortfall theo giả định phân phối chuẩn."""
    sample = clean_loss_series(losses)

    if len(sample) < 2:
        return {"var": np.nan, "es": np.nan, "mean": np.nan, "std": np.nan}

    mean_loss = float(sample.mean())
    std_loss = float(sample.std(ddof=1))

    if std_loss == 0:
        value = max(mean_loss, 0.0)
        return {"var": value, "es": value, "mean": mean_loss, "std": std_loss}

    normal = NormalDist()
    z_score = normal.inv_cdf(confidence_level)
    density = np.exp(-0.5 * z_score**2) / np.sqrt(2 * np.pi)

    var_value = mean_loss + z_score * std_loss
    es_value = mean_loss + std_loss * density / (1 - confidence_level)

    return {
        "var": max(float(var_value), 0.0),
        "es": max(float(es_value), float(var_value), 0.0),
        "mean": mean_loss,
        "std": std_loss,
    }


def calculate_var_table(
    losses: pd.Series,
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
) -> pd.DataFrame:
    """Tạo bảng VaR/ES cho Historical Simulation và Parametric Normal."""
    sample = clean_loss_series(losses)
    rows: list[dict[str, object]] = []

    for confidence_level in confidence_levels:
        historical = historical_var_es(sample, confidence_level)
        parametric = parametric_var_es(sample, confidence_level)

        rows.append(
            {
                "method": METHOD_HISTORICAL,
                "confidence_level": confidence_level,
                "var": historical["var"],
                "es": historical["es"],
                "mean_loss": historical["mean"],
                "std_loss": historical["std"],
                "observations": len(sample),
            }
        )

        rows.append(
            {
                "method": METHOD_PARAMETRIC,
                "confidence_level": confidence_level,
                "var": parametric["var"],
                "es": parametric["es"],
                "mean_loss": parametric["mean"],
                "std_loss": parametric["std"],
                "observations": len(sample),
            }
        )

    return pd.DataFrame(rows)


def rolling_historical_var(
    loss_data: pd.DataFrame,
    confidence_level: float = 0.99,
    window: int = 250,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """
    Tính Historical VaR động.

    Quan sát tại ngày t chỉ sử dụng chuỗi lỗ trước ngày t để xác định VaR.
    """
    if min_periods is None:
        min_periods = max(60, window // 2)

    data = loss_data[["date", "loss"]].copy()
    data = data.sort_values("date").reset_index(drop=True)

    history = data["loss"].shift(1)

    data["rolling_var"] = history.rolling(
        window=window,
        min_periods=min_periods,
    ).quantile(confidence_level)

    data["exception"] = (
        data["loss"].notna()
        & data["rolling_var"].notna()
        & (data["loss"] > data["rolling_var"])
    )

    return data


def summarize_rolling_var(
    rolling_data: pd.DataFrame,
) -> dict[str, float | int]:
    """Tóm tắt chuỗi Rolling VaR."""
    valid = rolling_data.dropna(subset=["rolling_var"]).copy()

    if valid.empty:
        return {
            "latest_var": np.nan,
            "latest_loss": np.nan,
            "exception_count": 0,
            "valid_days": 0,
            "exception_rate": np.nan,
        }

    exception_count = int(valid["exception"].sum())
    valid_days = len(valid)

    return {
        "latest_var": float(valid["rolling_var"].iloc[-1]),
        "latest_loss": float(valid["loss"].iloc[-1]),
        "exception_count": exception_count,
        "valid_days": valid_days,
        "exception_rate": exception_count / valid_days,
    }


def select_lookback(
    loss_data: pd.DataFrame,
    lookback_observations: int | None,
) -> pd.DataFrame:
    """Giới hạn số quan sát dùng để ước lượng VaR."""
    if lookback_observations is None:
        return loss_data.copy()

    return loss_data.tail(int(lookback_observations)).reset_index(drop=True)
