"""Tổng hợp cảnh báo rủi ro thị trường từ các phân hệ giám sát."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.deposit_rate_monitor import (
    build_deposit_rate_event_log,
    prepare_deposit_rate_data,
)
from modules.fx_risk_monitor import build_fx_event_log, prepare_fx_risk_data
from modules.money_market_monitor import (
    build_money_market_event_log,
    prepare_money_market_data,
)


STATUS_NORMAL = "Bình thường"
STATUS_WATCH = "Theo dõi"
STATUS_ALERT = "Cảnh báo"

SEVERITY_RANK = {
    STATUS_NORMAL: 0,
    STATUS_WATCH: 1,
    STATUS_ALERT: 2,
}

GROUP_ORDER = [
    "Ngoại hối",
    "Trái phiếu Chính phủ",
    "Liên ngân hàng",
    "Áp lực nguồn vốn",
    "Lãi suất huy động",
]


def _status_from_regime(regime: object) -> str:
    """Quy đổi chế độ biến động thành trạng thái giám sát."""
    if regime == "Rất cao":
        return STATUS_ALERT
    if regime == "Cao":
        return STATUS_WATCH
    return STATUS_NORMAL


def _make_row(
    date: object,
    group: str,
    indicator: str,
    value: float,
    value_unit: str,
    signal: float,
    signal_unit: str,
    watch_threshold: float,
    alert_threshold: float,
    status: str,
) -> dict[str, object]:
    """Chuẩn hóa một tín hiệu về cùng cấu trúc."""
    return {
        "date": pd.to_datetime(date, errors="coerce"),
        "group": group,
        "indicator": indicator,
        "value": value,
        "value_unit": value_unit,
        "signal": signal,
        "signal_unit": signal_unit,
        "watch_threshold": watch_threshold,
        "alert_threshold": alert_threshold,
        "status": status,
        "severity_rank": SEVERITY_RANK.get(status, 0),
    }


def build_current_alert_snapshot(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
    bond_monitor_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tạo snapshot các tín hiệu giám sát mới nhất từ dữ liệu thị trường."""
    rows: list[dict[str, object]] = []

    fx = prepare_fx_risk_data(fx_data)
    if not fx.empty:
        row = fx.iloc[-1]
        rows.extend(
            [
                _make_row(
                    row["date"],
                    "Ngoại hối",
                    "Biến động tỷ giá trong ngày",
                    row["daily_return_pct"],
                    "%",
                    row["abs_return_pct"],
                    "%",
                    row["return_p95"],
                    row["return_p99"],
                    row["move_status"],
                ),
                _make_row(
                    row["date"],
                    "Ngoại hối",
                    "Biên độ tỷ giá trong ngày",
                    row["intraday_range_pct"],
                    "%",
                    row["intraday_range_pct"],
                    "%",
                    row["range_p95"],
                    row["range_p99"],
                    row["range_status"],
                ),
                _make_row(
                    row["date"],
                    "Ngoại hối",
                    "Độ biến động tỷ giá 20 ngày",
                    row["volatility_20d_pct"],
                    "%/năm",
                    row["volatility_20d_pct"],
                    "%/năm",
                    row["vol20_p80"],
                    row["vol20_p95"],
                    _status_from_regime(row["volatility_regime"]),
                ),
            ]
        )

    money_market = prepare_money_market_data(interbank_data)
    if not money_market.empty:
        row = money_market.iloc[-1]
        rows.extend(
            [
                _make_row(
                    row["date"],
                    "Liên ngân hàng",
                    "Biến động lãi suất O/N trong ngày",
                    row["change_on_bps"],
                    "bps",
                    row["abs_on_change_bps"],
                    "bps",
                    row["on_change_p95_bps"],
                    row["on_change_p99_bps"],
                    row["on_change_status"],
                ),
                _make_row(
                    row["date"],
                    "Liên ngân hàng",
                    "Mặt bằng lãi suất O/N",
                    row["rate_on"],
                    "%",
                    abs(row["on_level_zscore"]),
                    "σ",
                    2.0,
                    3.0,
                    row["on_level_status"],
                ),
                _make_row(
                    row["date"],
                    "Liên ngân hàng",
                    "Đảo chiều cấu trúc kỳ hạn",
                    row["max_curve_inversion_bps"],
                    "bps",
                    row["max_curve_inversion_bps"],
                    "bps",
                    row["curve_inversion_p95_bps"],
                    row["curve_inversion_p99_bps"],
                    row["curve_status"],
                ),
            ]
        )

        turnover_rows = money_market.dropna(subset=["total_turnover", "turnover_zscore"])
        if not turnover_rows.empty:
            turnover_row = turnover_rows.iloc[-1]
            rows.append(
                _make_row(
                    turnover_row["date"],
                    "Liên ngân hàng",
                    "Doanh số giao dịch liên ngân hàng",
                    turnover_row["total_turnover"],
                    "tỷ đồng",
                    abs(turnover_row["turnover_zscore"]),
                    "σ",
                    2.0,
                    3.0,
                    turnover_row["turnover_status"],
                )
            )

    deposits = prepare_deposit_rate_data(deposit_data)
    if not deposits.empty:
        row = deposits.iloc[-1]
        tenor_rows = [
            ("1-3 tháng", "1_3m"),
            ("6-9 tháng", "6_9m"),
            ("12 tháng", "12m"),
        ]
        for tenor, short_name in tenor_rows:
            change = row[f"change_20obs_{short_name}_bps"]
            rows.append(
                _make_row(
                    row["date"],
                    "Lãi suất huy động",
                    f"Điều chỉnh lãi suất {tenor} trong 20 quan sát",
                    change,
                    "bps",
                    abs(change) if pd.notna(change) else np.nan,
                    "bps",
                    row[f"repricing_p95_{short_name}_bps"],
                    row[f"repricing_p99_{short_name}_bps"],
                    row[f"repricing_status_{short_name}"],
                )
            )

        rows.extend(
            [
                _make_row(
                    row["date"],
                    "Lãi suất huy động",
                    "Mặt bằng lãi suất huy động 12 tháng",
                    row["deposit_12m"],
                    "%",
                    abs(row["rate_12m_zscore"]),
                    "σ",
                    2.0,
                    3.0,
                    row["level_status"],
                ),
                _make_row(
                    row["date"],
                    "Lãi suất huy động",
                    "Chênh lệch 12 tháng - 1-3 tháng",
                    row["spread_12m_1_3m_bps"],
                    "bps",
                    abs(row["spread_12m_1_3m_zscore"]),
                    "σ",
                    2.0,
                    3.0,
                    row["spread_status"],
                ),
            ]
        )

    funding_valid = funding_pressure_data.dropna(
        subset=["funding_pressure_index", "watch_threshold", "alert_threshold"]
    )
    if not funding_valid.empty:
        row = funding_valid.iloc[-1]
        rows.append(
            _make_row(
                row["date"],
                "Áp lực nguồn vốn",
                "Chỉ số áp lực nguồn vốn",
                row["funding_pressure_index"],
                "điểm",
                row["funding_pressure_index"],
                "điểm",
                row["watch_threshold"],
                row["alert_threshold"],
                row["status"],
            )
        )

    if bond_monitor_data is not None and not bond_monitor_data.empty:
        latest_date = bond_monitor_data["date"].max()
        latest_curve = bond_monitor_data[bond_monitor_data["date"] == latest_date].copy()
        for _, row in latest_curve.iterrows():
            tenor = float(row["tenor_years"])
            move = row["yield_change_bps"]
            rows.append(
                _make_row(
                    row["date"],
                    "Trái phiếu Chính phủ",
                    f"Biến động lợi suất kỳ hạn {tenor:g} năm",
                    move,
                    "bps",
                    abs(move) if pd.notna(move) else np.nan,
                    "bps",
                    row["watch_threshold_bps"],
                    row["alert_threshold_bps"],
                    row["status"],
                )
            )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["severity_rank", "group", "indicator"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def _standardize_event_frame(
    frame: pd.DataFrame,
    group: str,
    value_unit: str | None = None,
    signal_unit: str | None = None,
) -> pd.DataFrame:
    """Chuẩn hóa nhật ký cảnh báo của từng phân hệ."""
    if frame.empty:
        return pd.DataFrame()

    result = frame.copy()
    result["group"] = group

    if "unit" not in result.columns:
        result["unit"] = value_unit or ""

    if "signal" not in result.columns:
        result["signal"] = result["value"].abs()

    result["value_unit"] = result["unit"].fillna(value_unit or "")
    result["signal_unit"] = signal_unit or result["value_unit"]
    result["severity_rank"] = result["status"].map(SEVERITY_RANK).fillna(0)

    columns = [
        "date",
        "group",
        "indicator",
        "value",
        "value_unit",
        "signal",
        "signal_unit",
        "watch_threshold",
        "alert_threshold",
        "status",
        "severity_rank",
    ]
    return result[columns]


def build_central_alert_history(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
    bond_monitor_data: pd.DataFrame | None = None,
    max_events: int = 500,
) -> pd.DataFrame:
    """Gom lịch sử cảnh báo từ các phân hệ dữ liệu thị trường."""
    frames: list[pd.DataFrame] = []

    fx = prepare_fx_risk_data(fx_data)
    fx_events = build_fx_event_log(fx, max_events=max_events)
    if not fx_events.empty:
        fx_events["unit"] = "%"
        frames.append(_standardize_event_frame(fx_events, "Ngoại hối"))

    if not fx.empty:
        volatility_status = fx["volatility_regime"].map(_status_from_regime)
        previous_status = volatility_status.shift(1)
        volatility_mask = (
            volatility_status.ne(previous_status)
            & volatility_status.isin([STATUS_WATCH, STATUS_ALERT])
        )
        if volatility_mask.any():
            selected = fx.loc[volatility_mask].copy()
            volatility_frame = pd.DataFrame(
                {
                    "date": selected["date"],
                    "indicator": "Độ biến động tỷ giá 20 ngày",
                    "value": selected["volatility_20d_pct"],
                    "unit": "%/năm",
                    "signal": selected["volatility_20d_pct"],
                    "watch_threshold": selected["vol20_p80"],
                    "alert_threshold": selected["vol20_p95"],
                    "status": volatility_status.loc[selected.index],
                }
            )
            frames.append(_standardize_event_frame(volatility_frame, "Ngoại hối"))

    money_market = prepare_money_market_data(interbank_data)
    mm_events = build_money_market_event_log(money_market, max_events=max_events)
    if not mm_events.empty:
        frames.append(_standardize_event_frame(mm_events, "Liên ngân hàng"))

    deposits = prepare_deposit_rate_data(deposit_data)
    deposit_events = build_deposit_rate_event_log(deposits, max_events=max_events)
    if not deposit_events.empty:
        frames.append(_standardize_event_frame(deposit_events, "Lãi suất huy động"))

    funding_events = funding_pressure_data[
        funding_pressure_data["status"].isin([STATUS_WATCH, STATUS_ALERT])
    ].copy()
    if not funding_events.empty:
        funding_frame = pd.DataFrame(
            {
                "date": funding_events["date"],
                "indicator": "Chỉ số áp lực nguồn vốn",
                "value": funding_events["funding_pressure_index"],
                "unit": "điểm",
                "signal": funding_events["funding_pressure_index"],
                "watch_threshold": funding_events["watch_threshold"],
                "alert_threshold": funding_events["alert_threshold"],
                "status": funding_events["status"],
            }
        )
        frames.append(_standardize_event_frame(funding_frame, "Áp lực nguồn vốn"))

    if bond_monitor_data is not None and not bond_monitor_data.empty:
        bond_events = bond_monitor_data[
            bond_monitor_data["status"].isin([STATUS_WATCH, STATUS_ALERT])
        ].copy()
        if not bond_events.empty:
            bond_frame = pd.DataFrame(
                {
                    "date": bond_events["date"],
                    "indicator": bond_events["tenor_years"].map(
                        lambda tenor: f"Biến động lợi suất kỳ hạn {float(tenor):g} năm"
                    ),
                    "value": bond_events["yield_change_bps"],
                    "unit": "bps",
                    "signal": bond_events["yield_change_bps"].abs(),
                    "watch_threshold": bond_events["watch_threshold_bps"],
                    "alert_threshold": bond_events["alert_threshold_bps"],
                    "status": bond_events["status"],
                }
            )
            frames.append(_standardize_event_frame(bond_frame, "Trái phiếu Chính phủ"))

    if not frames:
        return pd.DataFrame()

    history = pd.concat(frames, ignore_index=True)
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history = history.dropna(subset=["date"])

    return (
        history.sort_values(["date", "severity_rank"], ascending=[False, False])
        .head(max_events)
        .reset_index(drop=True)
    )


def summarize_alert_console(snapshot: pd.DataFrame) -> dict[str, object]:
    """Tổng hợp trạng thái hiện tại của trung tâm cảnh báo."""
    if snapshot.empty:
        return {
            "overall_status": STATUS_NORMAL,
            "open_count": 0,
            "watch_count": 0,
            "alert_count": 0,
            "active_group_count": 0,
            "total_indicators": 0,
        }

    watch_count = int(snapshot["status"].eq(STATUS_WATCH).sum())
    alert_count = int(snapshot["status"].eq(STATUS_ALERT).sum())
    open_mask = snapshot["status"].isin([STATUS_WATCH, STATUS_ALERT])
    open_count = int(open_mask.sum())
    active_group_count = int(snapshot.loc[open_mask, "group"].nunique())

    if alert_count > 0:
        overall_status = STATUS_ALERT
    elif watch_count > 0:
        overall_status = STATUS_WATCH
    else:
        overall_status = STATUS_NORMAL

    return {
        "overall_status": overall_status,
        "open_count": open_count,
        "watch_count": watch_count,
        "alert_count": alert_count,
        "active_group_count": active_group_count,
        "total_indicators": len(snapshot),
    }


def build_group_status_table(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp trạng thái và số tín hiệu đang mở theo nhóm."""
    if snapshot.empty:
        return pd.DataFrame(
            columns=["group", "latest_date", "status", "open_count", "indicator_count"]
        )

    rows = []
    existing_groups = list(dict.fromkeys(GROUP_ORDER + snapshot["group"].tolist()))

    for group in existing_groups:
        group_data = snapshot[snapshot["group"] == group]
        if group_data.empty:
            continue

        max_rank = int(group_data["severity_rank"].max())
        status = next(
            name for name, rank in SEVERITY_RANK.items() if rank == max_rank
        )
        open_count = int(group_data["status"].isin([STATUS_WATCH, STATUS_ALERT]).sum())

        rows.append(
            {
                "group": group,
                "latest_date": group_data["date"].max(),
                "status": status,
                "open_count": open_count,
                "indicator_count": len(group_data),
            }
        )

    return pd.DataFrame(rows)


def build_daily_alert_counts(history: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp số tín hiệu Theo dõi/Cảnh báo theo ngày."""
    if history.empty:
        return pd.DataFrame(columns=["date", "status", "count"])

    result = (
        history.groupby(["date", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    return result.sort_values("date").reset_index(drop=True)
