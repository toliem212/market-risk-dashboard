"""Tổng hợp bản đồ trạng thái rủi ro từ các phân hệ giám sát."""

from __future__ import annotations

import numpy as np
import pandas as pd


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"
STATUS_NOT_AVAILABLE = "—"

SEVERITY_RANK = {
    STATUS_NOT_AVAILABLE: -1,
    STATUS_NORMAL: 0,
    STATUS_WATCH: 1,
    STATUS_ALERT: 2,
}

HEATMAP_COLUMNS = [
    "Biến động",
    "Mặt bằng",
    "Cấu trúc kỳ hạn",
    "Thanh khoản / hoạt động",
    "Stress tổng hợp",
    "Chất lượng dữ liệu",
]

GROUP_ORDER = [
    "Ngoại hối",
    "Trái phiếu Chính phủ",
    "Liên ngân hàng",
    "Áp lực nguồn vốn",
    "Lãi suất huy động",
    "Căng thẳng đa yếu tố",
    "Chất lượng dữ liệu",
]


def _worst_status(statuses: pd.Series | list[str]) -> str:
    """Lấy trạng thái nghiêm trọng nhất trong một tập trạng thái."""
    values = pd.Series(statuses, dtype="object").dropna()
    values = values[values.isin(SEVERITY_RANK)]

    if values.empty:
        return STATUS_NOT_AVAILABLE

    max_rank = values.map(SEVERITY_RANK).max()
    for status, rank in SEVERITY_RANK.items():
        if rank == max_rank:
            return status

    return STATUS_NOT_AVAILABLE


def _indicator_pillar(group: str, indicator: str) -> str | None:
    """Ánh xạ chỉ báo về nhóm giám sát dùng trên heatmap."""
    text = str(indicator).lower()

    if group == "Ngoại hối":
        return "Biến động"

    if group == "Trái phiếu Chính phủ":
        return "Biến động"

    if group == "Liên ngân hàng":
        if "biến động lãi suất o/n" in text:
            return "Biến động"
        if "mặt bằng lãi suất o/n" in text:
            return "Mặt bằng"
        if "đảo chiều cấu trúc kỳ hạn" in text:
            return "Cấu trúc kỳ hạn"
        if "doanh số" in text:
            return "Thanh khoản / hoạt động"

    if group == "Áp lực nguồn vốn":
        return "Thanh khoản / hoạt động"

    if group == "Lãi suất huy động":
        if "điều chỉnh lãi suất" in text:
            return "Biến động"
        if "mặt bằng lãi suất" in text:
            return "Mặt bằng"
        if "chênh lệch" in text:
            return "Cấu trúc kỳ hạn"

    return None


def _stress_status(historical_stress_data: pd.DataFrame) -> tuple[str, pd.Timestamp, float, float, float]:
    """Đánh giá điểm stress mới nhất so với phân phối lịch sử của chính chỉ số."""
    if historical_stress_data is None or historical_stress_data.empty:
        return STATUS_NOT_AVAILABLE, pd.NaT, np.nan, np.nan, np.nan

    valid = historical_stress_data.dropna(subset=["date", "stress_score"]).copy()
    if valid.empty:
        return STATUS_NOT_AVAILABLE, pd.NaT, np.nan, np.nan, np.nan

    valid = valid.sort_values("date")
    latest = valid.iloc[-1]
    score = valid["stress_score"].dropna()

    if len(score) < 30:
        return STATUS_NOT_AVAILABLE, latest["date"], latest["stress_score"], np.nan, np.nan

    p95 = float(score.quantile(0.95))
    p99 = float(score.quantile(0.99))
    latest_score = float(latest["stress_score"])

    if latest_score >= p99:
        status = STATUS_ALERT
    elif latest_score >= p95:
        status = STATUS_WATCH
    else:
        status = STATUS_NORMAL

    return status, pd.Timestamp(latest["date"]), latest_score, p95, p99


def _quality_status(quality_report: pd.DataFrame) -> str:
    """Tổng hợp trạng thái chất lượng dữ liệu từ danh mục kiểm tra."""
    if quality_report is None or quality_report.empty:
        return STATUS_NOT_AVAILABLE

    flagged = quality_report[pd.to_numeric(quality_report["Số trường hợp"], errors="coerce").fillna(0) > 0]
    if flagged.empty:
        return STATUS_NORMAL

    critical = flagged[flagged["Mức độ"].eq("Quan trọng")]
    if not critical.empty:
        return STATUS_ALERT

    return STATUS_WATCH


def build_risk_heatmap(
    alert_snapshot: pd.DataFrame,
    quality_report: pd.DataFrame,
    historical_stress_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tạo ma trận Risk Factor × Risk Dimension × Status."""
    rows: list[dict[str, object]] = []

    market_groups = [
        "Ngoại hối",
        "Trái phiếu Chính phủ",
        "Liên ngân hàng",
        "Áp lực nguồn vốn",
        "Lãi suất huy động",
    ]

    snapshot = alert_snapshot.copy() if alert_snapshot is not None else pd.DataFrame()

    for group in market_groups:
        row: dict[str, object] = {
            "Nhóm rủi ro": group,
            "Ngày dữ liệu": pd.NaT,
        }
        for column in HEATMAP_COLUMNS:
            row[column] = STATUS_NOT_AVAILABLE

        group_data = snapshot[snapshot["group"].eq(group)].copy() if not snapshot.empty else pd.DataFrame()

        if not group_data.empty:
            row["Ngày dữ liệu"] = pd.to_datetime(group_data["date"], errors="coerce").max()

            group_data["pillar"] = group_data.apply(
                lambda item: _indicator_pillar(item["group"], item["indicator"]),
                axis=1,
            )

            for pillar in HEATMAP_COLUMNS:
                pillar_rows = group_data[group_data["pillar"].eq(pillar)]
                if not pillar_rows.empty:
                    row[pillar] = _worst_status(pillar_rows["status"])

        row["Trạng thái chung"] = _worst_status([row[column] for column in HEATMAP_COLUMNS])
        rows.append(row)

    stress_status, stress_date, _, _, _ = _stress_status(historical_stress_data)
    stress_row: dict[str, object] = {
        "Nhóm rủi ro": "Căng thẳng đa yếu tố",
        "Ngày dữ liệu": stress_date,
        **{column: STATUS_NOT_AVAILABLE for column in HEATMAP_COLUMNS},
    }
    stress_row["Stress tổng hợp"] = stress_status
    stress_row["Trạng thái chung"] = stress_status
    rows.append(stress_row)

    quality_row: dict[str, object] = {
        "Nhóm rủi ro": "Chất lượng dữ liệu",
        "Ngày dữ liệu": pd.NaT,
        **{column: STATUS_NOT_AVAILABLE for column in HEATMAP_COLUMNS},
    }
    quality_row["Chất lượng dữ liệu"] = _quality_status(quality_report)
    quality_row["Trạng thái chung"] = quality_row["Chất lượng dữ liệu"]
    rows.append(quality_row)

    result = pd.DataFrame(rows)
    order = {group: index for index, group in enumerate(GROUP_ORDER)}
    result["_order"] = result["Nhóm rủi ro"].map(order).fillna(len(order))

    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def build_risk_heatmap_detail(
    alert_snapshot: pd.DataFrame,
    quality_report: pd.DataFrame,
    historical_stress_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tạo bảng chi tiết các tín hiệu làm cơ sở cho heatmap."""
    rows: list[dict[str, object]] = []

    if alert_snapshot is not None and not alert_snapshot.empty:
        for _, item in alert_snapshot.iterrows():
            rows.append(
                {
                    "Ngày dữ liệu": pd.to_datetime(item.get("date"), errors="coerce"),
                    "Nhóm rủi ro": item.get("group", ""),
                    "Khía cạnh": _indicator_pillar(item.get("group", ""), item.get("indicator", "")) or "Khác",
                    "Chỉ báo": item.get("indicator", ""),
                    "Giá trị": item.get("value", np.nan),
                    "Đơn vị": item.get("value_unit", ""),
                    "Tín hiệu": item.get("signal", np.nan),
                    "Đơn vị tín hiệu": item.get("signal_unit", ""),
                    "Ngưỡng theo dõi": item.get("watch_threshold", np.nan),
                    "Ngưỡng cảnh báo": item.get("alert_threshold", np.nan),
                    "Trạng thái": item.get("status", STATUS_NORMAL),
                    "Mức độ": SEVERITY_RANK.get(item.get("status"), 0),
                }
            )

    stress_status, stress_date, stress_score, p95, p99 = _stress_status(historical_stress_data)
    if pd.notna(stress_date):
        rows.append(
            {
                "Ngày dữ liệu": stress_date,
                "Nhóm rủi ro": "Căng thẳng đa yếu tố",
                "Khía cạnh": "Stress tổng hợp",
                "Chỉ báo": "Điểm căng thẳng thị trường tổng hợp",
                "Giá trị": stress_score,
                "Đơn vị": "điểm",
                "Tín hiệu": stress_score,
                "Đơn vị tín hiệu": "điểm",
                "Ngưỡng theo dõi": p95,
                "Ngưỡng cảnh báo": p99,
                "Trạng thái": stress_status,
                "Mức độ": SEVERITY_RANK.get(stress_status, -1),
            }
        )

    if quality_report is not None and not quality_report.empty:
        for _, item in quality_report.iterrows():
            count = int(pd.to_numeric(item.get("Số trường hợp", 0), errors="coerce") or 0)
            if count <= 0:
                continue

            status = STATUS_ALERT if item.get("Mức độ") == "Quan trọng" else STATUS_WATCH
            rows.append(
                {
                    "Ngày dữ liệu": pd.NaT,
                    "Nhóm rủi ro": "Chất lượng dữ liệu",
                    "Khía cạnh": "Chất lượng dữ liệu",
                    "Chỉ báo": f"{item.get('Bộ dữ liệu', '')}: {item.get('Nội dung kiểm tra', '')}",
                    "Giá trị": count,
                    "Đơn vị": "trường hợp",
                    "Tín hiệu": count,
                    "Đơn vị tín hiệu": "trường hợp",
                    "Ngưỡng theo dõi": np.nan,
                    "Ngưỡng cảnh báo": np.nan,
                    "Trạng thái": status,
                    "Mức độ": SEVERITY_RANK[status],
                }
            )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["Mức độ", "Ngày dữ liệu", "Nhóm rủi ro", "Chỉ báo"],
        ascending=[False, False, True, True],
        na_position="last",
    ).reset_index(drop=True)


def summarize_risk_heatmap(matrix: pd.DataFrame) -> dict[str, object]:
    """Tóm tắt trạng thái ma trận rủi ro."""
    if matrix is None or matrix.empty:
        return {
            "overall_status": STATUS_NOT_AVAILABLE,
            "watch_cells": 0,
            "alert_cells": 0,
            "active_groups": 0,
            "evaluated_cells": 0,
        }

    status_values = matrix[HEATMAP_COLUMNS].stack()
    evaluated = status_values[status_values.ne(STATUS_NOT_AVAILABLE)]

    watch_cells = int(evaluated.eq(STATUS_WATCH).sum())
    alert_cells = int(evaluated.eq(STATUS_ALERT).sum())
    active_groups = int(matrix["Trạng thái chung"].isin([STATUS_WATCH, STATUS_ALERT]).sum())

    if alert_cells > 0:
        overall_status = STATUS_ALERT
    elif watch_cells > 0:
        overall_status = STATUS_WATCH
    elif not evaluated.empty:
        overall_status = STATUS_NORMAL
    else:
        overall_status = STATUS_NOT_AVAILABLE

    return {
        "overall_status": overall_status,
        "watch_cells": watch_cells,
        "alert_cells": alert_cells,
        "active_groups": active_groups,
        "evaluated_cells": int(len(evaluated)),
    }


def status_to_score(status: object) -> int:
    """Chuyển trạng thái sang điểm số phục vụ biểu đồ heatmap."""
    return SEVERITY_RANK.get(str(status), -1)
