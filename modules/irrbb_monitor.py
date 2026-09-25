"""
IRRBB and Repricing Gap Monitor
===============================

Khung mô phỏng IRRBB bằng Repricing Gap, NII sensitivity và EVE proxy.

Module không chứa RSA, RSL, duration hoặc số liệu banking book giả định.
Người dùng phải nhập hoặc tải dữ liệu trước khi hệ thống thực hiện tính toán.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


SCENARIO_PARALLEL_UP = "Song song tăng"
SCENARIO_PARALLEL_DOWN = "Song song giảm"
SCENARIO_STEEPENER = "Đường cong dốc lên"
SCENARIO_FLATTENER = "Đường cong phẳng hơn"
SCENARIO_CUSTOM = "Tự nhập theo bucket"

SCENARIO_OPTIONS = [
    SCENARIO_PARALLEL_UP,
    SCENARIO_PARALLEL_DOWN,
    SCENARIO_STEEPENER,
    SCENARIO_FLATTENER,
    SCENARIO_CUSTOM,
]

BUCKETS = [
    "Không kỳ hạn / O/N",
    "≤ 1 tháng",
    "> 1-3 tháng",
    "> 3-6 tháng",
    "> 6-12 tháng",
    "> 1-2 năm",
    "> 2-5 năm",
    "> 5 năm",
]

REQUIRED_COLUMNS = [
    "bucket",
    "midpoint_years",
    "rsa",
    "rsl",
    "asset_duration",
    "liability_duration",
    "custom_shock_bps",
]


def blank_repricing_template() -> pd.DataFrame:
    """Tạo khung IRRBB không chứa số liệu balance sheet giả định."""
    return pd.DataFrame(
        {
            "bucket": BUCKETS,
            "midpoint_years": np.nan,
            "rsa": np.nan,
            "rsl": np.nan,
            "asset_duration": np.nan,
            "liability_duration": np.nan,
            "custom_shock_bps": np.nan,
        }
    )


def default_repricing_template() -> pd.DataFrame:
    """Alias tương thích ngược; trả về khung trống."""
    return blank_repricing_template()


def irrbb_input_ready(data: pd.DataFrame, scenario: str) -> bool:
    """Kiểm tra dữ liệu đã đủ để chạy mô phỏng IRRBB hay chưa."""
    required = [
        "midpoint_years",
        "rsa",
        "rsl",
        "asset_duration",
        "liability_duration",
    ]

    if any(column not in data.columns for column in required):
        return False

    numeric = data[required].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        return False

    if scenario == SCENARIO_CUSTOM:
        if "custom_shock_bps" not in data.columns:
            return False
        custom = pd.to_numeric(data["custom_shock_bps"], errors="coerce")
        if custom.isna().any():
            return False

    return True


def validate_repricing_input(
    data: pd.DataFrame,
    require_custom_shock: bool = False,
) -> pd.DataFrame:
    """Kiểm tra và chuẩn hóa dữ liệu RSA/RSL do người dùng nhập."""
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]

    if missing:
        raise ValueError("Bảng IRRBB thiếu các cột bắt buộc: " + ", ".join(missing))

    cleaned = data[REQUIRED_COLUMNS].copy()
    numeric_columns = [
        "midpoint_years",
        "rsa",
        "rsl",
        "asset_duration",
        "liability_duration",
    ]

    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned["custom_shock_bps"] = pd.to_numeric(
        cleaned["custom_shock_bps"], errors="coerce"
    )

    if cleaned[numeric_columns].isna().any().any():
        raise ValueError(
            "Chưa đủ dữ liệu IRRBB. Hãy nhập midpoint, RSA, RSL và duration cho tất cả bucket."
        )

    if require_custom_shock and cleaned["custom_shock_bps"].isna().any():
        raise ValueError(
            "Kịch bản tự nhập yêu cầu shock bps cho tất cả bucket."
        )

    if not require_custom_shock:
        cleaned["custom_shock_bps"] = cleaned["custom_shock_bps"].fillna(0.0)

    non_negative_columns = [
        "midpoint_years",
        "rsa",
        "rsl",
        "asset_duration",
        "liability_duration",
    ]

    if (cleaned[non_negative_columns] < 0).any().any():
        raise ValueError("RSA, RSL, kỳ hạn và duration không được nhận giá trị âm.")

    if cleaned["bucket"].astype(str).str.strip().eq("").any():
        raise ValueError("Tên bucket không được để trống.")

    cleaned["bucket"] = cleaned["bucket"].astype(str).str.strip()
    return cleaned.reset_index(drop=True)


def build_shock_curve(
    data: pd.DataFrame,
    scenario: str,
    shock_size_bps: float,
) -> pd.Series:
    """Tạo cú sốc lãi suất theo từng bucket cho kịch bản mô phỏng."""
    n_buckets = len(data)

    if n_buckets == 0:
        return pd.Series(dtype="float64")

    magnitude = abs(float(shock_size_bps))

    if scenario == SCENARIO_PARALLEL_UP:
        shocks = np.full(n_buckets, magnitude)
    elif scenario == SCENARIO_PARALLEL_DOWN:
        shocks = np.full(n_buckets, -magnitude)
    elif scenario == SCENARIO_STEEPENER:
        shocks = np.linspace(-magnitude, magnitude, n_buckets)
    elif scenario == SCENARIO_FLATTENER:
        shocks = np.linspace(magnitude, -magnitude, n_buckets)
    elif scenario == SCENARIO_CUSTOM:
        shocks = data["custom_shock_bps"].to_numpy(dtype=float)
    else:
        raise ValueError(f"Kịch bản IRRBB không hợp lệ: {scenario}")

    return pd.Series(shocks, index=data.index, dtype="float64")


def nii_horizon_weight(midpoint_years: pd.Series) -> pd.Series:
    """Tính trọng số static-gap cho NII horizon một năm."""
    return (1.0 - midpoint_years.astype(float)).clip(lower=0.0, upper=1.0)


def calculate_irrbb(
    data: pd.DataFrame,
    scenario: str,
    shock_size_bps: float = 200.0,
) -> pd.DataFrame:
    """Tính Repricing Gap, NII sensitivity và duration-based EVE proxy."""
    result = validate_repricing_input(
        data,
        require_custom_shock=(scenario == SCENARIO_CUSTOM),
    )

    result["shock_bps"] = build_shock_curve(
        result,
        scenario=scenario,
        shock_size_bps=shock_size_bps,
    )

    result["repricing_gap"] = result["rsa"] - result["rsl"]
    result["cumulative_gap"] = result["repricing_gap"].cumsum()

    total_balance = result["rsa"] + result["rsl"]
    result["gap_share_pct"] = np.where(
        total_balance > 0,
        result["repricing_gap"] / total_balance * 100,
        np.nan,
    )

    result["nii_weight"] = nii_horizon_weight(result["midpoint_years"])
    shock_decimal = result["shock_bps"] / 10_000.0

    result["nii_impact"] = (
        result["repricing_gap"] * shock_decimal * result["nii_weight"]
    )
    result["asset_pv_impact"] = (
        -result["rsa"] * result["asset_duration"] * shock_decimal
    )
    result["liability_pv_impact"] = (
        -result["rsl"] * result["liability_duration"] * shock_decimal
    )
    result["eve_proxy_impact"] = (
        result["asset_pv_impact"] - result["liability_pv_impact"]
    )

    return result


def summarize_irrbb(
    results: pd.DataFrame,
    reference_equity: float | None = None,
    reference_nii: float | None = None,
) -> dict[str, float | str]:
    """Tóm tắt các chỉ tiêu IRRBB mô phỏng."""
    if results.empty:
        return {
            "total_rsa": 0.0,
            "total_rsl": 0.0,
            "net_gap": 0.0,
            "absolute_gap": 0.0,
            "nii_impact": 0.0,
            "eve_proxy_impact": 0.0,
            "nii_impact_pct": np.nan,
            "eve_proxy_pct": np.nan,
            "gap_direction": "Trung tính",
        }

    total_rsa = float(results["rsa"].sum())
    total_rsl = float(results["rsl"].sum())
    net_gap = float(results["repricing_gap"].sum())
    absolute_gap = float(results["repricing_gap"].abs().sum())
    nii_impact = float(results["nii_impact"].sum())
    eve_proxy_impact = float(results["eve_proxy_impact"].sum())

    if net_gap > 0:
        gap_direction = "Nhạy cảm tài sản"
    elif net_gap < 0:
        gap_direction = "Nhạy cảm nguồn vốn"
    else:
        gap_direction = "Trung tính"

    nii_impact_pct = np.nan
    if reference_nii is not None and reference_nii > 0:
        nii_impact_pct = nii_impact / float(reference_nii) * 100

    eve_proxy_pct = np.nan
    if reference_equity is not None and reference_equity > 0:
        eve_proxy_pct = eve_proxy_impact / float(reference_equity) * 100

    return {
        "total_rsa": total_rsa,
        "total_rsl": total_rsl,
        "net_gap": net_gap,
        "absolute_gap": absolute_gap,
        "nii_impact": nii_impact,
        "eve_proxy_impact": eve_proxy_impact,
        "nii_impact_pct": nii_impact_pct,
        "eve_proxy_pct": eve_proxy_pct,
        "gap_direction": gap_direction,
    }
