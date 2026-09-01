import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # HTML Mini App থেকে API রিকোয়েস্ট অ্যালাউ করার জন্য

# ----------------- টেলিগ্রাম বোট ও এডমিন সেটিং -----------------
BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"
ADMIN_CHAT_IDS = [8414665404, 5034445579]  # আপনার প্রদান করা ২টি এডমিন আইডি

# ডাটাবেস (মেমোরি স্টোরেজ)
device_db = {}
banned_users = set()

def send_telegram_alert(message):
    """উভয় এডমিনকে টেলিগ্রামে নোটিফিকেশন পাঠানোর ফাংশন"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    for admin_id in ADMIN_CHAT_IDS:
        payload = {
            "chat_id": admin_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Admin {admin_id} কে মেসেজ পাঠাতে সমস্যা হয়েছে: {e}")

@app.route('/')
def home():
    return "Earning App Backend Server is Running Live!"

@app.route('/check-device', methods=['POST'])
def check_device():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    device_id = data.get('device_id')
    user_id = str(data.get('user_id'))
    first_name = data.get('first_name', 'Unknown')
    username = data.get('username', 'No Username')

    # ১. ইউজার ব্যান কিনা চেক করা
    if user_id in banned_users:
        return jsonify({"status": "banned"}), 200

    # ২. নতুন ডিভাইস হলে এনট্রি নেওয়া
    if device_id not in device_db:
        device_db[device_id] = [user_id]
        return jsonify({"status": "success", "message": "New device registered"}), 200

    # ৩. একই ডিভাইসে একই ইউজার আবার প্রবেশ করলে
    if user_id in device_db[device_id]:
        return jsonify({"status": "success", "message": "User matched with device"}), 200

    # ৪. একই ডিভাইসে অন্য টেলিগ্রাম আইডি সনাক্ত হলে (Multi-Account Fraud!)
    device_db[device_id].append(user_id)
    all_associated_users = ", ".join(device_db[device_id])

    # ২টি এডমিন আইডিতেই নোটিফিকেশন পাঠাবে
    alert_msg = (
        f"<b>⚠️ মাল্টিপল অ্যাকাউন্ট সতর্কবার্তা!</b>\n\n"
        f"<b>ডিভাইস ID:</b> <code>{device_id}</code>\n"
        f"<b>নতুন ইউজার:</b> {first_name} (@{username})\n"
        f"<b>ইউজার ID:</b> <code>{user_id}</code>\n"
        f"<b>এই ডিভাইসের সব ID সমূহ:</b> <code>{all_associated_users}</code>\n\n"
        f"🚫 <i>একই ডিভাইসে একাধিক টেলিগ্রাম অ্যাকাউন্ট ব্যবহার করা হচ্ছে!</i>"
    )
    send_telegram_alert(alert_msg)

    return jsonify({
        "status": "multi_account_detected",
        "message": "Multiple Telegram accounts detected on this device!"
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
