"""Cấu hình dùng chung cho dashboard giám sát rủi ro thị trường."""

from pathlib import Path

APP_TITLE = "Giám sát rủi ro thị trường"
APP_ICON = "📊"
CANDIDATE_NAME = "Tô Thanh Liêm"
PROJECT_NAME = "Market Risk Monitoring Dashboard"
PAGE_TITLE = f"{APP_TITLE} | {CANDIDATE_NAME}"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "outputs"
WORKFLOW_CASE_FILE = OUTPUT_DIR / "alert_workflow_cases.csv"
WORKFLOW_EVENT_FILE = OUTPUT_DIR / "alert_workflow_events.csv"

FX_FILE = DATA_DIR / "usd_vnd_ohlc_daily.xlsx"
RATES_FILE = DATA_DIR / "vn_money_market_funding_rates.xlsx"
BOND_FILE = DATA_DIR / "vn_gov_bond_yield_curve.xlsx"
BOND_CSV_FILE = DATA_DIR / "vn_gov_bond_yield_curve.csv"
FX_SHEET_NAME = "Table Data"

PLOT_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}

PERIOD_OPTIONS = {
    "1 tháng": 30,
    "3 tháng": 60,
    "6 tháng": 120,
    "1 năm": 250,
    "2 năm": 500,
    "4 năm": 1000,
}

COLOR_ORANGE = "#F37021"
COLOR_BLUE = "#274C77"
COLOR_LIGHT_BLUE = "#7395AE"
COLOR_GREEN = "#278A57"
COLOR_RED = "#C94C4C"
COLOR_YELLOW = "#D89A24"
COLOR_GREY = "#727B86"

CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

[data-testid="stSidebar"] {
    background-color: #f7f8fa;
    border-right: 1px solid #e7e9ed;
}

h1 {
    font-size: 2.20rem !important;
    font-weight: 750 !important;
    letter-spacing: -0.025em;
    margin-bottom: 0.15rem !important;
}

h2 {
    font-size: 1.45rem !important;
    font-weight: 700 !important;
}

h3 {
    font-size: 1.10rem !important;
    font-weight: 680 !important;
}

[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e7e9ed;
    border-radius: 10px;
    padding: 14px 16px;
    min-height: 118px;
}

[data-testid="stMetricLabel"] {
    color: #59636e;
    font-size: 0.86rem;
}

[data-testid="stMetricValue"] {
    font-size: 1.85rem;
    font-weight: 650;
}

button[data-baseweb="tab"] {
    font-size: 0.92rem;
    font-weight: 600;
}

div[role="radiogroup"] {
    gap: 0.35rem;
}

[data-testid="stDataFrame"] {
    border: 1px solid #e7e9ed;
    border-radius: 8px;
}

[data-testid="stDownloadButton"] button,
[data-testid="stBaseButton-secondary"] {
    border-radius: 8px;
}

#MainMenu,
footer {
    visibility: hidden;
}
</style>
"""
