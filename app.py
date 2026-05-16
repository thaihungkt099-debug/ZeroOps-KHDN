from flask import Flask, request, Response
from functools import wraps
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# === THIẾT LẬP TÀI KHOẢN & MẬT KHẨU TRUY CẬP ===
USERNAME = "khdn"
PASSWORD = "bidv_secure"  # Bạn có thể đổi mật khẩu này theo ý muốn

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
    'Hệ thống nội bộ. Vui lòng nhập tài khoản và mật khẩu để truy cập Dashboard.', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# === LINK CSV CHUẨN CỦA BẠN ===
URL_GOOGLE_SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQFkRkojGZsUqAnzn9-sQEnH4EPaUo4F-7v4_CoNQGSmn0vtPE0Dyk6nEYsD6JS1LtQXor0FrDdLd_/pub?output=csv"

# === DANH SÁCH 12 ANH EM PHÒNG KHDN ===
DANH_SACH_CHUAN = [
    "Châu Hoàng Anh", "Nguyễn Thái Hưng", "Trần Đình Tuấn", 
    "Ngô Ngọc Phúc", "Mai Quốc Hiếu", "Nguyễn Hoàng Nam", 
    "Mai Xuân Dung", "Trần Thị Mỹ Phương", "Trần Thị Quỳnh Anh", 
    "Ngũ Vạn Đăng", "Cán bộ 11", "Cán bộ 12" 
]

@app.route('/')
@requires_auth  # Bật tính năng khóa mật khẩu
def home():
    try:
        df_raw = pd.read_csv(URL_GOOGLE_SHEET, on_bad_lines='skip', dtype=str)
        cols = df_raw.columns.tolist()

        def tim_cot(tu_khoa, vi_tri_du_phong):
            for col in cols:
                if tu_khoa.lower() in str(col).lower(): return col
            if vi_tri_du_phong < len(cols): return cols[vi_tri_du_phong]
            return cols[-1] 

        col_ten = tim_cot('tên cán bộ', 1)
        col_cty = tim_cot('tên công ty', 5)
        col_noidung = tim_cot('nội dung chính', 9)
        col_thoigian = tim_cot('thời gian ocr', 18)
        col_diadiem = tim_cot('địa điểm ocr', 19)

        if 'Thời Gian OCR' not in cols:
            return "<h2>Google đang đồng bộ dữ liệu, vui lòng F5 lại sau 1 phút...</h2>"

        # --- XỬ LÝ BẢNG 1: NHẬT KÝ CHI TIẾT ---
        df_log = df_raw[[col_ten, col_cty, col_noidung, col_thoigian, col_diadiem]].copy()
        df_log.columns = ['Cán Bộ', 'Doanh Nghiệp', 'Nội Dung Làm Việc', 'Thời Gian (Mắt Thần AI)', 'Địa Điểm (Mắt Thần AI)']
        df_log = df_log.dropna(subset=['Cán Bộ'])
        df_log = df_log.fillna("Chưa nhập") 
        df_log = df_log.iloc[::-1]
        html_table_log = df_log.to_html(classes='data-table', index=False, escape=False)

        # --- XỬ LÝ BẢNG 2: TỔNG HỢP KPI ---
        df_kpi = df_raw[[col_ten, col_thoigian]].copy()
        df_kpi.columns = ['NhanVien', 'ThoiGianOCR']
        df_kpi = df_kpi.dropna(subset=['NhanVien'])
        df_kpi['NhanVien'] = df_kpi['NhanVien'].str.strip().str.title()

        def xac_dinh_tuan(time_str):
            if pd.isna(time_str) or "Không" in str(time_str) or "Chưa" in str(time_str): return "Tuần ?"
            try:
                date_str = str(time_str).split(' at ')[0].strip()
                date_obj = datetime.strptime(date_str, "%d %b %Y")
                return f"Tuần {date_obj.isocalendar()[1]}"
            except Exception: return "Tuần ?"

        df_kpi['Tuan'] = df_kpi['ThoiGianOCR'].apply(xac_dinh_tuan)
        summary = df_kpi.groupby(['NhanVien', 'Tuan']).size().reset_index(name='SoLuotGap')
        pivot_df = summary.pivot(index='NhanVien', columns='Tuan', values='SoLuotGap').fillna(0)
        
        pivot_df = pivot_df.reindex(DANH_SACH_CHUAN).fillna(0)
        pivot_df.reset_index(inplace=True)
        pivot_df.rename(columns={'index': 'Nhân Sự'}, inplace=True)

        def tinh_diem_tru(row):
            diem_tru = 0
            for col in pivot_df.columns:
                if 'Tuần' in str(col) and col != "Tuần ?":
                    if int(row[col]) < 3: diem_tru += 1
            return -diem_tru 

        pivot_df['Tổng Điểm Trừ KPI'] = pivot_df.apply(tinh_diem_tru, axis=1)
        html_table_kpi = pivot_df.to_html(classes='data-table kpi-table', index=False, escape=False, float_format=lambda x: f'{int(x)} lượt')

        # --- XUẤT GIAO DIỆN KÉP ---
        html_template = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <title>Zero-Ops Dashboard</title>
            <meta http-equiv="refresh" content="60">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; padding: 20px; }}
                .container {{ max-width: 1400px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                h1 {{ text-align: center; color: #005F56; font-size: 28px; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 1px; }}
                h2 {{ color: #1f2937; font-size: 20px; border-left: 5px solid #005F56; padding-left: 10px; margin-top: 40px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; box-shadow: 0 0 10px rgba(0,0,0,0.02); }}
                .data-table th, .data-table td {{ border: 1px solid #dee2e6; padding: 12px; text-align: left; }}
                .data-table th {{ background-color: #005F56; color: white; }}
                .data-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .data-table tr:hover {{ background-color: #f1f8f6; }}
                .kpi-table th {{ background-color: #2c3e50; text-align: center; }}
                .kpi-table td {{ text-align: center; font-weight: 500; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>HỆ THỐNG QUẢN TRỊ TƯƠNG TÁC KHDN</h1>
                
                <h2>1. BẢNG TỔNG HỢP KPI THEO TUẦN</h2>
                <p style="color: #6c757d; font-size: 14px;"><i>* Quy định: Cán bộ thực hiện dưới 3 lượt gặp KH/tuần sẽ bị trừ 1 điểm KPI. Dữ liệu chốt tự động.</i></p>
                {html_table_kpi}

                <h2>2. NHẬT KÝ THỰC ĐỊA CHI TIẾT (KIỂM CHỨNG BỞI AI)</h2>
                <p style="color: #6c757d; font-size: 14px;"><i>* Dữ liệu bóc tách Real-time từ hình ảnh Timestamp. Tự động làm mới mỗi 60 giây.</i></p>
                {html_table_log}
            </div>
        </body>
        </html>
        """
        return html_template
        
    except Exception as e:
        return f"<h2>Đang có lỗi kỹ thuật: {e}</h2>"

if __name__ == '__main__':
    app.run(debug=True)
