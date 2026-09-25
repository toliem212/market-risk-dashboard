"""Theo dõi vòng đời xử lý cảnh báo rủi ro thị trường."""

from __future__ import annotations

from hashlib import sha1
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


STATUS_NEW = "Mới phát sinh"
STATUS_VERIFYING = "Đang xác minh"
STATUS_ESCALATED = "Đã chuyển cấp"
STATUS_HANDLING = "Đang xử lý"
STATUS_RESOLVED = "Đã xử lý"
STATUS_CLOSED = "Đóng"

WORKFLOW_STATUSES = [
    STATUS_NEW,
    STATUS_VERIFYING,
    STATUS_ESCALATED,
    STATUS_HANDLING,
    STATUS_RESOLVED,
    STATUS_CLOSED,
]

SEVERITY_ORDER = {
    "Bình thường": 0,
    "Theo dõi": 1,
    "Cảnh báo": 2,
}

CASE_COLUMNS = [
    "case_id",
    "source_date",
    "group",
    "indicator",
    "severity",
    "value",
    "value_unit",
    "signal",
    "signal_unit",
    "watch_threshold",
    "alert_threshold",
    "signal_active",
    "workflow_status",
    "owner",
    "action_note",
    "first_seen_at",
    "last_seen_at",
    "updated_at",
    "closed_at",
]

EVENT_COLUMNS = [
    "event_time",
    "case_id",
    "field",
    "old_value",
    "new_value",
]


def local_now() -> pd.Timestamp:
    """Thời gian hiện tại theo múi giờ Việt Nam, lưu ở dạng naive timestamp."""
    return pd.Timestamp.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).tz_localize(None)


def _empty_cases() -> pd.DataFrame:
    return pd.DataFrame(columns=CASE_COLUMNS)


def _empty_events() -> pd.DataFrame:
    return pd.DataFrame(columns=EVENT_COLUMNS)


def _normalize_cases(frame: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa cấu trúc kho hồ sơ xử lý."""
    if frame is None or frame.empty:
        return _empty_cases()

    result = frame.copy()
    for column in CASE_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    for column in ["source_date", "first_seen_at", "last_seen_at", "updated_at", "closed_at"]:
        result[column] = pd.to_datetime(result[column], errors="coerce")

    result["signal_active"] = result["signal_active"].astype("boolean").fillna(False)
    result["workflow_status"] = result["workflow_status"].fillna(STATUS_NEW)
    result["owner"] = result["owner"].fillna("").astype(str)
    result["action_note"] = result["action_note"].fillna("").astype(str)

    numeric_columns = [
        "value",
        "signal",
        "watch_threshold",
        "alert_threshold",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    return result[CASE_COLUMNS].copy()


def _normalize_events(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_events()

    result = frame.copy()
    for column in EVENT_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    result["event_time"] = pd.to_datetime(result["event_time"], errors="coerce")
    return result[EVENT_COLUMNS].copy()


def load_case_store(path: Path) -> pd.DataFrame:
    """Đọc kho hồ sơ cảnh báo đã lưu."""
    if not path.exists():
        return _empty_cases()

    try:
        return _normalize_cases(pd.read_csv(path))
    except (OSError, ValueError, pd.errors.ParserError):
        return _empty_cases()


def load_event_store(path: Path) -> pd.DataFrame:
    """Đọc nhật ký thay đổi trạng thái."""
    if not path.exists():
        return _empty_events()

    try:
        return _normalize_events(pd.read_csv(path))
    except (OSError, ValueError, pd.errors.ParserError):
        return _empty_events()


def save_case_store(frame: pd.DataFrame, path: Path) -> None:
    """Lưu kho hồ sơ cảnh báo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _normalize_cases(frame).to_csv(path, index=False, encoding="utf-8-sig")


def save_event_store(frame: pd.DataFrame, path: Path) -> None:
    """Lưu nhật ký thay đổi."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _normalize_events(frame).to_csv(path, index=False, encoding="utf-8-sig")


def _case_id(group: str, indicator: str, source_date: object) -> str:
    date_text = pd.to_datetime(source_date, errors="coerce")
    if pd.isna(date_text):
        date_key = "unknown"
    else:
        date_key = date_text.strftime("%Y-%m-%d")

    raw = f"{group}|{indicator}|{date_key}"
    return sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def _find_open_case(cases: pd.DataFrame, group: str, indicator: str) -> pd.Index:
    if cases.empty:
        return pd.Index([])

    return cases.index[
        cases["group"].eq(group)
        & cases["indicator"].eq(indicator)
        & cases["workflow_status"].ne(STATUS_CLOSED)
    ]


def sync_current_alerts(
    snapshot: pd.DataFrame,
    cases: pd.DataFrame,
    now: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, int]:
    """Đồng bộ các tín hiệu Theo dõi/Cảnh báo hiện tại vào sổ xử lý."""
    now = local_now() if now is None else pd.Timestamp(now)
    result = _normalize_cases(cases)

    if snapshot is None or snapshot.empty:
        if not result.empty:
            result["signal_active"] = False
        return result, 0

    active_snapshot = snapshot[snapshot["status"].isin(["Theo dõi", "Cảnh báo"])].copy()
    active_pairs = set(zip(active_snapshot["group"], active_snapshot["indicator"]))

    if not result.empty:
        result["signal_active"] = [
            (group, indicator) in active_pairs
            for group, indicator in zip(result["group"], result["indicator"])
        ]

    new_count = 0

    for _, row in active_snapshot.iterrows():
        group = str(row["group"])
        indicator = str(row["indicator"])
        open_indices = _find_open_case(result, group, indicator)

        if len(open_indices) > 0:
            idx = open_indices[-1]
            result.loc[idx, "source_date"] = pd.to_datetime(row["date"], errors="coerce")
            result.loc[idx, "severity"] = row["status"]
            result.loc[idx, "value"] = row.get("value", pd.NA)
            result.loc[idx, "value_unit"] = row.get("value_unit", "")
            result.loc[idx, "signal"] = row.get("signal", pd.NA)
            result.loc[idx, "signal_unit"] = row.get("signal_unit", "")
            result.loc[idx, "watch_threshold"] = row.get("watch_threshold", pd.NA)
            result.loc[idx, "alert_threshold"] = row.get("alert_threshold", pd.NA)
            result.loc[idx, "signal_active"] = True
            result.loc[idx, "last_seen_at"] = now
            continue

        case_id = _case_id(group, indicator, row["date"])
        same_case = result["case_id"].eq(case_id) if not result.empty else pd.Series(dtype=bool)
        if not result.empty and same_case.any():
            continue

        new_row = {
            "case_id": case_id,
            "source_date": pd.to_datetime(row["date"], errors="coerce"),
            "group": group,
            "indicator": indicator,
            "severity": row["status"],
            "value": row.get("value", pd.NA),
            "value_unit": row.get("value_unit", ""),
            "signal": row.get("signal", pd.NA),
            "signal_unit": row.get("signal_unit", ""),
            "watch_threshold": row.get("watch_threshold", pd.NA),
            "alert_threshold": row.get("alert_threshold", pd.NA),
            "signal_active": True,
            "workflow_status": STATUS_NEW,
            "owner": "",
            "action_note": "",
            "first_seen_at": now,
            "last_seen_at": now,
            "updated_at": now,
            "closed_at": pd.NaT,
        }

        new_frame = pd.DataFrame([new_row])
        if result.empty:
            result = new_frame
        else:
            result = pd.concat([result, new_frame], ignore_index=True)
        new_count += 1

    return _normalize_cases(result), new_count


def enrich_case_metrics(
    cases: pd.DataFrame,
    watch_sla_hours: float,
    alert_sla_hours: float,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Tính tuổi hồ sơ và trạng thái SLA."""
    now = local_now() if now is None else pd.Timestamp(now)
    result = _normalize_cases(cases)

    if result.empty:
        result["age_hours"] = pd.Series(dtype=float)
        result["sla_hours"] = pd.Series(dtype=float)
        result["sla_status"] = pd.Series(dtype=str)
        result["severity_rank"] = pd.Series(dtype=int)
        return result

    effective_end = result["closed_at"].where(result["closed_at"].notna(), now)
    result["age_hours"] = (
        (effective_end - result["first_seen_at"]).dt.total_seconds() / 3600
    ).clip(lower=0)

    result["sla_hours"] = result["severity"].map(
        {
            "Theo dõi": float(watch_sla_hours),
            "Cảnh báo": float(alert_sla_hours),
        }
    )

    def sla_status(row: pd.Series) -> str:
        if row["workflow_status"] == STATUS_CLOSED:
            return "Đã đóng"
        if pd.isna(row["sla_hours"]) or row["sla_hours"] <= 0:
            return "Không áp dụng"
        if row["age_hours"] > row["sla_hours"]:
            return "Quá hạn"
        return "Trong SLA"

    result["sla_status"] = result.apply(sla_status, axis=1)
    result["severity_rank"] = result["severity"].map(SEVERITY_ORDER).fillna(0).astype(int)

    return result


def apply_case_updates(
    cases: pd.DataFrame,
    updates: pd.DataFrame,
    events: pd.DataFrame,
    now: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Áp dụng thay đổi từ bảng chỉnh sửa và ghi nhật ký."""
    now = local_now() if now is None else pd.Timestamp(now)
    result = _normalize_cases(cases)
    event_store = _normalize_events(events)

    if result.empty or updates is None or updates.empty:
        return result, event_store, 0

    editable_fields = ["workflow_status", "owner", "action_note"]
    update_count = 0
    new_events: list[dict[str, object]] = []

    result = result.set_index("case_id", drop=False)
    update_frame = updates.copy()
    if "case_id" not in update_frame.columns:
        update_frame = update_frame.reset_index()

    for _, update_row in update_frame.iterrows():
        case_id = str(update_row["case_id"])
        if case_id not in result.index:
            continue

        changed = False
        old_workflow_status = str(result.loc[case_id, "workflow_status"])

        for field in editable_fields:
            if field not in update_row.index:
                continue

            old_value = result.loc[case_id, field]
            new_value = update_row[field]

            old_text = "" if pd.isna(old_value) else str(old_value)
            new_text = "" if pd.isna(new_value) else str(new_value)

            if old_text == new_text:
                continue

            result.loc[case_id, field] = new_text
            changed = True
            update_count += 1
            new_events.append(
                {
                    "event_time": now,
                    "case_id": case_id,
                    "field": field,
                    "old_value": old_text,
                    "new_value": new_text,
                }
            )

        if changed:
            result.loc[case_id, "updated_at"] = now
            new_workflow_status = str(result.loc[case_id, "workflow_status"])

            if new_workflow_status == STATUS_CLOSED and old_workflow_status != STATUS_CLOSED:
                result.loc[case_id, "closed_at"] = now
            elif new_workflow_status != STATUS_CLOSED and old_workflow_status == STATUS_CLOSED:
                result.loc[case_id, "closed_at"] = pd.NaT

    result = result.reset_index(drop=True)

    if new_events:
        new_event_frame = pd.DataFrame(new_events)
        if event_store.empty:
            event_store = new_event_frame
        else:
            event_store = pd.concat(
                [event_store, new_event_frame],
                ignore_index=True,
            )

    return _normalize_cases(result), _normalize_events(event_store), update_count


def summarize_cases(enriched_cases: pd.DataFrame) -> dict[str, int]:
    """Tóm tắt sổ xử lý cảnh báo."""
    if enriched_cases is None or enriched_cases.empty:
        return {
            "open_count": 0,
            "new_count": 0,
            "overdue_count": 0,
            "escalated_count": 0,
            "closed_count": 0,
        }

    open_mask = enriched_cases["workflow_status"].ne(STATUS_CLOSED)

    return {
        "open_count": int(open_mask.sum()),
        "new_count": int(enriched_cases["workflow_status"].eq(STATUS_NEW).sum()),
        "overdue_count": int(
            (open_mask & enriched_cases["sla_status"].eq("Quá hạn")).sum()
        ),
        "escalated_count": int(
            enriched_cases["workflow_status"].eq(STATUS_ESCALATED).sum()
        ),
        "closed_count": int(enriched_cases["workflow_status"].eq(STATUS_CLOSED).sum()),
    }


def export_workflow_excel(cases: pd.DataFrame, events: pd.DataFrame) -> bytes:
    """Xuất sổ xử lý và nhật ký thay đổi ra Excel."""
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _normalize_cases(cases).to_excel(writer, sheet_name="Ho_so_canh_bao", index=False)
        _normalize_events(events).to_excel(writer, sheet_name="Nhat_ky_thay_doi", index=False)

    output.seek(0)
    return output.getvalue()
