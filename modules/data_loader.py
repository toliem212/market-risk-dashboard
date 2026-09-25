"""Đọc, chuẩn hóa và kiểm tra cấu trúc dữ liệu đầu vào."""

from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from modules.app_config import FX_FILE, FX_SHEET_NAME, RATES_FILE


def normalize_text(value: object) -> str:
    """Chuẩn hóa chuỗi để tìm tên sheet."""
    text = unicodedata.normalize("NFD", str(value).strip().lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def find_sheet(file_path: Path, keyword: str) -> str:
    """Tìm tên sheet theo từ khóa."""
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    workbook = pd.ExcelFile(file_path)
    normalized_keyword = normalize_text(keyword)

    for sheet_name in workbook.sheet_names:
        if normalized_keyword in normalize_text(sheet_name):
            return sheet_name

    raise ValueError(
        f"Không tìm thấy sheet chứa từ khóa '{keyword}'. "
        f"Các sheet hiện có: {workbook.sheet_names}"
    )


def parse_dates(series: pd.Series) -> pd.Series:
    """Chuẩn hóa ngày từ datetime, ISO, DD/MM/YYYY hoặc Excel serial."""
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

    numeric_values = pd.to_numeric(series, errors="coerce")
    excel_serial_mask = (
        result.isna()
        & numeric_values.between(10_000, 100_000, inclusive="both")
    )
    if excel_serial_mask.any():
        result.loc[excel_serial_mask] = pd.to_datetime(
            numeric_values.loc[excel_serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    remaining = result.isna()
    if remaining.any():
        result.loc[remaining] = pd.to_datetime(
            text.loc[remaining], errors="coerce", dayfirst=False
        )

    return result


def require_columns(
    frame: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """Kiểm tra các cột bắt buộc."""
    missing_columns = [
        column for column in required_columns if column not in frame.columns
    ]
    if missing_columns:
        raise ValueError(
            f"{dataset_name} thiếu các cột: {', '.join(missing_columns)}"
        )


def _source_quality_metadata(date_series: pd.Series) -> dict[str, object]:
    """Lưu dấu vết chất lượng của cột ngày trước khi làm sạch dữ liệu."""
    parsed_dates = parse_dates(date_series)
    text = date_series.astype("string").str.strip()
    nonempty = date_series.notna() & text.ne("")
    invalid_mask = nonempty & parsed_dates.isna()
    duplicate_mask = parsed_dates.notna() & parsed_dates.duplicated(keep=False)
    duplicate_dates = sorted(parsed_dates.loc[duplicate_mask].dropna().unique())

    return {
        "raw_rows": int(len(date_series)),
        "invalid_date_rows": int(invalid_mask.sum()),
        "invalid_date_values": text.loc[invalid_mask].head(20).tolist(),
        "duplicate_date_rows": int(parsed_dates.duplicated(keep="first").sum()),
        "duplicate_dates": [pd.Timestamp(value) for value in duplicate_dates],
    }


def _attach_source_quality(frame: pd.DataFrame, metadata: dict[str, object]) -> pd.DataFrame:
    """Gắn metadata nguồn vào DataFrame đã làm sạch."""
    frame.attrs["source_quality"] = metadata
    return frame


def read_uploaded_table(uploaded_file, required_columns: list[str]) -> pd.DataFrame:
    """Đọc CSV/XLSX do người dùng tải lên và kiểm tra cấu trúc cột."""
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    elif file_name.endswith((".xlsx", ".xls")):
        data = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Chỉ hỗ trợ file CSV hoặc Excel.")

    data.columns = [str(column).strip() for column in data.columns]
    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError(
            "File tải lên thiếu các cột bắt buộc: " + ", ".join(missing)
        )

    return data[required_columns].copy()


def read_table_source(source) -> pd.DataFrame:
    """Đọc CSV/XLSX từ file tải lên hoặc đường dẫn cục bộ."""
    name = getattr(source, "name", str(source)).lower()

    if name.endswith(".csv"):
        return pd.read_csv(source)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)

    raise ValueError("Chỉ hỗ trợ file CSV hoặc Excel.")


@st.cache_data
def load_fx_data() -> pd.DataFrame:
    """Đọc và xử lý dữ liệu USD/VND."""
    if not FX_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file USD/VND: {FX_FILE}")

    raw = pd.read_excel(FX_FILE, sheet_name=FX_SHEET_NAME, header=None)
    if raw.shape[1] < 5:
        raise ValueError(
            "File USD/VND không đủ 5 cột "
            "Ngày/Mở cửa/Cao nhất/Thấp nhất/Đóng cửa."
        )

    data = raw.iloc[2:, :5].copy()
    data.columns = ["date", "open", "high", "low", "close"]
    source_quality = _source_quality_metadata(data["date"])
    data["date"] = parse_dates(data["date"])

    for column in ["open", "high", "low", "close"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = (
        data.dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    data["daily_return_pct"] = data["close"].pct_change().mul(100)
    data["intraday_range_pct"] = (
        (data["high"] - data["low"]).div(data["close"]).mul(100)
    )
    data["volatility_20d_pct"] = (
        data["daily_return_pct"].rolling(20).std().mul(np.sqrt(252))
    )
    data["volatility_60d_pct"] = (
        data["daily_return_pct"].rolling(60).std().mul(np.sqrt(252))
    )

    return _attach_source_quality(data, source_quality)


@st.cache_data
def load_deposit_data() -> pd.DataFrame:
    """Đọc dữ liệu lãi suất huy động."""
    sheet_name = find_sheet(RATES_FILE, "huy động")
    raw = pd.read_excel(RATES_FILE, sheet_name=sheet_name)
    raw.columns = [str(column).strip() for column in raw.columns]

    source_columns = {
        "Ngày": "date",
        "Lãi suất kỳ hạn 1-3 tháng (%)": "deposit_1_3m",
        "Lãi suất kỳ hạn 6-9 tháng (%)": "deposit_6_9m",
        "Lãi suất kỳ hạn 12 tháng (%)": "deposit_12m",
    }
    require_columns(raw, list(source_columns.keys()), "Dữ liệu lãi suất huy động")

    data = raw.rename(columns=source_columns).copy()
    source_quality = _source_quality_metadata(data["date"])
    data["date"] = parse_dates(data["date"])

    for column in ["deposit_1_3m", "deposit_6_9m", "deposit_12m"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = (
        data.dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    return _attach_source_quality(data, source_quality)


@st.cache_data
def load_interbank_data() -> pd.DataFrame:
    """Đọc và xử lý dữ liệu liên ngân hàng."""
    sheet_name = find_sheet(RATES_FILE, "liên ngân hàng")
    raw = pd.read_excel(RATES_FILE, sheet_name=sheet_name)
    raw.columns = [str(column).strip() for column in raw.columns]

    source_columns = {
        "Ngày": "date",
        "Lãi suất ON (%)": "rate_on",
        "Lãi suất 1W (%)": "rate_1w",
        "Lãi suất 2W (%)": "rate_2w",
        "Lãi suất 1M (%)": "rate_1m",
        "Lãi suất 3M (%)": "rate_3m",
        "Doanh số ON (tỷ đồng)": "turnover_on",
        "Doanh số 1W (tỷ đồng)": "turnover_1w",
        "Doanh số 2W (tỷ đồng)": "turnover_2w",
        "Doanh số 1M (tỷ đồng)": "turnover_1m",
        "Doanh số 3M (tỷ đồng)": "turnover_3m",
    }
    require_columns(raw, list(source_columns.keys()), "Dữ liệu liên ngân hàng")

    data = raw.rename(columns=source_columns).copy()
    source_quality = _source_quality_metadata(data["date"])
    data["date"] = parse_dates(data["date"])

    numeric_columns = [
        "rate_on",
        "rate_1w",
        "rate_2w",
        "rate_1m",
        "rate_3m",
        "turnover_on",
        "turnover_1w",
        "turnover_2w",
        "turnover_1m",
        "turnover_3m",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = (
        data.dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    data["on_change_bps"] = data["rate_on"].diff().mul(100)
    data["spread_1m_on"] = data["rate_1m"] - data["rate_on"]
    data["spread_3m_on"] = data["rate_3m"] - data["rate_on"]

    turnover_columns = [
        "turnover_on",
        "turnover_1w",
        "turnover_2w",
        "turnover_1m",
        "turnover_3m",
    ]
    data["total_turnover"] = data[turnover_columns].sum(axis=1, min_count=1)
    data["turnover_placeholder_flag"] = data[turnover_columns].eq(13).all(axis=1)
    data["total_turnover_monitoring"] = data["total_turnover"].mask(
        data["turnover_placeholder_flag"]
    )

    return _attach_source_quality(data, source_quality)
