import google.generativeai as genai
from config import GEMINI_API_KEY, VOUCHER_VALUE

def get_negotiation_text(user_name: str, missing_item: str = "quà tặng",
                          offer: str = None) -> str:
    """Gọi Gemini để sinh câu xin lỗi cá nhân hoá. Fallback nếu lỗi."""
    if offer is None:
        offer = f"Voucher {VOUCHER_VALUE:,}đ"

    # Nếu chưa có API key → dùng fallback luôn
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ĐIỀN_KEY_VÀO_ĐÂY":
        return _fallback(user_name, missing_item, offer)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"Viết 1 câu xin lỗi khách hàng tên {user_name}, "
            f"kho hết {missing_item}, bù {offer}. "
            f"Dưới 25 chữ, dễ thương, thân thiện."
        )
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return _fallback(user_name, missing_item, offer)

def _fallback(user_name, missing_item, offer):
    return f"Bạn {user_name} ơi, kho hết {missing_item} rồi 😢 Nhận {offer} nhé!"