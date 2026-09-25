"""Historical market stress scenario library."""

from __future__ import annotations

import numpy as np
import pandas as pd


CATEGORY_ALL = "Toàn thị trường"
CATEGORY_FX = "Ngoại hối USD/VND"
CATEGORY_ON = "Lãi suất qua đêm"
CATEGORY_CURVE = "Đường cong lãi suất"
CATEGORY_DEPOSIT = "Lãi suất huy động 12 tháng"

HISTORICAL_SCENARIO_CATEGORIES = [
    CATEGORY_ALL,
    CATEGORY_FX,
    CATEGORY_ON,
    CATEGORY_CURVE,
    CATEGORY_DEPOSIT,
]


def _percentile_rank(series: pd.Series) -> pd.Series:
    """Xếp hạng bách phân vị của trị tuyệt đối, bỏ qua giá trị thiếu."""
    values = pd.to_numeric(series, errors="coerce").abs()
    return values.rank(method="average", pct=True).mul(100)


def _max_abs_row(frame: pd.DataFrame) -> pd.Series:
    """Lấy trị tuyệt đối lớn nhất theo hàng, giữ NaN khi cả hàng đều thiếu."""
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    return numeric.abs().max(axis=1, skipna=True)


def prepare_historical_stress_data(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    deposit_tolerance_days: int = 7,
) -> pd.DataFrame:
    """Ghép các cú sốc thị trường lịch sử trên cùng một trục ngày."""
    fx = fx_data[["date", "close"]].copy()
    fx = fx.sort_values("date").drop_duplicates("date", keep="last")

    if "daily_return_pct" in fx_data.columns:
        fx["fx_shock_pct"] = pd.to_numeric(
            fx_data.set_index("date")["daily_return_pct"].reindex(fx["date"]).to_numpy(),
            errors="coerce",
        )
    else:
        fx["fx_shock_pct"] = fx["close"].pct_change().mul(100)

    rate_columns = ["rate_on", "rate_1w", "rate_1m", "rate_3m"]
    mm = interbank_data[["date", *rate_columns]].copy()
    mm = mm.sort_values("date").drop_duplicates("date", keep="last")

    shock_map = {
        "rate_on": "on_shock_bps",
        "rate_1w": "rate_1w_shock_bps",
        "rate_1m": "rate_1m_shock_bps",
        "rate_3m": "rate_3m_shock_bps",
    }

    for source, target in shock_map.items():
        mm[target] = pd.to_numeric(mm[source], errors="coerce").diff().mul(100)

    merged = fx[["date", "fx_shock_pct"]].merge(
        mm[["date", *shock_map.values()]],
        on="date",
        how="inner",
    )

    deposit = deposit_data[["date", "deposit_12m"]].copy()
    deposit = deposit.sort_values("date").drop_duplicates("date", keep="last")
    deposit["deposit_12m_shock_bps"] = (
        pd.to_numeric(deposit["deposit_12m"], errors="coerce").diff().mul(100)
    )
    deposit = deposit.rename(columns={"date": "deposit_source_date"})

    merged = pd.merge_asof(
        merged.sort_values("date"),
        deposit[["deposit_source_date", "deposit_12m_shock_bps"]].sort_values(
            "deposit_source_date"
        ),
        left_on="date",
        right_on="deposit_source_date",
        direction="backward",
        tolerance=pd.Timedelta(days=deposit_tolerance_days),
    )

    merged["deposit_lag_days"] = (
        merged["date"] - merged["deposit_source_date"]
    ).dt.days

    curve_columns = [
        "rate_1w_shock_bps",
        "rate_1m_shock_bps",
        "rate_3m_shock_bps",
    ]
    merged["curve_shock_abs_bps"] = _max_abs_row(merged[curve_columns])

    merged["fx_percentile"] = _percentile_rank(merged["fx_shock_pct"])
    merged["on_percentile"] = _percentile_rank(merged["on_shock_bps"])
    merged["curve_percentile"] = _percentile_rank(merged["curve_shock_abs_bps"])
    merged["deposit_percentile"] = _percentile_rank(
        merged["deposit_12m_shock_bps"]
    )

    market_percentile_columns = [
        "fx_percentile",
        "on_percentile",
        "curve_percentile",
    ]
    merged["stress_score"] = merged[market_percentile_columns].mean(
        axis=1, skipna=True
    )
    merged["max_component_percentile"] = merged[market_percentile_columns].max(
        axis=1, skipna=True
    )

    component_labels = {
        "fx_percentile": "Ngoại hối",
        "on_percentile": "Lãi suất qua đêm",
        "curve_percentile": "Đường cong lãi suất",
    }

    def strongest_driver(row: pd.Series) -> str:
        values = row[market_percentile_columns].dropna()
        if values.empty:
            return "—"
        return component_labels[values.idxmax()]

    merged["strongest_driver"] = merged.apply(strongest_driver, axis=1)

    required = [
        "fx_shock_pct",
        "on_shock_bps",
        "rate_1w_shock_bps",
        "rate_1m_shock_bps",
        "rate_3m_shock_bps",
    ]
    merged = merged.dropna(subset=required).reset_index(drop=True)

    return merged


def build_historical_scenario_library(
    historical_data: pd.DataFrame,
    category: str = CATEGORY_ALL,
    top_n: int = 20,
) -> pd.DataFrame:
    """Chọn các phiên lịch sử cực trị theo nhóm rủi ro."""
    if historical_data.empty:
        return historical_data.copy()

    score_column = {
        CATEGORY_ALL: "stress_score",
        CATEGORY_FX: "fx_percentile",
        CATEGORY_ON: "on_percentile",
        CATEGORY_CURVE: "curve_percentile",
        CATEGORY_DEPOSIT: "deposit_percentile",
    }.get(category)

    if score_column is None:
        raise ValueError(f"Nhóm kịch bản không hợp lệ: {category}")

    library = historical_data.dropna(subset=[score_column]).copy()
    library["selection_score"] = library[score_column]

    return (
        library.sort_values(
            ["selection_score", "max_component_percentile", "date"],
            ascending=[False, False, False],
        )
        .head(top_n)
        .reset_index(drop=True)
    )


def scenario_from_row(row: pd.Series) -> dict[str, float]:
    """Chuyển một phiên lịch sử thành vector cú sốc cho stress test hiện tại."""
    return {
        "fx_shock_pct": float(row["fx_shock_pct"]),
        "on_shock_bps": float(row["on_shock_bps"]),
        "rate_1w_shock_bps": float(row["rate_1w_shock_bps"]),
        "rate_1m_shock_bps": float(row["rate_1m_shock_bps"]),
        "rate_3m_shock_bps": float(row["rate_3m_shock_bps"]),
        "deposit_12m_shock_bps": (
            0.0
            if pd.isna(row.get("deposit_12m_shock_bps"))
            else float(row["deposit_12m_shock_bps"])
        ),
    }


def summarize_historical_stress(
    historical_data: pd.DataFrame,
) -> dict[str, object]:
    """Tóm tắt phân phối các phiên stress lịch sử."""
    if historical_data.empty:
        return {
            "observations": 0,
            "p95_score": np.nan,
            "p99_score": np.nan,
            "max_score": np.nan,
            "max_date": pd.NaT,
        }

    score = historical_data["stress_score"].dropna()
    if score.empty:
        return {
            "observations": len(historical_data),
            "p95_score": np.nan,
            "p99_score": np.nan,
            "max_score": np.nan,
            "max_date": pd.NaT,
        }

    max_index = score.idxmax()
    return {
        "observations": len(historical_data),
        "p95_score": float(score.quantile(0.95)),
        "p99_score": float(score.quantile(0.99)),
        "max_score": float(score.loc[max_index]),
        "max_date": historical_data.loc[max_index, "date"],
    }


def build_historical_stress_timeline(
    historical_data: pd.DataFrame,
) -> pd.DataFrame:
    """Chuẩn bị chuỗi điểm stress tổng hợp và ngưỡng lịch sử."""
    if historical_data.empty:
        return pd.DataFrame(
            columns=["date", "stress_score", "p95_score", "p99_score"]
        )

    result = historical_data[["date", "stress_score"]].copy()
    score = result["stress_score"].dropna()

    result["p95_score"] = score.quantile(0.95) if not score.empty else np.nan
    result["p99_score"] = score.quantile(0.99) if not score.empty else np.nan
    return result
