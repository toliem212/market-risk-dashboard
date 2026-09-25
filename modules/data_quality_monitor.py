"""Data Quality and Reconciliation Monitor."""

from __future__ import annotations

import numpy as np
import pandas as pd


SEVERITY_CRITICAL = "Quan trọng"
SEVERITY_REVIEW = "Cần đối chiếu"
SEVERITY_MONITOR = "Theo dõi"

STATUS_PASS = "Đạt"
STATUS_REVIEW = "Cần kiểm tra"


def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _robust_zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    median = values.median()
    mad = (values - median).abs().median()

    if pd.isna(mad) or mad == 0:
        std = values.std()
        if pd.isna(std) or std == 0:
            return pd.Series(np.nan, index=values.index, dtype="float64")
        return (values - values.mean()) / std

    return 0.6745 * (values - median) / mad


def _date_gap_mask(dates: pd.Series, max_gap_days: int = 7) -> pd.Series:
    ordered = _to_datetime(dates)
    gaps = ordered.diff().dt.days
    return gaps > max_gap_days


def _stale_run_mask(series: pd.Series, minimum_run: int = 5) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    group_id = values.ne(values.shift()).cumsum()
    run_length = values.groupby(group_id).transform("size")
    return values.notna() & run_length.ge(minimum_run)


def _freshness_status(lag_days: int) -> str:
    if lag_days <= 7:
        return "Cập nhật"
    if lag_days <= 30:
        return "Chậm cập nhật"
    return "Dữ liệu cũ"


def _source_quality(frame: pd.DataFrame) -> dict[str, object]:
    """Lấy metadata chất lượng nguồn được ghi nhận trước bước làm sạch."""
    metadata = frame.attrs.get("source_quality", {})
    return metadata if isinstance(metadata, dict) else {}


def _duplicate_count(frame: pd.DataFrame) -> int:
    metadata = _source_quality(frame)
    if "duplicate_date_rows" in metadata:
        return int(metadata.get("duplicate_date_rows", 0) or 0)
    return int(frame["date"].duplicated().sum())


def _invalid_date_count(frame: pd.DataFrame) -> int:
    metadata = _source_quality(frame)
    return int(metadata.get("invalid_date_rows", 0) or 0)


def build_data_quality_report(
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Tạo danh mục kiểm tra chất lượng dữ liệu."""
    today = pd.Timestamp.today().normalize() if as_of_date is None else pd.Timestamp(as_of_date).normalize()
    checks: list[dict[str, object]] = []

    def add_check(dataset: str, check_name: str, count: int, severity: str) -> None:
        checks.append(
            {
                "Bộ dữ liệu": dataset,
                "Nội dung kiểm tra": check_name,
                "Số trường hợp": int(count),
                "Mức độ": severity,
                "Trạng thái": STATUS_PASS if count == 0 else STATUS_REVIEW,
            }
        )

    fx_price_columns = ["open", "high", "low", "close"]
    fx_invalid_ohlc = (
        (fx_data["high"] < fx_data["low"])
        | (fx_data["high"] < fx_data["open"])
        | (fx_data["high"] < fx_data["close"])
        | (fx_data["low"] > fx_data["open"])
        | (fx_data["low"] > fx_data["close"])
    )
    fx_nonpositive = fx_data[fx_price_columns].le(0).any(axis=1)
    fx_modern_mask = pd.to_datetime(fx_data["date"], errors="coerce").ge(pd.Timestamp("2016-01-01"))
    fx_return_z = _robust_zscore(fx_data.loc[fx_modern_mask, "daily_return_pct"])
    fx_return_outlier = fx_return_z.abs().ge(8)
    fx_stale_rows = _stale_run_mask(fx_data.loc[fx_modern_mask, "close"], minimum_run=5)
    fx_stale_group = fx_data.loc[fx_modern_mask, "close"].ne(fx_data.loc[fx_modern_mask, "close"].shift()).cumsum()
    fx_stale_runs = int(fx_stale_rows.groupby(fx_stale_group).any().sum())
    fx_gap = _date_gap_mask(fx_data["date"], max_gap_days=7)

    add_check("USD/VND", "Ngày dữ liệu bị trùng", _duplicate_count(fx_data), SEVERITY_CRITICAL)
    add_check("USD/VND", "Ngày không đọc được", _invalid_date_count(fx_data), SEVERITY_CRITICAL)
    add_check("USD/VND", "Thiếu dữ liệu giá", fx_data[fx_price_columns].isna().any(axis=1).sum(), SEVERITY_CRITICAL)
    add_check("USD/VND", "Giá không dương", fx_nonpositive.sum(), SEVERITY_CRITICAL)
    add_check("USD/VND", "Sai quan hệ OHLC", fx_invalid_ohlc.sum(), SEVERITY_CRITICAL)
    add_check("USD/VND", "Biến động ngày là ngoại lệ thống kê từ 2016", fx_return_outlier.sum(), SEVERITY_REVIEW)
    add_check("USD/VND", "Chuỗi giá đóng cửa không đổi từ 5 quan sát liên tiếp từ 2016", fx_stale_runs, SEVERITY_MONITOR)
    add_check("USD/VND", "Khoảng trống ngày dữ liệu trên 7 ngày", fx_gap.sum(), SEVERITY_REVIEW)

    fx_latest = pd.to_datetime(fx_data["date"], errors="coerce").max()
    fx_lag = max(int((today - fx_latest.normalize()).days), 0) if pd.notna(fx_latest) else 999999
    add_check("USD/VND", "Nguồn dữ liệu chậm trên 30 ngày", int(fx_lag > 30), SEVERITY_REVIEW)

    deposit_columns = ["deposit_1_3m", "deposit_6_9m", "deposit_12m"]
    deposit_negative = deposit_data[deposit_columns].lt(0).any(axis=1)
    deposit_placeholder_13 = deposit_data[deposit_columns].eq(13).any(axis=1)
    deposit_change = deposit_data[deposit_columns].diff().abs().max(axis=1).mul(100)
    deposit_change_outlier = _robust_zscore(deposit_change).abs().ge(8)
    deposit_gap = _date_gap_mask(deposit_data["date"], max_gap_days=7)

    add_check("Lãi suất huy động", "Ngày dữ liệu bị trùng", _duplicate_count(deposit_data), SEVERITY_CRITICAL)
    add_check("Lãi suất huy động", "Ngày không đọc được", _invalid_date_count(deposit_data), SEVERITY_CRITICAL)
    add_check("Lãi suất huy động", "Thiếu dữ liệu lãi suất", deposit_data[deposit_columns].isna().any(axis=1).sum(), SEVERITY_CRITICAL)
    add_check("Lãi suất huy động", "Lãi suất âm", deposit_negative.sum(), SEVERITY_REVIEW)
    add_check("Lãi suất huy động", "Giá trị 13 cần đối chiếu nguồn", deposit_placeholder_13.sum(), SEVERITY_REVIEW)
    add_check("Lãi suất huy động", "Mức điều chỉnh là ngoại lệ thống kê", deposit_change_outlier.sum(), SEVERITY_REVIEW)
    add_check("Lãi suất huy động", "Khoảng trống ngày dữ liệu trên 7 ngày", deposit_gap.sum(), SEVERITY_REVIEW)

    deposit_latest = pd.to_datetime(deposit_data["date"], errors="coerce").max()
    deposit_lag = max(int((today - deposit_latest.normalize()).days), 0) if pd.notna(deposit_latest) else 999999
    add_check("Lãi suất huy động", "Nguồn dữ liệu chậm trên 30 ngày", int(deposit_lag > 30), SEVERITY_REVIEW)

    interbank_rate_columns = ["rate_on", "rate_1w", "rate_2w", "rate_1m", "rate_3m"]
    turnover_columns = ["turnover_on", "turnover_1w", "turnover_2w", "turnover_1m", "turnover_3m"]

    interbank_negative_rate = interbank_data[interbank_rate_columns].lt(0).any(axis=1)
    interbank_negative_turnover = interbank_data[turnover_columns].lt(0).any(axis=1)
    turnover_placeholder_13 = interbank_data[turnover_columns].eq(13).all(axis=1)
    rate_change = interbank_data[interbank_rate_columns].diff().abs().max(axis=1).mul(100)
    rate_change_outlier = _robust_zscore(rate_change).abs().ge(8)
    turnover_log_change = np.log1p(interbank_data["total_turnover"].clip(lower=0)).diff()
    turnover_outlier = _robust_zscore(turnover_log_change).abs().ge(8)
    interbank_gap = _date_gap_mask(interbank_data["date"], max_gap_days=7)

    add_check("Liên ngân hàng", "Ngày dữ liệu bị trùng", _duplicate_count(interbank_data), SEVERITY_CRITICAL)
    add_check("Liên ngân hàng", "Ngày không đọc được", _invalid_date_count(interbank_data), SEVERITY_CRITICAL)
    add_check("Liên ngân hàng", "Thiếu dữ liệu lãi suất", interbank_data[interbank_rate_columns].isna().any(axis=1).sum(), SEVERITY_CRITICAL)
    add_check("Liên ngân hàng", "Lãi suất âm", interbank_negative_rate.sum(), SEVERITY_REVIEW)
    add_check("Liên ngân hàng", "Thiếu dữ liệu doanh số", interbank_data[turnover_columns].isna().any(axis=1).sum(), SEVERITY_REVIEW)
    add_check("Liên ngân hàng", "Doanh số âm", interbank_negative_turnover.sum(), SEVERITY_CRITICAL)
    add_check("Liên ngân hàng", "Toàn bộ doanh số kỳ hạn cùng bằng 13", turnover_placeholder_13.sum(), SEVERITY_REVIEW)
    add_check("Liên ngân hàng", "Biến động lãi suất là ngoại lệ thống kê", rate_change_outlier.sum(), SEVERITY_REVIEW)
    add_check("Liên ngân hàng", "Biến động doanh số là ngoại lệ thống kê", turnover_outlier.sum(), SEVERITY_REVIEW)
    add_check("Liên ngân hàng", "Khoảng trống ngày dữ liệu trên 7 ngày", interbank_gap.sum(), SEVERITY_REVIEW)

    interbank_latest = pd.to_datetime(interbank_data["date"], errors="coerce").max()
    interbank_lag = max(int((today - interbank_latest.normalize()).days), 0) if pd.notna(interbank_latest) else 999999
    add_check("Liên ngân hàng", "Nguồn dữ liệu chậm trên 30 ngày", int(interbank_lag > 30), SEVERITY_REVIEW)

    matched = pd.merge_asof(
        interbank_data[["date"]].sort_values("date"),
        deposit_data[["date"]].rename(columns={"date": "deposit_date"}).sort_values("deposit_date"),
        left_on="date",
        right_on="deposit_date",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )
    unmatched = matched["deposit_date"].isna().sum()
    add_check("Đối chiếu nguồn", "Ngày liên ngân hàng không ghép được dữ liệu huy động trong 7 ngày trước đó", unmatched, SEVERITY_REVIEW)

    return pd.DataFrame(checks)


def build_quality_exceptions(
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    max_rows: int = 500,
) -> pd.DataFrame:
    """Tạo nhật ký ngoại lệ dữ liệu có ngày và chi tiết."""
    events: list[dict[str, object]] = []

    def add_event(date: object, dataset: str, issue: str, detail: str, severity: str) -> None:
        events.append(
            {
                "Ngày": pd.to_datetime(date, errors="coerce"),
                "Bộ dữ liệu": dataset,
                "Loại ngoại lệ": issue,
                "Chi tiết": detail,
                "Mức độ": severity,
            }
        )

    for dataset, frame in [
        ("USD/VND", fx_data),
        ("Lãi suất huy động", deposit_data),
        ("Liên ngân hàng", interbank_data),
    ]:
        metadata = _source_quality(frame)
        for duplicate_date in metadata.get("duplicate_dates", []):
            add_event(
                duplicate_date,
                dataset,
                "Ngày dữ liệu bị trùng",
                "Nguồn có nhiều hơn một dòng cho cùng ngày; dữ liệu phân tích giữ dòng cuối cùng.",
                SEVERITY_CRITICAL,
            )
        for raw_value in metadata.get("invalid_date_values", []):
            add_event(
                pd.NaT,
                dataset,
                "Ngày không đọc được",
                f"Giá trị ngày nguồn: {raw_value}",
                SEVERITY_CRITICAL,
            )

    fx_invalid = (
        (fx_data["high"] < fx_data["low"])
        | (fx_data["high"] < fx_data["open"])
        | (fx_data["high"] < fx_data["close"])
        | (fx_data["low"] > fx_data["open"])
        | (fx_data["low"] > fx_data["close"])
    )
    for _, row in fx_data.loc[fx_invalid].iterrows():
        add_event(
            row["date"],
            "USD/VND",
            "Sai quan hệ OHLC",
            f"Open={row['open']:.0f}; High={row['high']:.0f}; Low={row['low']:.0f}; Close={row['close']:.0f}",
            SEVERITY_CRITICAL,
        )

    fx_modern = fx_data[pd.to_datetime(fx_data["date"], errors="coerce").ge(pd.Timestamp("2016-01-01"))]
    fx_return_z = _robust_zscore(fx_modern["daily_return_pct"])
    for index in fx_return_z.index[fx_return_z.abs().ge(8)]:
        row = fx_data.loc[index]
        add_event(
            row["date"],
            "USD/VND",
            "Ngoại lệ biến động ngày",
            f"Biến động={row['daily_return_pct']:+.3f}%; robust Z={fx_return_z.loc[index]:+.2f}",
            SEVERITY_REVIEW,
        )

    fx_gap_mask = _date_gap_mask(fx_data["date"], max_gap_days=7)
    fx_dates = pd.to_datetime(fx_data["date"], errors="coerce")
    for index in fx_data.index[fx_gap_mask]:
        gap_days = int((fx_dates.loc[index] - fx_dates.shift().loc[index]).days)
        add_event(
            fx_dates.loc[index],
            "USD/VND",
            "Khoảng trống ngày dữ liệu",
            f"Khoảng cách {gap_days} ngày lịch so với quan sát trước.",
            SEVERITY_REVIEW,
        )

    deposit_columns = ["deposit_1_3m", "deposit_6_9m", "deposit_12m"]
    placeholder_mask = deposit_data[deposit_columns].eq(13).any(axis=1)
    for _, row in deposit_data.loc[placeholder_mask].iterrows():
        matched_columns = [column for column in deposit_columns if row[column] == 13]
        add_event(
            row["date"],
            "Lãi suất huy động",
            "Giá trị 13 cần đối chiếu nguồn",
            ", ".join(matched_columns),
            SEVERITY_REVIEW,
        )

    deposit_change = deposit_data[deposit_columns].diff().abs().max(axis=1).mul(100)
    deposit_z = _robust_zscore(deposit_change)
    for index in deposit_data.index[deposit_z.abs().ge(8)]:
        row = deposit_data.loc[index]
        add_event(
            row["date"],
            "Lãi suất huy động",
            "Ngoại lệ mức điều chỉnh",
            f"Mức thay đổi lớn nhất={deposit_change.loc[index]:.1f} bps; robust Z={deposit_z.loc[index]:+.2f}",
            SEVERITY_REVIEW,
        )

    turnover_columns = ["turnover_on", "turnover_1w", "turnover_2w", "turnover_1m", "turnover_3m"]
    turnover_placeholder = interbank_data[turnover_columns].eq(13).all(axis=1)
    for _, row in interbank_data.loc[turnover_placeholder].iterrows():
        add_event(
            row["date"],
            "Liên ngân hàng",
            "Mẫu doanh số cần đối chiếu",
            "Toàn bộ doanh số O/N, 1W, 2W, 1M và 3M cùng bằng 13.",
            SEVERITY_REVIEW,
        )

    rate_columns = ["rate_on", "rate_1w", "rate_2w", "rate_1m", "rate_3m"]
    rate_change = interbank_data[rate_columns].diff().abs().max(axis=1).mul(100)
    rate_z = _robust_zscore(rate_change)
    for index in interbank_data.index[rate_z.abs().ge(8)]:
        row = interbank_data.loc[index]
        add_event(
            row["date"],
            "Liên ngân hàng",
            "Ngoại lệ biến động lãi suất",
            f"Mức thay đổi lớn nhất={rate_change.loc[index]:.1f} bps; robust Z={rate_z.loc[index]:+.2f}",
            SEVERITY_REVIEW,
        )

    turnover_log_change = np.log1p(interbank_data["total_turnover"].clip(lower=0)).diff()
    turnover_z = _robust_zscore(turnover_log_change)
    for index in interbank_data.index[turnover_z.abs().ge(8)]:
        row = interbank_data.loc[index]
        add_event(
            row["date"],
            "Liên ngân hàng",
            "Ngoại lệ biến động doanh số",
            f"Tổng doanh số={row['total_turnover']:.0f} tỷ đồng; robust Z={turnover_z.loc[index]:+.2f}",
            SEVERITY_REVIEW,
        )

    if not events:
        return pd.DataFrame(columns=["Ngày", "Bộ dữ liệu", "Loại ngoại lệ", "Chi tiết", "Mức độ"])

    result = pd.DataFrame(events)
    result = result.drop_duplicates().sort_values(["Ngày", "Mức độ"], ascending=[False, True])
    return result.head(max_rows).reset_index(drop=True)


def build_freshness_table(
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Tổng hợp phạm vi và độ mới của các nguồn dữ liệu."""
    today = pd.Timestamp.today().normalize() if as_of_date is None else pd.Timestamp(as_of_date).normalize()
    rows = []

    for dataset, frame in [
        ("USD/VND", fx_data),
        ("Lãi suất huy động", deposit_data),
        ("Liên ngân hàng", interbank_data),
    ]:
        dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
        first_date = dates.min() if not dates.empty else pd.NaT
        last_date = dates.max() if not dates.empty else pd.NaT
        lag_days = max(int((today - last_date.normalize()).days), 0) if pd.notna(last_date) else np.nan

        rows.append(
            {
                "Bộ dữ liệu": dataset,
                "Số quan sát": len(frame),
                "Từ ngày": first_date,
                "Đến ngày": last_date,
                "Độ trễ (ngày lịch)": lag_days,
                "Trạng thái cập nhật": _freshness_status(int(lag_days)) if pd.notna(lag_days) else "Không xác định",
            }
        )

    return pd.DataFrame(rows)


def build_reconciliation_table(
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    tolerance_days: int = 7,
) -> pd.DataFrame:
    """Đối chiếu khả năng ghép dữ liệu huy động với dữ liệu liên ngân hàng."""
    left = interbank_data[["date"]].dropna().sort_values("date").copy()
    right = deposit_data[["date"]].dropna().sort_values("date").copy()
    right = right.rename(columns={"date": "deposit_date"})

    matched = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on="deposit_date",
        direction="backward",
        tolerance=pd.Timedelta(days=tolerance_days),
    )

    matched["lag_days"] = (matched["date"] - matched["deposit_date"]).dt.days
    matched["matched"] = matched["deposit_date"].notna()

    total = len(matched)
    matched_count = int(matched["matched"].sum())
    unmatched_count = total - matched_count
    coverage = matched_count / total * 100 if total else np.nan
    median_lag = matched.loc[matched["matched"], "lag_days"].median() if matched_count else np.nan
    max_lag = matched.loc[matched["matched"], "lag_days"].max() if matched_count else np.nan

    return pd.DataFrame(
        [
            {
                "Đối chiếu": f"Liên ngân hàng ↔ Huy động (lùi tối đa {tolerance_days} ngày)",
                "Số ngày liên ngân hàng": total,
                "Ghép được": matched_count,
                "Không ghép được": unmatched_count,
                "Tỷ lệ bao phủ (%)": coverage,
                "Độ trễ trung vị (ngày)": median_lag,
                "Độ trễ lớn nhất (ngày)": max_lag,
            }
        ]
    )


def summarize_quality(
    quality_report: pd.DataFrame,
    exceptions: pd.DataFrame,
) -> dict[str, int]:
    """Tóm tắt trạng thái kiểm soát dữ liệu."""
    flagged = quality_report[quality_report["Số trường hợp"] > 0]
    critical = flagged[flagged["Mức độ"] == SEVERITY_CRITICAL]

    return {
        "check_count": int(len(quality_report)),
        "flagged_check_count": int(len(flagged)),
        "critical_check_count": int(len(critical)),
        "exception_count": int(len(exceptions)),
    }
