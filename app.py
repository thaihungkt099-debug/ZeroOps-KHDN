from flask import Flask
import pandas as pd

app = Flask(__name__)

# === DÁN LINK CSV CỦA BẠN VÀO ĐÂY ===
URL_GOOGLE_SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQFkRkojGZsUqAnzn9-sQEnH4EPaUo4F-7v4_CoNQGSmn0vtPE0Dyk6nEYsD6JS1LtQXor0FrDdLd_/pub?output=csv"

@app.route('/')
def home():
    try:
        # Ép Google tải bản mới nhất, bỏ qua các dòng lỗi
        df_raw = pd.read_csv(URL_GOOGLE_SHEET, on_bad_lines='skip', dtype=str)
        cols = df_raw.columns.tolist()

        # CƠ CHẾ TỰ CHỮA LÀNH: Dò tìm tên cột bằng từ khóa thay vì đếm số thứ tự
        def tim_cot(tu_khoa, vi_tri_du_phong):
            for col in cols:
                if tu_khoa.lower() in str(col).lower():
                    return col
            # Nếu Google chưa kịp update cột mới, báo lỗi nhẹ nhàng thay vì sập web
            if vi_tri_du_phong < len(cols): return cols[vi_tri_du_phong]
            return cols[-1] 

        # Trích xuất 5 cột quan trọng nhất dựa trên từ khóa trong tiêu đề
        col_ten = tim_cot('tên cán bộ', 1)
        col_cty = tim_cot('tên công ty', 5)
        col_noidung = tim_cot('nội dung chính', 9)
        col_thoigian = tim_cot('thời gian ocr', 18)
        col_diadiem = tim_cot('địa điểm ocr', 19)

        # Kiểm tra xem Google đã nhả cột OCR ra chưa
        if 'Thời Gian OCR' not in cols:
            return f"""
            <div style="font-family: sans-serif; padding: 20px;">
                <h2 style="color: #d9534f;">Google đang đồng bộ dữ liệu...</h2>
                <p>Google Sheets đang bị trễ nhịp và chưa đẩy 3 cột OCR mới ra link CSV.</p>
                <p><b>Cách xử lý:</b> Bạn hãy vào Google Sheets > Tệp > Chia sẻ > Công bố lên web > Bấm <b>Dừng công bố</b>, sau đó bấm <b>Công bố lại</b> để ép nó làm mới nhé!</p>
                <p><i>Các cột hiện tại hệ thống đọc được: {cols}</i></p>
            </div>
            """

        # === QUY TRÌNH DỌN DẸP CHUẨN ===
        # 1. Ráp bảng dữ liệu sạch
        df = df_raw[[col_ten, col_cty, col_noidung, col_thoigian, col_diadiem]].copy()
        df.columns = ['Cán Bộ', 'Doanh Nghiệp', 'Nội Dung Làm Việc', 'Thời Gian (Mắt Thần AI)', 'Địa Điểm (Mắt Thần AI)']
        
        # 2. Lọc bỏ các dòng không có tên Cán bộ (dòng rác)
        df = df.dropna(subset=['Cán Bộ'])
        
        # 3. Quét sạch lỗi NaN, thay bằng chữ "Chưa nhập" cho đẹp mắt
        df = df.fillna("Chưa nhập") 
        
        # 4. Đảo ngược bảng (Tin mới nhất nổi lên trên cùng)
        df = df.iloc[::-1]
        # ==============================

        # Đóng gói HTML
        html_table = df.to_html(classes='data-table', index=False, escape=False)
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <title>Nhật Ký Tương Tác Khách Hàng - Realtime</title>
            <meta http-equiv="refresh" content="60">
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; }}
                .container {{ max-width: 1400px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                h2 {{ color: #005F56; border-bottom: 3px solid #005F56; padding-bottom: 10px; text-transform: uppercase; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                .data-table th, .data-table td {{ border: 1px solid #e0e0e0; padding: 12px; text-align: left; }}
                .data-table th {{ background-color: #005F56; color: white; position: sticky; top: 0; }}
                .data-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .data-table tr:hover {{ background-color: #f1f8f6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Cập Nhật Tương Tác Doanh Nghiệp - Kiểm Chứng Timestamp</h2>
                <p><i>* Dữ liệu được AI bóc tách trực tiếp từ hình ảnh thực địa của anh em Phòng KHDN. Tự động làm mới mỗi phút.</i></p>
                {html_table}
            </div>
        </body>
        </html>
        """
        return html_template
        
    except Exception as e:
        return f"<h2>Đang có lỗi kỹ thuật: {e}</h2>"

if __name__ == '__main__':
    app.run(debug=True)