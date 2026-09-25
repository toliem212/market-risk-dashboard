# Triển khai Streamlit Community Cloud

## Chuẩn bị GitHub

1. Tạo repository mới trên GitHub.
2. Đưa toàn bộ nội dung thư mục dự án vào root của repository.
3. Giữ `app.py` và `requirements.txt` ở root.
4. Kiểm tra hai file dữ liệu mặc định nằm trong `data/raw/`.
5. Không commit `.streamlit/secrets.toml`, `.venv/` hoặc các file trạng thái trong `outputs/`.

## Triển khai

1. Đăng nhập Streamlit Community Cloud bằng GitHub.
2. Kết nối repository cần triển khai.
3. Chọn entrypoint `app.py`.
4. Trong Advanced settings, chọn Python 3.12.
5. Không cần khai báo secrets cho phiên bản dashboard hiện tại.
6. Deploy và kiểm tra log build nếu ứng dụng không khởi động.

## Dependencies

Repository dùng duy nhất `requirements.txt` làm dependency file. Các thư viện cần thiết gồm Streamlit, pandas, NumPy, Plotly và openpyxl. Không cần `packages.txt` vì project không dùng dependency hệ điều hành bên ngoài Python.

## Lưu ý về trạng thái cảnh báo

`outputs/alert_workflow_cases.csv` và `outputs/alert_workflow_events.csv` là trạng thái cục bộ của workflow. Khi chạy trên môi trường cloud, không nên coi filesystem của ứng dụng là kho lưu trữ bền vững. Nếu cần sử dụng workflow thực tế lâu dài, nên chuyển phần lưu trạng thái sang một database hoặc dịch vụ lưu trữ phù hợp.
