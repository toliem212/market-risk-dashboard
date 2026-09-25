"""Chuẩn hóa bảng hiển thị và bảng xuất báo cáo."""

import pandas as pd

from modules.alert_engine import STATUS_NORMAL
from modules.ui_helpers import format_date, format_number, format_value, status_with_icon

def prepare_historical_scenario_table(library: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa thư viện kịch bản lịch sử để hiển thị."""
    if library.empty:
        return pd.DataFrame()

    table = library.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Điểm stress"] = table["stress_score"].map(
        lambda value: format_number(value, 1)
    )
    table["USD/VND"] = table["fx_shock_pct"].map(
        lambda value: f"{format_number(value, 3)}%"
    )
    table["O/N"] = table["on_shock_bps"].map(
        lambda value: f"{format_number(value, 0)} bps"
    )
    table["1W"] = table["rate_1w_shock_bps"].map(
        lambda value: f"{format_number(value, 0)} bps"
    )
    table["1M"] = table["rate_1m_shock_bps"].map(
        lambda value: f"{format_number(value, 0)} bps"
    )
    table["3M"] = table["rate_3m_shock_bps"].map(
        lambda value: f"{format_number(value, 0)} bps"
    )
    table["Huy động 12M"] = table["deposit_12m_shock_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{format_number(value, 1)} bps"
    )

    return table[
        [
            "Ngày",
            "Điểm stress",
            "strongest_driver",
            "USD/VND",
            "O/N",
            "1W",
            "1M",
            "3M",
            "Huy động 12M",
        ]
    ].rename(columns={"strongest_driver": "Yếu tố nổi bật"})

def prepare_selected_historical_shock(row: pd.Series) -> pd.DataFrame:
    """Tạo bảng cú sốc quan sát được của một phiên lịch sử."""
    values = [
        ("USD/VND", row["fx_shock_pct"], "%"),
        ("Lãi suất O/N", row["on_shock_bps"], "bps"),
        ("Lãi suất 1 tuần", row["rate_1w_shock_bps"], "bps"),
        ("Lãi suất 1 tháng", row["rate_1m_shock_bps"], "bps"),
        ("Lãi suất 3 tháng", row["rate_3m_shock_bps"], "bps"),
        ("Huy động 12 tháng", row["deposit_12m_shock_bps"], "bps"),
    ]

    records = []
    for factor, value, unit in values:
        records.append(
            {
                "Yếu tố": factor,
                "Cú sốc lịch sử": "—" if pd.isna(value) else format_value(value, unit),
            }
        )

    return pd.DataFrame(records)

def prepare_alert_table(alerts: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng cảnh báo."""
    if alerts.empty:
        return pd.DataFrame()

    table = alerts.copy()
    table["Ngày dữ liệu"] = table["date"].map(format_date)
    table["Trạng thái"] = table["status"].map(status_with_icon)

    table["Giá trị"] = table.apply(
        lambda row: format_value(row["value"], row["value_unit"]),
        axis=1,
    )

    table["Tín hiệu"] = table.apply(
        lambda row: format_value(row["signal_value"], row["signal_unit"]),
        axis=1,
    )

    table["Ngưỡng theo dõi"] = table.apply(
        lambda row: format_value(row["watch_threshold"], row["signal_unit"]),
        axis=1,
    )

    table["Ngưỡng cảnh báo"] = table.apply(
        lambda row: format_value(row["alert_threshold"], row["signal_unit"]),
        axis=1,
    )

    return table[
        [
            "Ngày dữ liệu",
            "group",
            "indicator",
            "Giá trị",
            "Tín hiệu",
            "Ngưỡng theo dõi",
            "Ngưỡng cảnh báo",
            "Trạng thái",
            "reason",
        ]
    ].rename(
        columns={
            "group": "Nhóm giám sát",
            "indicator": "Chỉ báo",
            "reason": "Diễn giải",
        }
    )

def prepare_stress_table(results: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng kiểm tra sức chịu đựng."""
    table = results.copy()

    table["Hiện tại"] = table.apply(
        lambda row: format_value(row["current_value"], row["value_unit"]),
        axis=1,
    )

    table["Cú sốc"] = table.apply(
        lambda row: format_value(row["shock_value"], row["shock_unit"]),
        axis=1,
    )

    table["Sau cú sốc"] = table.apply(
        lambda row: format_value(row["stressed_value"], row["value_unit"]),
        axis=1,
    )

    table["Ngưỡng theo dõi"] = table.apply(
        lambda row: format_value(row["watch_threshold"], row["shock_unit"]),
        axis=1,
    )

    table["Ngưỡng cảnh báo"] = table.apply(
        lambda row: format_value(row["alert_threshold"], row["shock_unit"]),
        axis=1,
    )

    table["Mức độ"] = table["status"].map(status_with_icon)

    return table[
        [
            "factor",
            "Hiện tại",
            "Cú sốc",
            "Sau cú sốc",
            "Ngưỡng theo dõi",
            "Ngưỡng cảnh báo",
            "Mức độ",
            "reason",
        ]
    ].rename(
        columns={
            "factor": "Yếu tố",
            "reason": "Diễn giải",
        }
    )

def prepare_var_table(var_table: pd.DataFrame, unit: str) -> pd.DataFrame:
    """Chuẩn hóa bảng VaR/ES."""
    table = var_table.copy()

    table["Mức tin cậy"] = table["confidence_level"].map(
        lambda value: f"{value * 100:.1f}%".replace(".0%", "%")
    )
    table["VaR"] = table["var"].map(lambda value: format_value(value, unit))
    table["Expected Shortfall (ES)"] = table["es"].map(
        lambda value: format_value(value, unit)
    )
    table["Lỗ trung bình"] = table["mean_loss"].map(
        lambda value: format_value(value, unit)
    )
    table["Độ lệch chuẩn"] = table["std_loss"].map(
        lambda value: format_value(value, unit)
    )

    return table[
        [
            "method",
            "Mức tin cậy",
            "VaR",
            "Expected Shortfall (ES)",
            "Lỗ trung bình",
            "Độ lệch chuẩn",
            "observations",
        ]
    ].rename(
        columns={
            "method": "Phương pháp",
            "observations": "Số quan sát",
        }
    )

def prepare_backtest_test_table(
    tests: pd.DataFrame,
) -> pd.DataFrame:
    """Chuẩn hóa bảng kiểm định VaR để hiển thị."""
    table = tests.copy()

    table["Thống kê LR"] = table["statistic"].map(
        lambda value: "—" if pd.isna(value) else format_number(value, 3)
    )
    table["p-value"] = table["p_value"].map(
        lambda value: "—" if pd.isna(value) else format_number(value, 4)
    )
    table["Kết quả"] = table["result"]

    return table[
        [
            "test",
            "Thống kê LR",
            "p-value",
            "Kết quả",
        ]
    ].rename(columns={"test": "Kiểm định"})

def prepare_exception_log(
    exceptions: pd.DataFrame,
    unit: str,
) -> pd.DataFrame:
    """Chuẩn hóa bảng các ngày vượt VaR."""
    if exceptions.empty:
        return pd.DataFrame()

    table = exceptions.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Lỗ thực tế"] = table["loss"].map(
        lambda value: format_value(value, unit)
    )
    table["VaR"] = table["rolling_var"].map(
        lambda value: format_value(value, unit)
    )
    table["Mức vượt"] = table["excess_loss"].map(
        lambda value: format_value(value, unit)
    )

    return table[
        [
            "Ngày",
            "Lỗ thực tế",
            "VaR",
            "Mức vượt",
        ]
    ]

def prepare_funding_component_table(components: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng phân rã áp lực nguồn vốn."""
    if components.empty:
        return pd.DataFrame()

    table = components.copy()
    table["Giá trị"] = table.apply(
        lambda row: format_value(row["raw_value"], row["raw_unit"]),
        axis=1,
    )
    table["Z-score"] = table["zscore"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}σ"
    )
    table["Điểm áp lực"] = table["pressure_score"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}"
    )

    return table[
        ["component", "Giá trị", "Z-score", "Điểm áp lực"]
    ].rename(columns={"component": "Thành phần"})

def prepare_funding_event_table(events: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng lịch sử các ngày áp lực nguồn vốn cao."""
    if events.empty:
        return pd.DataFrame()

    table = events.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Trạng thái"] = table["status"].map(status_with_icon)
    table["Chỉ số"] = table["funding_pressure_index"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}"
    )
    table["P95"] = table["watch_threshold"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}"
    )
    table["P99"] = table["alert_threshold"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}"
    )
    table["Chênh lệch 3M - huy động 1-3M"] = table["spread_3m_vs_deposit_1_3m"].map(
        lambda value: format_value(value, "điểm phần trăm")
    )
    table["Δ huy động 12M/20 quan sát"] = table[
        "deposit_12m_change_20d_bps"
    ].map(lambda value: format_value(value, "bps"))

    return table[
        [
            "Ngày",
            "Chỉ số",
            "P95",
            "P99",
            "Chênh lệch 3M - huy động 1-3M",
            "Δ huy động 12M/20 quan sát",
            "Trạng thái",
        ]
    ]

def prepare_irrbb_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng kết quả IRRBB để hiển thị."""
    table = data.copy()

    table["RSA"] = table["rsa"].map(
        lambda value: format_number(value, 0)
    )
    table["RSL"] = table["rsl"].map(
        lambda value: format_number(value, 0)
    )
    table["Chênh lệch kỳ định lại lãi suất"] = table["repricing_gap"].map(
        lambda value: format_number(value, 0)
    )
    table["Chênh lệch lũy kế"] = table["cumulative_gap"].map(
        lambda value: format_number(value, 0)
    )
    table["Cú sốc lãi suất"] = table["shock_bps"].map(
        lambda value: f"{value:+.0f} bps"
    )
    table["ΔNII xấp xỉ"] = table["nii_impact"].map(
        lambda value: f"{format_number(value, 1)} tỷ đồng"
    )
    table["ΔEVE xấp xỉ"] = table["eve_proxy_impact"].map(
        lambda value: f"{format_number(value, 1)} tỷ đồng"
    )

    return table[
        [
            "bucket",
            "RSA",
            "RSL",
            "Chênh lệch kỳ định lại lãi suất",
            "Chênh lệch lũy kế",
            "Cú sốc lãi suất",
            "ΔNII xấp xỉ",
            "ΔEVE xấp xỉ",
        ]
    ].rename(
        columns={
            "bucket": "Nhóm kỳ hạn tái định giá",
        }
    )

def prepare_liquidity_gap_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng chênh lệch dòng tiền thanh khoản để hiển thị."""
    table = data.copy()

    output = pd.DataFrame(
        {
            "Nhóm kỳ hạn": table["bucket"],
            "Dòng tiền vào cơ sở": table["cash_inflow"].map(
                lambda value: format_number(value, 0)
            ),
            "Dòng tiền ra cơ sở": table["cash_outflow"].map(
                lambda value: format_number(value, 0)
            ),
            "Dòng tiền vào sau cú sốc": table["stressed_inflow"].map(
                lambda value: format_number(value, 0)
            ),
            "Dòng tiền ra sau cú sốc": table["stressed_outflow"].map(
                lambda value: format_number(value, 0)
            ),
            "Chênh lệch dòng tiền thanh khoản": table["stressed_net_flow"].map(
                lambda value: format_number(value, 0)
            ),
            "Chênh lệch lũy kế": table["stressed_cumulative_gap"].map(
                lambda value: format_number(value, 0)
            ),
            "Trạng thái thanh khoản": table["liquidity_position"].map(
                lambda value: format_number(value, 0)
            ),
        }
    )

    return output

def prepare_limit_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng hạn mức để hiển thị."""
    if data.empty:
        return pd.DataFrame()

    table = data.copy()

    table["Giá trị hiện tại"] = table.apply(
        lambda row: format_value(row["current_value"], row["unit"]),
        axis=1,
    )

    table["Hạn mức"] = table.apply(
        lambda row: format_value(row["limit_value"], row["unit"]),
        axis=1,
    )

    table["Mức sử dụng"] = table["utilization_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.1f}%"
    )

    table["Dư địa hạn mức"] = table.apply(
        lambda row: format_value(row["headroom"], row["unit"]),
        axis=1,
    )

    table["Trạng thái"] = table["status"].map(status_with_icon)

    return table[
        [
            "book",
            "risk_type",
            "metric",
            "Giá trị hiện tại",
            "Hạn mức",
            "Mức sử dụng",
            "Dư địa hạn mức",
            "Trạng thái",
            "action",
        ]
    ].rename(
        columns={
            "book": "Sổ/Danh mục",
            "risk_type": "Nhóm rủi ro",
            "metric": "Chỉ tiêu",
            "action": "Hành động",
        }
    )

def prepare_limit_exception_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa nhật ký cảnh báo và vượt hạn mức."""
    if data.empty:
        return pd.DataFrame()

    table = prepare_limit_table(data)

    if "validation_message" in data.columns:
        validation = data["validation_message"].replace("", "—").reset_index(drop=True)
        table = table.reset_index(drop=True)
        table["Ghi chú dữ liệu"] = validation

    return table

def prepare_market_attribution_snapshot_table(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng phân rã biến động để hiển thị."""
    if snapshot.empty:
        return pd.DataFrame()

    table = snapshot.copy()
    table["Biến động"] = table.apply(
        lambda row: format_value(row["value"], row["unit"]),
        axis=1,
    )
    table["Điểm chuẩn hóa"] = table["score"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.2f}σ"
    )
    table["Tỷ trọng cường độ"] = table["contribution_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.1f}%"
    )
    table["Mức độ"] = table["status"].map(status_with_icon)

    return table[
        [
            "factor",
            "Biến động",
            "direction",
            "Điểm chuẩn hóa",
            "Tỷ trọng cường độ",
            "Mức độ",
        ]
    ].rename(
        columns={
            "factor": "Yếu tố",
            "direction": "Chiều biến động",
        }
    )

def prepare_extreme_attribution_table(events: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng các phiên biến động tổng hợp lớn nhất."""
    if events.empty:
        return pd.DataFrame()

    table = events.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Cường độ"] = table["market_move_intensity"].map(
        lambda value: format_number(value, 2)
    )
    table["Yếu tố chi phối"] = table["dominant_factor"]
    table["Tỷ trọng"] = table["dominant_contribution_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.1f}%"
    )
    table["Mức độ"] = table["status"].map(status_with_icon)

    return table[
        ["Ngày", "Cường độ", "Yếu tố chi phối", "Tỷ trọng", "Mức độ"]
    ]

def prepare_tail_exception_table(
    exceptions: pd.DataFrame,
    unit: str,
) -> pd.DataFrame:
    """Chuẩn hóa bảng các lần lỗ vượt VaR."""
    if exceptions.empty:
        return pd.DataFrame()

    table = exceptions.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Lỗ thực tế"] = table["loss"].map(lambda value: format_value(value, unit))
    table["VaR"] = table["historical_var"].map(lambda value: format_value(value, unit))
    table["ES"] = table["historical_es"].map(lambda value: format_value(value, unit))
    table["Phần lỗ vượt VaR"] = table["excess_loss"].map(
        lambda value: format_value(value, unit)
    )
    table["Mức vượt"] = table["exception_severity"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}x"
    )

    return table[
        [
            "Ngày",
            "Lỗ thực tế",
            "VaR",
            "ES",
            "Phần lỗ vượt VaR",
            "Mức vượt",
        ]
    ]

def prepare_fx_event_table(events: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng sự kiện ngoại hối."""
    if events.empty:
        return pd.DataFrame()

    table = events.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Giá trị"] = table["value"].map(lambda value: f"{value:+.3f}%")
    table["P95"] = table["watch_threshold"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.3f}%"
    )
    table["P99"] = table["alert_threshold"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.3f}%"
    )
    table["Trạng thái"] = table["status"].map(status_with_icon)

    return table[
        ["Ngày", "indicator", "Giá trị", "P95", "P99", "Trạng thái"]
    ].rename(columns={"indicator": "Chỉ báo"})

def prepare_fx_extreme_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng các phiên biến động mạnh."""
    if data.empty:
        return pd.DataFrame()

    table = data.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["Đóng cửa"] = table["close"].map(lambda value: format_number(value, 0))
    table["Thay đổi"] = table["daily_return_pct"].map(
        lambda value: f"{value:+.3f}%"
    )
    table["Biên độ"] = table["intraday_range_pct"].map(
        lambda value: f"{value:.3f}%"
    )
    table["Độ biến động 20 ngày"] = table["volatility_20d_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )
    table["Mức giảm từ đỉnh 250 ngày"] = table["drawdown_250d_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )

    return table[
        [
            "Ngày",
            "Đóng cửa",
            "Thay đổi",
            "Biên độ",
            "Độ biến động 20 ngày",
            "Mức giảm từ đỉnh 250 ngày",
        ]
    ]

def prepare_money_market_event_table(events: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng sự kiện thị trường liên ngân hàng."""
    if events.empty:
        return pd.DataFrame()

    table = events.copy()
    table["Ngày"] = table["date"].map(format_date)

    def format_signal(row: pd.Series) -> str:
        if pd.isna(row["value"]):
            return "—"
        if row["unit"] == "bps":
            return f"{row['value']:+.0f} bps"
        return f"{row['value']:+.2f}σ"

    def format_threshold(row: pd.Series, column: str) -> str:
        value = row[column]
        if pd.isna(value):
            return "—"
        if row["unit"] == "bps":
            return f"{value:.0f} bps"
        return f"{value:.1f}σ"

    table["Giá trị"] = table.apply(format_signal, axis=1)
    table["Ngưỡng theo dõi"] = table.apply(
        lambda row: format_threshold(row, "watch_threshold"), axis=1
    )
    table["Ngưỡng cảnh báo"] = table.apply(
        lambda row: format_threshold(row, "alert_threshold"), axis=1
    )
    table["Trạng thái"] = table["status"].map(status_with_icon)

    return table[
        [
            "Ngày",
            "indicator",
            "Giá trị",
            "Ngưỡng theo dõi",
            "Ngưỡng cảnh báo",
            "Trạng thái",
        ]
    ].rename(columns={"indicator": "Chỉ báo"})

def prepare_money_market_extreme_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng các phiên biến động O/N mạnh nhất."""
    if data.empty:
        return pd.DataFrame()

    table = data.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["O/N"] = table["rate_on"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )
    table["Δ O/N"] = table["change_on_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )
    table["1W"] = table["rate_1w"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )
    table["1M"] = table["rate_1m"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )
    table["3M"] = table["rate_3m"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}%"
    )
    table["3M - O/N"] = table["spread_3m_on_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )
    table["Tổng doanh số"] = table["total_turnover"].map(
        lambda value: "—" if pd.isna(value) else f"{format_number(value, 0)} tỷ"
    )

    return table[
        ["Ngày", "O/N", "Δ O/N", "1W", "1M", "3M", "3M - O/N", "Tổng doanh số"]
    ]

def prepare_deposit_rate_event_table(events: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng sự kiện lãi suất huy động."""
    if events.empty:
        return pd.DataFrame()

    table = events.copy()
    table["Ngày"] = table["date"].map(format_date)

    def format_signal(row: pd.Series) -> str:
        if pd.isna(row["value"]):
            return "—"
        if row["unit"] == "bps":
            return f"{row['value']:.0f} bps"
        return f"{row['value']:+.2f}σ"

    def format_threshold(row: pd.Series, column: str) -> str:
        value = row[column]
        if pd.isna(value):
            return "—"
        if row["unit"] == "bps":
            return f"{value:.0f} bps"
        return f"{value:.1f}σ"

    table["Giá trị"] = table.apply(format_signal, axis=1)
    table["Ngưỡng theo dõi"] = table.apply(
        lambda row: format_threshold(row, "watch_threshold"), axis=1
    )
    table["Ngưỡng cảnh báo"] = table.apply(
        lambda row: format_threshold(row, "alert_threshold"), axis=1
    )
    table["Trạng thái"] = table["status"].map(status_with_icon)

    return table[
        [
            "Ngày",
            "indicator",
            "Giá trị",
            "Ngưỡng theo dõi",
            "Ngưỡng cảnh báo",
            "Trạng thái",
        ]
    ].rename(columns={"indicator": "Chỉ báo"})

def prepare_deposit_rate_extreme_table(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa bảng các giai đoạn điều chỉnh lãi suất mạnh."""
    if data.empty:
        return pd.DataFrame()

    table = data.copy()
    table["Ngày"] = table["date"].map(format_date)
    table["1-3 tháng"] = table["deposit_1_3m"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.3f}%"
    )
    table["6-9 tháng"] = table["deposit_6_9m"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.3f}%"
    )
    table["12 tháng"] = table["deposit_12m"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.3f}%"
    )
    table["Δ 1-3M"] = table["change_1obs_1_3m_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )
    table["Δ 6-9M"] = table["change_1obs_6_9m_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )
    table["Δ 12M"] = table["change_1obs_12m_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )
    table["12M - 1-3M"] = table["spread_12m_1_3m_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{value:+.0f} bps"
    )

    return table[
        [
            "Ngày",
            "dominant_repricing_tenor",
            "1-3 tháng",
            "6-9 tháng",
            "12 tháng",
            "Δ 1-3M",
            "Δ 6-9M",
            "Δ 12M",
            "12M - 1-3M",
        ]
    ].rename(columns={"dominant_repricing_tenor": "Kỳ hạn biến động mạnh nhất"})

def build_overview_alert_table(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa các tín hiệu đang mở cho trang tổng quan."""
    if snapshot.empty:
        return pd.DataFrame()

    open_alerts = snapshot[snapshot["status"] != STATUS_NORMAL].copy()
    if open_alerts.empty:
        return pd.DataFrame()

    open_alerts["Ngày dữ liệu"] = open_alerts["date"].map(format_date)
    open_alerts["Giá trị"] = open_alerts.apply(
        lambda row: format_value(row.get("value"), row.get("value_unit", "")),
        axis=1,
    )
    open_alerts["Trạng thái"] = open_alerts["status"].map(status_with_icon)

    return (
        open_alerts[
            ["Ngày dữ liệu", "group", "indicator", "Giá trị", "Trạng thái"]
        ]
        .rename(columns={"group": "Nhóm giám sát", "indicator": "Chỉ báo"})
        .head(8)
        .reset_index(drop=True)
    )

def build_data_freshness_table(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> pd.DataFrame:
    """Tổng hợp phạm vi và ngày cập nhật của các bộ dữ liệu chính."""
    rows = []

    for name, data in [
        ("USD/VND", fx_data),
        ("Liên ngân hàng", interbank_data),
        ("Lãi suất huy động", deposit_data),
    ]:
        rows.append(
            {
                "Bộ dữ liệu": name,
                "Từ ngày": format_date(data["date"].min()),
                "Đến ngày": format_date(data["date"].max()),
                "Số quan sát": f"{len(data):,}".replace(",", "."),
            }
        )

    return pd.DataFrame(rows)

