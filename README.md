# Market Risk Monitoring Dashboard

**Ứng viên: Tô Thanh Liêm**

## 1. Mục tiêu

Dashboard được xây dựng để minh họa quy trình giám sát rủi ro thị trường theo hướng dữ liệu: theo dõi biến động thị trường, phát hiện bất thường, cảnh báo sớm, kiểm tra sức chịu đựng, đo lường VaR/ES, backtesting, theo dõi áp lực nguồn vốn, kiểm soát chất lượng dữ liệu và quản lý ngoại lệ.

Ứng dụng ưu tiên các chỉ tiêu có thể tính trực tiếp từ dữ liệu thị trường hiện có. Các phân hệ cần dữ liệu vị thế hoặc bảng cân đối chỉ thực hiện tính toán khi người dùng cung cấp dữ liệu đầu vào tương ứng.

## 2. Phạm vi chức năng

- Tổng quan và Bảng điều hành giám sát.
- Bản đồ rủi ro tổng hợp.
- Báo cáo giám sát ngày và xuất Excel.
- Giám sát ngoại hối USD/VND.
- Giám sát đường cong lợi suất Trái phiếu Chính phủ khi có dữ liệu.
- Giám sát thị trường liên ngân hàng.
- Giám sát lãi suất huy động và áp lực nguồn vốn.
- Trung tâm cảnh báo và theo dõi xử lý cảnh báo.
- Historical Stress / Scenario Analysis.
- VaR, Expected Shortfall và Backtesting VaR.
- Phân rã cường độ biến động theo yếu tố thị trường.
- Kiểm soát chất lượng dữ liệu và đối chiếu nguồn.
- Các phân hệ nhập liệu: hạn mức sổ kinh doanh, IRRBB và Liquidity Gap.

## 3. Điều hướng giao diện

Dashboard được chia thành năm khối chức năng để tránh một dải tab quá dài và giữ đúng trình tự giám sát:

1. **Điều hành**: Tổng quan, Bảng điều hành giám sát, Bản đồ rủi ro, Báo cáo ngày.
2. **Sổ kinh doanh**: Ngoại hối, Trái phiếu & đường cong lợi suất, Phân rã biến động thị trường, Kiểm tra sức chịu đựng, VaR & ES, Kiểm định lại VaR.
3. **Tiền tệ & nguồn vốn**: Liên ngân hàng, Áp lực nguồn vốn, Lãi suất huy động.
4. **Cảnh báo & kiểm soát**: Trung tâm cảnh báo, Theo dõi xử lý cảnh báo, Kiểm soát dữ liệu.
5. **Nhập liệu nghiệp vụ**: Hạn mức sổ kinh doanh, IRRBB, Thanh khoản.

Các phân hệ sử dụng dữ liệu thị trường hiện có được tách khỏi các phân hệ cần dữ liệu vị thế, hạn mức hoặc bảng cân đối.

## 4. Dữ liệu đầu vào

Các file chính được đặt tại `data/raw/`:

```text
data/raw/
├── usd_vnd_ohlc_daily.xlsx
├── vn_money_market_funding_rates.xlsx
├── vn_gov_bond_yield_curve.xlsx      # tùy chọn
└── vn_gov_bond_yield_curve.csv       # tùy chọn
```

### USD/VND

Dữ liệu OHLC theo ngày gồm ngày giao dịch, giá mở cửa, cao nhất, thấp nhất và đóng cửa.

### Thị trường tiền tệ và lãi suất huy động

Workbook gồm dữ liệu lãi suất liên ngân hàng theo kỳ hạn, doanh số giao dịch và mặt bằng lãi suất huy động theo nhóm kỳ hạn.

### Đường cong lợi suất TPCP

Phân hệ trái phiếu chấp nhận dữ liệu dạng long hoặc wide với tối thiểu ngày, kỳ hạn và lợi suất.

## 5. Nguyên tắc đo lường

Các cảnh báo thống kê chủ yếu sử dụng rolling Z-score và rolling percentile. Quan sát hiện tại được loại khỏi tập dữ liệu dùng để xác định ngưỡng khi phù hợp nhằm hạn chế look-ahead bias.

Các mức cảnh báo thường được diễn giải theo ba trạng thái:

- **Bình thường**: chưa vượt ngưỡng theo dõi.
- **Theo dõi**: tín hiệu vượt ngưỡng cảnh báo sớm.
- **Cảnh báo**: tín hiệu vượt ngưỡng cao hơn và cần ưu tiên kiểm tra.

Ngưỡng thống kê dùng để phát hiện bất thường, không thay thế hạn mức rủi ro được phê duyệt của một tổ chức cụ thể.

## 6. VaR và Expected Shortfall

Phân hệ VaR/ES hỗ trợ Historical Simulation và Parametric Normal VaR, kèm rolling VaR/ES, tail-risk metrics và exception analysis. Khi chưa có dữ liệu vị thế thực tế, người dùng nhập quy mô phơi nhiễm hoặc độ nhạy để chạy mô phỏng.

Backtesting VaR gồm kiểm tra tần suất exception và tính độc lập của exception theo các kiểm định thống kê được triển khai trong module `backtesting.py`.

## 7. Stress Testing

Ứng dụng hỗ trợ:

- kịch bản tùy chỉnh;
- kịch bản định sẵn;
- kịch bản lịch sử được trích xuất từ các phiên biến động lớn trong dữ liệu.

Stress trên dữ liệu thị trường phản ánh cú sốc của risk factor. Khi không có vị thế danh mục, kết quả không được diễn giải như P&L thực tế của ngân hàng.

## 8. Kiểm soát dữ liệu

Các kiểm tra bao gồm thiếu dữ liệu, ngày trùng, logic OHLC, dữ liệu không hợp lệ, giá trị cần đối chiếu, ngoại lệ thống kê, độ mới của nguồn và đối chiếu giữa chuỗi liên ngân hàng với lãi suất huy động.

Dữ liệu bị gắn cờ được giữ để đối chiếu; các giá trị cần xác minh có thể được loại khỏi một số chỉ báo giám sát nhằm tránh làm méo kết quả.

## 9. Cấu trúc dự án

```text
market-risk-dashboard/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   └── raw/
├── outputs/
└── modules/
    ├── app_config.py
    ├── data_loader.py
    ├── ui_helpers.py
    ├── charts.py
    ├── table_helpers.py
    ├── dashboard_views.py
    ├── alert_engine.py
    ├── fx_risk_monitor.py
    ├── money_market_monitor.py
    ├── deposit_rate_monitor.py
    ├── fixed_income_monitor.py
    ├── funding_pressure.py
    ├── stress_test.py
    ├── historical_stress.py
    ├── var_engine.py
    ├── tail_risk_monitor.py
    ├── backtesting.py
    ├── risk_alert_console.py
    ├── exception_workflow.py
    ├── market_factor_attribution.py
    ├── risk_heatmap.py
    ├── control_tower.py
    ├── daily_report.py
    ├── data_quality_monitor.py
    ├── limit_monitor.py
    ├── irrbb_monitor.py
    └── liquidity_gap.py
```

## 10. Khởi chạy

Tại thư mục dự án:

```powershell
.venv\Scripts\activate
streamlit run app.py
```

Nếu cần xóa cache:

```powershell
streamlit cache clear
streamlit run app.py
```

## 11. Phạm vi sử dụng

Dashboard là sản phẩm phân tích và minh họa quy trình giám sát rủi ro thị trường. Kết quả phụ thuộc vào chất lượng, phạm vi và thời điểm cập nhật của dữ liệu đầu vào. Các phân hệ hạn mức, IRRBB và Liquidity Gap cần dữ liệu nghiệp vụ phù hợp trước khi có thể diễn giải như chỉ tiêu quản trị của một danh mục hoặc tổ chức cụ thể.

## 12. Triển khai public

Bản release đã chuẩn bị sẵn `requirements.txt` và `.streamlit/config.toml`. Với Streamlit Community Cloud, đặt toàn bộ project trong một GitHub repository, chọn `app.py` làm entrypoint và dùng Python 3.12 khi deploy.

Chi tiết xem `DEPLOYMENT.md`.

### Lưu ý trước khi public dữ liệu

Hai workbook trong `data/raw/` được đóng gói để dashboard có thể chạy ngay. Trước khi chuyển repository sang chế độ công khai, cần xác nhận quyền tái phân phối dữ liệu nguồn. Nếu không muốn public file dữ liệu, có thể giữ repository private hoặc thay bằng dữ liệu công khai có quyền sử dụng phù hợp.

## 13. Phiên bản release

- Ứng viên: **Tô Thanh Liêm**
- Entrypoint: `app.py`
- Giao diện: Streamlit
- Python khuyến nghị khi deploy: 3.12
- Dữ liệu TPCP: tùy chọn; dashboard vẫn chạy khi chưa có file đường cong lợi suất.
