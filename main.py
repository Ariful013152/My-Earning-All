import os
import requests
import threading
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS

BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"
ADMIN_CHAT_IDS = [8414665404, 5034445579]

app = Flask(__name__)
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN)

device_db = {}
banned_users = set()

# -------- TELEGRAM BOT HANDLERS --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "👋 **স্বাগতম!**\n\nআমাদের অ্যাপ থেকে আয় করতে নিচে থাকা **Open App** বাটনে চাপ দিন।"
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

def run_bot():
    bot.infinity_polling()

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
    # বোট আলাদা থ্রেডে ব্যাকগ্রাউন্ডে চলবে
    threading.Thread(target=run_bot, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
