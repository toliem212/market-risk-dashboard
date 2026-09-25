"""
Fixed Income Market Monitor
===========================

Xử lý dữ liệu đường cong lợi suất trái phiếu Chính phủ phục vụ theo dõi
rủi ro lãi suất trên thị trường trái phiếu.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"


REQUIRED_COLUMNS = ["date", "tenor_years", "yield_pct"]
OPTIONAL_COLUMNS = ["turnover_billion"]

STATUS_RANK = {
    STATUS_NORMAL: 0,
    STATUS_WATCH: 1,
    STATUS_ALERT: 2,
}

COLUMN_ALIASES = {
    "date": {
        "date",
        "ngay",
        "trading date",
        "trade date",
        "ngay giao dich",
    },
    "tenor_years": {
        "tenor years",
        "tenor",
        "ky han",
        "ky han nam",
        "remaining maturity",
        "maturity years",
    },
    "yield_pct": {
        "yield pct",
        "yield",
        "yield %",
        "loi suat",
        "loi suat %",
        "spot rate",
        "spot rate %",
    },
    "turnover_billion": {
        "turnover billion",
        "turnover",
        "doanh so ty dong",
        "gia tri giao dich ty dong",
    },
}


def normalize_text(value: object) -> str:
    """Chuẩn hóa tên cột để nhận diện nhiều cách viết."""
    text = unicodedata.normalize("NFD", str(value).strip().lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[_\-()]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_dates(series: pd.Series) -> pd.Series:
    """Chuẩn hóa ngày từ datetime, chuỗi phổ biến hoặc Excel serial."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    text = series.astype("string").str.strip()

    iso_mask = text.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    result.loc[iso_mask] = pd.to_datetime(
        text.loc[iso_mask], format="%Y-%m-%d", errors="coerce"
    )

    dmy_mask = text.str.match(r"^\d{1,2}/\d{1,2}/\d{4}$", na=False) & result.isna()
    result.loc[dmy_mask] = pd.to_datetime(
        text.loc[dmy_mask], format="%d/%m/%Y", errors="coerce"
    )

    remaining = result.isna()
    if remaining.any():
        numeric = pd.to_numeric(series.loc[remaining], errors="coerce")
        serial_mask = numeric.between(20000, 80000)
        serial_index = numeric.index[serial_mask.fillna(False)]
        if len(serial_index) > 0:
            result.loc[serial_index] = pd.to_datetime(
                numeric.loc[serial_index], unit="D", origin="1899-12-30", errors="coerce"
            )

    remaining = result.isna()
    if remaining.any():
        result.loc[remaining] = pd.to_datetime(
            text.loc[remaining], errors="coerce", dayfirst=True
        )

    return result


def blank_yield_curve_template() -> pd.DataFrame:
    """Tạo template trống theo dạng long format."""
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def _find_alias_column(columns: list[str], canonical_name: str) -> str | None:
    aliases = COLUMN_ALIASES[canonical_name]
    for column in columns:
        if normalize_text(column) in aliases:
            return column
    return None


def _parse_tenor_label(value: object) -> float | None:
    """Nhận diện tenor từ tên cột như 2Y, 5 năm, 10 years."""
    text = normalize_text(value)
    patterns = [
        r"^(\d+(?:\.\d+)?)\s*y$",
        r"^(\d+(?:\.\d+)?)\s*year$",
        r"^(\d+(?:\.\d+)?)\s*years$",
        r"^(\d+(?:\.\d+)?)\s*nam$",
    ]

    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return float(match.group(1))

    return None


def standardize_yield_curve_input(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa dữ liệu đường cong lợi suất từ long hoặc wide format."""
    if data is None or data.empty:
        return blank_yield_curve_template()

    raw = data.copy()
    raw.columns = [str(column).strip() for column in raw.columns]
    columns = list(raw.columns)

    date_column = _find_alias_column(columns, "date")
    tenor_column = _find_alias_column(columns, "tenor_years")
    yield_column = _find_alias_column(columns, "yield_pct")
    turnover_column = _find_alias_column(columns, "turnover_billion")

    if date_column and tenor_column and yield_column:
        rename_map = {
            date_column: "date",
            tenor_column: "tenor_years",
            yield_column: "yield_pct",
        }
        if turnover_column:
            rename_map[turnover_column] = "turnover_billion"

        output_columns = list(rename_map.values())
        standardized = raw[list(rename_map.keys())].rename(columns=rename_map)
        standardized = standardized[output_columns]
    elif date_column:
        tenor_columns = []
        for column in columns:
            if column == date_column:
                continue
            tenor = _parse_tenor_label(column)
            if tenor is not None:
                tenor_columns.append((column, tenor))

        if not tenor_columns:
            raise ValueError(
                "Không nhận diện được cấu trúc dữ liệu. Cần tối thiểu các cột "
                "date, tenor_years, yield_pct hoặc dạng wide với các cột 2Y, 5Y, 10Y..."
            )

        pieces = []
        for column, tenor in tenor_columns:
            piece = pd.DataFrame(
                {
                    "date": raw[date_column],
                    "tenor_years": tenor,
                    "yield_pct": raw[column],
                }
            )
            pieces.append(piece)

        standardized = pd.concat(pieces, ignore_index=True)
    else:
        raise ValueError(
            "Không tìm thấy cột ngày. Dùng cột 'date' hoặc 'Ngày' trong file nguồn."
        )

    standardized["date"] = parse_dates(standardized["date"])
    standardized["tenor_years"] = pd.to_numeric(
        standardized["tenor_years"], errors="coerce"
    )
    standardized["yield_pct"] = pd.to_numeric(
        standardized["yield_pct"], errors="coerce"
    )

    if "turnover_billion" in standardized.columns:
        standardized["turnover_billion"] = pd.to_numeric(
            standardized["turnover_billion"], errors="coerce"
        )

    standardized = standardized.dropna(
        subset=["date", "tenor_years", "yield_pct"]
    )
    standardized = standardized[standardized["tenor_years"] > 0]
    standardized = (
        standardized.sort_values(["tenor_years", "date"])
        .drop_duplicates(subset=["date", "tenor_years"], keep="last")
        .reset_index(drop=True)
    )

    return standardized


def prepare_yield_curve_monitor(
    data: pd.DataFrame,
    rolling_window: int = 250,
    min_periods: int = 60,
) -> pd.DataFrame:
    """Tính biến động lợi suất và ngưỡng cảnh báo động theo từng kỳ hạn."""
    frame = standardize_yield_curve_input(data)
    if frame.empty:
        return frame

    frame = frame.sort_values(["tenor_years", "date"]).reset_index(drop=True)
    grouped = frame.groupby("tenor_years", group_keys=False)

    frame["yield_change_bps"] = grouped["yield_pct"].diff().mul(100)

    history = frame.groupby("tenor_years", group_keys=False)["yield_change_bps"].shift(1)
    abs_history = history.abs()

    frame["watch_threshold_bps"] = (
        abs_history.groupby(frame["tenor_years"])
        .rolling(rolling_window, min_periods=min_periods)
        .quantile(0.95)
        .reset_index(level=0, drop=True)
    )
    frame["alert_threshold_bps"] = (
        abs_history.groupby(frame["tenor_years"])
        .rolling(rolling_window, min_periods=min_periods)
        .quantile(0.99)
        .reset_index(level=0, drop=True)
    )

    rolling_mean = (
        history.groupby(frame["tenor_years"])
        .rolling(60, min_periods=30)
        .mean()
        .reset_index(level=0, drop=True)
    )
    rolling_std = (
        history.groupby(frame["tenor_years"])
        .rolling(60, min_periods=30)
        .std()
        .reset_index(level=0, drop=True)
        .replace(0, np.nan)
    )
    frame["change_zscore"] = (frame["yield_change_bps"] - rolling_mean) / rolling_std

    frame["status"] = STATUS_NORMAL
    valid = frame["yield_change_bps"].notna() & frame["watch_threshold_bps"].notna()
    watch = valid & (
        frame["yield_change_bps"].abs() >= frame["watch_threshold_bps"]
    )
    alert = valid & frame["alert_threshold_bps"].notna() & (
        frame["yield_change_bps"].abs() >= frame["alert_threshold_bps"]
    )
    frame.loc[watch, "status"] = STATUS_WATCH
    frame.loc[alert, "status"] = STATUS_ALERT
    frame["severity_rank"] = frame["status"].map(STATUS_RANK)

    return frame


def available_tenors(data: pd.DataFrame) -> list[float]:
    """Danh sách kỳ hạn có dữ liệu."""
    if data.empty:
        return []
    return sorted(data["tenor_years"].dropna().astype(float).unique().tolist())


def build_latest_curve_snapshot(data: pd.DataFrame) -> pd.DataFrame:
    """Lấy đường cong mới nhất cùng biến động ngày và trạng thái."""
    if data.empty:
        return pd.DataFrame()

    latest_date = data["date"].max()
    snapshot = data[data["date"] == latest_date].copy()
    return snapshot.sort_values("tenor_years").reset_index(drop=True)


def build_previous_curve_snapshot(data: pd.DataFrame) -> pd.DataFrame:
    """Lấy đường cong của ngày dữ liệu liền trước."""
    if data.empty:
        return pd.DataFrame()

    dates = sorted(pd.Series(data["date"].dropna().unique()).tolist())
    if len(dates) < 2:
        return pd.DataFrame()

    previous_date = dates[-2]
    snapshot = data[data["date"] == previous_date].copy()
    return snapshot.sort_values("tenor_years").reset_index(drop=True)


def build_curve_comparison(data: pd.DataFrame) -> pd.DataFrame:
    """So sánh đường cong mới nhất với ngày dữ liệu liền trước."""
    latest = build_latest_curve_snapshot(data)
    previous = build_previous_curve_snapshot(data)

    if latest.empty:
        return pd.DataFrame()

    latest_columns = [
        "tenor_years",
        "yield_pct",
        "yield_change_bps",
        "watch_threshold_bps",
        "alert_threshold_bps",
        "change_zscore",
        "status",
    ]
    latest = latest[latest_columns].rename(columns={"yield_pct": "current_yield_pct"})

    if previous.empty:
        latest["previous_yield_pct"] = np.nan
        return latest

    previous = previous[["tenor_years", "yield_pct"]].rename(
        columns={"yield_pct": "previous_yield_pct"}
    )

    comparison = latest.merge(previous, on="tenor_years", how="left")
    return comparison.sort_values("tenor_years").reset_index(drop=True)


def build_tenor_history(data: pd.DataFrame, tenor_years: float) -> pd.DataFrame:
    """Lấy lịch sử cho một kỳ hạn cụ thể."""
    if data.empty:
        return pd.DataFrame()

    mask = np.isclose(data["tenor_years"].astype(float), float(tenor_years), atol=1e-9)
    return data.loc[mask].sort_values("date").reset_index(drop=True)


def _latest_yield_for_tenor(snapshot: pd.DataFrame, tenor: float) -> float:
    if snapshot.empty:
        return np.nan

    mask = np.isclose(snapshot["tenor_years"].astype(float), tenor, atol=0.05)
    values = snapshot.loc[mask, "yield_pct"]
    if values.empty:
        return np.nan
    return float(values.iloc[0])


def summarize_yield_curve(data: pd.DataFrame) -> dict[str, object]:
    """Tổng hợp các chỉ tiêu giám sát đường cong mới nhất."""
    snapshot = build_latest_curve_snapshot(data)

    if snapshot.empty:
        return {
            "latest_date": pd.NaT,
            "status": STATUS_NORMAL,
            "yield_10y": np.nan,
            "slope_10y_2y_bps": np.nan,
            "curvature_2_5_10_bps": np.nan,
            "max_abs_move_bps": np.nan,
            "max_move_tenor": np.nan,
            "watch_count": 0,
            "alert_count": 0,
        }

    y2 = _latest_yield_for_tenor(snapshot, 2.0)
    y5 = _latest_yield_for_tenor(snapshot, 5.0)
    y10 = _latest_yield_for_tenor(snapshot, 10.0)

    slope = (y10 - y2) * 100 if pd.notna(y10) and pd.notna(y2) else np.nan
    curvature = (
        (2 * y5 - y2 - y10) * 100
        if pd.notna(y2) and pd.notna(y5) and pd.notna(y10)
        else np.nan
    )

    valid_moves = snapshot.dropna(subset=["yield_change_bps"])
    if valid_moves.empty:
        max_abs_move = np.nan
        max_move_tenor = np.nan
    else:
        max_index = valid_moves["yield_change_bps"].abs().idxmax()
        max_abs_move = float(abs(valid_moves.loc[max_index, "yield_change_bps"]))
        max_move_tenor = float(valid_moves.loc[max_index, "tenor_years"])

    watch_count = int(snapshot["status"].eq(STATUS_WATCH).sum())
    alert_count = int(snapshot["status"].eq(STATUS_ALERT).sum())

    if alert_count > 0:
        status = STATUS_ALERT
    elif watch_count > 0:
        status = STATUS_WATCH
    else:
        status = STATUS_NORMAL

    return {
        "latest_date": snapshot["date"].max(),
        "status": status,
        "yield_10y": y10,
        "slope_10y_2y_bps": slope,
        "curvature_2_5_10_bps": curvature,
        "max_abs_move_bps": max_abs_move,
        "max_move_tenor": max_move_tenor,
        "watch_count": watch_count,
        "alert_count": alert_count,
    }
