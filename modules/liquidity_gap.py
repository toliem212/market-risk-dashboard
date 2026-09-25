"""
Liquidity Gap and Survival Horizon Monitor
==========================================

Khung mô phỏng cash-flow mismatch, Liquidity Gap và Survival Horizon.

Module không chứa dòng tiền, liquidity buffer hoặc dữ liệu bảng cân đối giả định.
Người dùng phải nhập hoặc tải dữ liệu trước khi hệ thống thực hiện tính toán.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH


SCENARIO_BASE = "Cơ sở"
SCENARIO_MODERATE = "Căng thẳng vừa"
SCENARIO_SEVERE = "Căng thẳng mạnh"
SCENARIO_CUSTOM = "Tùy chỉnh"

SCENARIO_OPTIONS = [
    SCENARIO_BASE,
    SCENARIO_MODERATE,
    SCENARIO_SEVERE,
    SCENARIO_CUSTOM,
]

# Đây là tham số kịch bản mô phỏng, không phải dữ liệu ngân hàng.
SCENARIO_PARAMETERS = {
    SCENARIO_BASE: {
        "inflow_haircut_pct": 0.0,
        "outflow_increase_pct": 0.0,
        "buffer_haircut_pct": 0.0,
    },
    SCENARIO_MODERATE: {
        "inflow_haircut_pct": 10.0,
        "outflow_increase_pct": 15.0,
        "buffer_haircut_pct": 10.0,
    },
    SCENARIO_SEVERE: {
        "inflow_haircut_pct": 25.0,
        "outflow_increase_pct": 30.0,
        "buffer_haircut_pct": 20.0,
    },
}

REQUIRED_COLUMNS = [
    "bucket",
    "start_day",
    "end_day",
    "cash_inflow",
    "cash_outflow",
]

BUCKET_STRUCTURE = [
    ("T+0", 0, 0),
    ("1 ngày", 1, 1),
    ("2-7 ngày", 2, 7),
    ("8-14 ngày", 8, 14),
    ("15-30 ngày", 15, 30),
    ("31-90 ngày", 31, 90),
    ("91-180 ngày", 91, 180),
    ("181-365 ngày", 181, 365),
]


def blank_liquidity_template() -> pd.DataFrame:
    """Tạo cash-flow ladder trống; chỉ giữ cấu trúc bucket thời gian."""
    return pd.DataFrame(
        {
            "bucket": [row[0] for row in BUCKET_STRUCTURE],
            "start_day": [row[1] for row in BUCKET_STRUCTURE],
            "end_day": [row[2] for row in BUCKET_STRUCTURE],
            "cash_inflow": np.nan,
            "cash_outflow": np.nan,
        }
    )


def default_liquidity_template() -> pd.DataFrame:
    """Alias tương thích ngược; trả về cash-flow ladder trống."""
    return blank_liquidity_template()


def liquidity_input_ready(data: pd.DataFrame) -> bool:
    """Kiểm tra cash inflow/outflow đã được nhập đầy đủ hay chưa."""
    if any(column not in data.columns for column in REQUIRED_COLUMNS):
        return False

    cash_columns = ["cash_inflow", "cash_outflow"]
    numeric = data[cash_columns].apply(pd.to_numeric, errors="coerce")
    return not numeric.isna().any().any()


def get_scenario_parameters(scenario: str) -> dict[str, float]:
    """Trả về tham số của kịch bản dựng sẵn."""
    if scenario == SCENARIO_CUSTOM:
        raise ValueError("Kịch bản tùy chỉnh không có bộ tham số cố định.")

    if scenario not in SCENARIO_PARAMETERS:
        raise ValueError(f"Kịch bản không hợp lệ: {scenario}")

    return SCENARIO_PARAMETERS[scenario].copy()


def _validate_input(data: pd.DataFrame) -> pd.DataFrame:
    """Kiểm tra và chuẩn hóa bảng dòng tiền đầu vào."""
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]

    if missing:
        raise ValueError("Bảng dòng tiền thiếu các cột bắt buộc: " + ", ".join(missing))

    result = data[REQUIRED_COLUMNS].copy()

    for column in ["start_day", "end_day", "cash_inflow", "cash_outflow"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    if result[["start_day", "end_day"]].isna().any().any():
        raise ValueError("Bucket thời gian có giá trị ngày không hợp lệ.")

    if result[["cash_inflow", "cash_outflow"]].isna().any().any():
        raise ValueError(
            "Chưa đủ dữ liệu dòng tiền. Hãy nhập cash inflow và cash outflow cho tất cả bucket."
        )

    if (result["start_day"] < 0).any() or (result["end_day"] < 0).any():
        raise ValueError("Ngày bắt đầu và kết thúc bucket không được âm.")

    if (result["end_day"] < result["start_day"]).any():
        raise ValueError("Ngày kết thúc bucket phải lớn hơn hoặc bằng ngày bắt đầu.")

    if (result[["cash_inflow", "cash_outflow"]] < 0).any().any():
        raise ValueError("Dòng tiền vào và dòng tiền ra không được âm.")

    result = result.sort_values(
        by=["start_day", "end_day"],
        kind="stable",
    ).reset_index(drop=True)

    if result["end_day"].duplicated().any():
        raise ValueError("Mỗi bucket cần có ngày kết thúc riêng biệt.")

    return result


def calculate_liquidity_gap(
    data: pd.DataFrame,
    opening_buffer: float,
    inflow_haircut_pct: float = 0.0,
    outflow_increase_pct: float = 0.0,
    buffer_haircut_pct: float = 0.0,
) -> pd.DataFrame:
    """Tính Liquidity Gap, Cumulative Gap và Liquidity Position."""
    result = _validate_input(data)

    if opening_buffer < 0:
        raise ValueError("Đệm thanh khoản ban đầu không được âm.")

    for value, label in [
        (inflow_haircut_pct, "Haircut dòng tiền vào"),
        (outflow_increase_pct, "Mức tăng dòng tiền ra"),
        (buffer_haircut_pct, "Haircut đệm thanh khoản"),
    ]:
        if value < 0 or value > 100:
            raise ValueError(f"{label} phải nằm trong khoảng 0%-100%.")

    effective_buffer = opening_buffer * (1 - buffer_haircut_pct / 100)

    result["base_net_flow"] = result["cash_inflow"] - result["cash_outflow"]
    result["base_cumulative_gap"] = result["base_net_flow"].cumsum()
    result["stressed_inflow"] = result["cash_inflow"] * (1 - inflow_haircut_pct / 100)
    result["stressed_outflow"] = result["cash_outflow"] * (
        1 + outflow_increase_pct / 100
    )
    result["stressed_net_flow"] = result["stressed_inflow"] - result["stressed_outflow"]
    result["stressed_cumulative_gap"] = result["stressed_net_flow"].cumsum()
    result["effective_buffer"] = effective_buffer
    result["liquidity_position"] = effective_buffer + result["stressed_cumulative_gap"]
    result["bucket_days"] = (result["end_day"] - result["start_day"] + 1).clip(lower=1)

    return result


def estimate_survival_horizon(results: pd.DataFrame) -> dict[str, object]:
    """Ước tính Survival Horizon bằng nội suy tuyến tính trong bucket."""
    if results.empty:
        return {
            "survival_day": np.nan,
            "survival_bucket": None,
            "depleted": False,
        }

    opening_buffer = float(results["effective_buffer"].iloc[0])
    previous_position = opening_buffer

    if previous_position < 0:
        return {
            "survival_day": 0.0,
            "survival_bucket": "Trước T+0",
            "depleted": True,
        }

    for row in results.itertuples(index=False):
        end_position = float(row.liquidity_position)

        if end_position < 0:
            net_flow = float(row.stressed_net_flow)
            bucket_days = max(float(row.bucket_days), 1.0)

            if net_flow >= 0:
                estimated_day = float(row.start_day)
            else:
                fraction = previous_position / abs(net_flow)
                fraction = min(max(fraction, 0.0), 1.0)
                estimated_day = float(row.start_day) + fraction * bucket_days

            return {
                "survival_day": estimated_day,
                "survival_bucket": row.bucket,
                "depleted": True,
            }

        previous_position = end_position

    return {
        "survival_day": float(results["end_day"].max()),
        "survival_bucket": f"> {int(results['end_day'].max())} ngày",
        "depleted": False,
    }


def classify_survival_horizon(
    survival_day: float,
    depleted: bool,
    alert_horizon_days: float = 30.0,
    watch_horizon_days: float = 60.0,
) -> str:
    """Phân loại Survival Horizon theo ngưỡng do người dùng cấu hình."""
    if not depleted or pd.isna(survival_day):
        return STATUS_NORMAL

    if survival_day < alert_horizon_days:
        return STATUS_ALERT

    if survival_day < watch_horizon_days:
        return STATUS_WATCH

    return STATUS_NORMAL


def _value_at_horizon(results: pd.DataFrame, horizon_days: int) -> tuple[float, float]:
    """Lấy cumulative gap và liquidity position tại bucket chứa horizon."""
    eligible = results[results["end_day"] >= horizon_days]
    row = results.iloc[-1] if eligible.empty else eligible.iloc[0]

    return (
        float(row["stressed_cumulative_gap"]),
        float(row["liquidity_position"]),
    )


def summarize_liquidity_gap(
    results: pd.DataFrame,
    alert_horizon_days: float = 30.0,
    watch_horizon_days: float = 60.0,
) -> dict[str, object]:
    """Tóm tắt các chỉ tiêu chính của Liquidity Gap Monitor."""
    if results.empty:
        return {
            "effective_buffer": np.nan,
            "gap_30d": np.nan,
            "position_30d": np.nan,
            "minimum_position": np.nan,
            "survival_day": np.nan,
            "survival_bucket": None,
            "depleted": False,
            "status": STATUS_NORMAL,
        }

    survival = estimate_survival_horizon(results)
    gap_30d, position_30d = _value_at_horizon(results, 30)

    status = classify_survival_horizon(
        survival_day=survival["survival_day"],
        depleted=survival["depleted"],
        alert_horizon_days=alert_horizon_days,
        watch_horizon_days=watch_horizon_days,
    )

    return {
        "effective_buffer": float(results["effective_buffer"].iloc[0]),
        "gap_30d": gap_30d,
        "position_30d": position_30d,
        "minimum_position": float(results["liquidity_position"].min()),
        "survival_day": survival["survival_day"],
        "survival_bucket": survival["survival_bucket"],
        "depleted": survival["depleted"],
        "status": status,
    }
