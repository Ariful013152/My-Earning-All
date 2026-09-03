import os
import time
import random
import requests
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@myearningall")

ADMIN_IDS_RAW = os.environ.get("ADMIN_CHAT_IDS", "8414665404,5034445579")
ADMIN_CHAT_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_RAW.split(",") if admin_id.strip()]

MONGO_URI = os.environ.get("MONGO_URI")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN)

db = None
users_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client.get_database()
        users_collection = db["users"]
        print("✅ MongoDB Connected")
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")

device_db = {}
banned_users = set()

# -------- FAKE WITHDRAW AUTO SENDER ( 5 Mins Interval ) --------
def send_fake_withdraw_loop():
    while True:
        try:
            methods = ['bKash', 'Nagad']
            selected_method = random.choice(methods)
            random_amount = round(random.uniform(200.0, 850.0), 2)
            
            prefixes = ['017', '018', '019', '013', '014', '016', '015']
            prefix = random.choice(prefixes)
            last_two = random.randint(10, 99)
            fake_acc = f"{prefix}xxxx{last_two}"

            msg = (
                f"<b>My Earning All Payment</b>\n"
                f"✅ Withdrawal Paid\n\n"
                f"💵 <b>{random_amount} BDT</b>\n"
                f"🌐 <b>{selected_method}</b>\n"
                f"👛 <b>{fake_acc}</b>"
            )

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHANNEL_ID,
                "text": msg,
                "parse_mode": "HTML"
            }
            
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("✅ Fake withdraw message sent!")
            else:
                print(f"⚠️ Channel msg failed: {res.text}")
        except Exception as e:
            print(f"⚠️ Fake withdraw error: {e}")
            
        time.sleep(300)

# -------- KEEP ALIVE ( Render 24/7 Server Running ) --------
def keep_alive():
    if RENDER_EXTERNAL_URL:
        while True:
            time.sleep(840)
            try:
                requests.get(RENDER_EXTERNAL_URL, timeout=10)
                print("🔄 Ping Sent!")
            except Exception as e:
                print(f"⚠️ Ping Error: {e}")

# -------- TELEGRAM BOT HANDLERS & REFERRAL --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name
    username = message.from_user.username or "No Username"

    if user_id in banned_users:
        bot.reply_to(message, "❌ **আপনি এই বট থেকে ব্যান হয়েছেন!**", parse_mode="Markdown")
        return

    # রেফার কোড ট্র্যাকিং ও পয়েন্ট যোগ
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None

    if referrer_id and referrer_id != user_id:
        if users_collection is not None:
            try:
                users_collection.update_one(
                    {"user_id": str(referrer_id)},
                    {"$inc": {"balance": 0.50, "total_refers": 1}},
                    upsert=True
                )
                bot.send_message(referrer_id, f"🎉 আপনার রেফার লিংকে নতুন একজন জয়েন করায় আপনি <b>TK 0.50</b> বোনাস পেয়েছেন!", parse_mode="HTML")
            except Exception as e:
                print(f"Referral update error: {e}")

    welcome_text = "👋 **স্বাগতম!**\n\nআমাদের অ্যাপ থেকে আয় করতে নিচে থাকা **Open App** বাটনে চাপ দিন।"
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# -------- BAN / UNBAN CALLBACK HANDLER --------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('ban_', 'unban_')))
def handle_ban_callback(call):
    action, user_id = call.data.split('_')
    
    if action == 'ban':
        banned_users.add(user_id)
        bot.answer_callback_query(call.id, f"User {user_id} Banned Successfully!")
        bot.edit_message_text(f"🚫 **ইউজার ID: {user_id} সফলভাবে ব্যান করা হয়েছে!**", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id)
    elif action == 'unban':
        banned_users.discard(user_id)
        bot.answer_callback_query(call.id, f"User {user_id} Unbanned!")
        bot.edit_message_text(f"✅ **ইউজার ID: {user_id} সফলভাবে আনব্যান করা হয়েছে!**", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id)

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Bot polling restart error: {e}")
            time.sleep(5)

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

    # একাধিক অ্যাকাউন্ট শনাক্ত হলে এডমিনকে ব্যান/আনব্যান বাটনসহ নোটিফিকেশন পাঠাবে
    device_db[device_id].append(user_id)
    all_users = ", ".join(device_db[device_id])

    alert_msg = (
        f"<b>⚠️ মাল্টিপল অ্যাকাউন্ট সতর্কবার্তা!</b>\n\n"
        f"<b>ডিভাইস ID:</b> <code>{device_id}</code>\n"
        f"<b>নতুন ইউজার:</b> {first_name} (@{username})\n"
        f"<b>ইউজার ID:</b> <code>{user_id}</code>\n"
        f"<b>এই ডিভাইসের সব ID:</b> <code>{all_users}</code>"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_{user_id}"),
        InlineKeyboardButton("✅ Unban User", callback_data=f"unban_{user_id}")
    )

    for admin_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(admin_id, alert_msg, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"Error sending admin alert: {e}")

    return jsonify({"status": "multi_account_detected"}), 200

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=send_fake_withdraw_loop, daemon=True).start()
    
    if RENDER_EXTERNAL_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
