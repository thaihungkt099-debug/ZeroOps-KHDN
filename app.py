from flask import Flask, request, Response
from functools import wraps
import pandas as pd
from datetime import datetime
import urllib.parse
import urllib.request

app = Flask(__name__)

# === THIẾT LẬP TÀI KHOẢN & MẬT KHẨU TRUY CẬP WEB ===
USERNAME = "khdn"
PASSWORD = "bidv_secure"

# === THÔNG TIN CẤU HÌNH TELEGRAM BOT ===
TELEGRAM_TOKEN = "8738016733:AAG9FYpOLhpJ8XR64os8t3NNtX-54YslpJE"
TELEGRAM_CHAT_ID = "8753418113" 

# Chìa khóa bí mật để Cron-job kích hoạt
SECRET_CRON_KEY = "v60-auto-2026" 

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response('Hệ thống nội bộ. Vui lòng nhập tài khoản và mật khẩu.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

URL_GOOGLE_SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQFkRkojGZsUqAnzn9-sQEnH4EPaUo4F-7v4_CoNQGSmn0vtPE0Dyk6nEYsD6JS1LtQXor0FrDdLd_/pub?output=csv"
DANH_SACH_CHUAN = ["Châu Hoàng Anh", "Nguyễn Thái Hưng", "Trần Đình Tuấn", "Ngô Ngọc Phúc", "Mai Quốc Hiếu", "Nguyễn Hoàng Nam", "Mai Xuân Dung", "Trần Thị Mỹ Phương", "Trần Thị Quỳnh Anh", "Ngũ Vạn Đăng", "Cán bộ 11", "Cán bộ 12"]

def lay_du_lieu():
    df_raw = pd.read_csv(URL_GOOGLE_SHEET, on_bad_lines='skip', dtype=str)
    cols = df_raw.columns.tolist()
    def tim_cot(tu_khoa, vi_tri_du_phong):
        for col in cols:
            if tu_khoa.lower() in str(col).lower(): return col
        if vi_tri_du_phong < len(cols): return cols[vi_tri_du_phong]
        return cols[-1] 
        
    col_ten = tim_cot('tên cán bộ', 1)
    col_thoigian = tim_cot('thời gian ocr', 18)
    
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
    pivot_df.rename(columns={'NhanVien': 'Nhân Sự', 'index': 'Nhân Sự'}, inplace=True)
    return pivot_df

# === API ẨN GỬI CẢNH BÁO QUA TELEGRAM ===
@app.route('/api/gui-canh-bao')
def gui_canh_bao():
    key = request.args.get('key')
    if key != SECRET_CRON_KEY:
        return "Từ chối truy cập (Sai mã bảo mật)", 403
    
    try:
        pivot_df = lay_du_lieu()
        tuan_hien_tai = f"Tuần {datetime.now().isocalendar()[1]}"
        danh_sach_tre = []

        if tuan_hien_tai in pivot_df.columns:
            for _, row in pivot_df.iterrows():
                if int(row[tuan_hien_tai]) < 3:
                    danh_sach_tre.append(row['Nhân Sự'])
        else:
            danh_sach_tre = DANH_SACH_CHUAN 
            
        noi_dung = f"🚨 *[CẢNH BÁO KPI] Báo cáo tương tác KHDN - {tuan_hien_tai}*\n\n"
        noi_dung += "Hệ thống AI ghi nhận cán bộ chưa đạt đủ KPI (3 lượt/tuần):\n"
        for ten in danh_sach_tre:
            noi_dung += f"➖ {ten}\n"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({'chat_id': TELEGRAM_CHAT_ID, 'text': noi_dung, 'parse_mode': 'Markdown'}).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        
        with urllib.request.urlopen(req) as response:
            response.read()
            
        return "Đã gửi thành công tin nhắn báo cáo qua Telegram!", 200
    except Exception as e:
        return f"<h3>Lỗi hệ thống trong hàm gửi Telegram: {e}</h3>", 500

# === GIAO DIỆN WEB VÀ BẢNG THÔNG TIN MỚI ===
@app.route('/')
@requires_auth
def home():
    try:
        df_raw = pd.read_csv(URL_GOOGLE_SHEET, on_bad_lines='skip', dtype=str)
        cols = df_raw.columns.tolist()
        
        def tim_cot(tu_khoa, vi_tri_du_phong):
            for col in cols:
                if tu_khoa.lower() in str(col).lower(): return col
            if vi_tri_du_phong < len(cols): return cols[vi_tri_du_phong]
            return cols[-1] 

        # Trích xuất chính xác các trường dữ liệu theo Form mới cập nhật
        col_ten = tim_cot('tên cán bộ', 1)
        col_anh = tim_cot('upload ảnh', 2)
        col_cty = tim_cot('công ty', 3)
        col_lien_he = tim_cot('liên hệ', 4)
        col_muc_tieu = tim_cot('mục tiêu', 5)
        col_hanh_dong = tim_cot('hành động', 6)
        col_thoi_han = tim_cot('thời hạn', 7)
        col_ghi_chu = tim_cot('ghi chú', 8)
        col_thoigian = tim_cot('thời gian ocr', 18)
        col_diadiem = tim_cot('địa điểm ocr', 19)

        df_log = df_raw.copy()
        df_log = df_log.dropna(subset=[col_ten])
        df_log = df_log.fillna("")
        df_log = df_log.iloc[::-1] # Đẩy các tương tác mới nhất lên đầu bảng

        table_rows_html = ""
        for _, row in df_log.iterrows():
            ten = str(row.get(col_ten, "Chưa nhập")).strip().title()
            anh = str(row.get(col_anh, ""))
            cty = str(row.get(col_cty, "Chưa xác định"))
            lien_he = str(row.get(col_lien_he, "-"))
            muc_tieu = str(row.get(col_muc_tieu, "Chưa có"))
            hanh_dong = str(row.get(col_hanh_dong, "Không"))
            thoi_han = str(row.get(col_thoi_han, "-"))
            ghi_chu = str(row.get(col_ghi_chu, "-"))
            thoigian_ai = str(row.get(col_thoigian, "Chưa có data"))
            diadiem_ai = str(row.get(col_diadiem, "Đang xử lý GPS"))

            # Tạo nút xem ảnh thu nhỏ trực quan
            icon_anh = f'<a href="{anh}" target="_blank" style="text-decoration:none; margin-left:5px;" title="Xem ảnh thực địa">📷</a>' if anh.startswith('http') else ""

            table_rows_html += f"""
            <tr>
                <td><strong>{ten}</strong></td>
                <td><span style="color: #005F56; font-weight: 600;">{cty}</span></td>
                <td><small style="color: #666;">{lien_he}</small></td>
                <td><span style="background: #e0f2f1; color: #004d40; padding: 4px 8px; border-radius: 12px; font-size: 12px;">{muc_tieu}</span></td>
                <td><span style="font-size: 13px;">{hanh_dong}</span></td>
                <td><span style="color: #d93025; font-weight: bold; font-size: 13px;">{thoi_han}</span></td>
                <td>
                    <small style="line-height: 1.5; display: block;">
                        📅 {thoigian_ai}{icon_anh}<br>
                        📍 <span style="color: #5f6368;">{diadiem_ai}</span>
                    </small>
                </td>
                <td>
                    <details style="cursor: pointer; font-size: 13px;">
                        <summary style="color: #005F56; font-weight: 500;">Xem chi tiết</summary>
                        <p style="margin-top: 5px; color: #333; white-space: pre-wrap;">{ghi_chu}</p>
                    </details>
                </td>
            </tr>
            """

        html_table_log = f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 12%;">Cán Bộ</th>
                    <th style="width: 16%;">Doanh Nghiệp</th>
                    <th style="width: 12%;">Người Liên Hệ</th>
                    <th style="width: 12%;">Mục Tiêu</th>
                    <th style="width: 13%;">Hành Động Tiếp Theo</th>
                    <th style="width: 9%;">Deadline</th>
                    <th style="width: 16%;">Thời Gian & Địa Điểm (AI)</th>
                    <th style="width: 10%;">Ghi Chú</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
        """

        # Tính toán và kết xuất Bảng 1 (Tổng hợp điểm KPI tuần)
        pivot_df = lay_du_lieu()
        def tinh_diem_tru(row):
            diem_tru = 0
            for col in pivot_df.columns:
                if 'Tuần' in str(col) and col != "Tuần ?":
                    if int(row[col]) < 3: diem_tru += 1
            return -diem_tru 
            
        pivot_df['Tổng Điểm Trừ KPI'] = pivot_df.apply(tinh_diem_tru, axis=1)
        html_table_kpi = pivot_df.to_html(classes='data-table kpi-table', index=False, escape=False, float_format=lambda x: f'{int(x)} lượt')

        html_template = f"""
        <!DOCTYPE html>
        <html lang='vi'>
        <head>
            <meta charset='UTF-8'>
            <title>Zero-Ops Dashboard</title>
            <meta http-equiv='refresh' content='60'>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #e9ecef; padding: 20px; }} 
                .container {{ max-width: 1400px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }} 
                h1 {{ text-align: center; color: #005F56; font-size: 28px; margin-bottom: 30px; }} 
                h2 {{ color: #1f2937; font-size: 20px; border-left: 5px solid #005F56; padding-left: 10px; margin-top: 40px; }} 
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }} 
                .data-table th, .data-table td {{ border: 1px solid #dee2e6; padding: 12px; text-align: left; vertical-align: top; }} 
                .data-table th {{ background-color: #005F56; color: white; position: sticky; top: 0; }} 
                .kpi-table th, .kpi-table td {{ text-align: center; vertical-align: middle; }}
                details > summary {{ list-style-type: none; }}
                details > summary::-webkit-details-marker {{ display: none; }}
                tr:hover {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class='container'>
                <h1>HỆ THỐNG QUẢN TRỊ TƯƠNG TÁC KHDN</h1>
                <h2>1. BẢNG TỔNG HỢP KPI THEO TUẦN</h2>
                {html_table_kpi}
                <h2>2. NHẬT KÝ THỰC ĐỊA CHI TIẾT (KIỂM CHỨNG BỞI AI)</h2>
                <div style="overflow-x: auto; max-height: 600px;">
                    {html_table_log}
                </div>
            </div>
        </body>
        </html>
        """
        return html_template
    except Exception as e:
        return f"<h2>Đang có lỗi kỹ thuật ở giao diện hiển thị: {e}</h2>", 500

if __name__ == '__main__':
    app.run(debug=True)
