from flask import Flask, render_template, request, jsonify
import json, os, urllib.request
from core.logic_engine import process_checkout, DB
from config import OPENROUTER_API_KEY

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    return jsonify({
        "users": DB["users"],
        "warehouses": DB["warehouses"],
        "products": DB["products"],
        "upsell_threshold": DB["upsell_threshold"]
    })

@app.route("/api/checkout", methods=["POST"])
def checkout():
    data = request.json
    result = process_checkout(
        data.get("user_id", "USR-VIP-001"),
        data.get("warehouse_id", "WH-HCM"),
        data.get("gift_id", "GIFT_A")
    )
    return jsonify(result)

@app.route("/api/gen-text", methods=["POST"])
def gen_text():
    data      = request.json
    result    = data.get("result", {})
    ui_action = result.get("ui_action", "")
    is_vip    = data.get("is_vip", False)
    user_name = data.get("user_name", "bạn")
    gift_name = data.get("gift_name", "quà tặng")

    prompts = {
        "upsell":         f'Bạn là AI của sàn TMĐT LogiGift. Khách hàng thường tên {user_name} muốn nhận quà "{gift_name}" nhưng quà đang ở kho khác. Gợi ý mua thêm để gom đơn miễn phí. Viết 2 câu thân thiện. Không markdown.',
        "negotiation_ui": f'Bạn là AI LogiGift. Khách {user_name} hết quà tại kho, có phương án thay thế. Viết 2 câu xin lỗi + giới thiệu phương án. Tone ấm.',
        "fallback":       f'Bạn là AI LogiGift. Quà "{gift_name}" hết toàn quốc. Khách {"VIP" if is_vip else "thường"} tên {user_name}. Tự động đền voucher. Viết 2 câu xin lỗi + thông báo voucher. Ngắn gọn, ấm áp.'
    }
    prompt = prompts.get(ui_action, "")
    if not prompt:
        return jsonify({"text": result.get("detail",""), "by": "static"})
    
    try:
        if not OPENROUTER_API_KEY: raise ValueError("no key")
        
        payload = json.dumps({
            "model": "meta-llama/llama-3.3-70b-instruct:free", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }).encode()
        
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", 
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}" 
            }
        )
        
        with urllib.request.urlopen(req) as r:
            rd = json.loads(r.read().decode())
            
        generated_text = rd["choices"][0]["message"]["content"]
        
        return jsonify({"text": generated_text, "by": "Llama-3 via OpenRouter"})
        
    except Exception as e:
        # In nhẹ 1 dòng ra terminal để giám sát, không làm rác log
        print(f"⚠️ API Fallback kích hoạt do lỗi: {e}")
        
        fb = {
            "upsell":         f"Quà \"{gift_name}\" đang ở kho khác — mua thêm một chút là gom đơn miễn phí và giữ nguyên quà nhé! 🎁",
            "negotiation_ui": "Rất tiếc vì sự bất tiện! Chúng tôi đã chuẩn bị sẵn các phương án tốt nhất cho bạn.",
            "fallback":       f"Xin lỗi vì quà \"{gift_name}\" đã hết — một voucher ưu đãi đã tự động được gửi đến bạn như lời cảm ơn chân thành! 🎟️"
        }
        return jsonify({"text": fb.get(ui_action, result.get("detail","")), "by": "fallback"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
