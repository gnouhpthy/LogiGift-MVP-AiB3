import json, os
from pydantic import BaseModel
from typing import Literal
from config import CONFIDENCE_THRES, VIP_LTV_THRES, SHIP_FEE_VND, VOUCHER_VALUE, AVG_ORDER_VALUE, COMMISSION_RATE

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_db.json')

def load_db():
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ── Pydantic Models ──────────────────────────────────────────────
class WarehouseStatus(BaseModel):
    wh_id: str
    name: str
    gift_stock: int
    confidence_score: float
    last_sync_mins: int
    flag: Literal["OK", "LOW_CONFIDENCE", "OUT_OF_STOCK"]

class CheckoutResult(BaseModel):
    decision: Literal["APPROVE", "APPROVE_VIP_SUBSIDY", "OFFER_VOUCHER", "HUMAN_REVIEW"]
    message: str
    roi_ok: bool
    delta_value_vnd: int
    warehouse_used: str
    need_ai_message: bool

# ── Lưới lọc 1: Kiểm tra Confidence Score ───────────────────────
def check_warehouse(wh_id: str, wh_data: dict) -> WarehouseStatus:
    flag = "OK"
    if wh_data["gift_stock"] == 0:
        flag = "OUT_OF_STOCK"
    elif wh_data["confidence_score"] < CONFIDENCE_THRES:
        flag = "LOW_CONFIDENCE"
    return WarehouseStatus(wh_id=wh_id, flag=flag, **wh_data)

# ── Lưới lọc 2: ROI Guard ────────────────────────────────────────
def roi_guard(ltv_vnd: int) -> tuple[bool, int]:
    """Trả về (roi_ok, delta_value). Chỉ duyệt bù ship nếu LTV > ngưỡng VIP."""
    delta = int(AVG_ORDER_VALUE * COMMISSION_RATE)   # hoa hồng cứu được
    cost  = SHIP_FEE_VND
    roi_ok = (ltv_vnd >= VIP_LTV_THRES) and (delta > cost)
    return roi_ok, delta

# ── Lưới lọc 3: MAB Scoring & Quyết định ────────────────────────
def mab_score(confidence: float, roi_ok: bool, is_vip: bool) -> float:
    """Score = confidence × roi_weight × vip_weight"""
    roi_w = 1.2 if roi_ok else 0.8
    vip_w = 1.3 if is_vip else 1.0
    return round(confidence * roi_w * vip_w, 4)

# ── Hàm chính ────────────────────────────────────────────────────
def process_checkout(user_id: str, primary_wh: str = "WH_HCM") -> CheckoutResult:
    db = load_db()
    user = db["users"][user_id]
    is_vip = user["rank"] == "VIP"
    ltv    = user["ltv_vnd"]

    wh_primary = check_warehouse(primary_wh, db["warehouses"][primary_wh])

    # Kho chính hết hàng → thử kho dự phòng
    backup_wh_id = "WH_HN" if primary_wh == "WH_HCM" else "WH_HCM"
    wh_backup    = check_warehouse(backup_wh_id, db["warehouses"][backup_wh_id])

    roi_ok, delta = roi_guard(ltv)
    score = mab_score(wh_backup.confidence_score, roi_ok, is_vip)

    # ── Ra quyết định ──────────────────────────────────────────
    if wh_primary.flag == "OK":
        decision = "APPROVE"
        msg = f"✅ Duyệt đơn — giao quà từ {wh_primary.name}."
        wh_used = primary_wh
        need_ai = False

    elif wh_primary.flag == "LOW_CONFIDENCE":
        decision = "HUMAN_REVIEW"
        msg = f"🚨 Dữ liệu kho {wh_primary.name} không đáng tin (score={wh_primary.confidence_score}). Chuyển CSKH xử lý."
        wh_used = primary_wh
        need_ai = False

    elif wh_primary.flag == "OUT_OF_STOCK":
        if wh_backup.flag == "OK" and roi_ok:
            decision = "APPROVE_VIP_SUBSIDY" if is_vip else "APPROVE"
            label = "VIP — bù ship chéo kho" if is_vip else "chuyển kho dự phòng"
            msg = f"🔄 Kho HCM hết quà → {label} từ {wh_backup.name} (score={wh_backup.confidence_score})."
            wh_used = backup_wh_id
            need_ai = True
        elif wh_backup.flag == "LOW_CONFIDENCE":
            decision = "HUMAN_REVIEW"
            msg = "🚨 Cả 2 kho có vấn đề. Chuyển nhân viên CSKH xử lý thủ công."
            wh_used = backup_wh_id
            need_ai = False
        else:
            decision = "OFFER_VOUCHER"
            msg = f"🎟️ Hết quà toàn hệ thống — tặng Voucher {VOUCHER_VALUE:,}đ bù đắp."
            wh_used = backup_wh_id
            need_ai = True

    else:
        decision = "OFFER_VOUCHER"
        msg = "🎟️ Không thể xử lý tự động — tặng voucher bù đắp."
        wh_used = primary_wh
        need_ai = True

    # ── Cập nhật thống kê Admin ────────────────────────────────
    if decision in ("APPROVE", "APPROVE_VIP_SUBSIDY", "OFFER_VOUCHER"):
        db["orders_saved"]          = db.get("orders_saved", 0) + 1
        db["commission_rescued_vnd"] = db.get("commission_rescued_vnd", 0) + delta
        save_db(db)

    return CheckoutResult(
        decision=decision,
        message=msg,
        roi_ok=roi_ok,
        delta_value_vnd=delta,
        warehouse_used=wh_used,
        need_ai_message=need_ai,
    )