MARKET RISK DASHBOARD - REFACTOR NO MOCK INTERNAL DATA

Thay các file sau trong project hiện tại:
- app.py
- modules/limit_monitor.py
- modules/irrbb_monitor.py
- modules/liquidity_gap.py

Giữ nguyên:
- modules/alert_engine.py
- modules/stress_test.py
- modules/var_engine.py
- modules/backtesting.py
- modules/funding_pressure.py
- modules/__init__.py
- data/raw/*.xlsx

Điểm thay đổi:
1. Các tab dựa trên dữ liệu thị trường hiện có được đưa lên trước.
2. Ba tab thiếu dữ liệu nội bộ được chuyển xuống cuối và gắn nhãn "Mô phỏng".
3. Không tự sinh số vị thế/hạn mức, RSA/RSL, duration, cash inflow/outflow hay liquidity buffer.
4. Ba tab mô phỏng chỉ chạy sau khi người dùng nhập hoặc tải CSV/XLSX.
5. Có nút tải template trống ngay trong từng tab.

Chạy lại:
streamlit cache clear
streamlit run app.py
