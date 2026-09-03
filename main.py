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
        print("✅ MongoDB Connected Successfully")
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")

device_db = {}
banned_users = set()

# -------- FAKE WITHDRAW AUTO SENDER --------
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
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ Fake withdraw error: {e}")
            
        time.sleep(300)

# -------- KEEP ALIVE --------
def keep_alive():
    if RENDER_EXTERNAL_URL:
        while True:
            time.sleep(840)
            try:
                requests.get(RENDER_EXTERNAL_URL, timeout=10)
            except Exception as e:
                print(f"⚠️ Ping Error: {e}")

# -------- TELEGRAM BOT HANDLERS & REFERRAL --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name
    username = message.from_user.username or "No Username"

    if user_id in banned_users:
        bot.reply_to(message, "❌ <b>আপনি এই বট থেকে ব্যান হয়েছেন!</b>", parse_mode="HTML")
        return

    # ইউজারের প্রোফাইল ডাটাবেসে সেভ করা
    if users_collection is not None:
        users_collection.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "balance": 0.0, "total_refers": 0, "first_name": first_name, "username": username}},
            upsert=True
        )

    # রেফার কোড ট্র্যাকিং ও পয়েন্ট যোগ
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None

    if referrer_id and str(referrer_id) != user_id:
        if users_collection is not None:
            try:
                current_user = users_collection.find_one({"user_id": user_id})
                if current_user and not current_user.get("referred_by"):
                    users_collection.update_one(
                        {"user_id": str(referrer_id)},
                        {"$inc": {"balance": 0.50, "total_refers": 1}},
                        upsert=True
                    )
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"referred_by": str(referrer_id)}}
                    )
                    bot.send_message(referrer_id, f"🎉 আপনার রেফার লিংকে নতুন একজন জয়েন করায় আপনি <b>TK 0.50</b> বোনাস পেয়েছেন!", parse_mode="HTML")
            except Exception as e:
                print(f"Referral update error: {e}")

    welcome_text = "👋 <b>স্বাগতম!</b>\n\nআমাদের অ্যাপ থেকে আয় করতে নিচে থাকা <b>Open App</b> বাটনে চাপ দিন।"
    bot.reply_to(message, welcome_text, parse_mode="HTML")

# -------- BAN / UNBAN CALLBACK HANDLER --------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('ban_', 'unban_')))
def handle_ban_callback(call):
    action, target_user_id = call.data.split('_')
    
    if action == 'ban':
        banned_users.add(target_user_id)
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
        bot.answer_callback_query(call.id, f"User {target_user_id} Banned!")
        bot.edit_message_text(f"🚫 <b>ইউজার ID: {target_user_id} সফলভাবে ব্যান করা হয়েছে!</b>", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, parse_mode="HTML")
    elif action == 'unban':
        banned_users.discard(target_user_id)
        if users_collection is not None:
            users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
        bot.answer_callback_query(call.id, f"User {target_user_id} Unbanned!")
        bot.edit_message_text(f"✅ <b>ইউজার ID: {target_user_id} আনব্যান করা হয়েছে!</b>", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, parse_mode="HTML")

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"Bot polling restart error: {e}")
            time.sleep(5)

# -------- FLASK ROUTES --------
@app.route('/')
def home():
    return render_template('index.html')

# রিয়েল-টাইম ব্যালেন্স ও রেফার কাউন্ট রিটার্ন
@app.route('/get-user-data', methods=['GET'])
def get_user_data():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID required"}), 400

    if users_collection is not None:
        user_data = users_collection.find_one({"user_id": str(user_id)})
        if user_data:
            if user_data.get("banned", False):
                return jsonify({"status": "banned"}), 200
            return jsonify({
                "status": "success",
                "balance": float(user_data.get("balance", 0.00)),
                "total_refers": int(user_data.get("total_refers", 0))
            }), 200

    return jsonify({"status": "success", "balance": 0.00, "total_refers": 0}), 200

# ইউজার ব্যালেন্স আপডেট
@app.route('/update-balance', methods=['POST'])
def update_balance():
    data = request.json
    user_id = str(data.get('user_id'))
    amount = float(data.get('amount', 0.0))

    if users_collection is not None and user_id:
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 400

# সেফ উইথড্র প্রসেসিং
@app.route('/request-withdraw', methods=['POST'])
def request_withdraw():
    data = request.json
    user_id = str(data.get('user_id'))
    amount = float(data.get('amount', 0.0))
    account = str(data.get('account', ''))
    method = str(data.get('method', 'bKash'))

    if not user_id or amount < 200 or len(account) < 11:
        return jsonify({"status": "error", "message": "Invalid request parameters"}), 400

    if users_collection is not None:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or float(user_data.get("balance", 0)) < amount:
            return jsonify({"status": "error", "message": "Insufficient balance"}), 400

        users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})

        hidden_acc = account[:3] + "xxxx" + account[-2:]
        msg = (
            f"<b>My Earning All Payment</b>\n"
            f"✅ Withdrawal Paid\n\n"
            f"💵 <b>{amount:.2f} BDT</b>\n"
            f"🌐 <b>{method}</b>\n"
            f"👛 <b>{hidden_acc}</b>"
        )
        try:
            bot.send_message(CHANNEL_ID, msg, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending withdraw message: {e}")

        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500

# মাল্টি-অ্যাকাউন্ট চেক ও নোটিফিকেশন
@app.route('/check-device', methods=['POST'])
def check_device():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    device_id = str(data.get('device_id'))
    user_id = str(data.get('user_id'))
    first_name = data.get('first_name', 'Unknown')
    username = data.get('username', 'No Username')

    if user_id in banned_users:
        return jsonify({"status": "banned"}), 200

    if users_collection is not None:
        u_data = users_collection.find_one({"user_id": user_id})
        if u_data and u_data.get("banned", False):
            banned_users.add(user_id)
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
        f"<b>এই ডিভাইসের সকল ID:</b> <code>{all_users}</code>"
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
