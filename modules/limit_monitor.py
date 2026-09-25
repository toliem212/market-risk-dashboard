"""
Trading Book Limit Monitoring
=============================

Khung giám sát mức sử dụng hạn mức cho Trading Book.

Module này không chứa vị thế, P&L, VaR, PV01/DV01 hoặc hạn mức giả định.
Người dùng phải nhập hoặc tải dữ liệu trước khi hệ thống thực hiện tính toán.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"
STATUS_BREACH = "Vi phạm"
STATUS_INVALID = "Dữ liệu lỗi"

STATUS_RANK = {
    STATUS_INVALID: 0,
    STATUS_NORMAL: 1,
    STATUS_WATCH: 2,
    STATUS_ALERT: 3,
    STATUS_BREACH: 4,
}

LIMIT_COLUMNS = [
    "limit_id",
    "book",
    "risk_type",
    "metric",
    "current_value",
    "limit_value",
    "unit",
    "watch_pct",
    "alert_pct",
]


# Chỉ gợi ý các loại chỉ tiêu thường gặp. Không chứa số liệu nội bộ.
LIMIT_FRAMEWORK_ROWS = [
    {
        "limit_id": "FX_NOP",
        "book": "FX Trading Book",
        "risk_type": "Ngoại hối",
        "metric": "Trạng thái ngoại hối ròng",
        "unit": "tỷ đồng quy đổi",
    },
    {
        "limit_id": "FX_STOP_LOSS",
        "book": "FX Trading Book",
        "risk_type": "P&L / Stop-loss",
        "metric": "Lỗ giao dịch trong ngày",
        "unit": "tỷ đồng",
    },
    {
        "limit_id": "TB_VAR",
        "book": "Trading Book tổng",
        "risk_type": "VaR",
        "metric": "VaR",
        "unit": "tỷ đồng",
    },
    {
        "limit_id": "FI_PV01",
        "book": "Fixed Income Trading Book",
        "risk_type": "Độ nhạy lãi suất",
        "metric": "PV01 / DV01",
        "unit": "triệu đồng/bp",
    },
    {
        "limit_id": "FI_POSITION",
        "book": "Fixed Income Trading Book",
        "risk_type": "Trạng thái",
        "metric": "Quy mô vị thế trái phiếu",
        "unit": "tỷ đồng",
    },
    {
        "limit_id": "TB_STRESS_LOSS",
        "book": "Trading Book tổng",
        "risk_type": "Stress loss",
        "metric": "Lỗ theo kịch bản stress",
        "unit": "tỷ đồng",
    },
]


def blank_limit_template() -> pd.DataFrame:
    """Tạo khung nhập hạn mức không chứa số liệu giả định."""
    rows = []

    for framework_row in LIMIT_FRAMEWORK_ROWS:
        row = {column: np.nan for column in LIMIT_COLUMNS}
        row.update(framework_row)
        rows.append(row)

    return pd.DataFrame(rows, columns=LIMIT_COLUMNS)


def default_limit_template() -> pd.DataFrame:
    """Alias tương thích ngược; trả về khung trống, không có số giả định."""
    return blank_limit_template()


def completed_limit_rows(limit_table: pd.DataFrame) -> pd.DataFrame:
    """Lấy các dòng đã đủ trường số để thực hiện giám sát."""
    if limit_table.empty:
        return pd.DataFrame(columns=LIMIT_COLUMNS)

    missing_columns = [column for column in LIMIT_COLUMNS if column not in limit_table.columns]
    if missing_columns:
        raise ValueError("Bảng hạn mức thiếu các cột: " + ", ".join(missing_columns))

    result = limit_table.copy()
    numeric_columns = ["current_value", "limit_value", "watch_pct", "alert_pct"]

    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    text_columns = ["limit_id", "book", "risk_type", "metric", "unit"]
    text_ready = pd.Series(True, index=result.index)

    for column in text_columns:
        text_ready &= result[column].astype("string").str.strip().fillna("").ne("")

    numeric_ready = result[numeric_columns].notna().all(axis=1)
    return result.loc[text_ready & numeric_ready, LIMIT_COLUMNS].reset_index(drop=True)


def count_partial_limit_rows(limit_table: pd.DataFrame) -> int:
    """Đếm số dòng có nhập dữ liệu nhưng chưa đủ để tính."""
    if limit_table.empty:
        return 0

    result = limit_table.copy()
    numeric_columns = ["current_value", "limit_value", "watch_pct", "alert_pct"]

    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    any_numeric = result[numeric_columns].notna().any(axis=1)
    all_numeric = result[numeric_columns].notna().all(axis=1)
    return int((any_numeric & ~all_numeric).sum())


def validate_limit_row(row: pd.Series) -> tuple[bool, str]:
    """Kiểm tra cấu hình một dòng hạn mức."""
    numeric_fields = ["current_value", "limit_value", "watch_pct", "alert_pct"]

    for field in numeric_fields:
        if pd.isna(row[field]):
            return False, f"Thiếu giá trị {field}."

    if float(row["limit_value"]) <= 0:
        return False, "Hạn mức phải lớn hơn 0."

    watch_pct = float(row["watch_pct"])
    alert_pct = float(row["alert_pct"])

    if watch_pct < 0 or alert_pct < 0:
        return False, "Ngưỡng sử dụng không được âm."

    if watch_pct >= alert_pct:
        return False, "Ngưỡng theo dõi phải thấp hơn ngưỡng cảnh báo."

    if alert_pct >= 100:
        return False, "Ngưỡng cảnh báo phải thấp hơn 100%."

    return True, ""


def classify_utilization(
    utilization_pct: float,
    watch_pct: float,
    alert_pct: float,
) -> str:
    """Phân loại trạng thái sử dụng hạn mức."""
    if pd.isna(utilization_pct):
        return STATUS_INVALID

    if utilization_pct >= 100:
        return STATUS_BREACH

    if utilization_pct >= alert_pct:
        return STATUS_ALERT

    if utilization_pct >= watch_pct:
        return STATUS_WATCH

    return STATUS_NORMAL


def recommended_action(status: str) -> str:
    """Đề xuất bước xử lý chung theo trạng thái."""
    if status == STATUS_BREACH:
        return (
            "Ghi nhận vi phạm; xác minh nguyên nhân; thực hiện escalation theo "
            "quy trình và theo dõi hành động khắc phục."
        )

    if status == STATUS_ALERT:
        return (
            "Rà soát vị thế, P&L và nguồn biến động; đánh giá khả năng giảm rủi ro "
            "và chuẩn bị escalation nếu mức sử dụng tiếp tục tăng."
        )

    if status == STATUS_WATCH:
        return (
            "Theo dõi sát diễn biến; kiểm tra xu hướng sử dụng hạn mức và các giao dịch "
            "có thể làm mức sử dụng tăng thêm."
        )

    if status == STATUS_INVALID:
        return "Sửa cấu hình hoặc dữ liệu đầu vào trước khi sử dụng kết quả."

    return "Tiếp tục giám sát định kỳ."


def evaluate_limits(limit_table: pd.DataFrame) -> pd.DataFrame:
    """Tính mức sử dụng, headroom và trạng thái của từng hạn mức."""
    required_columns = set(LIMIT_COLUMNS)
    missing_columns = required_columns.difference(limit_table.columns)

    if missing_columns:
        raise ValueError(
            "Bảng hạn mức thiếu các cột: " + ", ".join(sorted(missing_columns))
        )

    result = limit_table.copy()

    for column in ["current_value", "limit_value", "watch_pct", "alert_pct"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    valid_flags = []
    validation_messages = []
    utilization_values = []
    headroom_values = []
    breach_values = []
    statuses = []
    actions = []

    for _, row in result.iterrows():
        is_valid, message = validate_limit_row(row)
        valid_flags.append(is_valid)
        validation_messages.append(message)

        if not is_valid:
            utilization_values.append(np.nan)
            headroom_values.append(np.nan)
            breach_values.append(np.nan)
            statuses.append(STATUS_INVALID)
            actions.append(recommended_action(STATUS_INVALID))
            continue

        absolute_value = abs(float(row["current_value"]))
        limit_value = float(row["limit_value"])
        utilization_pct = absolute_value / limit_value * 100
        headroom = limit_value - absolute_value
        breach_amount = max(absolute_value - limit_value, 0.0)

        status = classify_utilization(
            utilization_pct=utilization_pct,
            watch_pct=float(row["watch_pct"]),
            alert_pct=float(row["alert_pct"]),
        )

        utilization_values.append(utilization_pct)
        headroom_values.append(headroom)
        breach_values.append(breach_amount)
        statuses.append(status)
        actions.append(recommended_action(status))

    result["is_valid"] = valid_flags
    result["validation_message"] = validation_messages
    result["utilization_pct"] = utilization_values
    result["headroom"] = headroom_values
    result["breach_amount"] = breach_values
    result["status"] = statuses
    result["action"] = actions
    result["severity_rank"] = result["status"].map(STATUS_RANK).fillna(0).astype(int)

    return result


def summarize_limits(evaluated_limits: pd.DataFrame) -> dict[str, object]:
    """Tổng hợp trạng thái toàn bộ hạn mức."""
    if evaluated_limits.empty:
        return {
            "overall_status": STATUS_NORMAL,
            "max_utilization_pct": np.nan,
            "normal_count": 0,
            "watch_count": 0,
            "alert_count": 0,
            "breach_count": 0,
            "invalid_count": 0,
            "active_count": 0,
        }

    valid_utilization = evaluated_limits["utilization_pct"].dropna()
    max_utilization = (
        float(valid_utilization.max()) if not valid_utilization.empty else np.nan
    )

    counts = evaluated_limits["status"].value_counts()
    normal_count = int(counts.get(STATUS_NORMAL, 0))
    watch_count = int(counts.get(STATUS_WATCH, 0))
    alert_count = int(counts.get(STATUS_ALERT, 0))
    breach_count = int(counts.get(STATUS_BREACH, 0))
    invalid_count = int(counts.get(STATUS_INVALID, 0))

    if breach_count > 0:
        overall_status = STATUS_BREACH
    elif alert_count > 0:
        overall_status = STATUS_ALERT
    elif watch_count > 0:
        overall_status = STATUS_WATCH
    elif invalid_count > 0:
        overall_status = STATUS_INVALID
    else:
        overall_status = STATUS_NORMAL

    return {
        "overall_status": overall_status,
        "max_utilization_pct": max_utilization,
        "normal_count": normal_count,
        "watch_count": watch_count,
        "alert_count": alert_count,
        "breach_count": breach_count,
        "invalid_count": invalid_count,
        "active_count": watch_count + alert_count + breach_count,
    }


def build_exception_log(
    evaluated_limits: pd.DataFrame,
    include_watch: bool = True,
) -> pd.DataFrame:
    """Lấy danh sách các hạn mức cần theo dõi hoặc xử lý."""
    if evaluated_limits.empty:
        return evaluated_limits.copy()

    active_statuses = [STATUS_ALERT, STATUS_BREACH, STATUS_INVALID]

    if include_watch:
        active_statuses.insert(0, STATUS_WATCH)

    exceptions = evaluated_limits[
        evaluated_limits["status"].isin(active_statuses)
    ].copy()

    return exceptions.sort_values(
        by=["severity_rank", "utilization_pct"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)
