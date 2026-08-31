import os
import random
import threading
import time
from datetime import datetime, timezone, timedelta
import pymongo
import telebot
from flask import Flask, request
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo
)

# --- CONFIGURATION ---
BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"[cite: 1]
MONGO_URI = os.environ.get("MONGO_URI", "")[cite: 1]

BOT_USERNAME = "myearningall01_bot"[cite: 1]
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1", "@allinoneg2"][cite: 1]
PROOF_CHANNEL = "@myearningall"[cite: 1]

# মিনি অ্যাপের URL (আপনার Render অ্যাপের লিংক)
MINI_APP_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")

# স্ক্রিনশট সাবমিট হওয়ার নির্দিষ্ট চ্যানেল
SCREENSHOT_TARGET_CHANNEL = "@allinoneg3"[cite: 1]

PAYMENT_BANNER_URL = "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=800"[cite: 1]

MIN_WITHDRAW = 100.0   # সর্বনিম্ন উইথড্র ১০০ টাকা[cite: 1]
REFERRAL_BONUS = 0.50  # প্রতি রেফারে ০.৫০ টাকা বোনাস[cite: 1]
FAKE_USER_OFFSET = 506  # ৫০৬+ ফেক ইউজার কাউন্ট[cite: 1]

# --- TIMEZONE FUNCTION (Bangladesh Time GMT+6) ---
def get_bd_time_str():
    bd_tz = timezone(timedelta(hours=6))[cite: 1]
    bd_now = datetime.now(bd_tz)[cite: 1]
    return bd_now.strftime("%Y-%m-%d %I:%M:%S %p")[cite: 1]

# --- ADMIN IDS ---
ADMIN_IDS = [8414665404, 5034445579][cite: 1]

# --- 10 MONETAG & 10 ADSTERRA LINKS ---
MONETAG_LINKS = [
    'https://omg10.com/4/11522087', 'https://omg10.com/4/11522086', 'https://omg10.com/4/11522081',
    'https://omg10.com/4/11522080', 'https://omg10.com/4/11522079', 'https://omg10.com/4/11522078',
    'https://omg10.com/4/11522077', 'https://omg10.com/4/11522076', 'https://omg10.com/4/11522074',
    'https://omg10.com/4/11516146'
][cite: 1]

ADSTERRA_LINKS = [
    'https://www.effectivecpmnetwork.com/nx2nqegj3p?key=8fb4f6d68a89919faeee5ec3846d4292',
    'https://www.effectivecpmnetwork.com/bbjq6k48?key=4707c2aa3827755848d5332b72a9c955',
    'https://www.effectivecpmnetwork.com/hqrjr5jzm?key=fe9a5012689a62a78d579d93d0864575',
    'https://www.effectivecpmnetwork.com/nqch6m5jc?key=3eecd9428d8b55066d6cfdcadeda271c',
    'https://www.effectivecpmnetwork.com/ie1pgkmbcc?key=1298a27dc3477c9aef05ead4c6778088',
    'https://www.effectivecpmnetwork.com/wg9r001v7?key=4f2213d1fb414c2e0c9ac7dde1c72402',
    'https://www.effectivecpmnetwork.com/m36r7xvy?key=e8b267b7b19cae2daee8f96118e5326e',
    'https://www.effectivecpmnetwork.com/jwsp4r2rtr?key=63a26410a1f920c6de29b0e73bf69055',
    'https://www.effectivecpmnetwork.com/dwja24niv?key=6a9552e41b528897598e4eec709d5115',
    'https://www.effectivecpmnetwork.com/aqap5tdu?key=292364b4c9161a24064eaf503e245724'
][cite: 1]

WATCH_AD_2_LINKS = [
    'https://shrinkme.click/g2qGUb', 'https://shrinkme.click/8Uar', 'https://shrinkme.click/ptEvVdG',
    'https://shrinkme.click/ndirPw', 'https://shrinkme.click/LwsLmzvi', 'https://shrinkme.click/p4MaWq3R',
    'https://shrinkme.click/0jOAuZOk', 'https://shrinkme.click/EIZYof', 'https://shrinkme.click/ALuVs5',
    'https://shrinkme.click/9SB8', 'https://shrinkme.click/UYMQ', 'https://shrinkme.click/ven3VA7p',
    'https://shrinkme.click/xTRge', 'https://shrinkme.click/MjwBLrK', 'https://shrinkme.click/U9Tetn2'
][cite: 1]

WATCH_AD_3_LINKS = [
    'https://exe.io/0gptze35', 'https://exe.io/ry8Ka', 'https://exe.io/7nLiu', 'https://exe.io/57NKwlj',
    'https://exe.io/2qeCFj', 'https://exe.io/Bo0QN', 'https://exe.io/QcaC1jjV', 'https://exe.io/uJ8x4v',
    'https://exe.io/4CMD9lc', 'https://exe.io/7t5U3dg', 'https://exe.io/h3s7q', 'https://exe.io/vp05amHW',
    'https://exe.io/4VgpGc', 'https://exe.io/FhwbU5QN', 'https://exe.io/gCczg6'
][cite: 1]

# --- DATABASE SETUP ---
users_col = None
memory_users = {}

if MONGO_URI:
    try:
        client = pymongo.MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=2000, 
            maxPoolSize=200, 
            minPoolSize=20,
            maxIdleTimeMS=45000
        )[cite: 1]
        db = client["telegram_bot"][cite: 1]
        users_col = db["users"][cite: 1]
        users_col.create_index("user_id", unique=True)[cite: 1]
        print("MongoDB Connected Successfully.")[cite: 1]
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")[cite: 1]

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)[cite: 1]
app = Flask(__name__)[cite: 1]

# --- WEBHOOK & FLASK ROUTES (WITH MINI APP UI) ---
@app.route('/')
def home():
    # সম্পূর্ণ ডায়নামিক মিনি অ্যাপের ইন্টারফেস
    return """
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Earning All Mini App</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #0f172a;
                color: #ffffff;
                margin: 0;
                padding: 15px;
                text-align: center;
            }
            .card {
                background: #1e293b;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                margin-bottom: 15px;
            }
            h2 { color: #38bdf8; margin-top: 0; }
            .btn {
                background: linear-gradient(135deg, #0284c7, #2563eb);
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
                width: 100%;
                margin-top: 10px;
                cursor: pointer;
                font-size: 15px;
            }
            .btn:active { opacity: 0.8; }
            .notice { font-size: 13px; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>💎 My Earning App</h2>
            <p id="welcome-text">স্বাগতম!</p>
        </div>

        <div class="card">
            <h3>⚡ কাজ নির্বাচন করুন</h3>
            <button class="btn" onclick="sendTask('Watch Ad')">📺 Watch Ad (30 Task)</button>
            <button class="btn" onclick="sendTask('Watch Ad 2')">📺 Watch Ad 2 (ShrinkMe)</button>
            <button class="btn" onclick="sendTask('Watch Ad 3')">📺 Watch Ad 3 (Exe.io)</button>
        </div>

        <p class="notice">বাটনে ক্লিক করার পর চ্যাটে ফিরে গিয়ে নির্দেশনা অনুসরণ করুন।</p>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();
            
            if(tg.initDataUnsafe && tg.initDataUnsafe.user) {
                document.getElementById('welcome-text').innerText = "স্বাগতম, " + tg.initDataUnsafe.user.first_name + "!";
            }

            function sendTask(taskName) {
                tg.sendData(taskName);
                tg.close();
            }
        </script>
    </body>
    </html>
    """

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':[cite: 1]
        json_string = request.get_data().decode('utf-8')[cite: 1]
        update = telebot.types.Update.de_json(json_string)[cite: 1]
        threading.Thread(target=bot.process_new_updates, args=([update],), daemon=True).start()[cite: 1]
        return "OK", 200[cite: 1]
    else:
        return "Invalid request", 403[cite: 1]

@app.route('/verify-device')
def verify_device():
    user_id = request.args.get('user_id')[cite: 1]
    first_name = request.args.get('name', 'User')[cite: 1]
    
    if not user_id:
        return "<h3>❌ Invalid Request!</h3>", 400[cite: 1]

    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)[cite: 1]
    if user_ip and ',' in user_ip:[cite: 1]
        user_ip = user_ip.split(',')[0].strip()[cite: 1]

    target_id = int(user_id)[cite: 1]
    update_user_field(target_id, {"temp_ip": user_ip})[cite: 1]

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Device Verification</title>
    </head>
    <body style="text-align:center; font-family:sans-serif; margin-top:80px; background:#f4f7f6; color:#333;">
        <div style="max-width:400px; margin:auto; background:white; padding:30px; border-radius:10px; box-shadow:0px 4px 10px rgba(0,0,0,0.1);">
            <h2 style="color:#0088cc;">🔒 ডিভাইস সিকিউরিটি চেক</h2>
            <p style="font-size:15px; color:#555; line-height:1.5;">
                আপনার ডিভাইস এবং আইপি ভেরিফিকেশন প্রক্রিয়া সফল হয়েছে। নিচের বাটনে ক্লিক করে টেলিগ্রামে ফিরে যান এবং 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন।
            </p>
            <br>
            <a href="https://t.me/{BOT_USERNAME}" style="background:#0088cc; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block;">
                📥 টেলিগ্রামে ফিরে যান
            </a>
        </div>
    </body>
    </html>
    """[cite: 1]

# --- MEMORY TRACKING ---
user_withdraw_step = {}[cite: 1]
user_captcha_step = {}[cite: 1]
admin_step = {}[cite: 1]
user_waiting_screenshot = set()[cite: 1]
user_waiting_ad3_screenshot = set()[cite: 1]

# --- FAST IN-MEMORY & BACKGROUND DB HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    current_now = time.time()[cite: 1]
    
    if user_id in memory_users:[cite: 1]
        memory_users[user_id]["last_active"] = current_now[cite: 1]
        return memory_users[user_id].get("balance", 0.0), memory_users[user_id][cite: 1]

    default_user_data = {
        "user_id": user_id, 
        "first_name": str(first_name)[:30],
        "balance": 0.0, 
        "daily_count": 0,
        "last_reset": current_now,
        "last_task_time": 0,
        "can_claim": False,
        "captcha_locked": False,
        "referred_by": referred_by,
        "referrals_count": 0,
        "ref_reward_given": False,
        "is_banned": False,
        "verified_phone": None,
        "device_verified": False,
        "last_ip": None,
        "temp_ip": None,
        "history": [],
        "last_active": current_now,
        "last_inactivity_push": 0,
        "ad2_index": 0,
        "ad2_completed_today": 0,
        "ad2_last_reset": current_now,
        "ad3_index": 0,
        "ad3_completed_today": 0,
        "ad3_last_reset": current_now
    }[cite: 1]

    if users_col is not None:[cite: 1]
        try:
            user = users_col.find_one({"user_id": user_id})[cite: 1]
            if not user:[cite: 1]
                user = default_user_data[cite: 1]
                threading.Thread(target=lambda: users_col.insert_one(user), daemon=True).start()[cite: 1]
                
                if referred_by:[cite: 1]
                    def handle_ref():
                        ref_user = users_col.find_one({"user_id": referred_by})[cite: 1]
                        if ref_user and not ref_user.get("is_banned", False):[cite: 1]
                            add_balance(referred_by, REFERRAL_BONUS)[cite: 1]
                            if referred_by in memory_users:[cite: 1]
                                memory_users[referred_by]["referrals_count"] = memory_users[referred_by].get("referrals_count", 0) + 1[cite: 1]
                            users_col.update_one({"user_id": referred_by}, {"$inc": {"referrals_count": 1}})[cite: 1]
                            try:
                                bot.send_message(referred_by, f"🎉 আপনার রেফারেল লিংকের মাধ্যমে নতুন ইউজার যুক্ত হয়েছে! আপনি পেয়েছেন ৳{REFERRAL_BONUS:.2f} টাকা বোনাস।")[cite: 1]
                            except:
                                pass
                    threading.Thread(target=handle_ref, daemon=True).start()[cite: 1]
            memory_users[user_id] = user[cite: 1]
            return user.get("balance", 0.0), user[cite: 1]
        except Exception as e:
            print(f"DB Fetch Error: {e}")[cite: 1]

    memory_users[user_id] = default_user_data[cite: 1]
    return 0.0, default_user_data[cite: 1]

def update_user_field(user_id, field_dict):
    if user_id in memory_users:[cite: 1]
        memory_users[user_id].update(field_dict)[cite: 1]
    if users_col is not None:[cite: 1]
        threading.Thread(target=lambda: users_col.update_one({"user_id": user_id}, {"$set": field_dict}, upsert=True), daemon=True).start()[cite: 1]

def add_balance(user_id, amount):
    if user_id in memory_users:[cite: 1]
        memory_users[user_id]["balance"] = memory_users[user_id].get("balance", 0.0) + float(amount)[cite: 1]
    if users_col is not None:[cite: 1]
        threading.Thread(target=lambda: users_col.update_one({"user_id": user_id}, {"$inc": {"balance": float(amount)}}), daemon=True).start()[cite: 1]

def add_payment_history(user_id, method, amount_bdt, number):
    record = {
        "method": method,
        "amount_bdt": amount_bdt,
        "number": str(number).strip(),
        "date": get_bd_time_str()
    }[cite: 1]
    if user_id in memory_users:[cite: 1]
        if "history" not in memory_users[user_id]:[cite: 1]
            memory_users[user_id]["history"] = [][cite: 1]
        memory_users[user_id]["history"].append(record)[cite: 1]
    if users_col is not None:[cite: 1]
        threading.Thread(target=lambda: users_col.update_one({"user_id": user_id}, {"$push": {"history": record}}), daemon=True).start()[cite: 1]

def get_all_active_users():
    if users_col is not None:[cite: 1]
        try:
            return list(users_col.find({"is_banned": {"$ne": True}}))[cite: 1]
        except Exception as e:
            print(f"Error fetching users: {e}")[cite: 1]
    return [u for u in memory_users.values() if not u.get("is_banned", False)][cite: 1]

def check_duplicate_withdraw_number(current_user_id, current_name, number, method, withdraw_amount):
    def async_check():
        if users_col is None:[cite: 1]
            return
        try:
            clean_num = str(number).strip()[cite: 1]
            previous_users = list(users_col.find({"history.number": clean_num, "user_id": {"$ne": current_user_id}}))[cite: 1]
            
            if previous_users:[cite: 1]
                other_user_ids = [str(u.get("user_id")) for u in previous_users][cite: 1]
                other_ids_str = ", ".join(other_user_ids)[cite: 1]
                
                alert_msg = (
                    "🚨 **সন্দেহভাজন মাল্টি-অ্যাকাউন্ট উইথড্র অ্যালার্ট!**\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 ইউজারের নাম: {current_name}\n"
                    f"🆔 বর্তমান ইউজার আইডি: `{current_user_id}`\n"
                    f"📱 দেওয়া নম্বর: `{clean_num}` ({method})\n"
                    f"💵 উইথড্র পরিমাণ: ৳{withdraw_amount:.2f} BDT\n"
                    f"⚠️ পূর্বে একই নম্বর ব্যবহারকারী আইডি: `{other_ids_str}`\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "আপনি চাইলে নিচের বাটনে ক্লিক করে সিদ্ধান্ত নিতে পারেন:"
                )[cite: 1]
                
                markup = InlineKeyboardMarkup()[cite: 1]
                markup.row(
                    InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{current_user_id}"),
                    InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{current_user_id}")
                )[cite: 1]
                
                for admin_id in ADMIN_IDS:[cite: 1]
                    try:
                        bot.send_message(admin_id, alert_msg, parse_mode="Markdown", reply_markup=markup)[cite: 1]
                    except Exception as e:
                        print(f"Failed to send alert to admin {admin_id}: {e}")[cite: 1]
        except Exception as e:
            print(f"Duplicate withdraw check error: {e}")[cite: 1]
    
    threading.Thread(target=async_check, daemon=True).start()[cite: 1]

def check_user_channels(user_id):
    for channel in REQUIRED_CHANNELS:[cite: 1]
        try:
            member = bot.get_chat_member(channel, user_id)[cite: 1]
            if member.status in ['left', 'kicked']:[cite: 1]
                return False
        except Exception:
            return False
    return True[cite: 1]

def send_step_by_step_verification(chat_id, user_id, first_name):
    _, user = get_user(user_id, first_name)[cite: 1]
    
    if not user.get("verified_phone"):[cite: 1]
        bot.send_message(
            chat_id,
            "📱 **ধাপ ১: ফোন নম্বর ভেরিফিকেশন প্রয়োজন!**\n\nবটটি ব্যবহার শুরু করতে নিচের '📱 Share Contact' বাটনে ক্লিক করে আপনার টেলিগ্রাম নম্বর ভেরিফাই করুন।",
            reply_markup=contact_keyboard(),
            parse_mode="Markdown"
        )[cite: 1]
        return False

    if not user.get("device_verified", False):[cite: 1]
        server_domain = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")[cite: 1]
        browser_link = f"{server_domain}/verify-device?user_id={user_id}&name={first_name}"[cite: 1]

        markup = InlineKeyboardMarkup()[cite: 1]
        markup.add(InlineKeyboardButton("🌐 ১. ব্রাউজারে গিয়ে চেক করুন", url=browser_link))[cite: 1]
        markup.add(InlineKeyboardButton("✅ ২. ভেরিফাই কমপ্লিট করুন", callback_data="check_device_ip"))[cite: 1]

        bot.send_message(
            chat_id,
            "🛡️ **ধাপ ২: ডিভাইস ও আইপি সিকিউরিটি চেক!**\n\n"
            "👉 **ধাপ ১:** 'ব্রাউজারে গিয়ে চেক করুন' বাটনে ক্লিক করে ব্রাউজারে যান।\n"
            "👉 **ধাপ ২:** ব্রাউজার থেকে টেলিগ্রামে ফিরে এসে 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন.",
            reply_markup=markup,
            parse_mode="Markdown"
        )[cite: 1]
        return False

    if not check_user_channels(user_id):[cite: 1]
        markup = InlineKeyboardMarkup(row_width=1)[cite: 1]
        for channel in REQUIRED_CHANNELS:[cite: 1]
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))[cite: 1]
        markup.add(InlineKeyboardButton("✅ Checked / Verified", callback_data="check_join"))[cite: 1]
        
        bot.send_message(
            chat_id,
            "⚠️ **ধাপ ৩: চ্যানেল সাবস্ক্রিপশন চেক!**\n\nবটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:",
            reply_markup=markup,
            parse_mode="Markdown"
        )[cite: 1]
        return False

    return True[cite: 1]

def is_valid_bd_number(number_str):
    number_str = str(number_str).strip()[cite: 1]
    if len(number_str) == 11 and number_str.isdigit():[cite: 1]
        if number_str.startswith(("017", "018", "019", "016", "015", "013", "014")):[cite: 1]
            return True
    return False[cite: 1]

# --- KEYBOARDS ---
def contact_keyboard():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)[cite: 1]
    markup.add(KeyboardButton("📱 Share Contact", request_contact=True))[cite: 1]
    return markup[cite: 1]

def mini_app_inline_keyboard():
    markup = InlineKeyboardMarkup()[cite: 1]
    web_app = WebAppInfo(url=MINI_APP_URL)[cite: 1]
    markup.add(InlineKeyboardButton("🚀 Open App 🚀", web_app=web_app))[cite: 1]
    return markup[cite: 1]

def admin_dashboard_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)[cite: 1]
    markup.add(
        InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_panel_broadcast"),
        InlineKeyboardButton("📊 Bot Statistics", callback_data="adm_panel_stats"),
        InlineKeyboardButton("👤 Manage User", callback_data="adm_panel_manage"),
        InlineKeyboardButton("➕ Add Balance", callback_data="adm_panel_addbal"),
        InlineKeyboardButton("✂️ Cut Balance", callback_data="adm_panel_cutbal"),
        InlineKeyboardButton("❌ Close Panel", callback_data="adm_panel_close")
    )[cite: 1]
    return markup[cite: 1]

# --- LOOPS ---
def auto_post_loop():
    methods = ["bKash", "Nagad"][cite: 1]
    while True:
        try:
            time.sleep(180)[cite: 1]
            method = random.choice(methods)[cite: 1]
            amount_bdt = round(random.uniform(200.0, 800.0), 2)[cite: 1]
            
            prefix = random.choice(["017", "018", "019", "016", "015", "013", "014"])[cite: 1]
            fake_num = prefix + "".join([str(random.randint(0, 9)) for _ in range(8)])[cite: 1]
            masked_num = fake_num[:3] + "xxxxx" + fake_num[-2:][cite: 1]
            
            channel_msg = (
                "My Earning All Payment\n"
                "✅ Withdrawal Paid\n\n"
                f"💵 {amount_bdt:.2f} BDT\n"
                f"🌐 {method}\n"
                f"👛 {masked_num}"
            )[cite: 1]
            
            bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=channel_msg)[cite: 1]
        except Exception as e:
            print(f"Auto post loop error: {e}")[cite: 1]

def inactivity_push_loop():
    while True:
        try:
            time.sleep(3600)[cite: 1]
            active_users = get_all_active_users()[cite: 1]
            current_now = time.time()[cite: 1]
            day_in_seconds = 86400[cite: 1]

            for u in active_users:[cite: 1]
                last_act = u.get("last_active", 0)[cite: 1]
                last_push = u.get("last_inactivity_push", 0)[cite: 1]
                if (current_now - last_act >= day_in_seconds) and (current_now - last_push >= day_in_seconds):[cite: 1]
                    u_id = u.get("user_id")[cite: 1]
                    try:
                        bot.send_message(u_id, "আজকের এডগুলো দেখে আপনার আয় নিশ্চিত করুন!", reply_markup=mini_app_inline_keyboard())[cite: 1]
                        update_user_field(u_id, {"last_inactivity_push": current_now})[cite: 1]
                        time.sleep(0.05)[cite: 1]
                    except Exception as push_err:
                        print(f"Push error for user {u_id}: {push_err}")[cite: 1]
        except Exception as e:
            print(f"Inactivity push loop error: {e}")[cite: 1]

# --- WATCH AD HANDLERS ---
@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad")
def watch_ad_handler(message):
    user_id = message.from_user.id[cite: 1]
    _, user = get_user(user_id, message.from_user.first_name)[cite: 1]
    
    if user.get("is_banned", False):[cite: 1]
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")[cite: 1]
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):[cite: 1]
        return

    last_reset = user.get("last_reset", 0)[cite: 1]
    if user.get("captcha_locked", False) or user.get("daily_count", 0) >= 30:[cite: 1]
        if time.time() - last_reset >= 86400:[cite: 1]
            update_user_field(user_id, {"daily_count": 0, "captcha_locked": False, "last_reset": time.time()})[cite: 1]
            _, user = get_user(user_id)[cite: 1]
        else:
            remaining_time = int(86400 - (time.time() - last_reset))[cite: 1]
            hours = remaining_time // 3600[cite: 1]
            minutes = (remaining_time % 3600) // 60[cite: 1]
            bot.reply_to(message, f"❌ আপনার আজকের ৩০টি এড দেখা সম্পন্ন হয়েছে এবং ক্যাপচা লক রয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")[cite: 1]
            return

    current_count = user.get("daily_count", 0)[cite: 1]
    if current_count >= 30:[cite: 1]
        bot.reply_to(message, "❌ আজকের ৩০টি এড দেখা সম্পন্ন হয়েছে!")[cite: 1]
        return

    all_links = MONETAG_LINKS + ADSTERRA_LINKS[cite: 1]
    ad_link = random.choice(all_links)[cite: 1]

    current_time = time.time()[cite: 1]
    update_user_field(user_id, {"last_task_time": current_time, "can_claim": True})[cite: 1]

    markup = InlineKeyboardMarkup()[cite: 1]
    markup.add(InlineKeyboardButton("🌐 Visit Ad Link", url=ad_link))[cite: 1]
    markup.add(InlineKeyboardButton("🎁 Claim Reward", callback_data="claim_reward"))[cite: 1]

    bot.send_message(
        message.chat.id,
        f"📺 **বিজ্ঞাপন দেখুন এবং আয় করুন!**\n\n"
        f"👉 নিচের ভিজিট লিংকে ক্লিক করে ওয়েবসাইট ভিজিট করুন এবং অন্তত **২০ সেকেন্ড** অপেক্ষা করুন।\n"
        f"⏳ এরপর 'Claim Reward' বাটনে ক্লিক করে আপনার রিওয়ার্ড সংগ্রহ করুন。\n\n"
        f"📈 আজকের দেখা এড: {current_count}/30",
        reply_markup=markup,
        parse_mode="Markdown"
    )[cite: 1]

@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad 2")
def watch_ad_2_handler(message):
    user_id = message.from_user.id[cite: 1]
    _, user = get_user(user_id, message.from_user.first_name)[cite: 1]
    
    if user.get("is_banned", False):[cite: 1]
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")[cite: 1]
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):[cite: 1]
        return

    last_reset = user.get("ad2_last_reset", 0)[cite: 1]
    completed_today = user.get("ad2_completed_today", 0)[cite: 1]

    if completed_today >= 15:[cite: 1]
        if time.time() - last_reset >= 86400:[cite: 1]
            update_user_field(user_id, {"ad2_completed_today": 0, "ad2_index": 0, "ad2_last_reset": time.time()})[cite: 1]
            _, user = get_user(user_id)[cite: 1]
            completed_today = 0[cite: 1]
        else:
            remaining_time = int(86400 - (time.time() - last_reset))[cite: 1]
            hours = remaining_time // 3600[cite: 1]
            minutes = (remaining_time % 3600) // 60[cite: 1]
            bot.reply_to(message, f"❌ আপনার আজকের ১৫টি লিংকের কাজ সম্পন্ন হয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")[cite: 1]
            return

    current_index = user.get("ad2_index", 0)[cite: 1]
    if current_index >= len(WATCH_AD_2_LINKS):[cite: 1]
        current_index = 0[cite: 1]

    ad_link = WATCH_AD_2_LINKS[current_index][cite: 1]
    user_waiting_screenshot.add(user_id)[cite: 1]

    markup = InlineKeyboardMarkup(row_width=1)[cite: 1]
    markup.add(
        InlineKeyboardButton("🔗 Visit Link", url=ad_link),
        InlineKeyboardButton("📹 কিভাবে কাজ করবেন (ভিডিও)", url="https://t.me/allinoneg1/843")
    )[cite: 1]

    text_msg = (
        "📺 Watch Ad 2 - টাস্ক পেজ\n\n"
        "🔗 লিংক ক্লিক করার পর একটি স্ক্রিনশট নিবেন ভেরিফাই কমপ্লিট করবেন আর বাটনে ক্লিক করলে অ্যাড আসলে ব্যাক বাটনে ব্যাক করে আবার ক্লিক করবেন তারপর ইউটিউবে আপনাকে নিয়ে যাবে একটা স্ক্রিনশট নিবেন আপনার কাজ শেষ তারপর বটে ফিরে আসবেন স্ক্রিনশট দুটি পাঠিয়ে দিবেন ✅\n\n"
        f"💵 প্রতি কাজের রিওয়ার্ড: ৳0.10 টাকা\n"
        f"📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক"
    )[cite: 1]

    bot.send_message(message.chat.id, text_msg, reply_markup=markup, parse_mode="Markdown")[cite: 1]

@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad 3")
def watch_ad_3_handler(message):
    user_id = message.from_user.id[cite: 1]
    _, user = get_user(user_id, message.from_user.first_name)[cite: 1]
    
    if user.get("is_banned", False):[cite: 1]
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")[cite: 1]
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):[cite: 1]
        return

    last_reset = user.get("ad3_last_reset", 0)[cite: 1]
    completed_today = user.get("ad3_completed_today", 0)[cite: 1]

    if completed_today >= 15:[cite: 1]
        if time.time() - last_reset >= 86400:[cite: 1]
            update_user_field(user_id, {"ad3_completed_today": 0, "ad3_index": 0, "ad3_last_reset": time.time()})[cite: 1]
            _, user = get_user(user_id)[cite: 1]
            completed_today = 0[cite: 1]
        else:
            remaining_time = int(86400 - (time.time() - last_reset))[cite: 1]
            hours = remaining_time // 3600[cite: 1]
            minutes = (remaining_time % 3600) // 60[cite: 1]
            bot.reply_to(message, f"❌ আপনার আজকের ১৫টি exe.io লিংকের কাজ সম্পন্ন হয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")[cite: 1]
            return

    current_index = user.get("ad3_index", 0)[cite: 1]
    if current_index >= len(WATCH_AD_3_LINKS):[cite: 1]
        current_index = 0[cite: 1]

    ad_link = WATCH_AD_3_LINKS[current_index][cite: 1]
    user_waiting_ad3_screenshot.add(user_id)[cite: 1]

    markup = InlineKeyboardMarkup(row_width=1)[cite: 1]
    markup.add(
        InlineKeyboardButton("🔗 Visit Exe.io Link", url=ad_link),
        InlineKeyboardButton("📹 কিভাবে কাজ করবেন (ভিডিও)", url="https://t.me/allinoneg1/843")
    )[cite: 1]

    text_msg = (
        "📺 Watch Ad 3 - টাস্ক পেজ\n\n"
        "🔗 লিংক ক্লিক করার পর একটি স্ক্রিনশট নিবেন ভেরিফাই কমপ্লিট করবেন আর বাটনে ক্লিক করলে অ্যাড আসলে ব্যাক বাটনে ব্যাক করে আবার ক্লিক করবেন তারপর ShrinkMe তে আপনাকে নিয়ে যাবে একটা স্ক্রিনশট নিবেন আপনার কাজ শেষ তারপর বটে ফিরে আসবেন স্ক্রিনশট দুটি পাঠিয়ে দিবেন ✅\n\n"
        f"💵 প্রতি কাজের রিওয়ার্ড: ৳0.10 টাকা\n"
        f"📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক"
    )[cite: 1]

    bot.send_message(message.chat.id, text_msg, reply_markup=markup, parse_mode="Markdown")[cite: 1]

@bot.message_handler(content_types=['photo'])
def handle_user_screenshot(message):
    user_id = message.from_user.id[cite: 1]
    first_name = message.from_user.first_name[cite: 1]
    
    if user_id in user_waiting_screenshot:[cite: 1]
        user_waiting_screenshot.remove(user_id)[cite: 1]
        _, user = get_user(user_id, first_name)[cite: 1]
        
        file_id = message.photo[-1].file_id[cite: 1]
        completed_today = user.get("ad2_completed_today", 0) + 1[cite: 1]
        next_index = user.get("ad2_index", 0) + 1[cite: 1]

        markup = InlineKeyboardMarkup()[cite: 1]
        markup.row(
            InlineKeyboardButton("✅ Yes (Approve)", callback_data=f"scr_yes_{user_id}_{completed_today}_{next_index}"),
            InlineKeyboardButton("❌ No (Reject)", callback_data=f"scr_no_{user_id}")
        )[cite: 1]

        caption_text = (
            f"📥 **নতুন স্ক্রিনশট সাবমিশন (Watch Ad 2)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 ইউজার: {first_name}\n"
            f"🆔 ইউজার আইডি: `{user_id}`\n"
            f"📈 আজকের সম্পন্ন কাজ: {completed_today}/15\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"অ্যাডমিন, কাজের সত্যতা যাচাই করে নিচের বাটনে ক্লিক করুন:"
        )[cite: 1]

        try:
            bot.send_photo(SCREENSHOT_TARGET_CHANNEL, photo=file_id, caption=caption_text, parse_mode="Markdown", reply_markup=markup)[cite: 1]
            bot.reply_to(message, "✅ আপনার স্ক্রিনশটটি সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে!\nঅ্যাডমিন চেক করার পর আপনার ব্যালেন্সে রিওয়ার্ড যোগ করে দেওয়া হবে.", reply_markup=mini_app_inline_keyboard())[cite: 1]
        except Exception as e:
            print(f"Error sending screenshot to channel: {e}")[cite: 1]
            bot.reply_to(message, "❌ স্ক্রিনশট পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", reply_markup=mini_app_inline_keyboard())[cite: 1]
        return

    if user_id in user_waiting_ad3_screenshot:[cite: 1]
        user_waiting_ad3_screenshot.remove(user_id)[cite: 1]
        _, user = get_user(user_id, first_name)[cite: 1]
        
        file_id = message.photo[-1].file_id[cite: 1]
        completed_today = user.get("ad3_completed_today", 0) + 1[cite: 1]
        next_index = user.get("ad3_index", 0) + 1[cite: 1]

        markup = InlineKeyboardMarkup()[cite: 1]
        markup.row(
            InlineKeyboardButton("✅ Yes (Approve)", callback_data=f"ad3_yes_{user_id}_{completed_today}_{next_index}"),
            InlineKeyboardButton("❌ No (Reject)", callback_data=f"ad3_no_{user_id}")
        )[cite: 1]

        caption_text = (
            f"📥 **নতুন স্ক্রিনশট সাবমিশন (Watch Ad 3 - Exe.io)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 ইউজার: {first_name}\n"
            f"🆔 ইউজার আইডি: `{user_id}`\n"
            f"📈 আজকের সম্পন্ন কাজ: {completed_today}/15\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"অ্যাডমিন, কাজের সত্যতা যাচাই করে নিচের বাটনে ক্লিক করুন:"
        )[cite: 1]

        try:
            bot.send_photo(SCREENSHOT_TARGET_CHANNEL, photo=file_id, caption=caption_text, parse_mode="Markdown", reply_markup=markup)[cite: 1]
            bot.reply_to(message, "✅ আপনার Exe.io স্ক্রিনশটটি সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে!\nঅ্যাডমিন চেক করার পর আপনার ব্যালেন্সে রিওয়ার্ড যোগ করে দেওয়া হবে.", reply_markup=mini_app_inline_keyboard())[cite: 1]
        except Exception as e:
            print(f"Error sending ad3 screenshot to channel: {e}")[cite: 1]
            bot.reply_to(message, "❌ স্ক্রিনশট পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", reply_markup=mini_app_inline_keyboard())[cite: 1]
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("scr_yes_") or call.data.startswith("scr_no_") or call.data.startswith("ad3_yes_") or call.data.startswith("ad3_no_"))
def screenshot_approval_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    if call.from_user.id not in ADMIN_IDS:[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)[cite: 1]
        return

    data_parts = call.data.split("_")[cite: 1]
    prefix = data_parts[0][cite: 1]
    action = data_parts[1][cite: 1]
    target_user_id = int(data_parts[2])[cite: 1]

    if prefix == "scr":[cite: 1]
        if action == "yes":[cite: 1]
            completed_today = int(data_parts[3])[cite: 1]
            next_index = int(data_parts[4])[cite: 1]
            
            reward = 0.10[cite: 1]
            add_balance(target_user_id, reward)[cite: 1]
            
            update_user_field(target_user_id, {
                "ad2_completed_today": completed_today,
                "ad2_index": next_index
            })[cite: 1]

            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=call.message.caption + "\n\n✅ **স্ট্যাটাস: অ্যাপ্রুভড (Approved & Paid)**",
                    parse_mode="Markdown"
                )[cite: 1]
            except:
                pass

            try:
                bot.send_message(target_user_id, f"🎉 অভিনন্দন! আপনার স্ক্রিনশট অ্যাডমিন কর্তৃক অনুমোদিত হয়েছে। আপনি সফলভাবে ৳0.10 টাকা উপার্জন করেছেন!\n📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক", reply_markup=mini_app_inline_keyboard())[cite: 1]
            except:
                pass

        elif action == "no":[cite: 1]
            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=call.message.caption + "\n\n❌ **স্ট্যাটাস: রিজেক্টেড (Rejected)**",
                    parse_mode="Markdown"
                )[cite: 1]
            except:
                pass

            try:
                bot.send_message(target_user_id, "❌ দুঃখিত, আপনার সাবমিট করা স্ক্রিনশটটি সঠিক নয় বা রিজেক্ট করা হয়েছে। দয়া করে সঠিক নিয়মে আবার কাজ করুন.", reply_markup=mini_app_inline_keyboard())[cite: 1]
            except:
                pass

    elif prefix == "ad3":[cite: 1]
        if action == "yes":[cite: 1]
            completed_today = int(data_parts[3])[cite: 1]
            next_index = int(data_parts[4])[cite: 1]
            
            reward = 0.10[cite: 1]
            add_balance(target_user_id, reward)[cite: 1]
            
            update_user_field(target_user_id, {
                "ad3_completed_today": completed_today,
                "ad3_index": next_index
            })[cite: 1]

            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=call.message.caption + "\n\n✅ **স্ট্যাটাস: অ্যাপ্রুভড (Approved & Paid)**",
                    parse_mode="Markdown"
                )[cite: 1]
            except:
                pass

            try:
                bot.send_message(target_user_id, f"🎉 অভিনন্দন! আপনার Exe.io স্ক্রিনশট অ্যাডমিন কর্তৃক অনুমোদিত হয়েছে। আপনি সফলভাবে ৳0.10 টাকা উপার্জন করেছেন!\n📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক", reply_markup=mini_app_inline_keyboard())[cite: 1]
            except:
                pass

        elif action == "no":[cite: 1]
            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=call.message.caption + "\n\n❌ **স্ট্যাটাস: রিজেক্টেড (Rejected)**",
                    parse_mode="Markdown"
                )[cite: 1]
            except:
                pass

            try:
                bot.send_message(target_user_id, "❌ দুঃখিত, আপনার সাবমিট করা Exe.io স্ক্রিনশটটি সঠিক নয় বা রিজেক্ট করা হয়েছে। দয়া করে সঠিক নিয়মে আবার কাজ করুন.", reply_markup=mini_app_inline_keyboard())[cite: 1]
            except:
                pass

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:[cite: 1]
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")[cite: 1]
        return
    admin_msg = (
        "👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "নিচের বাটনগুলো ব্যবহার করে বটের যাবতীয় কার্যক্রম ম্যানেজ করুন:"
    )[cite: 1]
    bot.send_message(message.chat.id, admin_msg, reply_markup=admin_dashboard_keyboard(), parse_mode="Markdown")[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_panel_"))
def admin_panel_callbacks(call):
    bot.answer_callback_query(call.id)[cite: 1]
    if call.from_user.id not in ADMIN_IDS:[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)[cite: 1]
        return

    action = call.data.replace("adm_panel_", "")[cite: 1]
    if action == "close":[cite: 1]
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)[cite: 1]
        except:
            pass
    elif action == "stats":[cite: 1]
        all_u = get_all_active_users()[cite: 1]
        real_users = len(all_u)[cite: 1]
        stats_text = (
            f"📊 **বট সার্বিক পরিসংখ্যান (Stats)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট নিবন্ধিত ডাটাবেজ ইউজার: **{real_users}** জন\n"
            f"📈 ডিসপ্লেড ইউজার (ফেক সহ): **{FAKE_USER_OFFSET + real_users}** জন\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )[cite: 1]
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")[cite: 1]
    elif action == "broadcast":[cite: 1]
        admin_step[call.from_user.id] = {"action": "broadcast"}[cite: 1]
        bot.send_message(
            call.message.chat.id,
            "📢 **ব্রডকাস্ট মেসেজ পাঠান:**\n\nআপনি সব ইউজারের কাছে যে মেসেজ বা নোটিশটি পাঠাতে চান তা এখানে লিখে বা ফরোয়ার্ড করে পাঠান:\n\n*(বাতিল করতে /cancel টাইপ করুন)*",
            parse_mode="Markdown"
        )[cite: 1]
    elif action == "manage":[cite: 1]
        admin_step[call.from_user.id] = {"action": "manage_user"}[cite: 1]
        bot.send_message(call.message.chat.id, "👤 অনুগ্রহ করে যে ইউজারের বিবরণ দেখতে চান তার **User ID** লিখে পাঠান:")[cite: 1]
    elif action == "addbal":[cite: 1]
        admin_step[call.from_user.id] = {"action": "addbal_step1"}[cite: 1]
        bot.send_message(call.message.chat.id, "➕ যে ইউজারের অ্যাকাউন্টে ব্যালেন্স যোগ করবেন তার **User ID** দিন:")[cite: 1]
    elif action == "cutbal":[cite: 1]
        admin_step[call.from_user.id] = {"action": "cutbal_step1"}[cite: 1]
        bot.send_message(call.message.chat.id, "✂️ যে ইউজারের অ্যাকাউন্ট থেকে ব্যালেন্স কাটবেন তার **User ID** দিন:")[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_ban_") or call.data.startswith("adm_unban_"))
def admin_ban_unban_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    if call.from_user.id not in ADMIN_IDS:[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)[cite: 1]
        return
    parts = call.data.split("_")[cite: 1]
    action = parts[0] + "_" + parts[1][cite: 1]
    target_id = int(parts[2])[cite: 1]
    
    if action == "adm_ban":[cite: 1]
        update_user_field(target_id, {"is_banned": True})[cite: 1]
        bot.send_message(call.message.chat.id, f"🚫 ইউজার `{target_id}` কে সফলভাবে ব্যান করা হয়েছে।", parse_mode="Markdown")[cite: 1]
    elif action == "adm_unban":[cite: 1]
        update_user_field(target_id, {"is_banned": False})[cite: 1]
        bot.send_message(call.message.chat.id, f"✅ ইউজার `{target_id}` কে আনব্যান করা হয়েছে।", parse_mode="Markdown")[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    user_id = call.from_user.id[cite: 1]
    _, user_data = get_user(user_id, call.from_user.first_name)[cite: 1]
    if user_data.get("is_banned", False):[cite: 1]
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)[cite: 1]
        return

    if check_user_channels(user_id):[cite: 1]
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)[cite: 1]
        except:
            pass
        bot.send_message(
            call.message.chat.id,
            "✅ ধন্যবাদ! সমস্ত ভেরিফিকেশন সফলভাবে সম্পন্ন হয়েছে। এখন আপনি মিনি অ্যাপ ব্যবহার করতে পারেন:",
            reply_markup=mini_app_inline_keyboard()
        )[cite: 1]
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data == "claim_reward")
def claim_reward_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    user_id = call.from_user.id[cite: 1]
    _, user = get_user(user_id, call.from_user.first_name)[cite: 1]
    
    if user.get("is_banned", False):[cite: 1]
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)[cite: 1]
        return

    if user.get("captcha_locked", False):[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনার অ্যাকাউন্টটি ক্যাপচা দ্বারা লক করা আছে! অনুগ্রহ করে ক্যাপচা পূরণ করুন।", show_alert=True)[cite: 1]
        return

    if not user.get("can_claim", False):[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনি ইতিমধ্যে এই রিওয়ার্ড ক্লাইম করেছেন অথবা নতুন টাস্ক শুরু করুন!", show_alert=True)[cite: 1]
        return
        
    last_task = user.get("last_task_time", 0)[cite: 1]
    if time.time() - last_task < 20:[cite: 1]
        remaining = int(20 - (time.time() - last_task))[cite: 1]
        bot.answer_callback_query(call.id, f"⏳ আরও {remaining} সেকেন্ড অপেক্ষা করুন!", show_alert=True)[cite: 1]
        return

    reward = 0.10[cite: 1]
    add_balance(user_id, reward)[cite: 1]
    
    current_count = user.get("daily_count", 0) + 1[cite: 1]
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)[cite: 1]
    except:
        pass
        
    if current_count >= 30:[cite: 1]
        num1 = random.randint(10, 50)[cite: 1]
        num2 = random.randint(1, 20)[cite: 1]
        user_captcha_step[user_id] = num1 + num2[cite: 1]
        
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count, "captcha_locked": True, "last_reset": time.time()})[cite: 1]
        
        bot.send_message(
            call.message.chat.id,
            f"🎉 অভিনন্দন! আপনি আজকের ৩০টি এড দেখা সম্পূর্ণ করেছেন!\n\n"
            f"🔐 পরবর্তী কাজের জন্য আপনাকে একটি ম্যাথ ক্যাপচা পূরণ করতে হবে:\n"
            f"👉 কত হবে উত্তর: **{num1} + {num2} = ?**\n\n"
            f"সঠিক উত্তরটি চ্যাটে লিখে পাঠান:",
            parse_mode="Markdown"
        )[cite: 1]
    else:
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count})[cite: 1]
        bot.send_message(
            call.message.chat.id,
            f"🎉 অভিনন্দন! আপনি সফলভাবে ৳{reward:.2f} টাকা উপার্জন করেছেন。\n📈 আজকের দেখা মোট এড: {current_count}/30",
            reply_markup=mini_app_inline_keyboard()
        )[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_method_"))
def withdraw_method_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    user_id = call.from_user.id[cite: 1]
    _, user_data = get_user(user_id, call.from_user.first_name)[cite: 1]
    if user_data.get("is_banned", False):[cite: 1]
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)[cite: 1]
        return

    method = call.data.replace("w_method_", "")[cite: 1]
    balance, _ = get_user(user_id)[cite: 1]
    
    user_withdraw_step[user_id] = {
        'step': 'amount',
        'method': method
    }[cite: 1]
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)[cite: 1]
    except:
        pass
        
    bot.send_message(
        call.message.chat.id,
        f"💵 আপনি **{method}** এর মাধ্যমে উইথড্র করতে চান।\n\nবর্তমান ব্যালেন্স: **৳{balance:.2f} BDT**\n👉 আপনি কত টাকা উইথড্র করতে চান তা সংখ্যায় লিখে পাঠান (যেমন: 100):",
        parse_mode="Markdown"
    )[cite: 1]

@bot.callback_query_handler(func=lambda call: call.data == "check_device_ip")
def check_device_ip_callback(call):
    bot.answer_callback_query(call.id)[cite: 1]
    user_id = call.from_user.id[cite: 1]
    first_name = call.from_user.first_name[cite: 1]
    _, user = get_user(user_id, first_name)[cite: 1]
    
    if user.get("is_banned", False):[cite: 1]
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)[cite: 1]
        return

    user_ip = user.get("temp_ip")[cite: 1]
    if not user_ip:[cite: 1]
        bot.answer_callback_query(call.id, "❌ আপনি এখনো ব্রাউজারে গিয়ে লিংকটি ওপেন করেননি!", show_alert=True)[cite: 1]
        return

    def async_ip_check():
        existing_ip_user = None[cite: 1]
        if users_col is not None:[cite: 1]
            try:
                existing_ip_user = users_col.find_one({"last_ip": user_ip, "user_id": {"$ne": user_id}})[cite: 1]
            except Exception as e:
                print(f"IP Check Error: {e}")[cite: 1]

        if existing_ip_user:[cite: 1]
            other_id = existing_ip_user.get("user_id")[cite: 1]
            alert_msg = (
                "⚠️ **ডুপ্লিকেট ডিভাইস/আইপি ডিটেক্টেড!**\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"👤 ইউজার: {first_name} (ID: `{user_id}`)\n"
                f"🌐 আইপি: `{user_ip}`\n"
                f"🔗 আগে ব্যবহারকারী আইডি: `{other_id}`\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "ইউজার ভেরিফাই করেছে, আপনি চাইলে এখান থেকে ব্যবস্থা নিন:"
            )[cite: 1]
            
            markup = InlineKeyboardMarkup()[cite: 1]
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{user_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{user_id}")
            )[cite: 1]
            
            for admin_id in ADMIN_IDS:[cite: 1]
                try:
                    bot.send_message(admin_id, alert_msg, parse_mode="Markdown", reply_markup=markup)[cite: 1]
                except:
                    pass

    update_user_field(user_id, {"last_ip": user_ip, "device_verified": True})[cite: 1]
    threading.Thread(target=async_ip_check, daemon=True).start()[cite: 1]

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)[cite: 1]
    except:
        pass
        
    send_step_by_step_verification(call.message.chat.id, user_id, first_name)[cite: 1]

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id[cite: 1]
    first_name = message.from_user.first_name[cite: 1]
    
    args = message.text.split()[cite: 1]
    referred_by = None[cite: 1]
    if len(args) > 1 and args[1].isdigit():[cite: 1]
        ref_id = int(args[1])[cite: 1]
        if ref_id != user_id:[cite: 1]
            referred_by = ref_id[cite: 1]

    _, user = get_user(user_id, first_name, referred_by=referred_by)[cite: 1]
    if user.get("is_banned", False):[cite: 1]
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")[cite: 1]
        return

    if not send_step_by_step_verification(message.chat.id, user_id, first_name):[cite: 1]
        return

    remove_markup = ReplyKeyboardRemove()[cite: 1]
    bot.send_message(
        message.chat.id, 
        f"👋 স্বাগতম, 👤 {first_name}!\nআমাদের মিনি অ্যাপটি চালু করতে নিচের বাটনে ক্লিক করুন:",
        reply_markup=remove_markup
    )[cite: 1]

    bot.send_message(
        message.chat.id,
        "👇 অ্যাপ খুলুন:",
        reply_markup=mini_app_inline_keyboard()
    )[cite: 1]

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id[cite: 1]
    _, user_data = get_user(user_id, message.from_user.first_name)[cite: 1]
    if user_data.get("is_banned", False):[cite: 1]
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")[cite: 1]
        return

    if message.contact is not None:[cite: 1]
        phone_number = str(message.contact.phone_number).strip()[cite: 1]
        
        if users_col is not None:[cite: 1]
            existing_user = users_col.find_one({
                "verified_phone": phone_number, 
                "user_id": {"$ne": user_id}
            })[cite: 1]
            if existing_user:[cite: 1]
                bot.send_message(message.chat.id, "❌ **এই ফোন নম্বরটি দিয়ে ইতোমধ্যে একটি অ্যাকাউন্ট ভেরিফাই করা রয়েছে!**")[cite: 1]
                return

        update_user_field(user_id, {"verified_phone": phone_number, "last_active": time.time()})[cite: 1]
        bot.send_message(message.chat.id, "✅ আপনার ফোন নম্বর সফলভাবে ভেরিফাই হয়েছে!")[cite: 1]

        send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name)[cite: 1]

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id[cite: 1]
    text = message.text.strip() if message.text else ""[cite: 1]
    first_name = message.from_user.first_name[cite: 1]

    # মিনি অ্যাপ থেকে পাঠানো ডাটা হ্যান্ডেল করা
    if message.web_app_data:
        task = message.web_app_data.data
        if task == "Watch Ad":
            watch_ad_handler(message)
            return
        elif task == "Watch Ad 2":
            watch_ad_2_handler(message)
            return
        elif task == "Watch Ad 3":
            watch_ad_3_handler(message)
            return

    _, user_data = get_user(user_id, first_name)[cite: 1]
    if user_data.get("is_banned", False):[cite: 1]
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্লক/ব্যান করা হয়েছে। আপনি এই বট ব্যবহার করতে পারবেন না।")[cite: 1]
        return

    if text == "/cancel" and user_id in ADMIN_IDS:[cite: 1]
        if user_id in admin_step:[cite: 1]
            del admin_step[user_id][cite: 1]
        bot.send_message(message.chat.id, "❌ অ্যাডমিন অপারেশন বাতিল করা হয়েছে।")[cite: 1]
        return

    if user_id in ADMIN_IDS and user_id in admin_step:[cite: 1]
        state = admin_step[user_id].get("action")[cite: 1]
        if state == "broadcast":[cite: 1]
            del admin_step[user_id][cite: 1]
            all_users = get_all_active_users()[cite: 1]
            total = len(all_users)[cite: 1]
            success, failed = 0, 0[cite: 1]
            
            bot.send_message(message.chat.id, f"🚀 ব্রডকাস্টিং শুরু হচ্ছে... মোট ইউজার: {total}")[cite: 1]
            for u in all_users:[cite: 1]
                u_id = u.get("user_id")[cite: 1]
                try:
                    bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)[cite: 1]
                    success += 1[cite: 1]
                    time.sleep(0.04)[cite: 1]
                except Exception as e:
                    failed += 1[cite: 1]
            bot.send_message(message.chat.id, f"✅ **ব্রডকাস্ট সম্পন্ন হয়েছে!**\n📊 মোট প্রাপক: {total}\n✅ সফল: {success}\n❌ ব্যর্থ: {failed}", parse_mode="Markdown")[cite: 1]
            return

        elif state == "manage_user":[cite: 1]
            del admin_step[user_id][cite: 1]
            if not text.isdigit():[cite: 1]
                bot.send_message(message.chat.id, "❌ অকার্যকর ইউজার আইডি!")[cite: 1]
                return
            target_id = int(text)[cite: 1]
            _, target_user = get_user(target_id)[cite: 1]
            user_bal = target_user.get("balance", 0.0)[cite: 1]
            name = target_user.get("first_name", "Unknown")[cite: 1]
            ref_count = target_user.get("referrals_count", 0)[cite: 1]
            phone = target_user.get("verified_phone", "ভেরিফাই করা হয়নি")[cite: 1]
            is_banned = target_user.get("is_banned", False)[cite: 1]

            msg = (
                f"👤 **ইউজার প্যানেল**\n━━━━━━━━━━━━━━━━━━━\n"
                f"📛 নাম: {name}\n🆔 আইডি: `{target_id}`\n📱 ফোন: `{phone}`\n"
                f"💰 ব্যালেন্স: ৳{user_bal:.2f} BDT\n"
                f"👥 মোট রেফার: {ref_count} জন\n"
                f"🚫 স্ট্যাটাস: {'🚫 Banned' if is_banned else '✅ Active'}\n━━━━━━━━━━━━━━━━━━━"
            )[cite: 1]
            
            markup = InlineKeyboardMarkup()[cite: 1]
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_id}")
            )[cite: 1]

            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)[cite: 1]
            return

        elif state == "addbal_step1":[cite: 1]
            if not text.isdigit():[cite: 1]
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")[cite: 1]
                return
            admin_step[user_id] = {"action": "addbal_step2", "target_id": int(text)}[cite: 1]
            bot.send_message(message.chat.id, f"➕ যে ইউজারের অ্যাকাউন্টে ব্যালেন্স যোগ করবেন তার কত টাকা যোগ করতে চান তা লিখুন:")[cite: 1]
            return

        elif state == "addbal_step2":[cite: 1]
            target_id = admin_step[user_id].get("target_id")[cite: 1]
            del admin_step[user_id][cite: 1]
            try:
                amt = float(text)[cite: 1]
                add_balance(target_id, amt)[cite: 1]
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-কে ৳{amt:.2f} BDT প্রদান করা হয়েছে।", parse_mode="Markdown")[cite: 1]
                try:
                    bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে ৳{amt:.2f} BDT যোগ করা হয়েছে!")[cite: 1]
                except:
                    pass
            except ValueError:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")[cite: 1]
            return

        elif state == "cutbal_step1":[cite: 1]
            if not text.isdigit():[cite: 1]
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")[cite: 1]
                return
            admin_step[user_id] = {"action": "cutbal_step2", "target_id": int(text)}[cite: 1]
            bot.send_message(message.chat.id, f"✂️ যে ইউজারের অ্যাকাউন্ট থেকে ব্যালেন্স কাটবেন, কত টাকা কাটতে চান তা লিখুন:")[cite: 1]
            return

        elif state == "cutbal_step2":[cite: 1]
            target_id = admin_step[user_id].get("target_id")[cite: 1]
            del admin_step[user_id][cite: 1]
            try:
                amt = float(text)[cite: 1]
                current_bal, _ = get_user(target_id)[cite: 1]
                if amt > current_bal:[cite: 1]
                    amt = current_bal[cite: 1]
                
                add_balance(target_id, -amt)[cite: 1]
                bot.send_message(message.chat.id, f"✂️ ইউজার `{target_id}`-এর ব্যালেন্স থেকে ৳{amt:.2f} BDT কেটে নেওয়া হয়েছে।", parse_mode="Markdown")[cite: 1]
                try:
                    bot.send_message(target_id, f"⚠️ অ্যাডমিন আপনার অ্যাকাউন্ট থেকে ৳{amt:.2f} BDT কেটে নিয়েছেন।")[cite: 1]
                except:
                    pass
            except ValueError:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")[cite: 1]
            return

    if user_id in user_captcha_step:[cite: 1]
        try:
            ans = int(text)[cite: 1]
            correct_ans = user_captcha_step[user_id][cite: 1]
            if ans == correct_ans:[cite: 1]
                del user_captcha_step[user_id][cite: 1]
                update_user_field(user_id, {"captcha_locked": False})[cite: 1]
                bot.reply_to(message, "✅ ক্যাপচা সফলভাবে সমাধান হয়েছে! ২৪ ঘণ্টা পর আপনার কাজের লিমিট সম্পূর্ণ রিসেট হবে।", reply_markup=mini_app_inline_keyboard())[cite: 1]
            else:
                bot.reply_to(message, "❌ ভুল উত্তর! আবার সঠিক উত্তরটি লিখে পাঠান:")[cite: 1]
        except ValueError:
            bot.reply_to(message, "❌ দয়া করে সঠিক সংখ্যা লিখে উত্তর দিন:")[cite: 1]
        return

    if user_id in user_withdraw_step:[cite: 1]
        step_data = user_withdraw_step[user_id][cite: 1]
        if step_data['step'] == 'amount':[cite: 1]
            try:
                amt = float(text)[cite: 1]
                balance, _ = get_user(user_id)[cite: 1]
                if amt < MIN_WITHDRAW:[cite: 1]
                    bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র ৳{MIN_WITHDRAW:.2f} BDT। আবার সঠিক পরিমাণ লিখুন:")[cite: 1]
                    return
                if amt > balance:[cite: 1]
                    bot.reply_to(message, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! বর্তমান ব্যালেন্স: ৳{balance:.2f} BDT। সঠিক পরিমাণ লিখুন:")[cite: 1]
                    return
                
                step_data['amount'] = amt[cite: 1]
                step_data['step'] = 'number'[cite: 1]
                bot.send_message(message.chat.id, f"📱 আপনি **{step_data['method']}** নম্বরে উইথড্র করবেন।\n👉 আপনার ১১ ডিজিটের **{step_data['method']} নম্বর**টি লিখে পাঠান (যেমন: 017xxxxxxxx):", parse_mode="Markdown")[cite: 1]
            except ValueError:
                bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন (যেমন: 100):")[cite: 1]
            return
            
        elif step_data['step'] == 'number':[cite: 1]
            number = text[cite: 1]
            if not is_valid_bd_number(number):[cite: 1]
                bot.reply_to(message, "❌ ভুল নম্বর! সঠিক ১১ ডিজিটের বিকাশ/নগদ নম্বর দিন (যেমন: 017xxxxxxxx):")[cite: 1]
                return
                
            method = step_data['method'][cite: 1]
            amount_bdt = step_data['amount'][cite: 1]
            
            del user_withdraw_step[user_id][cite: 1]
            add_balance(user_id, -amount_bdt)[cite: 1]
            add_payment_history(user_id, method, amount_bdt, number)[cite: 1]
            
            check_duplicate_withdraw_number(user_id, first_name, number, method, amount_bdt)[cite: 1]
            
            channel_msg = (
                "My Earning All Payment\n"
                "✅ Withdrawal Paid\n\n"
                f"💵 {amount_bdt:.2f} BDT\n"
                f"🌐 {method}\n"
                f"👛 {str(number)[:3]}xxxxx{str(number)[-2:]}"
            )[cite: 1]
            try:
                bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=channel_msg)[cite: 1]
            except Exception as e:
                print(f"Channel post error: {e}")[cite: 1]

            _, current_user_data = get_user(user_id)[cite: 1]
            user_phone = current_user_data.get("verified_phone", "নেই")[cite: 1]
            ref_count = current_user_data.get("referrals_count", 0)[cite: 1]
            admin_alert = (
                f"👤 নাম: {first_name}\n"
                f"🆔 আইডি: `{user_id}`\n"
                f"📱 ফোন: {user_phone}\n"
                f"💰 ব্যালেন্স: ৳{current_user_data.get('balance', 0.0):.2f} BDT\n"
                f"👥 মোট রেফারেল: {ref_count} জন\n\n"
                f"💸 **নতুন উইথড্র রিকোয়েস্ট:**\n"
                f"💵 পরিমাণ: ৳{amount_bdt:.2f} BDT\n"
                f"🌐 মেথড: {method}\n"
                f"👛 নম্বর: `{number}`"
            )[cite: 1]
            for admin_id in ADMIN_IDS:[cite: 1]
                try:
                    bot.send_message(admin_id, admin_alert, parse_mode="Markdown")[cite: 1]
                except Exception as e:
                    print(f"Admin notification error: {e}")[cite: 1]

            bot.send_message(
                message.chat.id,
                f"✅ **উইথড্র সফলভাবে সাবমিট হয়েছে!**\n\n"
                f"💵 পরিমাণ: ৳{amount_bdt:.2f} BDT\n"
                f"🌐 মেথড: {method}\n"
                f"📱 নম্বর: `{number}`\n\n"
                f"⏳ ২৪ ঘণ্টার মধ্যে পেমেন্ট পৌঁছে যাবে।",
                reply_markup=mini_app_inline_keyboard(),
                parse_mode="Markdown"
            )[cite: 1]
            return

    if not send_step_by_step_verification(message.chat.id, user_id, first_name):[cite: 1]
        return

    bot.send_message(
        message.chat.id,
        "নিচের বাটনে ক্লিক করে অ্যাপ ওপেন করুন:",
        reply_markup=mini_app_inline_keyboard()
    )[cite: 1]

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    SERVER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")[cite: 1]
    
    bot.remove_webhook()[cite: 1]
    time.sleep(1)[cite: 1]
    bot.set_webhook(url=f"{SERVER_URL}/{BOT_TOKEN}")[cite: 1]
    print(f"Webhook set to: {SERVER_URL}/{BOT_TOKEN}")[cite: 1]

    threading.Thread(target=auto_post_loop, daemon=True).start()[cite: 1]
    threading.Thread(target=inactivity_push_loop, daemon=True).start()[cite: 1]

    print("Telegram Bot is running with Ultra Fast Webhook...")[cite: 1]
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))[cite: 1]
