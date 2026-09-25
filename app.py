"""Dashboard giám sát rủi ro thị trường."""

import streamlit as st

from modules.app_config import APP_ICON, CUSTOM_CSS, PAGE_TITLE
from modules.dashboard_views import render_dashboard
from modules.data_loader import load_deposit_data, load_fx_data, load_interbank_data
from modules.data_quality_monitor import build_data_quality_report
from modules.funding_pressure import build_funding_pressure_data, summarize_funding_pressure


def main() -> None:
    """Khởi tạo dữ liệu và dựng dashboard."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    try:
        fx_data = load_fx_data()
        deposit_data = load_deposit_data()
        interbank_data = load_interbank_data()
    except (FileNotFoundError, ValueError, KeyError, OSError) as error:
        st.error("Không thể khởi tạo dữ liệu.")
        st.exception(error)
        st.stop()

    quality_report = build_data_quality_report(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
    )

    funding_pressure_data = build_funding_pressure_data(
        interbank_data=interbank_data,
        deposit_data=deposit_data,
    )
    funding_summary = summarize_funding_pressure(funding_pressure_data)

    render_dashboard(
        fx_data=fx_data,
        deposit_data=deposit_data,
        interbank_data=interbank_data,
        quality_report=quality_report,
        funding_pressure_data=funding_pressure_data,
        funding_summary=funding_summary,
    )


if __name__ == "__main__":
    main()
