'''
Oi Thy, lõi AI tui xong rồi nha. Tui giải thích sơ cách Thy xài cái hàm của tui để vẽ UI nha:


1. Khúc Thy gọi AI (Input):

- Lúc người ta bấm nút Thanh toán, Thy lấy 3 cái mã từ dropdown rồi gọi hàm tui: ket_qua = process_checkout(user_id, warehouse_id, gift_id)

- Nhớ import cái hàm này từ file logic_engine.py vô nha.

2. Khúc AI trả về (Output):

- Cái biến ket_qua nó sẽ là 1 cái object JSON (hay Dict). Nó có mấy trường quan trọng nhất mà Thy cần để vẽ giao diện:

    + ui_action: Tui trả về 3 loại (Thy lấy cái này làm if/elif để vẽ luồng nè):

        "smooth_checkout": Tồn kho đủ hết hoặc tui tự bù ship ngầm rồi. Khúc này Thy cho bắn pháo hoa, chốt đơn suôn sẻ, không hiện popup hỏi han gì hết.

        "upsell": Lỡ hết hàng mà khách thường, tui sẽ gợi ý mua thêm. Khúc này Thy bật popup lên, hiện số tiền cần mua thêm ở trường "upsell_amount".

        "negotiation_ui" hoặc "fallback": Mấy ca hết hàng phải đền bù. Thy cũng bật cái popup lên.

    + headline & detail: Tui viết sẵn text rồi, Thy cứ lấy in thẳng ra tiêu đề với mô tả popup.

    + offer_options: (Quan trọng nè!) Nó là 1 cái list (danh sách) các lựa chọn ưu tiên tui đã sắp xếp từ trên xuống dưới (cái xịn nhất nằm đầu). Thy cứ dùng vòng lặp for lôi từng cái ra làm thành mấy cái nút bấm (button) cho người ta chọn nghen. Nút đầu tiên Thy tô màu nổi lên xíu (primary button) để tạo hiệu ứng chim mồi nha.

Đó, logic chỉ có nhiêu đó thuiiii

LƯU Ý: Trong cái file logic_engine.py tui gửi, cái cục data DB ở trên cùng với cái đoạn if __name__ == "__main__": ở tuốt dưới cùng là để tui test chay thôi nha. Lúc Thy ráp code thì nhớ xóa cái đoạn test ở dưới cùng i
'''



import json

# DATABASE

DB = {
    "users": {
        "USR-VIP-001": {"name": "Nguyễn Thành Long", "membership_rank": "VIP"},
        "USR-NOR-002": {"name": "Đặng Văn Hùng",     "membership_rank": "Normal"}
    },
    "warehouses": {
        "WH-HCM":    {"location": "TP.HCM",  "gift_stock_A": 50, "gift_stock_B": 0,   "gift_stock_C": 0},
        "WH-DANANG": {"location": "Đà Nẵng", "gift_stock_A": 50, "gift_stock_B": 100, "gift_stock_C": 0}
    },
    "products": {
        "GIFT_A": {"name": "Túi Tote (dồi dào)"},
        "GIFT_B": {"name": "Mặt nạ (HCM hết, ĐN còn)"},
        "GIFT_C": {"name": "Bình nước (toàn quốc hết)"}
    },
    "upsell_threshold": 50000
}


# ── TẦNG 1: DATA ACCESS ───────────────────────────────────────────
def fetch_wms_data(user_id, warehouse_id, gift_id):
    user          = DB["users"].get(user_id, {})
    current_wh    = DB["warehouses"].get(warehouse_id, {})
    gift          = DB["products"].get(gift_id, {})
    stock_key     = f"gift_stock_{gift_id[-1]}"
    current_stock = current_wh.get(stock_key, 0)
    return user, current_wh, gift, stock_key, current_stock


# ── TẦNG 2: MAB SCORING ───────────────────────────────────────────
def score_option(option_type, is_vip):
    """
    Trọng số thay đổi theo hạng khách:
    - VIP  : ưu tiên giữ chân (LTV 0.6)
    - Normal: ưu tiên tốc độ + lợi nhuận (0.5/0.5)
    """
    w_speed, w_profit, w_ltv = (0.2, 0.2, 0.6) if is_vip else (0.5, 0.5, 0.0)
    raw_scores = {
        "bu_ship":     (0.5, 0.4, 1.0),
        "voucher_100k":(1.0, 0.1, 0.9),
        "voucher_50k": (1.0, 0.6, 0.5),
    }
    s, p, l = raw_scores.get(option_type, (0, 0, 0))
    return round(s * w_speed + p * w_profit + l * w_ltv, 2)


def generate_and_rank_options(backup_wh, is_vip):
    options = []
    if backup_wh:
        options.append({
            "action_id": "bu_ship",
            "text":  f"🚚 Ship chéo từ {backup_wh['location']}",
            "score": score_option("bu_ship", is_vip)
        })
    voucher_type = "voucher_100k" if is_vip else "voucher_50k"
    options.append({
        "action_id": voucher_type,
        "text":  "🎟️ Voucher VIP 100k" if is_vip else "🎟️ Voucher 50k",
        "score": score_option(voucher_type, is_vip)
    })
    return sorted(options, key=lambda x: x["score"], reverse=True)


# ── TẦNG 3: PLATFORM LOGIC ────────────────────────────────────────
def analyze_platform_logic(user, current_wh_id, stock_key, current_stock):
    is_vip = user.get("membership_rank") == "VIP"

    # Quà còn hàng → checkout ngay
    if current_stock > 0:
        return "SUCCESS", None, [], is_vip

    # Tìm kho backup còn quà
    backup_wh = None
    for w_id, w_data in DB["warehouses"].items():
        if w_id != current_wh_id and w_data.get(stock_key, 0) > 0:
            backup_wh = w_data
            break

    # Không có kho nào còn quà → Fallback ngay, không cần rank
    if not backup_wh:
        ranked = generate_and_rank_options(None, is_vip)  # chỉ có voucher
        return "FALLBACK", None, ranked, is_vip

    # Có kho backup → rank các phương án
    ranked = generate_and_rank_options(backup_wh, is_vip)

    # MAB dùng để rank và hiển thị điểm — không dùng để route
    if is_vip:
        status = "VIP_SMOOTH"   # VIP + có kho khác → tự ship ngầm
    else:
        status = "UPSELL"       # Normal + có kho khác → gợi ý mua thêm

    return status, backup_wh, ranked, is_vip


# ── TẦNG 4: OUTPUT BUILDER ────────────────────────────────────────
def build_json_response(status, user, gift, current_wh, ranked, is_vip):

    if status == "SUCCESS":
        return {
            "status":       "SUCCESS",
            "ui_action":    "smooth_checkout",
            "headline":     "✅ Đơn hàng thông suốt!",
            "detail":       f"Quà **{gift.get('name')}** sẵn sàng xuất kho.",
            "groq_prompt":  False,
            "offer_options": []
        }

    if status == "VIP_SMOOTH":
        return {
            "status":       "VIP_SMOOTH",
            "ui_action":    "smooth_checkout",
            "headline":     "💎 VIP — LogiGift tự xử lý!",
            "detail":       f"Quà đang ở kho khác. LogiGift tự ship về — bạn không mất phí thêm.",
            "groq_prompt":  True,
            "offer_options": []
        }

    if status == "UPSELL":
        gap = DB["upsell_threshold"]
        opts = [o["text"] for o in ranked]
        opts.append("❌ Hủy đơn")
        return {
            "status":        "UPSELL",
            "ui_action":     "upsell",
            "headline":      "🛒 Mua thêm để giữ nguyên quà!",
            "detail":        f"Quà đang ở kho khác. Mua thêm **{gap:,}đ** để gom đơn miễn phí!",
            "upsell_amount": gap,
            "groq_prompt":   True,
            "offer_options": opts
        }

    if status == "NEGOTIATE":
        opts = []
        for i, o in enumerate(ranked):
            prefix = f"⭐ ƯU TIÊN (MAB {o['score']})" if i == 0 else f"➖ Lựa chọn {i+1} (MAB {o['score']})"
            opts.append(f"{prefix}: {o['text']}")
        opts.append("❌ Hủy đơn")
        return {
            "status":       "NEGOTIATE",
            "ui_action":    "negotiation_ui",
            "headline":     "🤝 LogiGift đề xuất phương án",
            "detail":       f"Kho {current_wh.get('location')} hết **{gift.get('name')}**. MAB đã xếp hạng:",
            "groq_prompt":  True,
            "offer_options": opts
        }

    # FALLBACK
    offer = "Voucher VIP 100k" if is_vip else "Voucher 50k"
    return {
        "status":       "FALLBACK",
        "ui_action":    "fallback",
        "headline":     "🎫 Hết quà toàn quốc — đền bù tự động",
        "detail":       f"Hết **{gift.get('name')}** trên toàn hệ thống. LogiGift tự động tặng **{offer}**.",
        "groq_prompt":  True,
        "offer_options": [f"✅ Nhận {offer}", "❌ Hủy đơn"]
    }


# ── TẦNG 5: ORCHESTRATOR ─────────────────────────────────────────
def process_checkout(user_id, warehouse_id, gift_id):
    user, current_wh, gift, stock_key, current_stock = fetch_wms_data(
        user_id, warehouse_id, gift_id
    )
    status, backup_wh, ranked, is_vip = analyze_platform_logic(
        user, warehouse_id, stock_key, current_stock
    )
    return build_json_response(status, user, gift, current_wh, ranked, is_vip)
