"""Tổng hợp trạng thái vận hành cho quy trình giám sát rủi ro thị trường."""

from __future__ import annotations

import pandas as pd

STATUS_NORMAL = "Bình thường"
STATUS_REVIEW = "Cần kiểm tra"
STATUS_READY = "Sẵn sàng"
STATUS_INPUT = "Cần nhập liệu"
STATUS_MISSING = "Chưa có dữ liệu"

STATUS_ORDER = {
    STATUS_NORMAL: 0,
    STATUS_READY: 0,
    STATUS_REVIEW: 1,
    STATUS_INPUT: 2,
    STATUS_MISSING: 3,
}


def build_control_tower_table(
    *,
    alert_summary: dict[str, object],
    quality_summary: dict[str, object],
    workflow_summary: dict[str, object],
    historical_stress_observations: int,
    bond_data_available: bool,
) -> pd.DataFrame:
    """Tạo bảng trạng thái theo chuỗi kiểm soát hằng ngày."""
    critical_checks = int(quality_summary.get("critical_check_count", 0) or 0)
    flagged_checks = int(quality_summary.get("flagged_check_count", 0) or 0)
    data_status = STATUS_REVIEW if flagged_checks > 0 else STATUS_NORMAL
    data_result = (
        f"{flagged_checks} phép kiểm tra có ngoại lệ; "
        f"{critical_checks} phép kiểm tra quan trọng"
        if flagged_checks > 0
        else "Không có phép kiểm tra bị gắn cờ"
    )

    open_alerts = int(alert_summary.get("open_count", 0) or 0)
    watch_count = int(alert_summary.get("watch_count", 0) or 0)
    alert_count = int(alert_summary.get("alert_count", 0) or 0)
    market_status = STATUS_REVIEW if open_alerts > 0 else STATUS_NORMAL
    market_result = (
        f"{open_alerts} tín hiệu đang mở: {watch_count} Theo dõi, "
        f"{alert_count} Cảnh báo"
        if open_alerts > 0
        else "Không có tín hiệu vượt ngưỡng hiện tại"
    )

    workflow_open = int(workflow_summary.get("open_count", 0) or 0)
    workflow_overdue = int(workflow_summary.get("overdue_count", 0) or 0)
    workflow_status = STATUS_REVIEW if workflow_open > 0 or workflow_overdue > 0 else STATUS_NORMAL
    if workflow_overdue > 0:
        workflow_result = f"{workflow_open} hồ sơ đang mở; {workflow_overdue} hồ sơ quá SLA"
    elif workflow_open > 0:
        workflow_result = f"{workflow_open} hồ sơ đang mở"
    else:
        workflow_result = "Không có hồ sơ xử lý đang mở"

    stress_status = STATUS_READY if historical_stress_observations > 0 else STATUS_MISSING
    stress_result = (
        f"Thư viện có {historical_stress_observations:,} phiên lịch sử".replace(",", ".")
        if historical_stress_observations > 0
        else "Chưa đủ dữ liệu để xây dựng kịch bản lịch sử"
    )

    bond_status = STATUS_READY if bond_data_available else STATUS_MISSING
    bond_result = (
        "Đã có dữ liệu đường cong lợi suất"
        if bond_data_available
        else "Chưa có dữ liệu đường cong lợi suất TPCP"
    )

    rows = [
        {
            "step": 1,
            "control": "Kiểm soát dữ liệu",
            "scope": "FX, liên ngân hàng, huy động",
            "status": data_status,
            "result": data_result,
            "destination": "Kiểm soát dữ liệu",
        },
        {
            "step": 2,
            "control": "Giám sát biến động thị trường",
            "scope": "FX, O/N, đường cong, doanh số, funding",
            "status": market_status,
            "result": market_result,
            "destination": "Bản đồ rủi ro / các monitor thị trường",
        },
        {
            "step": 3,
            "control": "Cảnh báo sớm",
            "scope": "Ngưỡng thống kê và tín hiệu bất thường",
            "status": market_status,
            "result": market_result,
            "destination": "Trung tâm cảnh báo",
        },
        {
            "step": 4,
            "control": "Kiểm tra sức chịu đựng",
            "scope": "Kịch bản lịch sử, định sẵn và tùy chỉnh",
            "status": stress_status,
            "result": stress_result,
            "destination": "Kiểm tra sức chịu đựng",
        },
        {
            "step": 5,
            "control": "VaR & ES",
            "scope": "FX và lãi suất",
            "status": STATUS_READY,
            "result": "Đủ dữ liệu thị trường; quy mô phơi nhiễm được nhập khi chạy",
            "destination": "VaR & ES",
        },
        {
            "step": 6,
            "control": "Kiểm định lại VaR",
            "scope": "Exception rate và kiểm định thống kê",
            "status": STATUS_READY,
            "result": "Đủ chuỗi dữ liệu để thực hiện kiểm định lại",
            "destination": "Kiểm định lại VaR",
        },
        {
            "step": 7,
            "control": "Theo dõi xử lý cảnh báo",
            "scope": "Hồ sơ, chuyển cấp và SLA",
            "status": workflow_status,
            "result": workflow_result,
            "destination": "Theo dõi xử lý cảnh báo",
        },
        {
            "step": 8,
            "control": "Giám sát hạn mức sổ kinh doanh",
            "scope": "Position, VaR, PV01, Stop-Loss và hạn mức liên quan",
            "status": STATUS_INPUT,
            "result": "Cần dữ liệu vị thế và hạn mức",
            "destination": "Hạn mức sổ kinh doanh · Nhập liệu",
        },
        {
            "step": 9,
            "control": "IRRBB",
            "scope": "Repricing Gap, NII và EVE",
            "status": STATUS_INPUT,
            "result": "Cần dữ liệu RSA/RSL và giả định định giá lại",
            "destination": "IRRBB · Nhập liệu",
        },
        {
            "step": 10,
            "control": "Thanh khoản",
            "scope": "Liquidity Gap và Survival Horizon",
            "status": STATUS_INPUT,
            "result": "Cần dòng tiền vào/ra và đệm thanh khoản",
            "destination": "Thanh khoản · Nhập liệu",
        },
        {
            "step": 11,
            "control": "Trái phiếu Chính phủ",
            "scope": "Yield curve và biến động lợi suất",
            "status": bond_status,
            "result": bond_result,
            "destination": "Trái phiếu / Đường cong lợi suất",
        },
    ]

    return pd.DataFrame(rows)


def summarize_control_tower(table: pd.DataFrame) -> dict[str, int]:
    """Tổng hợp số lượng trạng thái trong bảng Control Tower."""
    if table.empty:
        return {
            "normal_count": 0,
            "review_count": 0,
            "ready_count": 0,
            "input_count": 0,
            "missing_count": 0,
        }

    return {
        "normal_count": int(table["status"].eq(STATUS_NORMAL).sum()),
        "review_count": int(table["status"].eq(STATUS_REVIEW).sum()),
        "ready_count": int(table["status"].eq(STATUS_READY).sum()),
        "input_count": int(table["status"].eq(STATUS_INPUT).sum()),
        "missing_count": int(table["status"].eq(STATUS_MISSING).sum()),
    }


def build_priority_items(
    *,
    alert_summary: dict[str, object],
    quality_summary: dict[str, object],
    workflow_summary: dict[str, object],
    bond_data_available: bool,
) -> pd.DataFrame:
    """Tạo danh sách điểm cần xử lý dựa trên trạng thái hiện tại."""
    rows: list[dict[str, str]] = []

    critical_checks = int(quality_summary.get("critical_check_count", 0) or 0)
    flagged_checks = int(quality_summary.get("flagged_check_count", 0) or 0)
    if critical_checks > 0:
        rows.append(
            {
                "priority": "Cao",
                "item": "Đối chiếu các phép kiểm tra dữ liệu quan trọng đang có ngoại lệ",
                "source": "Kiểm soát dữ liệu",
            }
        )
    elif flagged_checks > 0:
        rows.append(
            {
                "priority": "Theo dõi",
                "item": "Rà soát các ngoại lệ dữ liệu đang được gắn cờ",
                "source": "Kiểm soát dữ liệu",
            }
        )

    alert_count = int(alert_summary.get("alert_count", 0) or 0)
    watch_count = int(alert_summary.get("watch_count", 0) or 0)
    if alert_count > 0:
        rows.append(
            {
                "priority": "Cao",
                "item": f"Xác minh {alert_count} tín hiệu đang ở mức Cảnh báo",
                "source": "Trung tâm cảnh báo",
            }
        )
    if watch_count > 0:
        rows.append(
            {
                "priority": "Theo dõi",
                "item": f"Theo dõi {watch_count} tín hiệu đang ở mức Theo dõi",
                "source": "Trung tâm cảnh báo",
            }
        )

    overdue_count = int(workflow_summary.get("overdue_count", 0) or 0)
    if overdue_count > 0:
        rows.append(
            {
                "priority": "Cao",
                "item": f"Xử lý {overdue_count} hồ sơ đã quá SLA",
                "source": "Theo dõi xử lý cảnh báo",
            }
        )

    if not bond_data_available:
        rows.append(
            {
                "priority": "Dữ liệu",
                "item": "Chưa có chuỗi đường cong lợi suất TPCP trong nguồn dữ liệu hiện tại",
                "source": "Trái phiếu / Đường cong lợi suất",
            }
        )

    return pd.DataFrame(rows)
