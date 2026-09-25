"""Các màn hình và luồng tương tác của dashboard."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.alert_engine import STATUS_ALERT, STATUS_NORMAL, STATUS_WATCH
from modules.fx_risk_monitor import (
    build_extreme_move_table,
    build_fx_event_log,
    build_fx_window_summary,
    prepare_fx_risk_data,
    summarize_fx_risk,
)
from modules.money_market_monitor import (
    build_money_market_event_log,
    build_money_market_extremes,
    build_money_market_window_summary,
    prepare_money_market_data,
    summarize_money_market,
)
from modules.deposit_rate_monitor import (
    build_deposit_rate_event_log,
    build_deposit_rate_extremes,
    build_deposit_rate_window_summary,
    prepare_deposit_rate_data,
    summarize_deposit_rates,
)
from modules.risk_alert_console import (
    build_central_alert_history,
    build_current_alert_snapshot,
    build_daily_alert_counts,
    build_group_status_table,
    summarize_alert_console,
)
from modules.data_quality_monitor import (
    build_data_quality_report as build_dq_report,
    build_freshness_table,
    build_quality_exceptions,
    build_reconciliation_table,
    summarize_quality,
)
from modules.daily_report import (
    build_exception_report,
    build_market_snapshot,
    build_report_filename,
    build_source_status,
    export_daily_report_excel,
    summarize_daily_report,
)
from modules.risk_heatmap import (
    HEATMAP_COLUMNS,
    STATUS_NOT_AVAILABLE as HEATMAP_STATUS_NOT_AVAILABLE,
    build_risk_heatmap,
    build_risk_heatmap_detail,
    status_to_score,
    summarize_risk_heatmap,
)
from modules.market_factor_attribution import (
    FACTOR_DEFINITIONS,
    build_attribution_snapshot,
    build_dominant_factor_summary,
    build_extreme_attribution_events,
    build_market_factor_attribution_data,
    summarize_market_factor_attribution,
)
from modules.control_tower import (
    STATUS_INPUT as CONTROL_STATUS_INPUT,
    STATUS_MISSING as CONTROL_STATUS_MISSING,
    STATUS_NORMAL as CONTROL_STATUS_NORMAL,
    STATUS_READY as CONTROL_STATUS_READY,
    STATUS_REVIEW as CONTROL_STATUS_REVIEW,
    build_control_tower_table,
    build_priority_items,
    summarize_control_tower,
)
from modules.exception_workflow import (
    STATUS_CLOSED as WORKFLOW_STATUS_CLOSED,
    STATUS_ESCALATED as WORKFLOW_STATUS_ESCALATED,
    STATUS_NEW as WORKFLOW_STATUS_NEW,
    WORKFLOW_STATUSES,
    apply_case_updates,
    enrich_case_metrics,
    export_workflow_excel,
    load_case_store,
    load_event_store,
    save_case_store,
    save_event_store,
    summarize_cases,
    sync_current_alerts,
)
from modules.limit_monitor import (
    STATUS_BREACH as LIMIT_STATUS_BREACH,
    STATUS_INVALID as LIMIT_STATUS_INVALID,
    blank_limit_template,
    build_exception_log,
    completed_limit_rows,
    count_partial_limit_rows,
    evaluate_limits,
    summarize_limits,
)
from modules.stress_test import (
    PRESET_SCENARIOS,
    build_interbank_curve,
    get_preset_scenario,
    run_stress_test,
    summarize_stress_results,
)
from modules.historical_stress import (
    HISTORICAL_SCENARIO_CATEGORIES,
    build_historical_scenario_library,
    build_historical_stress_timeline,
    prepare_historical_stress_data,
    scenario_from_row,
    summarize_historical_stress,
)
from modules.var_engine import (
    METHOD_HISTORICAL,
    METHOD_PARAMETRIC,
    POSITION_LONG_USD,
    POSITION_SHORT_USD,
    RATE_FACTORS,
    build_fx_loss_series,
    build_rate_loss_series,
    calculate_var_table,
    rolling_historical_var,
    select_lookback,
    summarize_rolling_var,
)
from modules.tail_risk_monitor import (
    build_confidence_ladder,
    build_rolling_tail_metrics,
    build_tail_exception_table,
    summarize_rolling_tail_metrics,
    summarize_tail_risk,
)
from modules.backtesting import (
    OVERALL_ACCEPTABLE,
    OVERALL_NOT_AVAILABLE,
    OVERALL_REVIEW,
    RESULT_NOT_AVAILABLE,
    run_var_backtest,
)
from modules.funding_pressure import (
    build_funding_pressure_data,
    build_pressure_components_snapshot,
    build_pressure_events,
    summarize_funding_pressure,
)
from modules.fixed_income_monitor import (
    available_tenors,
    blank_yield_curve_template,
    build_curve_comparison,
    build_latest_curve_snapshot,
    build_tenor_history,
    prepare_yield_curve_monitor,
    standardize_yield_curve_input,
    summarize_yield_curve,
)
from modules.liquidity_gap import (
    SCENARIO_CUSTOM as LIQUIDITY_SCENARIO_CUSTOM,
    SCENARIO_OPTIONS as LIQUIDITY_SCENARIO_OPTIONS,
    blank_liquidity_template,
    calculate_liquidity_gap,
    get_scenario_parameters as get_liquidity_scenario_parameters,
    liquidity_input_ready,
    summarize_liquidity_gap,
)
from modules.irrbb_monitor import (
    SCENARIO_CUSTOM,
    SCENARIO_OPTIONS,
    blank_repricing_template,
    calculate_irrbb,
    irrbb_input_ready,
    summarize_irrbb,
)


from modules.app_config import (
    APP_TITLE,
    BOND_CSV_FILE,
    BOND_FILE,
    CANDIDATE_NAME,
    WORKFLOW_CASE_FILE,
    WORKFLOW_EVENT_FILE,
)
from modules.data_loader import read_table_source, read_uploaded_table
from modules.ui_helpers import (
    apply_chart_layout, classify_data_quality, format_date, format_number, format_value,
    select_period, show_chart, status_with_icon,
)
from modules.charts import (
    create_fx_line_chart,
    create_interbank_rate_chart,
    create_fx_candlestick_chart,
    create_fx_return_chart,
    create_fx_volatility_chart,
    create_fx_threshold_chart,
    create_fx_drawdown_chart,
    create_fx_volatility_regime_chart,
    create_fx_range_threshold_chart,
    create_interbank_spread_chart,
    create_interbank_turnover_chart,
    create_on_change_threshold_chart,
    create_on_level_zscore_chart,
    create_money_market_curve_chart,
    create_turnover_zscore_chart,
    create_deposit_rate_chart,
    create_deposit_change_chart,
    create_deposit_repricing_threshold_chart,
    create_deposit_spread_chart,
    create_deposit_spread_zscore_chart,
    create_deposit_level_regime_chart,
    create_bond_yield_curve_chart,
    create_bond_curve_change_chart,
    create_bond_tenor_history_chart,
    create_bond_move_threshold_chart,
    create_stress_curve_chart,
    create_historical_stress_score_chart,
    create_loss_distribution_chart,
    create_rolling_var_chart,
    create_cumulative_exception_chart,
    create_funding_spread_chart,
    create_funding_pressure_index_chart,
    create_funding_component_chart,
    create_repricing_balance_chart,
    create_repricing_gap_chart,
    create_irrbb_shock_chart,
    create_irrbb_sensitivity_chart,
    create_liquidity_flow_chart,
    create_liquidity_gap_chart,
    create_liquidity_position_chart,
    create_limit_utilization_chart,
    create_risk_heatmap_chart,
    create_factor_contribution_chart,
    create_factor_contribution_history_chart,
    create_market_move_intensity_chart,
    create_dominant_factor_frequency_chart,
    create_confidence_ladder_chart,
    create_rolling_tail_chart,
    create_tail_ratio_chart,
    create_tail_volatility_chart
)
from modules.table_helpers import (
    prepare_historical_scenario_table,
    prepare_selected_historical_shock,
    prepare_alert_table,
    prepare_stress_table,
    prepare_var_table,
    prepare_backtest_test_table,
    prepare_exception_log,
    prepare_funding_component_table,
    prepare_funding_event_table,
    prepare_irrbb_table,
    prepare_liquidity_gap_table,
    prepare_limit_table,
    prepare_limit_exception_table,
    prepare_market_attribution_snapshot_table,
    prepare_extreme_attribution_table,
    prepare_tail_exception_table,
    prepare_fx_event_table,
    prepare_fx_extreme_table,
    prepare_money_market_event_table,
    prepare_money_market_extreme_table,
    prepare_deposit_rate_event_table,
    prepare_deposit_rate_extreme_table,
    build_overview_alert_table,
    build_data_freshness_table
)

def render_market_factor_attribution_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> None:
    """Hiển thị phân rã biến động thị trường theo các yếu tố quan sát được."""
    st.subheader("Phân rã biến động thị trường")

    attribution_data = build_market_factor_attribution_data(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )

    valid_data = attribution_data.dropna(subset=["market_move_intensity"]).copy()
    if valid_data.empty:
        st.info("Chưa đủ dữ liệu lịch sử để thực hiện phân rã biến động thị trường.")
        return

    available_dates = valid_data["date"].sort_values(ascending=False).tolist()
    selected_date = st.selectbox(
        "Ngày phân tích",
        options=available_dates,
        index=0,
        format_func=format_date,
        key="market_attribution_selected_date",
    )

    summary = summarize_market_factor_attribution(
        attribution_data,
        selected_date=selected_date,
    )
    snapshot = build_attribution_snapshot(
        attribution_data,
        selected_date=selected_date,
    )

    columns = st.columns(5)
    columns[0].metric("Ngày dữ liệu", format_date(summary["date"]))
    columns[1].metric("Yếu tố chi phối", summary["dominant_factor"])
    columns[2].metric(
        "Tỷ trọng chi phối",
        "—"
        if pd.isna(summary["dominant_contribution_pct"])
        else f"{summary['dominant_contribution_pct']:.1f}%",
    )
    columns[3].metric(
        "Cường độ biến động",
        format_number(summary["market_move_intensity"], 2),
    )
    columns[4].metric("Mức độ", summary["status"])

    st.caption(
        "Tỷ trọng phản ánh cường độ biến động chuẩn hóa của từng yếu tố tại cùng ngày, "
        "không phải mức đóng góp vào P&L của danh mục."
    )

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        show_chart(
            "Cơ cấu cường độ biến động theo yếu tố",
            create_factor_contribution_chart(snapshot),
            key="market_attribution_snapshot_chart",
        )

    with right:
        st.markdown("#### Chi tiết theo yếu tố")
        st.dataframe(
            prepare_market_attribution_snapshot_table(snapshot),
            width="stretch",
            hide_index=True,
        )

    period_options = {
        "3 tháng": 60,
        "6 tháng": 120,
        "1 năm": 250,
        "2 năm": 500,
    }
    selected_period = st.radio(
        "Khoảng thời gian phân tích",
        options=list(period_options.keys()),
        index=2,
        horizontal=True,
        key="market_attribution_period",
    )
    lookback = period_options[selected_period]

    left, right = st.columns(2, gap="large")

    with left:
        show_chart(
            "Tỷ trọng cường độ biến động theo thời gian",
            create_factor_contribution_history_chart(attribution_data, lookback),
            key="market_attribution_history_chart",
        )

    with right:
        show_chart(
            "Cường độ biến động tổng hợp",
            create_market_move_intensity_chart(attribution_data, lookback),
            key="market_attribution_intensity_chart",
        )

    dominant_summary = build_dominant_factor_summary(
        attribution_data,
        lookback=lookback,
    )

    left, right = st.columns([1, 1.25], gap="large")

    with left:
        show_chart(
            "Tần suất yếu tố chi phối",
            create_dominant_factor_frequency_chart(dominant_summary),
            key="market_attribution_dominant_frequency_chart",
        )

    with right:
        st.markdown("#### Các phiên biến động tổng hợp lớn nhất")
        extreme_events = build_extreme_attribution_events(
            attribution_data,
            lookback=max(lookback, 250),
            limit=12,
        )
        st.dataframe(
            prepare_extreme_attribution_table(extreme_events),
            width="stretch",
            hide_index=True,
        )

    export_columns = [
        "date",
        "market_move_intensity",
        "watch_threshold",
        "alert_threshold",
        "status",
        "dominant_factor",
        "dominant_contribution_pct",
    ]

    for factor in FACTOR_DEFINITIONS:
        export_columns.extend(
            [
                factor,
                f"{factor}_score",
                f"{factor}_contribution_pct",
            ]
        )

    export_data = attribution_data[export_columns].copy()
    st.download_button(
        "Tải dữ liệu phân rã",
        data=export_data.to_csv(index=False).encode("utf-8-sig"),
        file_name="market_factor_attribution.csv",
        mime="text/csv",
        width="content",
        key="download_market_factor_attribution",
    )

def render_sidebar() -> None:
    """Hiển thị thông tin dự án và cấu trúc chức năng."""
    with st.sidebar:
        st.markdown("## Giám sát rủi ro")
        st.caption("Market Risk Monitoring Dashboard")
        st.markdown(f"**Ứng viên: {CANDIDATE_NAME}**")

        st.divider()
        st.markdown("**Khối chức năng**")
        st.markdown(
            """- Điều hành
- Sổ kinh doanh
- Tiền tệ & nguồn vốn
- Cảnh báo & kiểm soát
- Nhập liệu nghiệp vụ"""
        )

        st.divider()
        st.caption(
            "Dữ liệu thị trường được tách khỏi các phân hệ cần vị thế, "
            "hạn mức hoặc dữ liệu bảng cân đối."
        )
        st.success("Dữ liệu đã nạp")

def render_status_card(
    title: str,
    status: str,
    description: str,
) -> None:
    """Hiển thị một thẻ trạng thái."""
    with st.container(border=True):
        st.caption(title)

        if status in {LIMIT_STATUS_BREACH, STATUS_ALERT}:
            st.error(status)
        elif status in {STATUS_WATCH, LIMIT_STATUS_INVALID}:
            st.warning(status)
        else:
            st.success(STATUS_NORMAL)

        st.caption(description)

def render_header() -> None:
    """Hiển thị tiêu đề."""
    st.title(APP_TITLE)
    st.caption(f"Ứng viên: {CANDIDATE_NAME}")
    st.caption(
        "Theo dõi biến động thị trường, cảnh báo sớm, kiểm tra sức chịu đựng "
        "và các chỉ tiêu định lượng phục vụ giám sát rủi ro."
    )

def render_kpis(
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
) -> None:
    """Hiển thị KPI thị trường."""
    latest_fx = fx_data.iloc[-1]
    latest_deposit = deposit_data.iloc[-1]
    latest_interbank = interbank_data.iloc[-1]

    columns = st.columns(4)

    with columns[0]:
        st.metric(
            "USD/VND",
            format_number(latest_fx["close"], 0),
            delta=f"{format_number(latest_fx['daily_return_pct'], 2)}%",
        )
        st.caption(f"Cập nhật {format_date(latest_fx['date'])}")

    with columns[1]:
        st.metric(
            "Lãi suất qua đêm",
            f"{format_number(latest_interbank['rate_on'], 2)}%",
            delta=(
                f"{format_number(latest_interbank['on_change_bps'], 0)} "
                "điểm cơ bản"
            ),
        )
        st.caption(f"Cập nhật {format_date(latest_interbank['date'])}")

    with columns[2]:
        st.metric(
            "Liên ngân hàng 3 tháng",
            f"{format_number(latest_interbank['rate_3m'], 2)}%",
        )
        st.caption(f"Cập nhật {format_date(latest_interbank['date'])}")

    with columns[3]:
        st.metric(
            "Huy động 12 tháng",
            f"{format_number(latest_deposit['deposit_12m'], 2)}%",
        )
        st.caption(f"Cập nhật {format_date(latest_deposit['date'])}")

def render_monitoring_status(
    alert_snapshot: pd.DataFrame,
    quality_report: pd.DataFrame,
) -> None:
    """Hiển thị trạng thái theo từng nhóm giám sát từ nguồn cảnh báo hợp nhất."""
    quality_status = classify_data_quality(quality_report)
    group_table = build_group_status_table(alert_snapshot)
    group_status = dict(zip(group_table.get("group", []), group_table.get("status", [])))

    st.markdown("### Trạng thái giám sát")
    columns = st.columns(5)

    with columns[0]:
        render_status_card(
            "Ngoại hối",
            group_status.get("Ngoại hối", STATUS_NORMAL),
            "Biến động tỷ giá, biên độ và độ biến động.",
        )

    with columns[1]:
        render_status_card(
            "Liên ngân hàng",
            group_status.get("Liên ngân hàng", STATUS_NORMAL),
            "Lãi suất qua đêm, cấu trúc kỳ hạn và doanh số.",
        )

    with columns[2]:
        render_status_card(
            "Áp lực nguồn vốn",
            group_status.get("Áp lực nguồn vốn", STATUS_NORMAL),
            "Tổng hợp lãi suất, chênh lệch lãi suất, huy động và doanh số.",
        )

    with columns[3]:
        render_status_card(
            "Lãi suất huy động",
            group_status.get("Lãi suất huy động", STATUS_NORMAL),
            "Biến động mặt bằng và cấu trúc kỳ hạn huy động.",
        )

    with columns[4]:
        render_status_card(
            "Chất lượng dữ liệu",
            quality_status,
            "Kiểm tra tính đầy đủ và hợp lý của dữ liệu.",
        )

def render_limit_monitor_tab() -> None:
    """Mô phỏng giám sát hạn mức khi người dùng cung cấp dữ liệu vị thế/hạn mức."""
    st.subheader("Giám sát hạn mức rủi ro - Sổ kinh doanh")

    st.caption("Dữ liệu yêu cầu: vị thế hoặc mức sử dụng rủi ro và hạn mức tương ứng.")

    template = blank_limit_template()
    required_columns = list(template.columns)

    if "trading_book_limit_table" not in st.session_state:
        st.session_state["trading_book_limit_table"] = template.copy()

    upload_col, download_col, reset_col = st.columns([2, 1, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Tải bảng hạn mức (CSV/XLSX)",
            type=["csv", "xlsx", "xls"],
            key="trading_book_limit_upload",
        )

    with download_col:
        st.download_button(
            "Tải tệp mẫu trống",
            data=template.to_csv(index=False).encode("utf-8-sig"),
            file_name="trading_book_limit_template.csv",
            mime="text/csv",
            width="stretch",
            key="download_trading_book_limit_template",
        )

    with reset_col:
        if st.button(
            "Làm trống bảng",
            key="reset_trading_book_limits",
            width="stretch",
        ):
            st.session_state["trading_book_limit_table"] = template.copy()

    if uploaded_file is not None:
        try:
            uploaded_data = read_uploaded_table(uploaded_file, required_columns)
            st.session_state["trading_book_limit_table"] = uploaded_data
        except ValueError as error:
            st.error(str(error))

    st.markdown("#### Dữ liệu vị thế và hạn mức")
    st.caption("Nhập giá trị hiện tại, hạn mức và các ngưỡng giám sát tương ứng.")

    edited_table = st.data_editor(
        st.session_state["trading_book_limit_table"].copy(),
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="trading_book_limit_editor",
        column_config={
            "limit_id": st.column_config.TextColumn("Mã hạn mức"),
            "book": st.column_config.TextColumn("Sổ/Danh mục"),
            "risk_type": st.column_config.TextColumn("Nhóm rủi ro"),
            "metric": st.column_config.TextColumn("Chỉ tiêu"),
            "current_value": st.column_config.NumberColumn("Giá trị hiện tại", format="%.2f"),
            "limit_value": st.column_config.NumberColumn("Hạn mức", format="%.2f", min_value=0.0),
            "unit": st.column_config.TextColumn("Đơn vị"),
            "watch_pct": st.column_config.NumberColumn(
                "Ngưỡng theo dõi (%)", format="%.1f", min_value=0.0, max_value=99.0
            ),
            "alert_pct": st.column_config.NumberColumn(
                "Ngưỡng cảnh báo (%)", format="%.1f", min_value=0.0, max_value=99.9
            ),
        },
    )

    st.session_state["trading_book_limit_table"] = edited_table.copy()

    try:
        completed = completed_limit_rows(edited_table)
        partial_count = count_partial_limit_rows(edited_table)
    except ValueError as error:
        st.error(str(error))
        return

    if partial_count > 0:
        st.warning(
            f"Có {partial_count} dòng đã nhập một phần nhưng chưa đủ trường số để tính."
        )

    if completed.empty:
        st.info("Chưa đủ dữ liệu để tính mức sử dụng hạn mức.")
        return

    evaluated = evaluate_limits(completed)
    summary = summarize_limits(evaluated)
    exceptions = build_exception_log(evaluated, include_watch=True)

    st.markdown("#### Trạng thái tổng hợp")
    columns = st.columns(5)
    columns[0].metric("Trạng thái chung", status_with_icon(summary["overall_status"]))

    max_utilization = summary["max_utilization_pct"]
    columns[1].metric(
        "Mức sử dụng cao nhất",
        "—" if pd.isna(max_utilization) else f"{max_utilization:.1f}%",
    )
    columns[2].metric("Theo dõi", summary["watch_count"])
    columns[3].metric("Cảnh báo", summary["alert_count"])
    columns[4].metric("Vượt hạn mức", summary["breach_count"])

    show_chart(
        "Mức sử dụng hạn mức",
        create_limit_utilization_chart(evaluated),
        key="trading_book_limit_utilization_chart",
    )

    st.markdown("#### Chi tiết hạn mức")
    st.dataframe(prepare_limit_table(evaluated), width="stretch", hide_index=True)

    st.markdown("#### Nhật ký cảnh báo và vượt hạn mức")
    if exceptions.empty:
        st.success("Không có hạn mức cần chuyển cấp trong dữ liệu đã nhập.")
    else:
        st.dataframe(
            prepare_limit_exception_table(exceptions),
            width="stretch",
            hide_index=True,
        )

    st.caption("Mức sử dụng hạn mức = |Giá trị hiện tại| / Hạn mức × 100.")

def render_control_tower_status_card(
    title: str,
    status: str,
    result: str,
) -> None:
    """Hiển thị trạng thái một bước kiểm soát."""
    with st.container(border=True):
        st.caption(title)

        if status == CONTROL_STATUS_NORMAL:
            st.success(status)
        elif status == CONTROL_STATUS_REVIEW:
            st.warning(status)
        elif status == CONTROL_STATUS_READY:
            st.info(status)
        elif status == CONTROL_STATUS_INPUT:
            st.info(status)
        else:
            st.warning(status)

        st.caption(result)

def render_control_tower_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
) -> None:
    """Màn hình điều hành chuỗi kiểm soát rủi ro thị trường hằng ngày."""
    st.subheader("Bảng điều hành giám sát")

    bond_monitor_data = load_bond_monitor_data_for_report()
    bond_data_available = not bond_monitor_data.empty

    current_alerts = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )
    central_summary = summarize_alert_console(current_alerts)

    dq_report = build_dq_report(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    dq_exceptions = build_quality_exceptions(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    quality_summary = summarize_quality(dq_report, dq_exceptions)

    historical_stress_data = prepare_historical_stress_data(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )
    historical_summary = summarize_historical_stress(historical_stress_data)

    workflow_cases = load_case_store(WORKFLOW_CASE_FILE)
    workflow_enriched = enrich_case_metrics(
        cases=workflow_cases,
        watch_sla_hours=24.0,
        alert_sla_hours=8.0,
    )
    workflow_summary = summarize_cases(workflow_enriched)

    table = build_control_tower_table(
        alert_summary=central_summary,
        quality_summary=quality_summary,
        workflow_summary=workflow_summary,
        historical_stress_observations=int(historical_summary.get("observations", 0) or 0),
        bond_data_available=bond_data_available,
    )
    summary = summarize_control_tower(table)

    metrics = st.columns(5)
    metrics[0].metric("Bình thường", summary["normal_count"])
    metrics[1].metric("Cần kiểm tra", summary["review_count"])
    metrics[2].metric("Sẵn sàng", summary["ready_count"])
    metrics[3].metric("Cần nhập liệu", summary["input_count"])
    metrics[4].metric("Chưa có dữ liệu", summary["missing_count"])

    st.markdown("#### Chuỗi kiểm soát hằng ngày")
    primary_steps = table[table["step"] <= 7]

    for start in range(0, len(primary_steps), 4):
        row = primary_steps.iloc[start : start + 4]
        columns = st.columns(len(row))
        for column, (_, item) in zip(columns, row.iterrows()):
            with column:
                render_control_tower_status_card(
                    title=f"{int(item['step'])}. {item['control']}",
                    status=item["status"],
                    result=item["result"],
                )

    st.markdown("#### Trạng thái toàn bộ điểm kiểm soát")
    table_view = table.copy()
    table_view["Trạng thái"] = table_view["status"].map(
        {
            CONTROL_STATUS_NORMAL: "🟢 Bình thường",
            CONTROL_STATUS_REVIEW: "🟡 Cần kiểm tra",
            CONTROL_STATUS_READY: "🔵 Sẵn sàng",
            CONTROL_STATUS_INPUT: "⚪ Cần nhập liệu",
            CONTROL_STATUS_MISSING: "⚪ Chưa có dữ liệu",
        }
    )
    table_view = table_view.rename(
        columns={
            "step": "Bước",
            "control": "Điểm kiểm soát",
            "scope": "Phạm vi",
            "result": "Kết quả hiện tại",
            "destination": "Phân hệ",
        }
    )
    st.dataframe(
        table_view[
            [
                "Bước",
                "Điểm kiểm soát",
                "Phạm vi",
                "Trạng thái",
                "Kết quả hiện tại",
                "Phân hệ",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Điểm cần xử lý")
    priorities = build_priority_items(
        alert_summary=central_summary,
        quality_summary=quality_summary,
        workflow_summary=workflow_summary,
        bond_data_available=bond_data_available,
    )

    if priorities.empty:
        st.success("Không có điểm cần xử lý được ghi nhận trong trạng thái hiện tại.")
    else:
        priority_view = priorities.rename(
            columns={
                "priority": "Mức ưu tiên",
                "item": "Nội dung",
                "source": "Phân hệ",
            }
        )
        st.dataframe(priority_view, width="stretch", hide_index=True)

    st.markdown("#### Phạm vi dữ liệu thị trường")
    freshness = build_data_freshness_table(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )

    if bond_data_available:
        bond_row = pd.DataFrame(
            [
                {
                    "Bộ dữ liệu": "TPCP / Đường cong lợi suất",
                    "Từ ngày": format_date(bond_monitor_data["date"].min()),
                    "Đến ngày": format_date(bond_monitor_data["date"].max()),
                    "Số quan sát": f"{len(bond_monitor_data):,}".replace(",", "."),
                }
            ]
        )
        freshness = pd.concat([freshness, bond_row], ignore_index=True)

    st.dataframe(freshness, width="stretch", hide_index=True)

def render_overview_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    alert_snapshot: pd.DataFrame,
    alert_summary: dict[str, object],
    funding_pressure_data: pd.DataFrame,
    funding_summary: dict[str, object],
    quality_report: pd.DataFrame,
) -> None:
    """Trang tổng quan giám sát hằng ngày."""
    st.subheader("Tổng quan giám sát")

    latest_fx = fx_data.iloc[-1]
    latest_interbank = interbank_data.iloc[-1]
    latest_deposit = deposit_data.iloc[-1]
    quality_status = classify_data_quality(quality_report)

    first_row = st.columns(4)
    first_row[0].metric(
        "USD/VND",
        format_number(latest_fx["close"], 0),
        delta=f"{format_number(latest_fx['daily_return_pct'], 2)}%",
    )
    first_row[1].metric(
        "Lãi suất O/N",
        f"{format_number(latest_interbank['rate_on'], 2)}%",
        delta=f"{format_number(latest_interbank['on_change_bps'], 0)} bps",
    )
    first_row[2].metric(
        "Chỉ số áp lực nguồn vốn",
        format_number(funding_summary["index"], 2),
    )
    first_row[3].metric(
        "Tín hiệu đang mở",
        int(alert_summary["open_count"]),
    )

    second_row = st.columns(4)
    second_row[0].metric(
        "Độ biến động USD/VND 20 ngày",
        f"{format_number(latest_fx['volatility_20d_pct'], 2)}%",
    )
    second_row[1].metric(
        "Chênh lệch lãi suất 3M - O/N",
        f"{format_number(latest_interbank['spread_3m_on'], 2)} điểm %",
    )
    second_row[2].metric(
        "Huy động 12 tháng",
        f"{format_number(latest_deposit['deposit_12m'], 2)}%",
    )
    second_row[3].metric(
        "Chất lượng dữ liệu",
        quality_status,
    )

    st.markdown("#### Tín hiệu cần theo dõi")
    overview_alerts = build_overview_alert_table(alert_snapshot)
    if overview_alerts.empty:
        st.success("Không có tín hiệu đang mở.")
    else:
        st.dataframe(overview_alerts, width="stretch", hide_index=True)

    count = select_period("overview_period", default_label="1 năm")
    recent_fx = fx_data.tail(count)
    recent_interbank = interbank_data.tail(count)
    recent_deposit = deposit_data.tail(count)
    funding_count = min(max(count, 250), 500)
    recent_funding = funding_pressure_data.tail(funding_count)

    st.markdown("#### Diễn biến thị trường")
    left, right = st.columns(2, gap="large")

    with left:
        show_chart(
            "Tỷ giá USD/VND",
            create_fx_line_chart(recent_fx),
            key="overview_fx_chart",
        )

    with right:
        show_chart(
            "Lãi suất liên ngân hàng",
            create_interbank_rate_chart(recent_interbank, include_two_week=False),
            key="overview_interbank_chart",
        )

    left, right = st.columns(2, gap="large")

    with left:
        show_chart(
            "Chỉ số áp lực nguồn vốn",
            create_funding_pressure_index_chart(recent_funding),
            key="overview_funding_pressure_chart",
        )

    with right:
        show_chart(
            "Lãi suất huy động",
            create_deposit_rate_chart(recent_deposit),
            key="overview_deposit_chart",
        )

    st.markdown("#### Phạm vi dữ liệu")
    st.dataframe(
        build_data_freshness_table(fx_data, interbank_data, deposit_data),
        width="stretch",
        hide_index=True,
    )

def render_risk_heatmap_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
) -> None:
    """Hiển thị bản đồ trạng thái rủi ro tổng hợp."""
    st.subheader("Bản đồ rủi ro")

    bond_monitor_data = load_bond_monitor_data_for_report()

    current_alerts = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )

    quality_report = build_dq_report(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )

    historical_stress_data = prepare_historical_stress_data(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )

    matrix = build_risk_heatmap(
        alert_snapshot=current_alerts,
        quality_report=quality_report,
        historical_stress_data=historical_stress_data,
    )
    detail = build_risk_heatmap_detail(
        alert_snapshot=current_alerts,
        quality_report=quality_report,
        historical_stress_data=historical_stress_data,
    )
    summary = summarize_risk_heatmap(matrix)

    columns = st.columns(5)
    columns[0].metric("Trạng thái tổng hợp", summary["overall_status"])
    columns[1].metric("Ô đang theo dõi", summary["watch_cells"])
    columns[2].metric("Ô cảnh báo", summary["alert_cells"])
    columns[3].metric("Nhóm có tín hiệu", summary["active_groups"])
    columns[4].metric("Ô đã đánh giá", summary["evaluated_cells"])

    show_chart(
        "Ma trận trạng thái rủi ro",
        create_risk_heatmap_chart(matrix),
        key="executive_risk_heatmap_chart",
    )

    st.caption(
        "Xanh: Bình thường · Vàng: Theo dõi · Đỏ: Cảnh báo · Xám: chưa có chỉ báo phù hợp."
    )

    st.markdown("#### Trạng thái theo nhóm")
    group_view = matrix[["Nhóm rủi ro", "Ngày dữ liệu", "Trạng thái chung"]].copy()
    group_view["Ngày dữ liệu"] = group_view["Ngày dữ liệu"].map(format_date)
    group_view["Trạng thái"] = group_view["Trạng thái chung"].map(
        lambda value: value if value == HEATMAP_STATUS_NOT_AVAILABLE else status_with_icon(value)
    )
    st.dataframe(
        group_view[["Nhóm rủi ro", "Ngày dữ liệu", "Trạng thái"]],
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Tín hiệu cần theo dõi")
    if detail.empty:
        st.success("Không có tín hiệu cần theo dõi.")
        return

    open_detail = detail[detail["Trạng thái"].isin([STATUS_WATCH, STATUS_ALERT])].copy()
    if open_detail.empty:
        st.success("Không có tín hiệu Theo dõi hoặc Cảnh báo trong dữ liệu hiện tại.")
        return

    open_detail["Ngày dữ liệu"] = open_detail["Ngày dữ liệu"].map(format_date)
    open_detail["Giá trị hiển thị"] = open_detail.apply(
        lambda row: format_value(row["Giá trị"], row["Đơn vị"]),
        axis=1,
    )
    open_detail["Ngưỡng theo dõi hiển thị"] = open_detail.apply(
        lambda row: format_value(row["Ngưỡng theo dõi"], row["Đơn vị tín hiệu"]),
        axis=1,
    )
    open_detail["Ngưỡng cảnh báo hiển thị"] = open_detail.apply(
        lambda row: format_value(row["Ngưỡng cảnh báo"], row["Đơn vị tín hiệu"]),
        axis=1,
    )
    open_detail["Trạng thái hiển thị"] = open_detail["Trạng thái"].map(status_with_icon)

    st.dataframe(
        open_detail[
            [
                "Ngày dữ liệu",
                "Nhóm rủi ro",
                "Khía cạnh",
                "Chỉ báo",
                "Giá trị hiển thị",
                "Ngưỡng theo dõi hiển thị",
                "Ngưỡng cảnh báo hiển thị",
                "Trạng thái hiển thị",
            ]
        ].rename(
            columns={
                "Giá trị hiển thị": "Giá trị",
                "Ngưỡng theo dõi hiển thị": "Ngưỡng theo dõi",
                "Ngưỡng cảnh báo hiển thị": "Ngưỡng cảnh báo",
                "Trạng thái hiển thị": "Trạng thái",
            }
        ),
        width="stretch",
        hide_index=True,
    )

def load_bond_monitor_data_for_report() -> pd.DataFrame:
    """Đọc dữ liệu đường cong lợi suất đang có để đưa vào báo cáo ngày."""
    session_data = st.session_state.get("fixed_income_monitor_data")
    if isinstance(session_data, pd.DataFrame) and not session_data.empty:
        return session_data.copy()

    for candidate in (BOND_FILE, BOND_CSV_FILE):
        if not candidate.exists():
            continue

        try:
            raw_data = read_table_source(candidate)
            standardized = standardize_yield_curve_input(raw_data)
            monitor_data = prepare_yield_curve_monitor(standardized)
            if not monitor_data.empty:
                return monitor_data
        except (ValueError, TypeError, OSError):
            continue

    return pd.DataFrame()

def render_daily_report_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
) -> None:
    """Báo cáo giám sát rủi ro thị trường hằng ngày và tệp Excel xuất báo cáo."""
    st.subheader("Báo cáo giám sát ngày")

    bond_monitor_data = load_bond_monitor_data_for_report()

    current_alerts = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )
    alert_history = build_central_alert_history(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
        max_events=500,
    )
    group_status = build_group_status_table(current_alerts)

    quality_report = build_dq_report(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    quality_exceptions = build_quality_exceptions(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
        max_rows=500,
    )
    reconciliation = build_reconciliation_table(
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )

    market_snapshot = build_market_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        alert_snapshot=current_alerts,
        bond_monitor_data=bond_monitor_data,
    )
    source_status = build_source_status(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )
    exception_report = build_exception_report(
        alert_snapshot=current_alerts,
        quality_exceptions=quality_exceptions,
    )
    report_summary = summarize_daily_report(
        alert_snapshot=current_alerts,
        quality_report=quality_report,
        quality_exceptions=quality_exceptions,
        source_status=source_status,
    )

    metrics = st.columns(5)
    metrics[0].metric("Ngày dữ liệu mới nhất", format_date(report_summary["latest_date"]))
    metrics[1].metric("Trạng thái", report_summary["overall_status"])
    metrics[2].metric("Tín hiệu đang mở", report_summary["open_alert_count"])
    metrics[3].metric("Cảnh báo", report_summary["alert_count"])
    metrics[4].metric("Ngoại lệ dữ liệu", report_summary["data_exception_count"])

    st.markdown("#### Trạng thái theo nhóm")
    if group_status.empty:
        st.info("Chưa có dữ liệu để tổng hợp trạng thái.")
    else:
        group_view = group_status.copy()
        group_view["Ngày dữ liệu"] = group_view["latest_date"].map(format_date)
        group_view["Trạng thái"] = group_view["status"].map(status_with_icon)
        group_view = group_view.rename(
            columns={
                "group": "Nhóm giám sát",
                "open_count": "Tín hiệu đang mở",
                "indicator_count": "Số chỉ báo",
            }
        )
        st.dataframe(
            group_view[
                [
                    "Nhóm giám sát",
                    "Ngày dữ liệu",
                    "Trạng thái",
                    "Tín hiệu đang mở",
                    "Số chỉ báo",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Chỉ báo thị trường")
    market_view = market_snapshot.copy()
    if not market_view.empty:
        market_view["Ngày dữ liệu"] = market_view["Ngày dữ liệu"].map(format_date)
        market_view["Giá trị"] = market_view.apply(
            lambda row: format_value(row["Giá trị"], row["Đơn vị"]),
            axis=1,
        )
        market_view["Trạng thái"] = market_view["Trạng thái"].map(status_with_icon)
        st.dataframe(market_view, width="stretch", hide_index=True)
    else:
        st.info("Chưa có chỉ báo thị trường để tổng hợp.")

    st.markdown("#### Ngoại lệ đang cần theo dõi")
    open_exceptions = exception_report.copy()
    if not open_exceptions.empty:
        open_exceptions["Ngày"] = open_exceptions["Ngày"].map(format_date)
        st.dataframe(open_exceptions.head(100), width="stretch", hide_index=True)
    else:
        st.success("Không có ngoại lệ đang mở trong dữ liệu hiện tại.")

    st.markdown("#### Phạm vi dữ liệu")
    source_view = source_status.copy()
    if not source_view.empty:
        source_view["Từ ngày"] = source_view["Từ ngày"].map(format_date)
        source_view["Đến ngày"] = source_view["Đến ngày"].map(format_date)
        st.dataframe(source_view, width="stretch", hide_index=True)

    excel_bytes = export_daily_report_excel(
        report_summary=report_summary,
        market_snapshot=market_snapshot,
        alert_snapshot=current_alerts,
        alert_history=alert_history,
        group_status=group_status,
        quality_report=quality_report,
        quality_exceptions=quality_exceptions,
        source_status=source_status,
        reconciliation=reconciliation,
        exception_report=exception_report,
        bond_monitor_data=bond_monitor_data,
    )

    st.download_button(
        "Tải báo cáo Excel",
        data=excel_bytes,
        file_name=build_report_filename(report_summary["latest_date"]),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key="download_daily_market_risk_report",
    )

def render_fixed_income_tab() -> None:
    """Theo dõi đường cong lợi suất TPCP từ dữ liệu file."""
    st.subheader("Trái phiếu Chính phủ / Đường cong lợi suất")

    template = blank_yield_curve_template()
    upload_col, download_col = st.columns([2, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Tải dữ liệu đường cong lợi suất (CSV/XLSX)",
            type=["csv", "xlsx", "xls"],
            key="fixed_income_yield_curve_upload",
        )

    with download_col:
        st.download_button(
            "Tải tệp mẫu",
            data=template.to_csv(index=False).encode("utf-8-sig"),
            file_name="vn_gov_bond_yield_curve_template.csv",
            mime="text/csv",
            width="stretch",
            key="download_bond_yield_curve_template",
        )

    source = uploaded_file
    source_label = None

    if source is None:
        for candidate in (BOND_FILE, BOND_CSV_FILE):
            if candidate.exists():
                source = candidate
                source_label = candidate.name
                break
    else:
        source_label = uploaded_file.name

    if source is None:
        st.info(
            "Chưa có dữ liệu đường cong lợi suất. Cấu trúc tối thiểu gồm "
            "date (ngày), tenor_years (kỳ hạn, năm) và yield_pct (lợi suất, %); "
            "cũng hỗ trợ dạng bảng rộng (wide format) với các cột 2Y, 5Y, 10Y..."
        )
        return

    try:
        raw_data = read_table_source(source)
        standardized = standardize_yield_curve_input(raw_data)
        monitor_data = prepare_yield_curve_monitor(standardized)
        st.session_state["fixed_income_monitor_data"] = monitor_data.copy()
    except (ValueError, TypeError) as error:
        st.error(str(error))
        return

    if monitor_data.empty:
        st.warning("File không có quan sát hợp lệ sau khi chuẩn hóa.")
        return

    summary = summarize_yield_curve(monitor_data)
    comparison = build_curve_comparison(monitor_data)
    snapshot = build_latest_curve_snapshot(monitor_data)

    st.caption(f"Nguồn dữ liệu đang dùng: {source_label}")

    columns = st.columns(5)
    columns[0].metric("Ngày dữ liệu", format_date(summary["latest_date"]))
    columns[1].metric(
        "Lợi suất 10 năm",
        "—" if pd.isna(summary["yield_10y"]) else f"{format_number(summary['yield_10y'], 3)}%",
    )
    columns[2].metric(
        "10Y - 2Y",
        "—" if pd.isna(summary["slope_10y_2y_bps"]) else f"{format_number(summary['slope_10y_2y_bps'], 1)} bps",
    )
    max_move_text = "—"
    if pd.notna(summary["max_abs_move_bps"]):
        max_move_text = f"{format_number(summary['max_abs_move_bps'], 1)} bps"
    columns[3].metric("Biến động lợi suất lớn nhất", max_move_text)
    columns[4].metric("Trạng thái", summary["status"])

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Đường cong lợi suất",
            create_bond_yield_curve_chart(comparison),
            key="bond_yield_curve_chart",
        )
    with right:
        show_chart(
            "Biến động lợi suất theo kỳ hạn",
            create_bond_curve_change_chart(snapshot),
            key="bond_curve_change_chart",
        )

    tenors = available_tenors(monitor_data)
    selected_tenor = st.selectbox(
        "Kỳ hạn theo dõi",
        options=tenors,
        format_func=lambda value: f"{value:g} năm",
        key="bond_selected_tenor",
    )

    tenor_history = build_tenor_history(monitor_data, selected_tenor)
    history_options = {
        "1 năm": 250,
        "2 năm": 500,
        "4 năm": 1000,
        "Toàn bộ": None,
    }
    history_label = st.radio(
        "Khoảng lịch sử",
        options=list(history_options.keys()),
        index=1,
        horizontal=True,
        key="bond_history_period",
    )
    history_count = history_options[history_label]
    if history_count is not None:
        tenor_history = tenor_history.tail(history_count)

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            f"Lợi suất kỳ hạn {selected_tenor:g} năm",
            create_bond_tenor_history_chart(tenor_history),
            key="bond_tenor_history_chart",
        )
    with right:
        show_chart(
            "Mức thay đổi lợi suất và ngưỡng P95/P99",
            create_bond_move_threshold_chart(tenor_history),
            key="bond_move_threshold_chart",
        )

    latest_table = snapshot.copy()
    latest_table["Kỳ hạn"] = latest_table["tenor_years"].map(lambda value: f"{value:g} năm")
    latest_table["Lợi suất"] = latest_table["yield_pct"].map(
        lambda value: f"{format_number(value, 3)}%"
    )
    latest_table["Δ ngày"] = latest_table["yield_change_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{format_number(value, 1)} bps"
    )
    latest_table["P95"] = latest_table["watch_threshold_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{format_number(value, 1)} bps"
    )
    latest_table["P99"] = latest_table["alert_threshold_bps"].map(
        lambda value: "—" if pd.isna(value) else f"{format_number(value, 1)} bps"
    )
    latest_table["Z-score"] = latest_table["change_zscore"].map(
        lambda value: "—" if pd.isna(value) else format_number(value, 2)
    )
    latest_table["Trạng thái"] = latest_table["status"].map(status_with_icon)

    st.markdown("#### Chi tiết đường cong mới nhất")
    st.dataframe(
        latest_table[["Kỳ hạn", "Lợi suất", "Δ ngày", "P95", "P99", "Z-score", "Trạng thái"]],
        width="stretch",
        hide_index=True,
    )

    with st.expander("Phương pháp giám sát"):
        st.markdown(
            """
**Thay đổi lợi suất (Δ yield)** được tính theo từng kỳ hạn, đơn vị điểm cơ bản (bps).
Ngưỡng **P95/P99** là các bách phân vị động của trị tuyệt đối biến động lợi suất lịch sử
trên cùng kỳ hạn và chỉ sử dụng các quan sát trước ngày đang đánh giá.

**10Y - 2Y** phản ánh độ dốc giữa hai kỳ hạn khi dữ liệu có đủ 2 năm và 10 năm.
Các chỉ tiêu trong tab này mô tả biến động thị trường trái phiếu; PV01/DV01 và P&L
danh mục chỉ được tính khi có thêm dữ liệu vị thế và độ nhạy của danh mục.
            """
        )

def render_alert_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
) -> None:
    """Trung tâm cảnh báo rủi ro thị trường."""
    st.subheader("Trung tâm cảnh báo rủi ro")
    st.caption(
        "Tổng hợp các tín hiệu bất thường từ ngoại hối, trái phiếu Chính phủ, "
        "thị trường liên ngân hàng, áp lực nguồn vốn và lãi suất huy động."
    )

    bond_monitor_data = st.session_state.get("fixed_income_monitor_data")

    snapshot = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )
    history = build_central_alert_history(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
        max_events=500,
    )
    summary = summarize_alert_console(snapshot)
    group_table = build_group_status_table(snapshot)

    metrics = st.columns(5)
    metrics[0].metric("Trạng thái chung", summary["overall_status"])
    metrics[1].metric("Tín hiệu đang mở", summary["open_count"])
    metrics[2].metric("Theo dõi", summary["watch_count"])
    metrics[3].metric("Cảnh báo", summary["alert_count"])
    metrics[4].metric("Nhóm có tín hiệu", summary["active_group_count"])

    st.markdown("#### Trạng thái theo nhóm")
    if group_table.empty:
        st.info("Chưa có dữ liệu để tổng hợp trạng thái.")
    else:
        group_view = group_table.copy()
        group_view["Ngày dữ liệu"] = group_view["latest_date"].map(format_date)
        group_view["Trạng thái"] = group_view["status"].map(status_with_icon)
        group_view = group_view.rename(
            columns={
                "group": "Nhóm giám sát",
                "open_count": "Tín hiệu đang mở",
                "indicator_count": "Số chỉ báo",
            }
        )
        st.dataframe(
            group_view[
                [
                    "Nhóm giám sát",
                    "Ngày dữ liệu",
                    "Trạng thái",
                    "Tín hiệu đang mở",
                    "Số chỉ báo",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Tín hiệu hiện tại")
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        status_filter = st.multiselect(
            "Mức độ",
            options=[STATUS_ALERT, STATUS_WATCH, STATUS_NORMAL],
            default=[STATUS_ALERT, STATUS_WATCH],
            key="central_alert_status_filter",
        )

    group_options = snapshot["group"].dropna().drop_duplicates().tolist()
    with filter_col2:
        group_filter = st.multiselect(
            "Nhóm giám sát",
            options=group_options,
            default=group_options,
            key="central_alert_group_filter",
        )

    current_view = snapshot[
        snapshot["status"].isin(status_filter) & snapshot["group"].isin(group_filter)
    ].copy()

    if current_view.empty:
        st.success("Không có tín hiệu phù hợp với bộ lọc hiện tại.")
    else:
        current_view["Ngày dữ liệu"] = current_view["date"].map(format_date)
        current_view["Giá trị"] = current_view.apply(
            lambda row: format_value(row["value"], row["value_unit"]),
            axis=1,
        )
        current_view["Tín hiệu"] = current_view.apply(
            lambda row: format_value(row["signal"], row["signal_unit"]),
            axis=1,
        )
        current_view["Ngưỡng theo dõi"] = current_view.apply(
            lambda row: format_value(row["watch_threshold"], row["signal_unit"]),
            axis=1,
        )
        current_view["Ngưỡng cảnh báo"] = current_view.apply(
            lambda row: format_value(row["alert_threshold"], row["signal_unit"]),
            axis=1,
        )
        current_view["Mức độ"] = current_view["status"].map(status_with_icon)
        current_view = current_view.rename(
            columns={"group": "Nhóm giám sát", "indicator": "Chỉ báo"}
        )
        st.dataframe(
            current_view[
                [
                    "Ngày dữ liệu",
                    "Nhóm giám sát",
                    "Chỉ báo",
                    "Giá trị",
                    "Tín hiệu",
                    "Ngưỡng theo dõi",
                    "Ngưỡng cảnh báo",
                    "Mức độ",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Lịch sử tín hiệu vượt ngưỡng")
    history_col1, history_col2 = st.columns(2)
    with history_col1:
        history_period = st.selectbox(
            "Khoảng lịch sử",
            options=["30 ngày", "90 ngày", "180 ngày", "1 năm", "Toàn bộ"],
            index=2,
            key="central_alert_history_period",
        )
    with history_col2:
        history_groups = st.multiselect(
            "Nhóm trong lịch sử",
            options=group_options,
            default=group_options,
            key="central_alert_history_groups",
        )

    history_days = {
        "30 ngày": 30,
        "90 ngày": 90,
        "180 ngày": 180,
        "1 năm": 365,
        "Toàn bộ": None,
    }[history_period]

    history_view = history[history["group"].isin(history_groups)].copy()
    if history_days is not None and not history_view.empty:
        cutoff = history_view["date"].max() - pd.Timedelta(days=history_days)
        history_view = history_view[history_view["date"] >= cutoff]

    daily_counts = build_daily_alert_counts(history_view)
    if not daily_counts.empty:
        figure = go.Figure()
        for status, label in [(STATUS_WATCH, "Theo dõi"), (STATUS_ALERT, "Cảnh báo")]:
            subset = daily_counts[daily_counts["status"] == status]
            if subset.empty:
                continue
            figure.add_trace(
                go.Bar(
                    x=subset["date"],
                    y=subset["count"],
                    name=label,
                    hovertemplate=(
                        "<b>%{x|%d/%m/%Y}</b><br>"
                        f"{label}: %{{y:.0f}} tín hiệu"
                        "<extra></extra>"
                    ),
                )
            )
        figure.update_layout(barmode="stack")
        show_chart(
            "Số tín hiệu vượt ngưỡng theo ngày",
            apply_chart_layout(
                figure,
                y_title="Số tín hiệu",
                height=360,
                show_legend=True,
            ),
            key="central_alert_timeline_chart",
        )

    if history_view.empty:
        st.info("Chưa ghi nhận tín hiệu vượt ngưỡng trong khoảng đang chọn.")
    else:
        history_table = history_view.copy()
        history_table["Ngày"] = history_table["date"].map(format_date)
        history_table["Giá trị"] = history_table.apply(
            lambda row: format_value(row["value"], row["value_unit"]),
            axis=1,
        )
        history_table["Tín hiệu"] = history_table.apply(
            lambda row: format_value(row["signal"], row["signal_unit"]),
            axis=1,
        )
        history_table["P95 / Theo dõi"] = history_table.apply(
            lambda row: format_value(row["watch_threshold"], row["signal_unit"]),
            axis=1,
        )
        history_table["P99 / Cảnh báo"] = history_table.apply(
            lambda row: format_value(row["alert_threshold"], row["signal_unit"]),
            axis=1,
        )
        history_table["Mức độ"] = history_table["status"].map(status_with_icon)
        history_table = history_table.rename(
            columns={"group": "Nhóm giám sát", "indicator": "Chỉ báo"}
        )
        st.dataframe(
            history_table[
                [
                    "Ngày",
                    "Nhóm giám sát",
                    "Chỉ báo",
                    "Giá trị",
                    "Tín hiệu",
                    "P95 / Theo dõi",
                    "P99 / Cảnh báo",
                    "Mức độ",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

def render_exception_workflow_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
) -> None:
    """Theo dõi vòng đời xử lý các tín hiệu đang mở."""
    st.subheader("Theo dõi xử lý cảnh báo")
    st.caption(
        "Theo dõi từ thời điểm phát hiện đến xác minh, chuyển cấp, xử lý và đóng hồ sơ."
    )

    bond_monitor_data = st.session_state.get("fixed_income_monitor_data")
    snapshot = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )

    config_cols = st.columns(2)
    with config_cols[0]:
        watch_sla_hours = st.number_input(
            "SLA Theo dõi (giờ)",
            min_value=0.0,
            max_value=720.0,
            value=24.0,
            step=1.0,
            key="workflow_watch_sla_hours",
        )
    with config_cols[1]:
        alert_sla_hours = st.number_input(
            "SLA Cảnh báo (giờ)",
            min_value=0.0,
            max_value=720.0,
            value=8.0,
            step=1.0,
            key="workflow_alert_sla_hours",
        )

    cases = load_case_store(WORKFLOW_CASE_FILE)
    events = load_event_store(WORKFLOW_EVENT_FILE)
    cases, new_case_count = sync_current_alerts(snapshot=snapshot, cases=cases)
    save_case_store(cases, WORKFLOW_CASE_FILE)

    enriched = enrich_case_metrics(
        cases=cases,
        watch_sla_hours=watch_sla_hours,
        alert_sla_hours=alert_sla_hours,
    )
    summary = summarize_cases(enriched)

    metric_cols = st.columns(5)
    metric_cols[0].metric("Hồ sơ đang mở", summary["open_count"])
    metric_cols[1].metric("Mới phát sinh", summary["new_count"])
    metric_cols[2].metric("Quá hạn SLA", summary["overdue_count"])
    metric_cols[3].metric("Đã chuyển cấp", summary["escalated_count"])
    metric_cols[4].metric("Đã đóng", summary["closed_count"])

    if new_case_count > 0:
        st.success(f"Đã ghi nhận {new_case_count} hồ sơ cảnh báo mới.")

    st.markdown("#### Sổ theo dõi xử lý")
    filter_cols = st.columns(4)

    with filter_cols[0]:
        status_filter = st.multiselect(
            "Trạng thái xử lý",
            options=WORKFLOW_STATUSES,
            default=[status for status in WORKFLOW_STATUSES if status != WORKFLOW_STATUS_CLOSED],
            key="workflow_status_filter",
        )

    severity_options = ["Cảnh báo", "Theo dõi"]
    with filter_cols[1]:
        severity_filter = st.multiselect(
            "Mức độ",
            options=severity_options,
            default=severity_options,
            key="workflow_severity_filter",
        )

    group_options = sorted(enriched["group"].dropna().astype(str).unique().tolist())
    with filter_cols[2]:
        group_filter = st.multiselect(
            "Nhóm giám sát",
            options=group_options,
            default=group_options,
            key="workflow_group_filter",
        )

    with filter_cols[3]:
        active_only = st.checkbox(
            "Chỉ tín hiệu còn hoạt động",
            value=False,
            key="workflow_active_only",
        )

    view = enriched.copy()
    if status_filter:
        view = view[view["workflow_status"].isin(status_filter)]
    else:
        view = view.iloc[0:0]

    if severity_filter:
        view = view[view["severity"].isin(severity_filter)]
    else:
        view = view.iloc[0:0]

    if group_filter:
        view = view[view["group"].isin(group_filter)]
    elif group_options:
        view = view.iloc[0:0]

    if active_only:
        view = view[view["signal_active"]]

    view = view.sort_values(
        ["severity_rank", "sla_status", "first_seen_at"],
        ascending=[False, False, True],
    )

    if view.empty:
        st.info("Không có hồ sơ phù hợp với bộ lọc hiện tại.")
    else:
        editor_data = view[
            [
                "case_id",
                "source_date",
                "group",
                "indicator",
                "severity",
                "signal_active",
                "workflow_status",
                "owner",
                "age_hours",
                "sla_status",
                "action_note",
            ]
        ].copy()

        editor_data["source_date"] = editor_data["source_date"].dt.date
        editor_data["age_hours"] = editor_data["age_hours"].round(1)

        edited = st.data_editor(
            editor_data,
            width="stretch",
            hide_index=True,
            disabled=[
                "case_id",
                "source_date",
                "group",
                "indicator",
                "severity",
                "signal_active",
                "age_hours",
                "sla_status",
            ],
            column_config={
                "case_id": st.column_config.TextColumn("Mã hồ sơ"),
                "source_date": st.column_config.DateColumn("Ngày dữ liệu", format="DD/MM/YYYY"),
                "group": st.column_config.TextColumn("Nhóm giám sát"),
                "indicator": st.column_config.TextColumn("Chỉ báo"),
                "severity": st.column_config.TextColumn("Mức độ"),
                "signal_active": st.column_config.CheckboxColumn("Tín hiệu đang hoạt động"),
                "workflow_status": st.column_config.SelectboxColumn(
                    "Trạng thái xử lý",
                    options=WORKFLOW_STATUSES,
                    required=True,
                ),
                "owner": st.column_config.TextColumn("Đầu mối xử lý"),
                "age_hours": st.column_config.NumberColumn("Tuổi hồ sơ (giờ)", format="%.1f"),
                "sla_status": st.column_config.TextColumn("SLA"),
                "action_note": st.column_config.TextColumn("Ghi chú xử lý", width="large"),
            },
            key="exception_workflow_editor",
        )

        action_cols = st.columns([1, 1, 3])
        with action_cols[0]:
            if st.button("Lưu cập nhật", type="primary", key="workflow_save_button"):
                updated_cases, updated_events, update_count = apply_case_updates(
                    cases=cases,
                    updates=edited,
                    events=events,
                )
                save_case_store(updated_cases, WORKFLOW_CASE_FILE)
                save_event_store(updated_events, WORKFLOW_EVENT_FILE)
                if update_count > 0:
                    st.success("Đã lưu cập nhật hồ sơ.")
                else:
                    st.info("Không có thay đổi cần lưu.")
                st.rerun()

        with action_cols[1]:
            export_bytes = export_workflow_excel(cases=cases, events=events)
            st.download_button(
                "Tải sổ xử lý",
                data=export_bytes,
                file_name="market_risk_alert_workflow.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="workflow_download_button",
            )

    st.markdown("#### Nhật ký thay đổi")
    if events.empty:
        st.info("Chưa có thay đổi trạng thái được ghi nhận.")
    else:
        event_view = events.sort_values("event_time", ascending=False).head(200).copy()
        event_view["Thời điểm"] = event_view["event_time"].map(
            lambda value: pd.Timestamp(value).strftime("%d/%m/%Y %H:%M")
            if pd.notna(value)
            else "—"
        )
        event_view["field"] = event_view["field"].replace(
            {
                "workflow_status": "Trạng thái xử lý",
                "owner": "Đầu mối xử lý",
                "action_note": "Ghi chú xử lý",
            }
        )
        event_view = event_view.rename(
            columns={
                "case_id": "Mã hồ sơ",
                "field": "Trường thay đổi",
                "old_value": "Giá trị trước",
                "new_value": "Giá trị sau",
            }
        )
        st.dataframe(
            event_view[
                [
                    "Thời điểm",
                    "Mã hồ sơ",
                    "Trường thay đổi",
                    "Giá trị trước",
                    "Giá trị sau",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

def render_stress_test_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
) -> None:
    """Trang kiểm tra sức chịu đựng và thư viện kịch bản lịch sử."""
    st.subheader("Kiểm tra sức chịu đựng")
    st.caption(
        "Mô phỏng cú sốc thị trường theo kịch bản lịch sử, kịch bản định sẵn "
        "hoặc tham số tùy chỉnh."
    )

    historical_data = prepare_historical_stress_data(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )
    historical_summary = summarize_historical_stress(historical_data)

    scenario_source = st.radio(
        "Nguồn kịch bản",
        options=["Kịch bản lịch sử", "Kịch bản định sẵn", "Tùy chỉnh"],
        horizontal=True,
        key="stress_scenario_source",
    )

    selected_historical_row = None
    selected_historical_date = None

    if scenario_source == "Kịch bản lịch sử":
        category = st.selectbox(
            "Nhóm kịch bản lịch sử",
            options=HISTORICAL_SCENARIO_CATEGORIES,
            key="historical_stress_category",
        )

        library = build_historical_scenario_library(
            historical_data,
            category=category,
            top_n=25,
        )

        if library.empty:
            st.warning("Chưa có đủ dữ liệu để xây dựng thư viện kịch bản lịch sử.")
            return

        scenario_labels = {
            index: (
                f"{format_date(row['date'])} · {row['strongest_driver']} · "
                f"điểm {format_number(row['selection_score'], 1)}"
            )
            for index, row in library.iterrows()
        }

        selected_index = st.selectbox(
            "Phiên lịch sử",
            options=list(scenario_labels.keys()),
            format_func=lambda index: scenario_labels[index],
            key="historical_stress_date",
        )

        selected_historical_row = library.loc[selected_index]
        selected_historical_date = pd.Timestamp(selected_historical_row["date"])
        defaults = scenario_from_row(selected_historical_row)

        summary_columns = st.columns(4)
        summary_columns[0].metric(
            "Ngày kịch bản",
            format_date(selected_historical_date),
        )
        summary_columns[1].metric(
            "Điểm stress",
            format_number(selected_historical_row["stress_score"], 1),
        )
        summary_columns[2].metric(
            "Yếu tố nổi bật",
            selected_historical_row["strongest_driver"],
        )
        summary_columns[3].metric(
            "Số phiên lịch sử",
            historical_summary["observations"],
        )

        st.dataframe(
            prepare_selected_historical_shock(selected_historical_row),
            width="stretch",
            hide_index=True,
        )

    elif scenario_source == "Kịch bản định sẵn":
        scenario_name = st.selectbox(
            "Kịch bản",
            options=list(PRESET_SCENARIOS.keys()),
            key="preset_stress_scenario",
        )
        defaults = get_preset_scenario(scenario_name)

    else:
        defaults = {
            "fx_shock_pct": 0.0,
            "on_shock_bps": 0.0,
            "rate_1w_shock_bps": 0.0,
            "rate_1m_shock_bps": 0.0,
            "rate_3m_shock_bps": 0.0,
            "deposit_12m_shock_bps": 0.0,
        }

    st.markdown("#### Tham số kịch bản")

    first_row = st.columns(3)

    with first_row[0]:
        fx_shock_pct = st.number_input(
            "USD/VND (%)",
            min_value=-10.0,
            max_value=10.0,
            value=float(defaults["fx_shock_pct"]),
            step=0.10,
            key=f"stress_fx_{scenario_source}",
        )

    with first_row[1]:
        on_shock_bps = st.number_input(
            "Qua đêm (bps)",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(defaults["on_shock_bps"]),
            step=25.0,
            key=f"stress_on_{scenario_source}",
        )

    with first_row[2]:
        rate_1w_shock_bps = st.number_input(
            "1 tuần (bps)",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(defaults["rate_1w_shock_bps"]),
            step=25.0,
            key=f"stress_1w_{scenario_source}",
        )

    second_row = st.columns(3)

    with second_row[0]:
        rate_1m_shock_bps = st.number_input(
            "1 tháng (bps)",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(defaults["rate_1m_shock_bps"]),
            step=25.0,
            key=f"stress_1m_{scenario_source}",
        )

    with second_row[1]:
        rate_3m_shock_bps = st.number_input(
            "3 tháng (bps)",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(defaults["rate_3m_shock_bps"]),
            step=25.0,
            key=f"stress_3m_{scenario_source}",
        )

    with second_row[2]:
        deposit_12m_shock_bps = st.number_input(
            "Huy động 12 tháng (bps)",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(defaults["deposit_12m_shock_bps"]),
            step=25.0,
            key=f"stress_dep12_{scenario_source}",
        )

    results = run_stress_test(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        fx_shock_pct=fx_shock_pct,
        on_shock_bps=on_shock_bps,
        rate_1w_shock_bps=rate_1w_shock_bps,
        rate_1m_shock_bps=rate_1m_shock_bps,
        rate_3m_shock_bps=rate_3m_shock_bps,
        deposit_12m_shock_bps=deposit_12m_shock_bps,
    )

    summary = summarize_stress_results(results)

    st.markdown("#### Kết quả kịch bản")
    columns = st.columns(4)
    columns[0].metric("Trạng thái chung", summary["overall_status"])
    columns[1].metric("Bình thường", summary["normal_count"])
    columns[2].metric("Theo dõi", summary["watch_count"])
    columns[3].metric("Cảnh báo", summary["alert_count"])

    st.dataframe(
        prepare_stress_table(results),
        width="stretch",
        hide_index=True,
    )

    curve = build_interbank_curve(results)
    if not curve.empty:
        show_chart(
            "Đường cong lãi suất trước và sau cú sốc",
            create_stress_curve_chart(curve),
            key="stress_curve_chart",
        )

    if scenario_source == "Kịch bản lịch sử":
        st.markdown("#### Thư viện kịch bản lịch sử")
        st.dataframe(
            prepare_historical_scenario_table(library),
            width="stretch",
            hide_index=True,
        )

        timeline = build_historical_stress_timeline(historical_data)
        if not timeline.empty:
            show_chart(
                "Điểm stress thị trường theo lịch sử",
                create_historical_stress_score_chart(
                    timeline,
                    selected_date=selected_historical_date,
                ),
                key="historical_stress_score_chart",
            )

        method_columns = st.columns(4)
        method_columns[0].metric(
            "P95 điểm stress",
            format_number(historical_summary["p95_score"], 1),
        )
        method_columns[1].metric(
            "P99 điểm stress",
            format_number(historical_summary["p99_score"], 1),
        )
        method_columns[2].metric(
            "Điểm cao nhất",
            format_number(historical_summary["max_score"], 1),
        )
        method_columns[3].metric(
            "Ngày cực trị",
            format_date(historical_summary["max_date"]),
        )

        st.caption(
            "Điểm stress tổng hợp được tính từ bách phân vị của biến động "
            "USD/VND, lãi suất qua đêm và đường cong lãi suất. "
            "Biến động lãi suất huy động được hiển thị bổ sung trong kịch bản."
        )

def render_var_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
) -> None:
    """Trang Giá trị chịu rủi ro (VaR) và Expected Shortfall (ES)."""
    st.subheader("Giá trị chịu rủi ro (VaR) & Expected Shortfall (ES)")
    st.caption(
        "Ước lượng Giá trị chịu rủi ro (VaR) và Expected Shortfall (ES) từ chuỗi biến động thị trường và quy mô vị thế hoặc độ nhạy giả định."
    )

    risk_type = st.radio(
        "Loại yếu tố rủi ro",
        options=[
            "Ngoại hối USD/VND",
            "Lãi suất liên ngân hàng",
        ],
        horizontal=True,
        key="var_risk_type",
    )

    left, middle, right = st.columns(3)

    if risk_type == "Ngoại hối USD/VND":
        with left:
            position = st.selectbox(
                "Trạng thái giả định",
                options=[
                    POSITION_LONG_USD,
                    POSITION_SHORT_USD,
                ],
                key="var_fx_position",
            )

        with middle:
            exposure = st.number_input(
                "Quy mô vị thế giả định (tỷ đồng)",
                min_value=1.0,
                value=1000.0,
                step=100.0,
                key="var_fx_exposure",
            )

        loss_data = build_fx_loss_series(
            fx_data=fx_data,
            exposure_billion_vnd=exposure,
            position=position,
        )

        unit = "tỷ đồng"
        factor_description = (
            f"{position}, quy mô vị thế giả định "
            f"{format_number(exposure, 0)} tỷ đồng."
        )

    else:
        with left:
            factor_name = st.selectbox(
                "Kỳ hạn",
                options=list(RATE_FACTORS.keys()),
                key="var_rate_factor",
            )

        with middle:
            sensitivity = st.number_input(
                "Độ nhạy P&L khi lãi suất tăng 1 bp (triệu đồng/bp)",
                min_value=-10000.0,
                max_value=10000.0,
                value=10.0,
                step=1.0,
                key="var_rate_sensitivity",
            )

        loss_data = build_rate_loss_series(
            interbank_data=interbank_data,
            factor_name=factor_name,
            sensitivity_million_vnd_per_bp=sensitivity,
        )

        unit = "triệu đồng"
        factor_description = (
            f"{factor_name}, độ nhạy giả định "
            f"{format_number(sensitivity, 2)} triệu đồng/bp."
        )

    with right:
        lookback_label = st.selectbox(
            "Mẫu ước lượng",
            options=[
                "250 quan sát",
                "500 quan sát",
                "Toàn bộ dữ liệu",
            ],
            index=0,
            key="var_lookback",
        )

    lookback_map = {
        "250 quan sát": 250,
        "500 quan sát": 500,
        "Toàn bộ dữ liệu": None,
    }

    analysis_data = select_lookback(
        loss_data,
        lookback_map[lookback_label],
    )

    st.caption(f"Thiết lập hiện tại: {factor_description}")

    confidence = st.select_slider(
        "Mức tin cậy dùng cho chỉ tiêu chính",
        options=[0.95, 0.975, 0.99],
        value=0.99,
        format_func=lambda value: f"{value * 100:g}%",
        key="var_confidence",
    )

    var_table = calculate_var_table(
        analysis_data["loss"],
        confidence_levels=(0.95, 0.975, 0.99),
    )

    selected_rows = var_table[
        np.isclose(
            var_table["confidence_level"],
            confidence,
        )
    ]

    historical_row = selected_rows[
        selected_rows["method"] == METHOD_HISTORICAL
    ].iloc[0]

    parametric_row = selected_rows[
        selected_rows["method"] == METHOD_PARAMETRIC
    ].iloc[0]

    st.markdown("#### Chỉ tiêu chính")
    columns = st.columns(4)

    columns[0].metric(
        f"VaR mô phỏng lịch sử {confidence * 100:g}%",
        format_value(historical_row["var"], unit),
    )

    columns[1].metric(
        f"ES mô phỏng lịch sử {confidence * 100:g}%",
        format_value(historical_row["es"], unit),
    )

    columns[2].metric(
        f"VaR tham số {confidence * 100:g}%",
        format_value(parametric_row["var"], unit),
    )

    columns[3].metric(
        f"ES tham số {confidence * 100:g}%",
        format_value(parametric_row["es"], unit),
    )

    st.markdown("#### Bảng VaR và Expected Shortfall (ES)")

    st.dataframe(
        prepare_var_table(var_table, unit),
        width="stretch",
        hide_index=True,
    )

    show_chart(
        "Phân phối lỗ/lãi giả định",
        create_loss_distribution_chart(
            loss_data=analysis_data,
            unit=unit,
            historical_var=historical_row["var"],
            historical_es=historical_row["es"],
            parametric_var=parametric_row["var"],
        ),
        key="var_distribution_chart",
    )

    st.markdown("#### VaR mô phỏng lịch sử theo cửa sổ trượt")

    rolling_window = st.selectbox(
        "Cửa sổ ước lượng VaR",
        options=[125, 250, 500],
        index=1,
        format_func=lambda value: f"{value} quan sát",
        key="var_rolling_window",
    )

    rolling_data = rolling_historical_var(
        loss_data=loss_data,
        confidence_level=confidence,
        window=rolling_window,
    )

    rolling_summary = summarize_rolling_var(
        rolling_data
    )

    columns = st.columns(4)

    columns[0].metric(
        "VaR theo cửa sổ trượt mới nhất",
        format_value(
            rolling_summary["latest_var"],
            unit,
        ),
    )

    columns[1].metric(
        "Lỗ/lãi mới nhất",
        format_value(
            rolling_summary["latest_loss"],
            unit,
        ),
    )

    columns[2].metric(
        "Số lần vượt VaR",
        rolling_summary["exception_count"],
    )

    exception_rate = rolling_summary["exception_rate"]

    columns[3].metric(
        "Tỷ lệ vượt VaR",
        (
            "—"
            if pd.isna(exception_rate)
            else f"{exception_rate * 100:.2f}%"
        ),
    )

    show_chart(
        "Lỗ/lãi thực tế và VaR theo cửa sổ trượt",
        create_rolling_var_chart(
            rolling_data,
            unit,
        ),
        key="var_rolling_chart",
    )

    st.markdown("#### Phân phối rủi ro và đuôi phân phối")

    tail_summary = summarize_tail_risk(
        analysis_data["loss"],
        confidence=confidence,
    )
    confidence_ladder = build_confidence_ladder(
        analysis_data["loss"],
        confidence_levels=(0.95, 0.975, 0.99),
    )
    tail_history = loss_data.tail(max(1000, rolling_window * 2)).copy()
    rolling_tail = build_rolling_tail_metrics(
        loss_data=tail_history,
        confidence=confidence,
        window=rolling_window,
    )
    rolling_tail_summary = summarize_rolling_tail_metrics(rolling_tail)

    tail_columns = st.columns(4)
    tail_columns[0].metric(
        "ES / VaR",
        (
            "—"
            if pd.isna(tail_summary["tail_loss_ratio"])
            else f"{tail_summary['tail_loss_ratio']:.2f}x"
        ),
    )
    tail_columns[1].metric(
        "VaR tham số / VaR lịch sử",
        (
            "—"
            if pd.isna(tail_summary["model_var_ratio"])
            else f"{tail_summary['model_var_ratio']:.2f}x"
        ),
    )
    tail_columns[2].metric(
        "Mức lỗ lớn nhất trong mẫu",
        format_value(tail_summary["maximum_loss"], unit),
    )
    tail_columns[3].metric(
        "Chế độ biến động hiện tại",
        rolling_tail_summary["volatility_regime"],
    )

    distribution_columns = st.columns(4)
    distribution_columns[0].metric(
        "Độ lệch (Skewness)",
        format_number(tail_summary["skewness"], 2),
    )
    distribution_columns[1].metric(
        "Độ nhọn vượt chuẩn",
        format_number(tail_summary["excess_kurtosis"], 2),
    )
    distribution_columns[2].metric(
        "Độ lệch chuẩn phía lỗ",
        format_value(tail_summary["downside_deviation"], unit),
    )
    distribution_columns[3].metric(
        "Số quan sát trong đuôi",
        tail_summary["tail_observations"],
    )

    show_chart(
        "VaR và ES theo mức tin cậy",
        create_confidence_ladder_chart(confidence_ladder, unit),
        key="var_confidence_ladder_chart",
    )

    left_tail, right_tail = st.columns(2, gap="large")
    with left_tail:
        show_chart(
            "VaR và ES theo cửa sổ trượt",
            create_rolling_tail_chart(rolling_tail, unit),
            key="var_tail_rolling_chart",
        )

    with right_tail:
        show_chart(
            "Độ nặng của đuôi và chênh lệch mô hình",
            create_tail_ratio_chart(rolling_tail),
            key="var_tail_ratio_chart",
        )

    show_chart(
        "Chế độ biến động của chuỗi lỗ",
        create_tail_volatility_chart(rolling_tail, unit),
        key="var_tail_volatility_chart",
    )

    st.markdown("#### Các lần lỗ vượt VaR nghiêm trọng nhất")
    tail_exceptions = build_tail_exception_table(
        rolling_tail,
        max_rows=20,
    )
    tail_exception_table = prepare_tail_exception_table(
        tail_exceptions,
        unit,
    )

    if tail_exception_table.empty:
        st.success("Không ghi nhận lần lỗ vượt VaR trong chuỗi đủ điều kiện.")
    else:
        st.dataframe(
            tail_exception_table,
            width="stretch",
            hide_index=True,
        )

    with st.expander("Phương pháp và giới hạn"):
        st.markdown(
            """
**Mô phỏng lịch sử (Historical Simulation)** lấy phân vị trực tiếp từ chuỗi lỗ giả định trong
quá khứ, không giả định phân phối chuẩn.

**Phương pháp tham số với phân phối chuẩn (Parametric Normal)** ước lượng VaR và ES từ trung bình và
độ lệch chuẩn của chuỗi lỗ, với giả định phân phối chuẩn.

**Expected Shortfall (ES)** là mức lỗ trung bình của các quan sát nằm trong phần đuôi vượt ngưỡng VaR.

**VaR mô phỏng lịch sử theo cửa sổ trượt** tại ngày *t* chỉ dùng dữ liệu trước ngày *t* để
ước lượng ngưỡng. Các điểm “Vượt VaR” là các lần vượt ngưỡng VaR; kiểm định
Kupiec và Christoffersen được trình bày tại phần kiểm định lại VaR.

Kết quả hiện tại dựa trên quy mô vị thế hoặc độ nhạy giả định, chưa bao gồm
vị thế thực tế, định giá lại đầy đủ, rủi ro cơ sở (basis risk), quyền chọn (optionality), tương quan
giữa nhiều yếu tố rủi ro hay hiệu ứng phi tuyến.
            """
        )

def render_backtesting_tab(
    fx_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
) -> None:
    """Trang kiểm định lại VaR theo cửa sổ trượt."""
    st.subheader("Kiểm định lại VaR (Backtesting)")
    st.caption(
        "Kiểm định tần suất và tính độc lập của các lần vượt VaR bằng "
        "Kupiec POF và Christoffersen."
    )

    risk_type = st.radio(
        "Loại yếu tố rủi ro",
        options=[
            "Ngoại hối USD/VND",
            "Lãi suất liên ngân hàng",
        ],
        horizontal=True,
        key="backtest_risk_type",
    )

    left, middle = st.columns(2)

    if risk_type == "Ngoại hối USD/VND":
        with left:
            position = st.selectbox(
                "Trạng thái giả định",
                options=[POSITION_LONG_USD, POSITION_SHORT_USD],
                key="backtest_fx_position",
            )

        with middle:
            exposure = st.number_input(
                "Quy mô vị thế giả định (tỷ đồng)",
                min_value=1.0,
                value=1000.0,
                step=100.0,
                key="backtest_fx_exposure",
            )

        loss_data = build_fx_loss_series(
            fx_data=fx_data,
            exposure_billion_vnd=exposure,
            position=position,
        )
        unit = "tỷ đồng"
        setup_description = (
            f"{position}, quy mô vị thế giả định "
            f"{format_number(exposure, 0)} tỷ đồng."
        )

    else:
        with left:
            factor_name = st.selectbox(
                "Kỳ hạn",
                options=list(RATE_FACTORS.keys()),
                key="backtest_rate_factor",
            )

        with middle:
            sensitivity = st.number_input(
                "Độ nhạy P&L khi lãi suất tăng 1 bp (triệu đồng/bp)",
                min_value=-10000.0,
                max_value=10000.0,
                value=10.0,
                step=1.0,
                key="backtest_rate_sensitivity",
            )

        loss_data = build_rate_loss_series(
            interbank_data=interbank_data,
            factor_name=factor_name,
            sensitivity_million_vnd_per_bp=sensitivity,
        )
        unit = "triệu đồng"
        setup_description = (
            f"{factor_name}, độ nhạy giả định "
            f"{format_number(sensitivity, 2)} triệu đồng/bp."
        )

    st.caption(f"Thiết lập hiện tại: {setup_description}")

    parameter_columns = st.columns(4)

    with parameter_columns[0]:
        confidence = st.select_slider(
            "Mức tin cậy VaR",
            options=[0.95, 0.975, 0.99],
            value=0.99,
            format_func=lambda value: f"{value * 100:g}%",
            key="backtest_confidence",
        )

    with parameter_columns[1]:
        rolling_window = st.selectbox(
            "Cửa sổ ước lượng",
            options=[125, 250, 500],
            index=1,
            format_func=lambda value: f"{value} quan sát",
            key="backtest_window",
        )

    with parameter_columns[2]:
        evaluation_label = st.selectbox(
            "Mẫu kiểm định",
            options=[
                "250 quan sát gần nhất",
                "500 quan sát gần nhất",
                "1.000 quan sát gần nhất",
                "Toàn bộ dữ liệu khả dụng",
            ],
            index=1,
            key="backtest_evaluation_sample",
        )

    with parameter_columns[3]:
        significance_level = st.selectbox(
            "Mức ý nghĩa kiểm định",
            options=[0.01, 0.05, 0.10],
            index=1,
            format_func=lambda value: f"{value * 100:g}%",
            key="backtest_significance",
        )

    rolling_data = rolling_historical_var(
        loss_data=loss_data,
        confidence_level=confidence,
        window=rolling_window,
    )

    evaluation_map = {
        "250 quan sát gần nhất": 250,
        "500 quan sát gần nhất": 500,
        "1.000 quan sát gần nhất": 1000,
        "Toàn bộ dữ liệu khả dụng": None,
    }

    evaluation_count = evaluation_map[evaluation_label]

    if evaluation_count is None:
        backtest_data = rolling_data
    else:
        backtest_data = rolling_data.dropna(
            subset=["rolling_var"]
        ).tail(evaluation_count)

    backtest = run_var_backtest(
        rolling_data=backtest_data,
        confidence_level=confidence,
        significance_level=significance_level,
    )

    overall_result = backtest["overall_result"]

    if overall_result == OVERALL_ACCEPTABLE:
        st.success(
            "Các kiểm định khả dụng chưa cung cấp đủ bằng chứng để bác bỏ "
            "mô hình ở mức ý nghĩa đã chọn."
        )
    elif overall_result == OVERALL_REVIEW:
        st.warning(
            "Ít nhất một kiểm định bác bỏ giả thuyết không. "
            "Cần xem xét lại đặc tính của mô hình và chuỗi các lần vượt VaR."
        )
    else:
        st.info(
            "Chưa đủ số lần vượt VaR hoặc chuyển trạng thái để thực hiện đầy đủ "
            "các kiểm định lại."
        )

    st.markdown("#### Thống kê các lần vượt VaR")
    columns = st.columns(4)

    columns[0].metric(
        "Số quan sát kiểm định",
        backtest["observations"],
    )
    columns[1].metric(
        "Số lần vượt VaR thực tế",
        backtest["exception_count"],
    )
    columns[2].metric(
        "Số lần vượt VaR kỳ vọng",
        format_number(backtest["expected_exceptions"], 2),
    )

    observed_rate = backtest["observed_rate"]
    expected_rate = backtest["expected_rate"]

    columns[3].metric(
        "Tỷ lệ vượt VaR",
        "—" if pd.isna(observed_rate) else f"{observed_rate * 100:.2f}%",
        delta=(
            f"Kỳ vọng {expected_rate * 100:.2f}%"
            if pd.notna(expected_rate)
            else None
        ),
        delta_color="off",
    )

    st.markdown("#### Kiểm định thống kê")
    st.dataframe(
        prepare_backtest_test_table(backtest["tests"]),
        width="stretch",
        hide_index=True,
    )

    chart_left, chart_right = st.columns(2, gap="large")

    with chart_left:
        show_chart(
            "Lỗ thực tế và VaR theo cửa sổ trượt",
            create_rolling_var_chart(
                rolling_data,
                unit,
            ),
            key="backtest_rolling_chart",
        )

    with chart_right:
        show_chart(
            "Số lần vượt VaR tích lũy: thực tế và kỳ vọng",
            create_cumulative_exception_chart(
                backtest["cumulative"]
            ),
            key="backtest_cumulative_chart",
        )

    st.markdown("#### Nhật ký các ngày vượt VaR")
    exception_table = prepare_exception_log(
        backtest["exceptions"],
        unit,
    )

    if exception_table.empty:
        st.success("Không ghi nhận ngày vượt VaR trong mẫu kiểm định.")
    else:
        st.dataframe(
            exception_table,
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Cấu trúc các lần vượt VaR")
    detail_columns = st.columns(3)

    detail_columns[0].metric(
        "Chuỗi vượt VaR liên tiếp dài nhất",
        backtest["max_consecutive_exceptions"],
    )

    mean_gap = backtest["mean_gap"]
    detail_columns[1].metric(
        "Khoảng cách trung bình",
        "—" if pd.isna(mean_gap) else f"{mean_gap:.1f} quan sát",
    )

    minimum_gap = backtest["minimum_gap"]
    detail_columns[2].metric(
        "Khoảng cách ngắn nhất",
        "—" if pd.isna(minimum_gap) else f"{minimum_gap} quan sát",
    )

    with st.expander("Ý nghĩa các kiểm định"):
        st.markdown(
            f"""
**Kupiec POF** kiểm tra xem tỷ lệ vượt VaR quan sát có phù hợp với tỷ lệ
kỳ vọng `{(1 - confidence) * 100:.2f}%` hay không.

**Christoffersen Independence** kiểm tra các lần vượt VaR có độc lập theo thời
gian hay có xu hướng xuất hiện thành cụm.

**Christoffersen Conditional Coverage** kết hợp cả hai yêu cầu: tần suất vượt VaR phù hợp
và các lần vượt VaR không có xu hướng tập trung thành cụm.

Với mức ý nghĩa `{significance_level * 100:g}%`, `p-value` nhỏ hơn mức này
được ghi là **Bác bỏ**. `p-value` lớn hơn hoặc bằng mức này được ghi là
**Không bác bỏ**. “Không bác bỏ” không đồng nghĩa chứng minh mô hình đúng;
nó chỉ cho biết mẫu hiện tại chưa cung cấp đủ bằng chứng thống kê để bác bỏ
giả thuyết không.

Kiểm định lại VaR ở đây sử dụng quy mô vị thế/độ nhạy giả định và VaR mô phỏng lịch sử
một ngày theo cửa sổ trượt. Kết quả không thay thế quy trình thẩm định mô hình, quản trị mô hình hay
hạn mức của một tổ chức tài chính thực tế.
            """
        )

def render_funding_pressure_tab(
    pressure_data: pd.DataFrame,
    funding_summary: dict[str, object],
) -> None:
    """Trang giám sát áp lực nguồn vốn và thanh khoản thị trường."""
    st.subheader("Giám sát áp lực nguồn vốn")

    st.caption(
        "Chỉ số tổng hợp sử dụng lãi suất qua đêm, chênh lệch lãi suất "
        "liên ngân hàng so với huy động, biến động huy động và doanh số "
        "liên ngân hàng để theo dõi áp lực nguồn vốn trên thị trường."
    )

    count = select_period(
        "funding_pressure_period",
        default_label="2 năm",
    )
    recent = pressure_data.tail(count)

    columns = st.columns(4)
    columns[0].metric(
        "Chỉ số áp lực nguồn vốn",
        format_number(funding_summary["index"], 2),
    )
    columns[1].metric(
        "Chênh lệch 3M liên ngân hàng - huy động 1-3M",
        format_value(funding_summary["spread_3m"], "điểm phần trăm"),
    )
    columns[2].metric(
        "Δ huy động 12M / 20 quan sát",
        format_value(funding_summary["deposit_change_20d_bps"], "bps"),
    )
    columns[3].metric(
        "Trạng thái",
        funding_summary["status"],
    )

    if pd.notna(funding_summary["date"]):
        age_text = (
            "—"
            if pd.isna(funding_summary["deposit_age_days"])
            else f"{int(funding_summary['deposit_age_days'])} ngày"
        )
        st.caption(
            f"Ngày đánh giá: {format_date(funding_summary['date'])}. "
            f"Độ trễ dữ liệu huy động được ghép: {age_text}."
        )

    left, right = st.columns(2, gap="large")

    with left:
        show_chart(
            "Chênh lệch lãi suất liên ngân hàng - huy động",
            create_funding_spread_chart(recent),
            key="funding_spread_chart",
        )

    with right:
        show_chart(
            "Chỉ số áp lực nguồn vốn",
            create_funding_pressure_index_chart(recent),
            key="funding_pressure_index_chart",
        )

    components = build_pressure_components_snapshot(pressure_data)

    st.markdown("#### Phân rã áp lực hiện tại")
    left, right = st.columns(2, gap="large")

    with left:
        component_table = prepare_funding_component_table(components)
        if component_table.empty:
            st.info("Chưa đủ dữ liệu để phân rã chỉ số.")
        else:
            st.dataframe(
                component_table,
                width="stretch",
                hide_index=True,
            )

    with right:
        if not components.empty:
            show_chart(
                "Đóng góp của từng thành phần",
                create_funding_component_chart(components),
                key="funding_component_chart",
            )

    st.markdown("#### Lịch sử các giai đoạn áp lực cao")
    events = build_pressure_events(pressure_data, max_events=50)
    event_table = prepare_funding_event_table(events)

    if event_table.empty:
        st.info(
            "Chưa ghi nhận quan sát vượt ngưỡng theo dõi trong mẫu hiệu chỉnh."
        )
    else:
        st.dataframe(
            event_table,
            width="stretch",
            hide_index=True,
        )

    with st.expander("Phương pháp xây dựng chỉ số"):
        st.markdown(
            """
**1. Căn chỉnh dữ liệu**

Mỗi ngày liên ngân hàng được ghép với quan sát lãi suất huy động gần nhất
**tại hoặc trước ngày đó**, với độ trễ tối đa 7 ngày. Cách làm này tránh
sai lệch do sử dụng thông tin tương lai (look-ahead bias).

**2. Bốn thành phần áp lực**

- Mặt bằng lãi suất qua đêm.
- Chênh lệch lãi suất 3 tháng liên ngân hàng so với huy động 1-3 tháng.
- Mức thay đổi lãi suất huy động 12 tháng trong 20 quan sát.
- Doanh số liên ngân hàng sau biến đổi log.

Mỗi thành phần được chuẩn hóa bằng Z-score theo cửa sổ trượt 250 quan sát. Chỉ phần
Z-score dương được đưa vào chỉ số vì mục tiêu là nhận diện **áp lực tăng**.

**3. Phân loại trạng thái**

Chỉ số áp lực nguồn vốn là trung bình của các thành phần khả dụng. Ngưỡng
Theo dõi và Cảnh báo lần lượt là bách phân vị 95% và 99% của chính chỉ số
trong lịch sử động, không phải các hạn mức nội bộ của ngân hàng.

**4. Giới hạn diễn giải**

Chỉ số này phản ánh áp lực thị trường và chi phí vốn tương đối. Không thể
thay thế các chỉ tiêu thanh khoản nội bộ như chênh lệch dòng tiền theo kỳ hạn,
chênh lệch dòng tiền thanh khoản, LCR, NSFR, thời gian duy trì thanh khoản hoặc mức sử dụng hạn mức thanh khoản khi
không có dữ liệu bảng cân đối và dòng tiền của ngân hàng.
            """
        )

def render_liquidity_gap_tab() -> None:
    """Mô phỏng chênh lệch dòng tiền thanh khoản khi có thang dòng tiền theo kỳ hạn."""
    st.subheader("Chênh lệch dòng tiền thanh khoản / Thời gian duy trì thanh khoản")

    st.caption("Dữ liệu yêu cầu: thang dòng tiền theo kỳ hạn (cash-flow ladder) và đệm thanh khoản ban đầu.")

    template = blank_liquidity_template()
    required_columns = list(template.columns)

    if "liquidity_gap_table" not in st.session_state:
        st.session_state["liquidity_gap_table"] = template.copy()

    upload_col, download_col, reset_col = st.columns([2, 1, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Tải thang dòng tiền theo kỳ hạn (CSV/XLSX)",
            type=["csv", "xlsx", "xls"],
            key="liquidity_gap_upload",
        )

    with download_col:
        st.download_button(
            "Tải tệp mẫu trống",
            data=template.to_csv(index=False).encode("utf-8-sig"),
            file_name="liquidity_gap_template.csv",
            mime="text/csv",
            width="stretch",
            key="download_liquidity_gap_template",
        )

    with reset_col:
        if st.button("Làm trống bảng", key="reset_liquidity_gap", width="stretch"):
            st.session_state["liquidity_gap_table"] = template.copy()

    if uploaded_file is not None:
        try:
            uploaded_data = read_uploaded_table(uploaded_file, required_columns)
            st.session_state["liquidity_gap_table"] = uploaded_data
        except ValueError as error:
            st.error(str(error))

    st.markdown("#### Thang dòng tiền theo kỳ hạn")
    input_data = st.data_editor(
        st.session_state["liquidity_gap_table"].copy(),
        width="stretch",
        hide_index=True,
        key="liquidity_gap_editor",
        disabled=["bucket", "start_day", "end_day"],
        column_config={
            "bucket": st.column_config.TextColumn("Nhóm kỳ hạn"),
            "start_day": st.column_config.NumberColumn("Từ ngày", format="%.0f"),
            "end_day": st.column_config.NumberColumn("Đến ngày", format="%.0f"),
            "cash_inflow": st.column_config.NumberColumn(
                "Dòng tiền vào (tỷ đồng)", min_value=0.0, format="%.0f"
            ),
            "cash_outflow": st.column_config.NumberColumn(
                "Dòng tiền ra (tỷ đồng)", min_value=0.0, format="%.0f"
            ),
        },
    )
    st.session_state["liquidity_gap_table"] = input_data.copy()

    st.markdown("#### Kịch bản thanh khoản")
    scenario_columns = st.columns(2)

    with scenario_columns[0]:
        opening_buffer_text = st.text_input(
            "Đệm thanh khoản ban đầu (tỷ đồng)",
            value="",
            placeholder="Nhập giá trị",
            key="liquidity_opening_buffer_text",
        )

    with scenario_columns[1]:
        scenario = st.selectbox(
            "Kịch bản",
            options=LIQUIDITY_SCENARIO_OPTIONS,
            index=0,
            key="liquidity_scenario",
        )

    if scenario == LIQUIDITY_SCENARIO_CUSTOM:
        stress_columns = st.columns(3)
        with stress_columns[0]:
            inflow_haircut_pct = st.number_input(
                "Khấu trừ dòng tiền vào (haircut, %)", min_value=0.0, max_value=100.0,
                value=10.0, step=5.0, key="liquidity_inflow_haircut"
            )
        with stress_columns[1]:
            outflow_increase_pct = st.number_input(
                "Tăng dòng tiền ra (%)", min_value=0.0, max_value=100.0,
                value=15.0, step=5.0, key="liquidity_outflow_increase"
            )
        with stress_columns[2]:
            buffer_haircut_pct = st.number_input(
                "Khấu trừ đệm thanh khoản (haircut, %)", min_value=0.0, max_value=100.0,
                value=10.0, step=5.0, key="liquidity_buffer_haircut"
            )
    else:
        parameters = get_liquidity_scenario_parameters(scenario)
        inflow_haircut_pct = parameters["inflow_haircut_pct"]
        outflow_increase_pct = parameters["outflow_increase_pct"]
        buffer_haircut_pct = parameters["buffer_haircut_pct"]

        parameter_columns = st.columns(3)
        parameter_columns[0].metric("Khấu trừ dòng tiền vào", f"{format_number(inflow_haircut_pct, 0)}%")
        parameter_columns[1].metric("Tăng dòng tiền ra", f"{format_number(outflow_increase_pct, 0)}%")
        parameter_columns[2].metric("Khấu trừ đệm thanh khoản", f"{format_number(buffer_haircut_pct, 0)}%")

    with st.expander("Ngưỡng giám sát thời gian duy trì thanh khoản"):
        threshold_columns = st.columns(2)
        with threshold_columns[0]:
            alert_horizon_days = st.number_input(
                "Ngưỡng Cảnh báo (ngày)", min_value=1.0, value=30.0,
                step=5.0, key="liquidity_alert_horizon"
            )
        with threshold_columns[1]:
            watch_horizon_days = st.number_input(
                "Ngưỡng Theo dõi (ngày)", min_value=1.0, value=60.0,
                step=5.0, key="liquidity_watch_horizon"
            )
        st.caption(
            "Ngưỡng giám sát được áp dụng cho chỉ tiêu thời gian duy trì thanh khoản (Survival Horizon)."
        )

    if watch_horizon_days < alert_horizon_days:
        st.error("Ngưỡng Theo dõi phải lớn hơn hoặc bằng ngưỡng Cảnh báo.")
        return

    if not liquidity_input_ready(input_data):
        st.info(
            "Chưa đủ dữ liệu dòng tiền vào/ra. Hệ thống chưa thực hiện tính chênh lệch dòng tiền thanh khoản."
        )
        return

    try:
        opening_buffer = float(opening_buffer_text.replace(",", "").strip())
    except ValueError:
        st.info("Hãy nhập đệm thanh khoản ban đầu để thực hiện tính toán.")
        return

    try:
        results = calculate_liquidity_gap(
            input_data,
            opening_buffer=opening_buffer,
            inflow_haircut_pct=inflow_haircut_pct,
            outflow_increase_pct=outflow_increase_pct,
            buffer_haircut_pct=buffer_haircut_pct,
        )
    except ValueError as error:
        st.error(str(error))
        return

    summary = summarize_liquidity_gap(
        results,
        alert_horizon_days=alert_horizon_days,
        watch_horizon_days=watch_horizon_days,
    )

    st.markdown("#### Kết quả tổng hợp")
    survival_text = (
        f"{format_number(summary['survival_day'], 1)} ngày"
        if summary["depleted"]
        else f"> {int(results['end_day'].max())} ngày"
    )

    columns = st.columns(5)
    columns[0].metric("Đệm thanh khoản sau khấu trừ", f"{format_number(summary['effective_buffer'], 0)} tỷ")
    columns[1].metric("Chênh lệch lũy kế 30 ngày", f"{format_number(summary['gap_30d'], 0)} tỷ")
    columns[2].metric("Trạng thái thanh khoản 30 ngày", f"{format_number(summary['position_30d'], 0)} tỷ")
    columns[3].metric("Thời gian duy trì thanh khoản", survival_text)
    columns[4].metric("Trạng thái", summary["status"])

    if summary["depleted"]:
        st.caption(
            "Đệm thanh khoản được ước tính cạn trong nhóm kỳ hạn "
            f"{summary['survival_bucket']}. Thời gian duy trì thanh khoản được nội suy tuyến tính."
        )
    else:
        st.caption(
            "Đệm thanh khoản vẫn dương đến cuối khoảng thời gian mô phỏng. "
            f"Trạng thái thanh khoản thấp nhất: {format_number(summary['minimum_position'], 0)} tỷ đồng."
        )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Dòng tiền vào và dòng tiền ra sau cú sốc",
            create_liquidity_flow_chart(results),
            key="liquidity_flow_chart",
        )
    with right:
        show_chart(
            "Chênh lệch dòng tiền thanh khoản và chênh lệch lũy kế",
            create_liquidity_gap_chart(results),
            key="liquidity_gap_chart",
        )

    show_chart(
        "Trạng thái thanh khoản và thời gian duy trì thanh khoản",
        create_liquidity_position_chart(results),
        key="liquidity_position_chart",
    )

    st.markdown("#### Chi tiết theo nhóm kỳ hạn")
    st.dataframe(prepare_liquidity_gap_table(results), width="stretch", hide_index=True)

    with st.expander("Phương pháp và giới hạn diễn giải"):
        st.markdown(
            """
**Chênh lệch dòng tiền thanh khoản (Liquidity Gap)** = dòng tiền vào - dòng tiền ra trong từng nhóm kỳ hạn.
**Chênh lệch dòng tiền thanh khoản lũy kế (Cumulative Gap)** là tổng lũy kế chênh lệch dòng tiền.

**Trạng thái thanh khoản (Liquidity Position)** = đệm thanh khoản khả dụng sau khấu trừ + chênh lệch dòng tiền thanh khoản lũy kế sau cú sốc.
**Thời gian duy trì thanh khoản (Survival Horizon)** là thời điểm trạng thái thanh khoản lần đầu xuống dưới 0; nếu xảy ra
trong một nhóm kỳ hạn nhiều ngày, hệ thống nội suy tuyến tính.

LCR và NSFR không nằm trong phạm vi tính toán của module này.
            """
        )

def render_irrbb_tab() -> None:
    """Mô phỏng IRRBB khi có dữ liệu đầu vào của sổ ngân hàng."""
    st.subheader("Rủi ro lãi suất trên sổ ngân hàng (IRRBB)")

    st.caption("Dữ liệu yêu cầu: tài sản nhạy cảm lãi suất (RSA), nguồn vốn nhạy cảm lãi suất (RSL) và độ nhạy theo nhóm kỳ hạn tái định giá.")

    template = blank_repricing_template()
    required_columns = list(template.columns)

    if "irrbb_repricing_table" not in st.session_state:
        st.session_state["irrbb_repricing_table"] = template.copy()

    upload_col, download_col, reset_col = st.columns([2, 1, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Tải bảng tái định giá (CSV/XLSX)",
            type=["csv", "xlsx", "xls"],
            key="irrbb_repricing_upload",
        )

    with download_col:
        st.download_button(
            "Tải tệp mẫu trống",
            data=template.to_csv(index=False).encode("utf-8-sig"),
            file_name="irrbb_repricing_template.csv",
            mime="text/csv",
            width="stretch",
            key="download_irrbb_repricing_template",
        )

    with reset_col:
        if st.button("Làm trống bảng", key="reset_irrbb_table", width="stretch"):
            st.session_state["irrbb_repricing_table"] = template.copy()

    if uploaded_file is not None:
        try:
            uploaded_data = read_uploaded_table(uploaded_file, required_columns)
            st.session_state["irrbb_repricing_table"] = uploaded_data
        except ValueError as error:
            st.error(str(error))

    st.markdown("#### Cấu trúc tái định giá")
    input_data = st.data_editor(
        st.session_state["irrbb_repricing_table"].copy(),
        width="stretch",
        hide_index=True,
        key="irrbb_repricing_editor",
        disabled=["bucket"],
        column_config={
            "bucket": st.column_config.TextColumn("Nhóm kỳ hạn tái định giá"),
            "midpoint_years": st.column_config.NumberColumn(
                "Kỳ hạn đại diện (năm)", min_value=0.0, format="%.3f"
            ),
            "rsa": st.column_config.NumberColumn("RSA (tỷ đồng)", min_value=0.0, format="%.0f"),
            "rsl": st.column_config.NumberColumn("RSL (tỷ đồng)", min_value=0.0, format="%.0f"),
            "asset_duration": st.column_config.NumberColumn(
                "Thời lượng điều chỉnh (Modified Duration) - tài sản", min_value=0.0, format="%.2f"
            ),
            "liability_duration": st.column_config.NumberColumn(
                "Thời lượng điều chỉnh (Modified Duration) - nguồn vốn", min_value=0.0, format="%.2f"
            ),
            "custom_shock_bps": st.column_config.NumberColumn(
                "Cú sốc tùy chỉnh (bps)", format="%.0f"
            ),
        },
    )
    st.session_state["irrbb_repricing_table"] = input_data.copy()

    st.markdown("#### Kịch bản lãi suất")
    scenario_columns = st.columns(3)

    with scenario_columns[0]:
        scenario = st.selectbox(
            "Dạng kịch bản", options=SCENARIO_OPTIONS, index=0, key="irrbb_scenario"
        )
    with scenario_columns[1]:
        shock_size_bps = st.number_input(
            "Độ lớn cú sốc (bps)", min_value=0.0, max_value=1000.0,
            value=200.0, step=25.0, disabled=(scenario == SCENARIO_CUSTOM),
            key="irrbb_shock_size"
        )
    with scenario_columns[2]:
        reference_equity = st.number_input(
            "Vốn chủ sở hữu tham chiếu (tỷ đồng, tùy chọn)", min_value=0.0,
            value=0.0, step=1000.0, key="irrbb_reference_equity"
        )

    reference_nii = st.number_input(
        "Thu nhập lãi thuần (NII) tham chiếu một năm (tỷ đồng, tùy chọn)", min_value=0.0,
        value=0.0, step=500.0, key="irrbb_reference_nii"
    )

    if not irrbb_input_ready(input_data, scenario):
        required_note = (
            "kỳ hạn đại diện, RSA, RSL và thời lượng điều chỉnh (Modified Duration) cho tất cả nhóm kỳ hạn"
            if scenario != SCENARIO_CUSTOM
            else "kỳ hạn đại diện, RSA, RSL, thời lượng điều chỉnh (Modified Duration) và cú sốc (bps) cho tất cả nhóm kỳ hạn"
        )
        st.info(f"Chưa đủ dữ liệu IRRBB. Hãy nhập {required_note} trước khi tính.")
        return

    try:
        results = calculate_irrbb(
            input_data,
            scenario=scenario,
            shock_size_bps=shock_size_bps,
        )
    except ValueError as error:
        st.error(str(error))
        return

    summary = summarize_irrbb(
        results,
        reference_equity=reference_equity if reference_equity > 0 else None,
        reference_nii=reference_nii if reference_nii > 0 else None,
    )

    st.markdown("#### Kết quả tổng hợp")
    columns = st.columns(5)
    columns[0].metric("Tổng RSA", f"{format_number(summary['total_rsa'], 0)} tỷ")
    columns[1].metric("Tổng RSL", f"{format_number(summary['total_rsl'], 0)} tỷ")
    columns[2].metric("Chênh lệch kỳ định lại lãi suất ròng", f"{format_number(summary['net_gap'], 0)} tỷ")
    columns[3].metric("ΔNII xấp xỉ", f"{format_number(summary['nii_impact'], 1)} tỷ")
    columns[4].metric("ΔEVE xấp xỉ", f"{format_number(summary['eve_proxy_impact'], 1)} tỷ")

    ratio_text = []
    if pd.notna(summary["nii_impact_pct"]):
        ratio_text.append(
            "ΔNII / NII tham chiếu: " f"{format_number(summary['nii_impact_pct'], 2)}%"
        )
    if pd.notna(summary["eve_proxy_pct"]):
        ratio_text.append(
            "ΔEVE xấp xỉ / vốn chủ sở hữu tham chiếu: " f"{format_number(summary['eve_proxy_pct'], 2)}%"
        )

    caption = f"Trạng thái chênh lệch kỳ định lại lãi suất tổng thể: {summary['gap_direction']}."
    if ratio_text:
        caption += " " + " | ".join(ratio_text)
    st.caption(caption)

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "RSA và RSL theo nhóm kỳ hạn",
            create_repricing_balance_chart(results),
            key="irrbb_balance_chart",
        )
    with right:
        show_chart(
            "Chênh lệch kỳ định lại lãi suất và chênh lệch lũy kế",
            create_repricing_gap_chart(results),
            key="irrbb_gap_chart",
        )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Cú sốc lãi suất theo nhóm kỳ hạn",
            create_irrbb_shock_chart(results),
            key="irrbb_shock_chart",
        )
    with right:
        show_chart(
            "Độ nhạy ΔNII và ΔEVE xấp xỉ",
            create_irrbb_sensitivity_chart(results),
            key="irrbb_sensitivity_chart",
        )

    st.markdown("#### Chi tiết theo nhóm kỳ hạn")
    st.dataframe(prepare_irrbb_table(results), width="stretch", hide_index=True)

    with st.expander("Phương pháp và giới hạn diễn giải"):
        st.markdown(
            """
**Chênh lệch kỳ định lại lãi suất (Repricing Gap)** = RSA - RSL. **Độ nhạy thu nhập lãi thuần (NII Sensitivity)** được xấp xỉ theo phương pháp chênh lệch kỳ định lại lãi suất tĩnh.
**Thay đổi giá trị kinh tế vốn chủ sở hữu (ΔEVE) xấp xỉ** sử dụng thời lượng điều chỉnh (Modified Duration) và chỉ phản ánh xấp xỉ bậc một.

Để đo lường IRRBB đầy đủ cần dòng tiền của sổ ngân hàng, các giả định hành vi đối với
tiền gửi không kỳ hạn (NMD), trả trước/mua lại trước hạn, rủi ro cơ sở (basis risk), quyền chọn (optionality) và
đường cong chiết khấu phù hợp.
            """
        )

def render_fx_tab(fx_data: pd.DataFrame) -> None:
    """Trang giám sát ngoại hối USD/VND."""
    st.subheader("Giám sát ngoại hối USD/VND")

    monitor_data = prepare_fx_risk_data(fx_data)
    summary = summarize_fx_risk(monitor_data)
    count = select_period("fx_period")
    data = monitor_data.tail(count).copy()
    window_summary = build_fx_window_summary(data)

    metrics = st.columns(6)
    metrics[0].metric("USD/VND", format_number(summary["close"], 0))
    metrics[1].metric("Thay đổi 1 ngày", f"{summary['return_1d_pct']:+.2f}%")
    metrics[2].metric("Thay đổi 5 ngày", f"{summary['return_5d_pct']:+.2f}%")
    metrics[3].metric("Độ biến động 20 ngày", f"{summary['volatility_20d_pct']:.2f}%")
    metrics[4].metric("Mức giảm từ đỉnh 250 ngày", f"{summary['drawdown_250d_pct']:.2f}%")
    metrics[5].metric("Trạng thái biến động", summary["volatility_regime"])

    st.caption(f"Cập nhật {format_date(summary['date'])}")

    regime_status = STATUS_NORMAL
    if summary["volatility_regime"] == "Cao":
        regime_status = STATUS_WATCH
    elif summary["volatility_regime"] == "Rất cao":
        regime_status = STATUS_ALERT

    st.markdown("#### Trạng thái hiện tại")
    status_columns = st.columns(3)

    with status_columns[0]:
        render_status_card(
            "Biến động tỷ giá ngày",
            summary["move_status"],
            (
                f"|Δ| {abs(summary['return_1d_pct']):.3f}% · "
                f"P95 {summary['return_p95']:.3f}% · "
                f"P99 {summary['return_p99']:.3f}%"
            ),
        )

    with status_columns[1]:
        render_status_card(
            "Biên độ trong ngày",
            summary["range_status"],
            (
                f"Biên độ {summary['intraday_range_pct']:.3f}% · "
                f"P95 {summary['range_p95']:.3f}% · "
                f"P99 {summary['range_p99']:.3f}%"
            ),
        )

    with status_columns[2]:
        render_status_card(
            "Trạng thái biến động",
            regime_status,
            (
                f"Độ biến động 20 ngày {summary['volatility_20d_pct']:.2f}% · "
                f"P80 {summary['vol20_p80']:.2f}% · "
                f"P95 {summary['vol20_p95']:.2f}%"
            ),
        )

    show_chart(
        "Diễn biến tỷ giá USD/VND",
        create_fx_candlestick_chart(data),
        key="fx_candlestick_chart",
    )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Biến động ngày và ngưỡng lịch sử",
            create_fx_threshold_chart(data),
            key="fx_threshold_chart",
        )
    with right:
        show_chart(
            "Mức giảm từ đỉnh 250 ngày",
            create_fx_drawdown_chart(data),
            key="fx_drawdown_chart",
        )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Trạng thái biến động",
            create_fx_volatility_regime_chart(data),
            key="fx_volatility_regime_chart",
        )
    with right:
        show_chart(
            "Biên độ trong ngày và ngưỡng lịch sử",
            create_fx_range_threshold_chart(data),
            key="fx_range_threshold_chart",
        )

    st.markdown("#### Thống kê trong khoảng thời gian đã chọn")
    statistics = st.columns(6)
    statistics[0].metric("Phiên tăng mạnh nhất", f"{window_summary['max_up_pct']:+.2f}%")
    statistics[1].metric("Phiên giảm mạnh nhất", f"{window_summary['max_down_pct']:+.2f}%")
    statistics[2].metric("Biên độ lớn nhất", f"{window_summary['max_range_pct']:.2f}%")
    statistics[3].metric("Mức giảm từ đỉnh sâu nhất", f"{window_summary['min_drawdown_pct']:.2f}%")
    statistics[4].metric("Ngày theo dõi", window_summary["watch_days"])
    statistics[5].metric("Ngày cảnh báo", window_summary["alert_days"])

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Sự kiện vượt ngưỡng gần nhất")
        events = build_fx_event_log(data, max_events=20)
        event_table = prepare_fx_event_table(events)

        if event_table.empty:
            st.success("Không ghi nhận sự kiện vượt ngưỡng trong khoảng thời gian đã chọn.")
        else:
            st.dataframe(event_table, width="stretch", hide_index=True)

    with right:
        st.markdown("#### Các phiên biến động mạnh nhất")
        extremes = build_extreme_move_table(data, top_n=10)
        st.dataframe(
            prepare_fx_extreme_table(extremes),
            width="stretch",
            hide_index=True,
        )

def render_interbank_tab(interbank_data: pd.DataFrame) -> None:
    """Trang giám sát thị trường tiền tệ liên ngân hàng."""
    st.subheader("Giám sát thị trường tiền tệ liên ngân hàng")

    monitor_data = prepare_money_market_data(interbank_data)
    summary = summarize_money_market(monitor_data)
    count = select_period("interbank_period")
    data = monitor_data.tail(count).copy()
    window_summary = build_money_market_window_summary(data)

    metrics = st.columns(6)
    metrics[0].metric("Lãi suất O/N", f"{summary['rate_on']:.2f}%")
    metrics[1].metric("Thay đổi O/N", f"{summary['on_change_bps']:+.0f} bps")
    metrics[2].metric(
        "Biến động O/N 20 ngày",
        f"{summary['on_volatility_20d_bps']:.0f} bps",
    )
    metrics[3].metric("3M - O/N", f"{summary['spread_3m_on_bps']:+.0f} bps")
    metrics[4].metric(
        "Tổng doanh số",
        "—" if pd.isna(summary["total_turnover"]) else f"{format_number(summary['total_turnover'], 0)} tỷ",
    )
    metrics[5].metric(
        "Tỷ trọng O/N",
        "—" if pd.isna(summary["turnover_on_share_pct"]) else f"{summary['turnover_on_share_pct']:.1f}%",
    )

    update_text = f"Lãi suất cập nhật {format_date(summary['date'])}"
    if pd.notna(summary["turnover_date"]):
        update_text += f" · Doanh số cập nhật {format_date(summary['turnover_date'])}"
    st.caption(update_text)

    st.markdown("#### Trạng thái hiện tại")
    status_columns = st.columns(4)

    with status_columns[0]:
        render_status_card(
            "Biến động O/N trong ngày",
            summary["on_change_status"],
            (
                f"|Δ| {abs(summary['on_change_bps']):.0f} bps · "
                f"P95 {summary['on_change_p95_bps']:.0f} bps · "
                f"P99 {summary['on_change_p99_bps']:.0f} bps"
            ),
        )

    with status_columns[1]:
        render_status_card(
            "Mặt bằng lãi suất O/N",
            summary["on_level_status"],
            f"Z-score {summary['on_level_zscore']:+.2f}σ · O/N {summary['rate_on']:.2f}%",
        )

    with status_columns[2]:
        render_status_card(
            "Cấu trúc kỳ hạn",
            summary["curve_status"],
            (
                f"Đảo chiều lớn nhất {summary['max_curve_inversion_bps']:.0f} bps · "
                f"P95 {summary['curve_inversion_p95_bps']:.0f} bps · "
                f"P99 {summary['curve_inversion_p99_bps']:.0f} bps"
            ),
        )

    with status_columns[3]:
        turnover_description = "Chưa đủ dữ liệu doanh số để đánh giá."
        if pd.notna(summary["turnover_zscore"]):
            turnover_description = (
                f"Z-score {summary['turnover_zscore']:+.2f}σ · "
                f"{format_number(summary['total_turnover'], 0)} tỷ đồng"
            )
        render_status_card(
            "Doanh số giao dịch",
            summary["turnover_status"],
            turnover_description,
        )

    show_chart(
        "Lãi suất liên ngân hàng theo kỳ hạn",
        create_interbank_rate_chart(data),
        key="interbank_rates_chart",
    )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Biến động O/N và ngưỡng lịch sử",
            create_on_change_threshold_chart(data),
            key="interbank_on_change_threshold_chart",
        )
    with right:
        show_chart(
            "Mức độ bất thường của lãi suất O/N",
            create_on_level_zscore_chart(data),
            key="interbank_on_zscore_chart",
        )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Chênh lệch kỳ hạn so với O/N",
            create_money_market_curve_chart(data),
            key="interbank_curve_spread_bps_chart",
        )
    with right:
        show_chart(
            "Mức độ bất thường của doanh số giao dịch",
            create_turnover_zscore_chart(data),
            key="interbank_turnover_zscore_chart",
        )

    show_chart(
        "Tổng doanh số liên ngân hàng",
        create_interbank_turnover_chart(data),
        key="interbank_turnover_chart",
    )

    st.markdown("#### Thống kê trong khoảng thời gian đã chọn")
    statistics = st.columns(7)
    statistics[0].metric("O/N cao nhất", f"{window_summary['max_on_rate']:.2f}%")
    statistics[1].metric("O/N thấp nhất", f"{window_summary['min_on_rate']:.2f}%")
    statistics[2].metric("Mức tăng O/N lớn nhất", f"{window_summary['max_up_bps']:+.0f} bps")
    statistics[3].metric("Mức giảm O/N lớn nhất", f"{window_summary['max_down_bps']:+.0f} bps")
    statistics[4].metric("Đảo chiều lớn nhất", f"{window_summary['max_inversion_bps']:.0f} bps")
    statistics[5].metric("Ngày theo dõi", window_summary["watch_days"])
    statistics[6].metric("Ngày cảnh báo", window_summary["alert_days"])

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Sự kiện vượt ngưỡng gần nhất")
        events = build_money_market_event_log(data, max_events=20)
        event_table = prepare_money_market_event_table(events)

        if event_table.empty:
            st.success("Không ghi nhận sự kiện vượt ngưỡng trong khoảng thời gian đã chọn.")
        else:
            st.dataframe(event_table, width="stretch", hide_index=True)

    with right:
        st.markdown("#### Các phiên O/N biến động mạnh nhất")
        extremes = build_money_market_extremes(data, top_n=10)
        st.dataframe(
            prepare_money_market_extreme_table(extremes),
            width="stretch",
            hide_index=True,
        )

def render_deposit_tab(deposit_data: pd.DataFrame) -> None:
    """Trang giám sát lãi suất huy động."""
    st.subheader("Giám sát lãi suất huy động")

    monitor_data = prepare_deposit_rate_data(deposit_data)
    summary = summarize_deposit_rates(monitor_data)
    count = select_period("deposit_period")
    data = monitor_data.tail(count).copy()
    window_summary = build_deposit_rate_window_summary(data)

    metrics = st.columns(6)
    metrics[0].metric("1-3 tháng", f"{summary['deposit_1_3m']:.3f}%")
    metrics[1].metric("6-9 tháng", f"{summary['deposit_6_9m']:.3f}%")
    metrics[2].metric("12 tháng", f"{summary['deposit_12m']:.3f}%")
    metrics[3].metric("Δ12M · 5 quan sát", f"{summary['change_5obs_12m_bps']:+.0f} bps")
    metrics[4].metric("Δ12M · 20 quan sát", f"{summary['change_20obs_12m_bps']:+.0f} bps")
    metrics[5].metric("12M - 1-3M", f"{summary['spread_12m_1_3m_bps']:+.0f} bps")

    st.caption(
        f"Cập nhật {format_date(summary['date'])} · "
        f"Chế độ mặt bằng 12 tháng: {summary['rate_regime']}"
    )

    st.markdown("#### Trạng thái hiện tại")
    status_columns = st.columns(3)

    with status_columns[0]:
        render_status_card(
            "Tốc độ điều chỉnh lãi suất",
            summary["repricing_status"],
            (
                f"Δ12M/20 quan sát {summary['change_20obs_12m_bps']:+.0f} bps · "
                f"P95 {summary['repricing_p95_12m_bps']:.0f} bps · "
                f"P99 {summary['repricing_p99_12m_bps']:.0f} bps"
            ),
        )

    with status_columns[1]:
        render_status_card(
            "Mặt bằng lãi suất 12 tháng",
            summary["level_status"],
            (
                f"12 tháng {summary['deposit_12m']:.3f}% · "
                f"Z-score {summary['rate_12m_zscore']:+.2f}σ · "
                f"{summary['rate_regime']}"
            ),
        )

    with status_columns[2]:
        render_status_card(
            "Cấu trúc kỳ hạn huy động",
            summary["spread_status"],
            (
                f"12M - 1-3M {summary['spread_12m_1_3m_bps']:+.0f} bps · "
                f"Z-score {summary['spread_zscore']:+.2f}σ"
            ),
        )

    show_chart(
        "Lãi suất huy động theo kỳ hạn",
        create_deposit_rate_chart(data),
        key="deposit_rates_chart",
    )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Mức điều chỉnh trong 20 quan sát",
            create_deposit_change_chart(data),
            key="deposit_20obs_change_chart",
        )
    with right:
        show_chart(
            "Tốc độ điều chỉnh kỳ hạn 12 tháng",
            create_deposit_repricing_threshold_chart(data),
            key="deposit_12m_repricing_threshold_chart",
        )

    left, right = st.columns(2, gap="large")
    with left:
        show_chart(
            "Chênh lệch lãi suất giữa các kỳ hạn",
            create_deposit_spread_chart(data),
            key="deposit_term_spread_chart",
        )
    with right:
        show_chart(
            "Mức độ bất thường của chênh lệch kỳ hạn",
            create_deposit_spread_zscore_chart(data),
            key="deposit_spread_zscore_chart",
        )

    show_chart(
        "Mặt bằng lãi suất 12 tháng và phân vị lịch sử",
        create_deposit_level_regime_chart(data),
        key="deposit_12m_regime_chart",
    )

    st.markdown("#### Thống kê trong khoảng thời gian đã chọn")
    statistics = st.columns(8)
    statistics[0].metric("12M cao nhất", f"{window_summary['max_12m_rate']:.3f}%")
    statistics[1].metric("12M thấp nhất", f"{window_summary['min_12m_rate']:.3f}%")
    statistics[2].metric("Tăng mạnh nhất", f"{window_summary['max_up_20obs_bps']:+.0f} bps")
    statistics[3].metric("Giảm mạnh nhất", f"{window_summary['max_down_20obs_bps']:+.0f} bps")
    statistics[4].metric("Spread rộng nhất", f"{window_summary['widest_spread_bps']:+.0f} bps")
    statistics[5].metric("Spread hẹp nhất", f"{window_summary['narrowest_spread_bps']:+.0f} bps")
    statistics[6].metric("Ngày theo dõi", window_summary["watch_days"])
    statistics[7].metric("Ngày cảnh báo", window_summary["alert_days"])

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Sự kiện vượt ngưỡng gần nhất")
        events = build_deposit_rate_event_log(data, max_events=20)
        event_table = prepare_deposit_rate_event_table(events)

        if event_table.empty:
            st.success("Không ghi nhận sự kiện vượt ngưỡng trong khoảng thời gian đã chọn.")
        else:
            st.dataframe(event_table, width="stretch", hide_index=True)

    with right:
        st.markdown("#### Các giai đoạn điều chỉnh mạnh nhất")
        extremes = build_deposit_rate_extremes(data, top_n=10)
        st.dataframe(
            prepare_deposit_rate_extreme_table(extremes),
            width="stretch",
            hide_index=True,
        )

def render_quality_tab(
    quality_report: pd.DataFrame,
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
) -> None:
    """Trang kiểm soát chất lượng và đối chiếu dữ liệu."""
    st.subheader("Kiểm soát chất lượng dữ liệu")

    exceptions = build_quality_exceptions(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    freshness = build_freshness_table(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    reconciliation = build_reconciliation_table(
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )
    summary = summarize_quality(quality_report, exceptions)

    columns = st.columns(4)
    columns[0].metric("Số phép kiểm tra", summary["check_count"])
    columns[1].metric("Phép kiểm tra có ngoại lệ", summary["flagged_check_count"])
    columns[2].metric("Kiểm tra quan trọng có ngoại lệ", summary["critical_check_count"])
    columns[3].metric("Ngoại lệ có chi tiết", summary["exception_count"])

    st.markdown("#### Trạng thái các phép kiểm tra")
    st.dataframe(quality_report, width="stretch", hide_index=True)

    st.markdown("#### Độ mới và phạm vi dữ liệu")
    freshness_view = freshness.copy()
    freshness_view["Từ ngày"] = freshness_view["Từ ngày"].map(format_date)
    freshness_view["Đến ngày"] = freshness_view["Đến ngày"].map(format_date)
    st.dataframe(freshness_view, width="stretch", hide_index=True)

    st.markdown("#### Đối chiếu dữ liệu liên ngân hàng và huy động")
    reconciliation_view = reconciliation.copy()
    for column in ["Tỷ lệ bao phủ (%)", "Độ trễ trung vị (ngày)", "Độ trễ lớn nhất (ngày)"]:
        reconciliation_view[column] = reconciliation_view[column].round(2)
    st.dataframe(reconciliation_view, width="stretch", hide_index=True)

    st.markdown("#### Nhật ký ngoại lệ dữ liệu")
    filter_columns = st.columns(2)
    dataset_options = sorted(exceptions["Bộ dữ liệu"].dropna().unique().tolist()) if not exceptions.empty else []
    severity_options = sorted(exceptions["Mức độ"].dropna().unique().tolist()) if not exceptions.empty else []

    selected_datasets = filter_columns[0].multiselect(
        "Bộ dữ liệu",
        options=dataset_options,
        default=dataset_options,
        key="dq_dataset_filter",
    )
    selected_severity = filter_columns[1].multiselect(
        "Mức độ",
        options=severity_options,
        default=severity_options,
        key="dq_severity_filter",
    )

    exception_view = exceptions.copy()
    if selected_datasets:
        exception_view = exception_view[exception_view["Bộ dữ liệu"].isin(selected_datasets)]
    if selected_severity:
        exception_view = exception_view[exception_view["Mức độ"].isin(selected_severity)]

    if exception_view.empty:
        st.success("Không có ngoại lệ dữ liệu trong phạm vi lọc.")
    else:
        exception_view["Ngày"] = exception_view["Ngày"].map(format_date)
        st.dataframe(exception_view, width="stretch", hide_index=True)

def render_dashboard(
    fx_data: pd.DataFrame,
    deposit_data: pd.DataFrame,
    interbank_data: pd.DataFrame,
    quality_report: pd.DataFrame,
    funding_pressure_data: pd.DataFrame,
    funding_summary: dict[str, object],
) -> None:
    """Dựng dashboard giám sát rủi ro thị trường."""
    bond_monitor_data = load_bond_monitor_data_for_report()
    alert_snapshot = build_current_alert_snapshot(
        fx_data=fx_data,
        interbank_data=interbank_data,
        deposit_data=deposit_data,
        funding_pressure_data=funding_pressure_data,
        bond_monitor_data=bond_monitor_data,
    )
    alert_summary = summarize_alert_console(alert_snapshot)

    render_sidebar()
    render_header()

    render_kpis(fx_data, deposit_data, interbank_data)
    render_monitoring_status(alert_snapshot, quality_report)

    st.divider()

    navigation_sections = [
        "Điều hành",
        "Sổ kinh doanh",
        "Tiền tệ & nguồn vốn",
        "Cảnh báo & kiểm soát",
        "Nhập liệu nghiệp vụ",
    ]
    section_descriptions = {
        "Điều hành": "Tổng quan trạng thái, bản đồ rủi ro và báo cáo giám sát ngày.",
        "Sổ kinh doanh": "Các yếu tố rủi ro thị trường, stress testing, VaR/ES và backtesting.",
        "Tiền tệ & nguồn vốn": "Thị trường liên ngân hàng, áp lực nguồn vốn và lãi suất huy động.",
        "Cảnh báo & kiểm soát": "Cảnh báo, quy trình xử lý ngoại lệ và kiểm soát chất lượng dữ liệu.",
        "Nhập liệu nghiệp vụ": "Các phân hệ cần dữ liệu vị thế, hạn mức hoặc bảng cân đối.",
    }

    st.markdown("#### Điều hướng")
    selected_section = st.radio(
        "Nhóm chức năng",
        options=navigation_sections,
        horizontal=True,
        label_visibility="collapsed",
        key="primary_navigation",
    )
    st.caption(section_descriptions[selected_section])

    if selected_section == "Điều hành":
        tabs = st.tabs(
            [
                "Tổng quan",
                "Bảng điều hành giám sát",
                "Bản đồ rủi ro",
                "Báo cáo ngày",
            ]
        )

        with tabs[0]:
            render_overview_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                alert_snapshot=alert_snapshot,
                alert_summary=alert_summary,
                funding_pressure_data=funding_pressure_data,
                funding_summary=funding_summary,
                quality_report=quality_report,
            )

        with tabs[1]:
            render_control_tower_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                funding_pressure_data=funding_pressure_data,
            )

        with tabs[2]:
            render_risk_heatmap_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                funding_pressure_data=funding_pressure_data,
            )

        with tabs[3]:
            render_daily_report_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                funding_pressure_data=funding_pressure_data,
            )

    elif selected_section == "Sổ kinh doanh":
        tabs = st.tabs(
            [
                "Ngoại hối",
                "Trái phiếu & đường cong lợi suất",
                "Phân rã biến động thị trường",
                "Kiểm tra sức chịu đựng",
                "VaR & ES",
                "Kiểm định lại VaR",
            ]
        )

        with tabs[0]:
            render_fx_tab(fx_data)

        with tabs[1]:
            render_fixed_income_tab()

        with tabs[2]:
            render_market_factor_attribution_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
            )

        with tabs[3]:
            render_stress_test_tab(fx_data, interbank_data, deposit_data)

        with tabs[4]:
            render_var_tab(fx_data, interbank_data)

        with tabs[5]:
            render_backtesting_tab(fx_data, interbank_data)

    elif selected_section == "Tiền tệ & nguồn vốn":
        tabs = st.tabs(
            [
                "Liên ngân hàng",
                "Áp lực nguồn vốn",
                "Lãi suất huy động",
            ]
        )

        with tabs[0]:
            render_interbank_tab(interbank_data)

        with tabs[1]:
            render_funding_pressure_tab(funding_pressure_data, funding_summary)

        with tabs[2]:
            render_deposit_tab(deposit_data)

    elif selected_section == "Cảnh báo & kiểm soát":
        tabs = st.tabs(
            [
                "Trung tâm cảnh báo",
                "Theo dõi xử lý cảnh báo",
                "Kiểm soát dữ liệu",
            ]
        )

        with tabs[0]:
            render_alert_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                funding_pressure_data=funding_pressure_data,
            )

        with tabs[1]:
            render_exception_workflow_tab(
                fx_data=fx_data,
                interbank_data=interbank_data,
                deposit_data=deposit_data,
                funding_pressure_data=funding_pressure_data,
            )

        with tabs[2]:
            render_quality_tab(
                quality_report=quality_report,
                fx_data=fx_data,
                deposit_data=deposit_data,
                interbank_data=interbank_data,
            )

    else:
        tabs = st.tabs(
            [
                "Hạn mức sổ kinh doanh",
                "IRRBB",
                "Thanh khoản",
            ]
        )

        with tabs[0]:
            render_limit_monitor_tab()

        with tabs[1]:
            render_irrbb_tab()

        with tabs[2]:
            render_liquidity_gap_tab()

    st.divider()
    st.caption(f"Ứng viên: {CANDIDATE_NAME} · Market Risk Monitoring Dashboard")

