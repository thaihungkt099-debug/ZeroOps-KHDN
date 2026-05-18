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
