import os
import time
import requests
import threading
import telebot
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient

# Environment Variables থেকে মানসমূহ সংগ্রহ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k")

ADMIN_IDS_RAW = os.environ.get("ADMIN_CHAT_IDS", "8414665404,5034445579")
ADMIN_CHAT_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_RAW.split(",") if admin_id.strip()]

MONGO_URI = os.environ.get("MONGO_URI")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Flask & Telegram Bot ইনিশিয়ালাইজেশন
app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN)

# MongoDB কানেকশন সেটআপ
db = None
users_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client.get_database() # ডিফল্ট ডাটাবেজ
        users_collection = db["users"]
        print("✅ MongoDB Connection Successful!")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")

device_db = {}
banned_users = set()

# -------- KEEP ALIVE SCRIPT (Render 24/7 Active) --------
def keep_alive():
    """ Render-এর ফ্রি ইনস্ট্যান্স যেন বন্ধ না হয় তাই প্রতি ১৪ মিনিটে সার্ভারে পিং করবে """
    if RENDER_EXTERNAL_URL:
        while True:
            time.sleep(840)  # ১৪ মিনিট (৮৪০ সেকেন্ড)
            try:
                requests.get(RENDER_EXTERNAL_URL, timeout=10)
                print("🔄 Keep-Alive Ping Sent Successfully!")
            except Exception as e:
                print(f"⚠️ Keep-Alive Ping Failed: {e}")

# -------- TELEGRAM BOT HANDLERS --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "👋 **স্বাগতম!**\n\nআমাদের অ্যাপ থেকে আয় করতে নিচে থাকা **Open App** বাটনে চাপ দিন।"
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

def run_bot():
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook remove error: {e}")
        
    bot.infinity_polling(skip_pending=True)

# -------- TELEGRAM ALERT FUNCTION --------
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for admin_id in ADMIN_CHAT_IDS:
        payload = {"chat_id": admin_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Error sending alert: {e}")

# -------- FLASK ROUTES --------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check-device', methods=['POST'])
def check_device():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    device_id = data.get('device_id')
    user_id = str(data.get('user_id'))
    first_name = data.get('first_name', 'Unknown')
    username = data.get('username', 'No Username')

    # MongoDB-তে ইউজার ডাটা সেভ/আপডেট করার লজিক
    if users_collection is not None:
        try:
            users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "first_name": first_name,
                        "username": username,
                        "device_id": device_id,
                        "last_active": time.time()
                    }
                },
                upsert=True
            )
        except Exception as e:
            print(f"Database save error: {e}")

    if user_id in banned_users:
        return jsonify({"status": "banned"}), 200

    if device_id not in device_db:
        device_db[device_id] = [user_id]
        return jsonify({"status": "success"}), 200

    if user_id in device_db[device_id]:
        return jsonify({"status": "success"}), 200

    device_db[device_id].append(user_id)
    all_users = ", ".join(device_db[device_id])

    alert_msg = (
        f"<b>⚠️ মাল্টিপল অ্যাকাউন্ট সতর্কবার্তা!</b>\n\n"
        f"<b>ডিভাইস ID:</b> <code>{device_id}</code>\n"
        f"<b>নতুন ইউজার:</b> {first_name} (@{username})\n"
        f"<b>ইউজার ID:</b> <code>{user_id}</code>\n"
        f"<b>এই ডিভাইসের সব ID:</b> <code>{all_users}</code>"
    )
    send_telegram_alert(alert_msg)
    return jsonify({"status": "multi_account_detected"}), 200

if __name__ == '__main__':
    # টেলিগ্রাম বট চালানোর জন্য থ্রেড
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Render সার্ভার ২৪ ঘণ্টা সচল রাখার জন্য Keep-Alive থ্রেড
    if RENDER_EXTERNAL_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
