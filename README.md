# LogiGift AI — MVP
## AI in Business Season 3 · Bảng A

### Mô tả
MVP mô phỏng hệ thống LogiGift AI tối ưu hóa xung đột đơn hàng và phân bổ quà tặng thương mại điện tử, tích hợp dưới dạng **popup thông minh trong luồng checkout** của sàn TMĐT.

---

### Cài đặt & Chạy

```bash
pip install -r requirements.txt
python app.py
# Truy cập: http://localhost:5001
```

**Để kích hoạt Claude AI (Negotiation Popup):**
```bash
export ANTHROPIC_API_KEY=your_key_here
python app.py
```
Nếu không có API key, hệ thống tự động dùng fallback text.

---

### Cấu trúc thư mục

```
logigift/
├── app.py              # Flask backend + API routes
├── logic_engine.py     # AI Logic Engine (4 tầng)
├── requirements.txt
├── data/
│   └── mock_db.json    # Mock database (sản phẩm, quà, khách hàng, kho)
└── templates/
    └── index.html      # Full-stack web UI
```

---

### Kiến trúc AI (4 Tầng)

#### Tầng 0 — Đồng bộ Real-time
- Event-driven data sync (mock)
- **Confidence Score**: Chấm điểm tin cậy từng luồng dữ liệu (tồn kho, backlog kho)
- Graceful Degradation khi data không đáng tin

#### Tầng 1 — Data Aggregation
Thu thập 4 luồng: **ATP** (tồn kho/ngân sách quà), **CTP** (năng lực kho/backlog), **PTP** (chi phí/biên lợi nhuận), **Customer LTV** (hạng VIP).

#### Tầng 2 — AI Core (Weighted Scoring Model)
- **Bước 1 - CSP**: Lập không gian kịch bản khả thi (Tách/Gộp/Đổi quà/Voucher/Cross-ship)
- **Bước 2 - XGBoost logic**: Tính ETA thực tế theo backlog từng kho
- **Bước 3 - K-Means LTV + Linear Programming**: Tính điểm hòa vốn, duyệt bù lỗ ship cho VIP
- **Bước 4 - Multi-Armed Bandit (MAB)**: Score = f(Tốc độ × Lợi nhuận × LTV)

**Risk Controls:**
- 🛡️ Confidence Score — tước quyền tự quyết khi data lệch
- 🛡️ ROI Guard — loại kịch bản gây lỗ
- 🛡️ Uncertain Flag — hạ trọng số data dự đoán  
- 🛡️ Human-in-the-loop — chuyển CSKH khi ambiguous

#### Tầng 3 — Output & UX
- **Negotiation Popup**: Claude API (claude-sonnet-4) sinh text thuyết phục cá nhân hóa theo tier khách
- **Admin Dashboard**: Log real-time, Uncertain Flag alert
- **Smooth Checkout**: Xử lý trong suốt với khách VIP

---

### Công nghệ sử dụng

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask 3.0 |
| AI Engine | Rule-based Weighted Scoring (CSP, XGBoost logic, K-Means LTV, MAB) |
| GenAI Popup | Anthropic Claude API (claude-sonnet-4-20250514) |
| Frontend | Vanilla HTML/CSS/JS (Dark mode, responsive) |
| Database | Mock JSON (mô phỏng WMS/ERP) |

---


1. **Chọn khách VIP** (Nguyễn Minh Khoa)
2. **Thêm vào giỏ**: Áo khoác (Kho HN) + Giày Nike (Kho HCM) → tạo multi-warehouse
3. **Chọn quà**: "Quà Vớ" (stock = 0, hết hàng) → tạo conflict
4. **Nhấn Thanh toán** → xem AI Engine chạy 4 tầng
5. **Xem Negotiation Popup** do Claude AI sinh ra
6. **Chấp nhận phương án** → xem Admin Dashboard cập nhật

---

### ROI Logic — Delta Value

- **Không có AI**: Lỗi quà → Chặn checkout → Khách hủy đơn → Sàn mất 100% hoa hồng (5-8%)
- **Có LogiGift AI**: Đổi quà linh hoạt → Khách chốt đơn → Commission Rescued
- **Ví dụ**: 100k đơn rớt/ngày × 200k AOV × 5% phí = **1 tỷ VNĐ/ngày** được bảo vệ
