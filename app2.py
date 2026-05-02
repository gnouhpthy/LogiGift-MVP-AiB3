import streamlit as st
import json, os
from core.logic_engine import process_checkout, load_db
from core.grok_service import get_negotiation_text

# ── Cấu hình trang ────────────────────────────────────────────────
st.set_page_config(
    page_title="LogiGift AI",
    page_icon="🎁",
    layout="wide"
)

# ── CSS tuỳ chỉnh ─────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #f0f4ff; }
    .stButton>button {
        background: linear-gradient(135deg,#4f8ef7,#7c3aed);
        color:white; border:none; border-radius:10px;
        padding:10px 28px; font-size:16px; font-weight:600;
    }
    .metric-card {
        background:white; border-radius:14px; padding:18px;
        box-shadow:0 2px 12px rgba(80,80,200,0.10);
        text-align:center; margin:4px;
    }
    .flag-red   { color:#ef4444; font-weight:700; }
    .flag-green { color:#22c55e; font-weight:700; }
    .flag-yellow{ color:#f59e0b; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────
st.markdown("## 🎁 LogiGift AI — Hệ thống Tối ưu Quà tặng TMĐT")
st.markdown("*Giải quyết xung đột kho thời gian thực · AI-powered · MVP Demo*")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────
tab = st.sidebar.selectbox("📌 Chọn Tab", ["🛒 Checkout", "📊 Admin Dashboard"])
st.sidebar.divider()
st.sidebar.markdown("**⚙️ Cấu hình hệ thống**")
conf_thres = st.sidebar.slider("Confidence Threshold", 0.0, 1.0, 0.6, 0.05)
st.sidebar.caption("Dưới ngưỡng này → cắm cờ đỏ ⚠️")

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CHECKOUT
# ══════════════════════════════════════════════════════════════════
if tab == "🛒 Checkout":
    st.subheader("🛒 Thanh toán & Phân bổ Quà tặng")

    col1, col2 = st.columns(2)
    with col1:
        user_id = st.selectbox(
            "👤 Chọn khách hàng",
            ["U_001", "U_002"],
            format_func=lambda x: "Tuấn VIP 💎 (LTV: 15,000,000đ)" if x == "U_001"
                                  else "Mai Thường 🙂 (LTV: 200,000đ)"
        )
    with col2:
        wh_choice = st.selectbox(
            "🏭 Kho chính xử lý",
            ["WH_HCM", "WH_HN"],
            format_func=lambda x: "Kho Quận 1 — HCM (hết hàng 🔴)" if x == "WH_HCM"
                                  else "Kho Đống Đa — HN (đủ hàng 🟢)"
        )

    # Hiển thị trạng thái kho
    db = load_db()
    st.markdown("#### 📦 Trạng thái kho hiện tại")
    wh_cols = st.columns(2)
    for i, (wh_id, wh) in enumerate(db["warehouses"].items()):
        score = wh["confidence_score"]
        stock = wh["gift_stock"]
        flag_color = "flag-green" if score >= conf_thres and stock > 0 else "flag-red"
        status_icon = "🟢" if score >= conf_thres and stock > 0 else "🔴"
        with wh_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>{status_icon} {wh['name']}</h4>
                <p>Tồn kho quà: <b>{stock} sản phẩm</b></p>
                <p>Confidence Score: <span class="{flag_color}">{score}</span></p>
                <p>Đồng bộ: {wh['last_sync_mins']} phút trước</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Nút thanh toán
    if st.button("💳 Thanh Toán Ngay", use_container_width=True):
        with st.spinner("🤖 AI đang xử lý 3 lưới lọc..."):
            result = process_checkout(user_id, wh_choice)

        st.session_state["last_result"] = result
        st.session_state["last_user"]   = db["users"][user_id]["name"]
        st.session_state["show_modal"]  = True

    # ── Modal kết quả ─────────────────────────────────────────────
    if st.session_state.get("show_modal"):
        result    = st.session_state["last_result"]
        user_name = st.session_state["last_user"]

        decision_color = {
            "APPROVE":           "#22c55e",
            "APPROVE_VIP_SUBSIDY":"#4f8ef7",
            "OFFER_VOUCHER":     "#f59e0b",
            "HUMAN_REVIEW":      "#ef4444",
        }
        color = decision_color.get(result.decision, "#888")

        st.markdown(f"""
        <div style="background:{color}18; border-left:5px solid {color};
                    border-radius:12px; padding:20px; margin-top:16px;">
            <h3 style="color:{color}">Kết quả: {result.decision}</h3>
            <p style="font-size:17px">{result.message}</p>
            <p>ROI Guard: {'✅ Duyệt' if result.roi_ok else '❌ Không duyệt bù lỗ'} &nbsp;|&nbsp;
               Delta Value: <b>{result.delta_value_vnd:,}đ</b> hoa hồng cứu được</p>
        </div>
        """, unsafe_allow_html=True)

        # GenAI message
        if result.need_ai_message:
            with st.spinner("✨ GenAI đang soạn tin nhắn cá nhân hoá..."):
                ai_msg = get_negotiation_text(user_name)
            st.info(f"💬 **Tin nhắn AI gửi khách:** {ai_msg}")

        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("✅ Xác nhận & Hoàn tất", use_container_width=True):
                st.session_state["show_modal"] = False
                st.success("🎉 Đơn hàng đã được xử lý thành công!")
        with col_cancel:
            if st.button("❌ Huỷ", use_container_width=True):
                st.session_state["show_modal"] = False

# ══════════════════════════════════════════════════════════════════
# TAB 2 — ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════
else:
    st.subheader("📊 Admin Dashboard — LogiGift AI")
    db = load_db()

    # KPI Cards
    orders_saved  = db.get("orders_saved", 0)
    comm_rescued  = db.get("commission_rescued_vnd", 0)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""<div class="metric-card">
            <h2 style="color:#4f8ef7">{orders_saved}</h2>
            <p>Đơn được cứu</p></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="metric-card">
            <h2 style="color:#22c55e">{comm_rescued:,}đ</h2>
            <p>Hoa hồng giữ lại</p></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="metric-card">
            <h2 style="color:#7c3aed">{orders_saved * 200000:,}đ</h2>
            <p>GMV bảo vệ (ước tính)</p></div>""", unsafe_allow_html=True)
    with k4:
        wh_ok = sum(1 for w in db["warehouses"].values()
                    if w["confidence_score"] >= conf_thres)
        st.markdown(f"""<div class="metric-card">
            <h2 style="color:#f59e0b">{wh_ok}/{len(db['warehouses'])}</h2>
            <p>Kho tin cậy</p></div>""", unsafe_allow_html=True)

    st.divider()

    # Confidence Score per kho
    st.markdown("#### 🏭 Tình trạng Kho & Confidence Score")
    import pandas as pd
    wh_rows = []
    for wh_id, wh in db["warehouses"].items():
        score = wh["confidence_score"]
        flag  = ("🟢 OK" if score >= conf_thres and wh["gift_stock"] > 0
                 else "🔴 Cần kiểm tra")
        wh_rows.append({
            "Kho": wh["name"],
            "Tồn kho": wh["gift_stock"],
            "Confidence Score": score,
            "Đồng bộ (phút trước)": wh["last_sync_mins"],
            "Trạng thái": flag,
        })
    st.dataframe(pd.DataFrame(wh_rows), use_container_width=True)

    st.divider()

    # Delta Value explanation
    st.markdown("#### 💡 Mô hình Delta Value — LogiGift vs Không có AI")
    d1, d2 = st.columns(2)
    with d1:
        st.error("**❌ Không có LogiGift AI**\n\nKho hết quà → Chặn thanh toán → Khách hủy đơn → Mất 100% hoa hồng")
    with d2:
        st.success("**✅ Có LogiGift AI**\n\nKho hết quà → AI chuyển kho / đổi voucher → Khách chốt đơn → Thu hoa hồng")

    if st.button("🔄 Reset thống kê demo"):
        db["orders_saved"] = 0
        db["commission_rescued_vnd"] = 0
        from core.logic_engine import save_db
        save_db(db)
        st.rerun()