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
)

# --- CONFIGURATION ---
BOT_TOKEN = "8615856288:AAFhhFONNIB56invYKb00GfUxkExtuU0C3k"
MONGO_URI = os.environ.get("MONGO_URI", "")

BOT_USERNAME = "myearningall01_bot"
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1", "@allinoneg2"]
PROOF_CHANNEL = "@myearningall"

# স্ক্রিনশট সাবমিট হওয়ার নির্দিষ্ট চ্যানেল (আপনার দেওয়া লিংক অনুযায়ী)
SCREENSHOT_TARGET_CHANNEL = "@allinoneg3"

PAYMENT_BANNER_URL = "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=800"

MIN_WITHDRAW = 1.0    # সর্বনিম্ন উইথড্র ১ ডলার
USDT_TO_BDT = 110.0   # ১ ডলার = ১১০ টাকা
REFERRAL_BONUS = 0.005
FAKE_USER_OFFSET = 506  # ৫০৬+ ফেক ইউজার কাউন্ট

# --- TIMEZONE FUNCTION (Bangladesh Time GMT+6) ---
def get_bd_time_str():
    bd_tz = timezone(timedelta(hours=6))
    bd_now = datetime.now(bd_tz)
    return bd_now.strftime("%Y-%m-%d %I:%M:%S %p")

# --- ADMIN IDS ---
ADMIN_IDS = [8414665404, 5034445579]

# --- 10 MONETAG & 10 ADSTERRA LINKS ---
MONETAG_LINKS = [
    'https://omg10.com/4/11522087',
    'https://omg10.com/4/11522086',
    'https://omg10.com/4/11522081',
    'https://omg10.com/4/11522080',
    'https://omg10.com/4/11522079',
    'https://omg10.com/4/11522078',
    'https://omg10.com/4/11522077',
    'https://omg10.com/4/11522076',
    'https://omg10.com/4/11522074',
    'https://omg10.com/4/11516146'
]

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
]

# --- WATCH AD 2 15 SHRINKME LINKS ---
WATCH_AD_2_LINKS = [
    'https://shrinkme.click/g2qGUb',
    'https://shrinkme.click/8Uar',
    'https://shrinkme.click/ptEvVdG',
    'https://shrinkme.click/ndirPw',
    'https://shrinkme.click/LwsLmzvi',
    'https://shrinkme.click/p4MaWq3R',
    'https://shrinkme.click/0jOAuZOk',
    'https://shrinkme.click/EIZYof',
    'https://shrinkme.click/ALuVs5',
    'https://shrinkme.click/9SB8',
    'https://shrinkme.click/UYMQ',
    'https://shrinkme.click/ven3VA7p',
    'https://shrinkme.click/xTRge',
    'https://shrinkme.click/MjwBLrK',
    'https://shrinkme.click/U9Tetn2'
]

# --- DATABASE SETUP ---
users_col = None
memory_users = {}

if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, maxPoolSize=100)
        db = client["telegram_bot"]
        users_col = db["users"]
        print("MongoDB Connected Successfully.")
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=50)
app = Flask(__name__)

# --- WEBHOOK & FLASK ROUTES ---
@app.route('/')
def home():
    return "Bot is running with Webhook!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Invalid request", 403

# --- FLASK ROUTE FOR BROWSER IP & DEVICE VERIFICATION ---
@app.route('/verify-device')
def verify_device():
    user_id = request.args.get('user_id')
    first_name = request.args.get('name', 'User')
    
    if not user_id:
        return "<h3>❌ Invalid Request!</h3>", 400

    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip and ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()

    target_id = int(user_id)
    
    if users_col is not None:
        try:
            users_col.update_one({"user_id": target_id}, {"$set": {"temp_ip": user_ip}}, upsert=True)
        except Exception as e:
            print(f"IP Save Error: {e}")

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
                আপনার ডিভাইস এবং আইপি ভেরিফিকেশন প্রক্রিয়া প্রায় শেষ। নিচের বাটনে ক্লিক করে টেলিগ্রামে ফিরে যান এবং 'Verify Device Now' বাটনে ক্লিক করুন।
            </p>
            <br>
            <a href="https://t.me/{BOT_USERNAME}" style="background:#0088cc; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block;">
                📥 টেলিগ্রামে ফিরে যান
            </a>
        </div>
    </body>
    </html>
    """

# --- MEMORY TRACKING ---
user_withdraw_step = {}
user_captcha_step = {}
admin_step = {}
user_waiting_screenshot = set()

# --- DATABASE HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    current_now = time.time()
    
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
        "ad2_last_reset": current_now
    }

    if users_col is None:
        if user_id not in memory_users:
            memory_users[user_id] = default_user_data
        else:
            memory_users[user_id]["last_active"] = current_now
        return memory_users[user_id].get("balance", 0.0), memory_users[user_id]
        
    try:
        user = users_col.find_one({"user_id": user_id})
        if not user:
            user = default_user_data
            users_col.insert_one(user)
            
            if referred_by:
                ref_user = users_col.find_one({"user_id": referred_by})
                if ref_user and not ref_user.get("is_banned", False):
                    users_col.update_one({"user_id": referred_by}, {"$inc": {"balance": REFERRAL_BONUS, "referrals_count": 1}})
                    try:
                        bot.send_message(referred_by, f"🎉 আপনার রেফারেল লিংকের মাধ্যমে নতুন ইউজার যুক্ত হয়েছে! আপনি পেয়েছেন ${REFERRAL_BONUS:.3f} USDT বোনাস।")
                    except:
                        pass
        else:
            users_col.update_one({"user_id": user_id}, {"$set": {"last_active": current_now}})
            user["last_active"] = current_now

        return user.get("balance", 0.0), user
    except Exception as e:
        print(f"DB Error: {e}")
        return 0.0, default_user_data

def update_user_field(user_id, field_dict):
    if users_col is not None:
        try:
            users_col.update_one({"user_id": user_id}, {"$set": field_dict}, upsert=True)
        except Exception as e:
            print(f"DB Update Error: {e}")
    if user_id in memory_users:
        memory_users[user_id].update(field_dict)

def add_balance(user_id, amount):
    if users_col is not None:
        try:
            users_col.update_one({"user_id": user_id}, {"$inc": {"balance": float(amount)}})
        except Exception as e:
            print(f"DB Balance Error: {e}")
    if user_id in memory_users:
        memory_users[user_id]["balance"] = memory_users[user_id].get("balance", 0.0) + float(amount)

def add_payment_history(user_id, method, amount_usdt, amount_bdt, number):
    record = {
        "method": method,
        "amount_usdt": amount_usdt,
        "amount_bdt": amount_bdt,
        "number": str(number).strip(),
        "date": get_bd_time_str()
    }
    if users_col is not None:
        try:
            users_col.update_one({"user_id": user_id}, {"$push": {"history": record}})
        except Exception as e:
            print(f"DB History Error: {e}")
    if user_id in memory_users:
        if "history" not in memory_users[user_id]:
            memory_users[user_id]["history"] = []
        memory_users[user_id]["history"].append(record)

def get_all_active_users():
    if users_col is not None:
        try:
            return list(users_col.find({"is_banned": {"$ne": True}}))
        except Exception as e:
            print(f"Error fetching users: {e}")
    return [u for u in memory_users.values() if not u.get("is_banned", False)]

def check_duplicate_withdraw_number(current_user_id, current_name, number, method, withdraw_amount, bdt_amount):
    if users_col is None:
        return
    try:
        clean_num = str(number).strip()
        previous_users = list(users_col.find({"history.number": clean_num, "user_id": {"$ne": current_user_id}}))
        
        if previous_users:
            other_user_ids = [str(u.get("user_id")) for u in previous_users]
            other_ids_str = ", ".join(other_user_ids)
            
            alert_msg = (
                "🚨 **সন্দেহভাজন মাল্টি-অ্যাকাউন্ট উইথড্র অ্যালার্ট!**\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"👤 ইউজারের নাম: {current_name}\n"
                f"🆔 বর্তমান ইউজার আইডি: `{current_user_id}`\n"
                f"📱 দেওয়া নম্বর: `{clean_num}` ({method})\n"
                f"💵 উইথড্র পরিমাণ: ${withdraw_amount:.4f} USDT (={bdt_amount:.2f} BDT)\n"
                f"⚠️ পূর্বে একই নম্বর ব্যবহারকারী আইডি: `{other_ids_str}`\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "আপনি চাইলে নিচের বাটনে ক্লিক করে সিদ্ধান্ত নিতে পারেন:"
            )
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{current_user_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{current_user_id}")
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, alert_msg, parse_mode="Markdown", reply_markup=markup)
                except Exception as e:
                    print(f"Failed to send alert to admin {admin_id}: {e}")
    except Exception as e:
        print(f"Duplicate withdraw check error: {e}")

def check_user_channels(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def send_force_join_msg(chat_id):
    markup = InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(InlineKeyboardButton("✅ Checked / Verified", callback_data="check_join"))
    
    bot.send_message(
        chat_id,
        "⚠️ বটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:",
        reply_markup=markup
    )

def is_valid_bd_number(number_str):
    number_str = str(number_str).strip()
    if len(number_str) == 11 and number_str.isdigit():
        if number_str.startswith(("017", "018", "019", "016", "015", "013", "014")):
            return True
    return False

# --- KEYBOARDS ---
def contact_keyboard():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("📱 Share Contact", request_contact=True))
    return markup

def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📺 Watch Ad"),
        KeyboardButton("📺 Watch Ad 2"),
        KeyboardButton("🖥 Account"),
        KeyboardButton("📜 Payment History"),
        KeyboardButton("✨ Referral"),
        KeyboardButton("💸 Withdraw"),
        KeyboardButton("📩 Support")
    )
    return markup

def admin_dashboard_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_panel_broadcast"),
        InlineKeyboardButton("📊 Bot Statistics", callback_data="adm_panel_stats"),
        InlineKeyboardButton("👤 Manage User", callback_data="adm_panel_manage"),
        InlineKeyboardButton("➕ Add Balance", callback_data="adm_panel_addbal"),
        InlineKeyboardButton("✂️ Cut Balance", callback_data="adm_panel_cutbal"),
        InlineKeyboardButton("❌ Close Panel", callback_data="adm_panel_close")
    )
    return markup

# --- LOOPS ---
def auto_post_loop():
    methods = ["bKash", "Nagad"]
    while True:
        try:
            time.sleep(180)
            method = random.choice(methods)
            amount_usdt = round(random.uniform(2.0, 8.0), 3)
            amount_bdt = round(amount_usdt * USDT_TO_BDT, 2)
            
            prefix = random.choice(["017", "018", "019", "016", "015", "013", "014"])
            fake_num = prefix + "".join([str(random.randint(0, 9)) for _ in range(8)])
            masked_num = fake_num[:3] + "xxxxx" + fake_num[-2:]
            
            channel_msg = (
                "My Earning All Payment\n"
                "✅ Withdrawal Paid\n\n"
                f"💵 {amount_usdt} USDT ({amount_bdt} BDT)\n"
                f"🌐 {method}\n"
                f"👛 {masked_num}"
            )
            
            bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=channel_msg)
        except Exception as e:
            print(f"Auto post loop error: {e}")

def inactivity_push_loop():
    while True:
        try:
            time.sleep(3600)
            active_users = get_all_active_users()
            current_now = time.time()
            day_in_seconds = 86400

            for u in active_users:
                last_act = u.get("last_active", 0)
                last_push = u.get("last_inactivity_push", 0)
                if (current_now - last_act >= day_in_seconds) and (current_now - last_push >= day_in_seconds):
                    u_id = u.get("user_id")
                    try:
                        bot.send_message(u_id, "আজকের এডগুলো দেখে আপনার আয় নিশ্চিত করুন!")
                        update_user_field(u_id, {"last_inactivity_push": current_now})
                        time.sleep(0.05)
                    except Exception as push_err:
                        print(f"Push error for user {u_id}: {push_err}")
        except Exception as e:
            print(f"Inactivity push loop error: {e}")

# --- WATCH AD HANDLER ---
@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad")
def watch_ad_handler(message):
    user_id = message.from_user.id
    _, user = get_user(user_id, message.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if user.get("captcha_locked", False):
        bot.reply_to(message, "❌ আপনার অ্যাকাউন্টটি ক্যাপচা দ্বারা লক করা আছে! সঠিক উত্তর দিয়ে আনলক করুন।")
        return

    current_count = user.get("daily_count", 0)
    if current_count >= 30:
        bot.reply_to(message, "❌ আজকের ৩০টি এড দেখা সম্পন্ন হয়েছে! ক্যাপচা পূরণ করে লিমিট রিসেট করুন।")
        return

    all_links = MONETAG_LINKS + ADSTERRA_LINKS
    ad_link = random.choice(all_links)

    current_time = time.time()
    update_user_field(user_id, {"last_task_time": current_time, "can_claim": True})

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🌐 Visit Ad Link", url=ad_link))
    markup.add(InlineKeyboardButton("🎁 Claim Reward", callback_data="claim_reward"))

    bot.send_message(
        message.chat.id,
        f"📺 **বিজ্ঞাপন দেখুন এবং আয় করুন!**\n\n"
        f"👉 নিচের ভিজিট লিংকে ক্লিক করে ওয়েবসাইট ভিজিট করুন এবং অন্তত **১৫ সেকেন্ড** অপেক্ষা করুন。\n"
        f"⏳ এরপর 'Claim Reward' বাটনে ক্লিক করে আপনার রিওয়ার্ড সংগ্রহ করুন。\n\n"
        f"📈 আজকের দেখা এড: {current_count}/30",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- WATCH AD 2 HANDLER (UPDATED FOR SCREENSHOT SUBMISSION) ---
@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad 2")
def watch_ad_2_handler(message):
    user_id = message.from_user.id
    _, user = get_user(user_id, message.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    last_reset = user.get("ad2_last_reset", 0)
    if time.time() - last_reset >= 86400:
        update_user_field(user_id, {"ad2_completed_today": 0, "ad2_index": 0, "ad2_last_reset": time.time()})
        _, user = get_user(user_id)

    completed_today = user.get("ad2_completed_today", 0)
    if completed_today >= 15:
        bot.reply_to(message, "❌ আপনার আজকের ১৫টি লিংকের কাজ সম্পন্ন হয়েছে! লিমিট রিসেট হবে ২৪ ঘণ্টা পর।")
        return

    current_index = user.get("ad2_index", 0)
    if current_index >= len(WATCH_AD_2_LINKS):
        current_index = 0

    ad_link = WATCH_AD_2_LINKS[current_index]
    bdt_val = 0.001 * USDT_TO_BDT

    user_waiting_screenshot.add(user_id)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌐 Visit Link & Watch YouTube", url=ad_link),
        InlineKeyboardButton("📹 কিভাবে কাজ করবেন (ভিডিও)", url="https://t.me/allinoneg1/843")
    )

    bot.send_message(
        message.chat.id,
        f"📺 **Watch Ad 2 - টাস্ক পেজ**\n\n"
        f"👉 নিচের **Visit Link & Watch YouTube** এ ক্লিক করে ShrinkMe পার হয়ে সরাসরি ইউটিউব ভিডিওটি সম্পূর্ণ দেখুন।\n"
        f"📸 ইউটিউব ভিডিও দেখার পর তার একটি **স্ক্রিনশট** সরাসরি এই বটে চ্যাটে পাঠিয়ে দিন!\n"
        f"⚠️ স্ক্রিনশট পাঠানোর সাথে সাথে সেটি অ্যাডমিনের কাছে চলে যাবে এবং অ্যাপ্রুভ হলে ব্যালেন্সে টাকা যোগ হবে।\n\n"
        f"💵 প্রতি কাজের রিওয়ার্ড: `0.001 USDT` (={bdt_val:.2f} টাকা)\n"
        f"📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- PHOTO/SCREENSHOT HANDLER FOR WATCH AD 2 ---
@bot.message_handler(content_types=['photo'])
def handle_user_screenshot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    if user_id not in user_waiting_screenshot:
        return

    user_waiting_screenshot.remove(user_id)
    _, user = get_user(user_id, first_name)
    
    file_id = message.photo[-1].file_id
    completed_today = user.get("ad2_completed_today", 0) + 1
    next_index = user.get("ad2_index", 0) + 1

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes (Approve)", callback_data=f"scr_yes_{user_id}_{completed_today}_{next_index}"),
        InlineKeyboardButton("❌ No (Reject)", callback_data=f"scr_no_{user_id}")
    )

    caption_text = (
        f"📥 **নতুন স্ক্রিনশট সাবমিশন (Watch Ad 2)**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ইউজার: {first_name}\n"
        f"🆔 ইউজার আইডি: `{user_id}`\n"
        f"📈 আজকের সম্পন্ন কাজ: {completed_today}/15\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"অ্যাডমিন, কাজের সত্যতা যাচাই করে নিচের বাটনে ক্লিক করুন:"
    )

    try:
        bot.send_photo(SCREENSHOT_TARGET_CHANNEL, photo=file_id, caption=caption_text, parse_mode="Markdown", reply_markup=markup)
        
        bot.reply_to(
            message,
            "✅ আপনার স্ক্রিনশটটি সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে!\nঅ্যাডমিন চেক করার পর আপনার ব্যালেন্সে রিওয়ার্ড যোগ করে দেওয়া হবে।",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        print(f"Error sending screenshot to channel: {e}")
        bot.reply_to(message, "❌ স্ক্রিনশট পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", reply_markup=main_menu_keyboard())

# --- SCREENSHOT APPROVAL CALLBACK (ADMIN ACTION) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("scr_yes_") or call.data.startswith("scr_no_"))
def screenshot_approval_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    data_parts = call.data.split("_")
    action = data_parts[1]
    target_user_id = int(data_parts[2])

    if action == "yes":
        completed_today = int(data_parts[3])
        next_index = int(data_parts[4])
        
        reward = 0.001
        add_balance(target_user_id, reward)
        
        update_user_field(target_user_id, {
            "ad2_completed_today": completed_today,
            "ad2_index": next_index
        })

        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=call.message.caption + "\n\n✅ **স্ট্যাটাস: অ্যাপ্রুভড (Approved & Paid)**",
                parse_mode="Markdown"
            )
        except:
            pass

        bot.answer_callback_query(call.id, "✅ সফলভাবে পেমেন্ট প্রদান করা হয়েছে!")
        
        try:
            bot.send_message(
                target_user_id,
                f"🎉 অভিনন্দন! আপনার স্ক্রিনশট অ্যাডমিন কর্তৃক অনুমোদিত হয়েছে। আপনি সফলভাবে $0.001 USDT উপার্জন করেছেন!\n📈 সম্পন্ন হয়েছে: {completed_today}/15 টি লিংক",
                reply_markup=main_menu_keyboard()
            )
        except:
            pass

    elif action == "no":
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=call.message.caption + "\n\n❌ **স্ট্যাটাস: রিজেক্টেড (Rejected)**",
                parse_mode="Markdown"
            )
        except:
            pass

        bot.answer_callback_query(call.id, "❌ স্ক্রিনশটটি বাতিল করা হয়েছে।")
        
        try:
            bot.send_message(
                target_user_id,
                "❌ দুঃখিত, আপনার সাবমিট করা স্ক্রিনশটটি সঠিক নয় বা রিজেক্ট করা হয়েছে। দয়া করে সঠিক নিয়মে আবার কাজ করুন।",
                reply_markup=main_menu_keyboard()
            )
        except:
            pass

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    admin_msg = (
        "👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "নিচের বাটনগুলো ব্যবহার করে বটের যাবতীয় কার্যক্রম ম্যানেজ করুন:"
    )
    bot.send_message(message.chat.id, admin_msg, reply_markup=admin_dashboard_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_panel_"))
def admin_panel_callbacks(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    action = call.data.replace("adm_panel_", "")
    if action == "close":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
    elif action == "stats":
        all_u = get_all_active_users()
        real_users = len(all_u)
        stats_text = (
            f"📊 **বট সার্বিক পরিসংখ্যান (Stats)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট নিবন্ধিত ডাটাবেজ ইউজার: **{real_users}** জন\n"
            f"📈 ডিসপ্লেড ইউজার (ফেক সহ): **{FAKE_USER_OFFSET + real_users}** জন\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")
    elif action == "broadcast":
        admin_step[call.from_user.id] = {"action": "broadcast"}
        bot.send_message(
            call.message.chat.id,
            "📢 **ব্রডকাস্ট মেসেজ পাঠান:**\n\nআপনি সব ইউজারের কাছে যে মেসেজ বা নোটিশটি পাঠাতে চান তা এখানে লিখে বা ফরোয়ার্ড করে পাঠান:\n\n*(বাতিল করতে /cancel টাইপ করুন)*",
            parse_mode="Markdown"
        )
    elif action == "manage":
        admin_step[call.from_user.id] = {"action": "manage_user"}
        bot.send_message(call.message.chat.id, "👤 অনুগ্রহ করে যে ইউজারের বিবরণ দেখতে চান তার **User ID** লিখে পাঠান:")
    elif action == "addbal":
        admin_step[call.from_user.id] = {"action": "addbal_step1"}
        bot.send_message(call.message.chat.id, "➕ যে ইউজারের অ্যাকাউন্টে ব্যালেন্স যোগ করবেন তার **User ID** দিন:")
    elif action == "cutbal":
        admin_step[call.from_user.id] = {"action": "cutbal_step1"}
        bot.send_message(call.message.chat.id, "✂️ যে ইউজারের অ্যাকাউন্ট থেকে ব্যালেন্স কাটবেন তার **User ID** দিন:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_ban_") or call.data.startswith("adm_unban_"))
def admin_ban_unban_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return
    parts = call.data.split("_")
    action = parts[0] + "_" + parts[1]
    target_id = int(parts[2])
    
    if action == "adm_ban":
        update_user_field(target_id, {"is_banned": True})
        bot.answer_callback_query(call.id, f"User {target_id} banned successfully.")
        bot.send_message(call.message.chat.id, f"🚫 ইউজার `{target_id}` কে সফলভাবে ব্যান করা হয়েছে।", parse_mode="Markdown")
    elif action == "adm_unban":
        update_user_field(target_id, {"is_banned": False})
        bot.answer_callback_query(call.id, f"User {target_id} unbanned successfully.")
        bot.send_message(call.message.chat.id, f"✅ ইউজার `{target_id}` কে আনব্যান করা হয়েছে।", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    _, user_data = get_user(user_id, call.from_user.first_name)
    if user_data.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    if check_user_channels(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(
            call.message.chat.id,
            "✅ ধন্যবাদ! চ্যানেল ভেরিফিকেশন সফল হয়েছে। এখন আপনি নিচের মেনু থেকে কাজ করতে পারেন:",
            reply_markup=main_menu_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

# --- CLAIM REWARD & CAPTCHA FLOW ---
@bot.callback_query_handler(func=lambda call: call.data == "claim_reward")
def claim_reward_callback(call):
    user_id = call.from_user.id
    _, user = get_user(user_id, call.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    if user.get("captcha_locked", False):
        bot.answer_callback_query(call.id, "❌ আপনার অ্যাকাউন্টটি ক্যাপচা দ্বারা লক করা আছে! অনুগ্রহ করে ক্যাপচা পূরণ করুন।", show_alert=True)
        return

    if not user.get("can_claim", False):
        bot.answer_callback_query(call.id, "❌ আপনি ইতিমধ্যে এই রিওয়ার্ড ক্লাইম করেছেন অথবা নতুন টাস্ক শুরু করুন!", show_alert=True)
        return
        
    last_task = user.get("last_task_time", 0)
    if time.time() - last_task < 15:
        remaining = int(15 - (time.time() - last_task))
        bot.answer_callback_query(call.id, f"⏳ আরও {remaining} সেকেন্ড অপেক্ষা করুন!", show_alert=True)
        return

    reward = 0.001
    add_balance(user_id, reward)
    
    current_count = user.get("daily_count", 0) + 1
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    if current_count >= 30:
        num1 = random.randint(10, 50)
        num2 = random.randint(1, 20)
        ans = num1 + num2
        user_captcha_step[user_id] = ans
        
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count, "captcha_locked": True})
        
        bot.send_message(
            call.message.chat.id,
            f"🎉 অভিনন্দন! আপনি আজকের ৩০টি এড দেখা সম্পূর্ণ করেছেন!\n\n"
            f"🔐 পরবর্তী কাজের জন্য আপনাকে একটি ম্যাথ ক্যাপচা পূরণ করতে হবে:\n"
            f"👉 কত হবে উত্তর: **{num1} + {num2} = ?**\n\n"
            f"সঠিক উত্তরটি চ্যাটে লিখে পাঠান:",
            parse_mode="Markdown"
        )
    else:
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count})
        bot.send_message(
            call.message.chat.id,
            f"🎉 অভিনন্দন! আপনি সফলভাবে ${reward:.3f} USDT উপার্জন করেছেন।\n📈 আজকের দেখা মোট এড: {current_count}/30",
            reply_markup=main_menu_keyboard()
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_method_"))
def withdraw_method_callback(call):
    user_id = call.from_user.id
    _, user_data = get_user(user_id, call.from_user.first_name)
    if user_data.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    method = call.data.replace("w_method_", "")
    balance, _ = get_user(user_id)
    
    user_withdraw_step[user_id] = {
        'step': 'amount',
        'method': method
    }
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    bot.send_message(
        call.message.chat.id,
        f"💵 আপনি **{method}** এর মাধ্যমে উইথড্র করতে চান।\n\nবর্তমান ব্যালেন্স: **${balance:.4f} USDT**\n👉 আপনি কত USDT উইথড্র করতে চান তা সংখ্যায় লিখে পাঠান (যেমন: 1.0):",
        parse_mode="Markdown"
    )

# --- BROWSER DEVICE VERIFICATION CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data == "check_device_ip")
def check_device_ip_callback(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    _, user = get_user(user_id, first_name)
    
    if user.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    user_ip = user.get("temp_ip")
    if not user_ip:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো ব্রাউজারে গিয়ে লিংকটি ওপেন করেননি!", show_alert=True)
        return

    existing_ip_user = None
    if users_col is not None:
        try:
            existing_ip_user = users_col.find_one({"last_ip": user_ip, "user_id": {"$ne": user_id}})
        except Exception as e:
            print(f"IP Check Error: {e}")

    update_user_field(user_id, {"last_ip": user_ip, "device_verified": True})

    if existing_ip_user:
        other_id = existing_ip_user.get("user_id")
        
        alert_msg = (
            "⚠️ **ডুপ্লিকেট ডিভাইস/আইপি ডিটেক্টেড!**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 ইউজার: {first_name} (ID: `{user_id}`)\n"
            f"🌐 আইপি: `{user_ip}`\n"
            f"🔗 আগে ব্যবহারকারী আইডি: `{other_id}`\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "ইউজার ভেরিফাই করেছে, আপনি চাইলে এখান থেকে ব্যবস্থা নিন:"
        )
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{user_id}"),
            InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{user_id}")
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, alert_msg, parse_mode="Markdown", reply_markup=markup)
            except:
                pass

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    bot.send_message(
        call.message.chat.id,
        "✅ **ডিভাইস ভেরিফিকেশন সফল হয়েছে!**\n\nএখন আপনি নিচের মেনু থেকে বট ব্যবহার করতে পারবেন:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            referred_by = ref_id

    _, user = get_user(user_id, first_name, referred_by=referred_by)
    if user.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if not user.get("verified_phone"):
        bot.send_message(
            message.chat.id,
            "📱 **ফোন নম্বর ভেরিফিকেশন প্রয়োজন!**\n\nবটটি ব্যবহার শুরু করতে নিচের '📱 Share Contact' বাটনে ক্লিক করে আপনার টেলিগ্রাম নম্বর ভেরিফাই করুন।",
            reply_markup=contact_keyboard(),
            parse_mode="Markdown"
        )
        return

    if not user.get("device_verified", False):
        server_domain = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
        browser_link = f"{server_domain}/verify-device?user_id={user_id}&name={first_name}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌐 ১. ব্রাউজারে গিয়ে চেক করুন", url=browser_link))
        markup.add(InlineKeyboardButton("✅ ২. ভেরিফাই কমপ্লিট করুন", callback_data="check_device_ip"))

        bot.send_message(
            message.chat.id,
            f"👋 স্বাগতম, 👤 {first_name}!\n\n"
            "🛡️ বটটি ব্যবহার করার জন্য আপনাকে সিকিউরিটি ভেরিফিকেশন সম্পন্ন করতে হবে:\n\n"
            "👉 **ধাপ ১:** 'ব্রাউজারে গিয়ে চেক করুন' বাটনে ক্লিক করে ব্রাউজারে যান।\n"
            "👉 **ধাপ ২:** ব্রাউজার থেকে টেলিগ্রামে ফিরে এসে 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন।",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 স্বাগতম, 👤 {first_name}!\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:",
            reply_markup=main_menu_keyboard()
        )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    _, user_data = get_user(user_id, message.from_user.first_name)
    if user_data.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if message.contact is not None:
        phone_number = str(message.contact.phone_number).strip()
        
        if users_col is not None:
            existing_user = users_col.find_one({
                "verified_phone": phone_number, 
                "user_id": {"$ne": user_id}
            })
            if existing_user:
                bot.send_message(message.chat.id, "❌ **এই ফোন নম্বরটি দিয়ে ইতোমধ্যে একটি অ্যাকাউন্ট ভেরিফাই করা রয়েছে!**")
                return

        update_user_field(user_id, {"verified_phone": phone_number, "last_active": time.time()})
        bot.send_message(message.chat.id, "✅ আপনার ফোন নম্বর সফলভাবে ভেরিফাই হয়েছে!", reply_markup=main_menu_keyboard())

        _, user = get_user(user_id)
        if not user.get("device_verified", False):
            server_domain = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
            browser_link = f"{server_domain}/verify-device?user_id={user_id}&name={message.from_user.first_name}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🌐 ১. ব্রাউজারে গিয়ে চেক করুন", url=browser_link))
            markup.add(InlineKeyboardButton("✅ ২. ভেরিফাই কমপ্লিট করুন", callback_data="check_device_ip"))

            bot.send_message(
                message.chat.id,
                "🛡️ বটটি ব্যবহার করার জন্য আপনাকে সিকিউরিটি ভেরিফিকেশন সম্পন্ন করতে হবে:\n\n"
                "👉 **ধাপ ১:** 'ব্রাউজারে গিয়ে চেক করুন' বাটনে ক্লিক করে ব্রাউজারে যান।\n"
                "👉 **ধাপ ২:** ব্রাউজার থেকে টেলিগ্রামে ফিরে এসে 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন।",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

        if not check_user_channels(user_id):
            send_force_join_msg(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    _, user_data = get_user(user_id, first_name)
    if user_data.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্লক/ব্যান করা হয়েছে। আপনি এই বট ব্যবহার করতে পারবেন না।")
        return

    if text == "/cancel" and user_id in ADMIN_IDS:
        if user_id in admin_step:
            del admin_step[user_id]
        bot.send_message(message.chat.id, "❌ অ্যাডমিন অপারেশন বাতিল করা হয়েছে।")
        return

    if user_id in ADMIN_IDS and user_id in admin_step:
        state = admin_step[user_id].get("action")
        if state == "broadcast":
            del admin_step[user_id]
            all_users = get_all_active_users()
            total = len(all_users)
            success, failed = 0, 0
            
            bot.send_message(message.chat.id, f"🚀 ব্রডকাস্টিং শুরু হচ্ছে... মোট ইউজার: {total}")
            for u in all_users:
                u_id = u.get("user_id")
                try:
                    bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    success += 1
                    time.sleep(0.04)
                except Exception as e:
                    failed += 1
            bot.send_message(message.chat.id, f"✅ **ব্রডকাস্ট সম্পন্ন হয়েছে!**\n📊 মোট প্রাপক: {total}\n✅ সফল: {success}\n❌ ব্যর্থ: {failed}", parse_mode="Markdown")
            return

        elif state == "manage_user":
            del admin_step[user_id]
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ অকার্যকর ইউজার আইডি!")
                return
            target_id = int(text)
            _, target_user = get_user(target_id)
            user_bal = target_user.get("balance", 0.0)
            bdt_val = user_bal * USDT_TO_BDT
            name = target_user.get("first_name", "Unknown")
            ref_count = target_user.get("referrals_count", 0)
            phone = target_user.get("verified_phone", "ভেরিফাই করা হয়নি")
            is_banned = target_user.get("is_banned", False)

            msg = (
                f"👤 **ইউজার প্যানেল**\n━━━━━━━━━━━━━━━━━━━\n"
                f"📛 নাম: {name}\n🆔 আইডি: `{target_id}`\n📱 ফোন: `{phone}`\n"
                f"💰 ব্যালেন্স: ${user_bal:.4f} USDT (={bdt_val:.2f} টাকা)\n"
                f"👥 মোট রেফার: {ref_count} জন\n"
                f"🚫 স্ট্যাটাস: {'🚫 Banned' if is_banned else '✅ Active'}\n━━━━━━━━━━━━━━━━━━━"
            )
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_id}")
            )

            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
            return

        elif state == "addbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")
                return
            admin_step[user_id] = {"action": "addbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, f"💰 আইডি `{text}`-এর জন্য কত USDT যোগ করতে চান তা লিখুন:")
            return

        elif state == "addbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, amt)
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-কে ${amt:.4f} USDT প্রদান করা হয়েছে।", parse_mode="Markdown")
                try:
                    bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে ${amt:.4f} USDT যোগ করা হয়েছে!")
                except:
                    pass
            except ValueError:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

        elif state == "cutbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")
                return
            admin_step[user_id] = {"action": "cutbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, f"✂️ যে ইউজারের অ্যাকাউন্ট থেকে ব্যালেন্স কাটবেন তার **User ID** দিন:")
            return

        elif state == "cutbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, -amt)
                bot.send_message(message.chat.id, f"✂️ ইউজার `{target_id}`-এর ব্যালেন্স থেকে ${amt:.4f} USDT কেটে নেওয়া হয়েছে।", parse_mode="Markdown")
            except ValueError:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

    if user_id in user_captcha_step:
        try:
            ans = int(text)
            correct_ans = user_captcha_step[user_id]
            if ans == correct_ans:
                del user_captcha_step[user_id]
                update_user_field(user_id, {"captcha_locked": False, "daily_count": 0})
                bot.reply_to(message, "✅ ক্যাপচা সফলভাবে সমাধান হয়েছে! আপনার লিমিট রিসেট করা হয়েছে। এখন আবার কাজ করতে পারেন।", reply_markup=main_menu_keyboard())
            else:
                bot.reply_to(message, "❌ ভুল উত্তর! আবার সঠিক উত্তরটি লিখে পাঠান:")
        except ValueError:
            bot.reply_to(message, "❌ দয়া করে সঠিক সংখ্যা লিখে উত্তর দিন:")
        return

    if user_id in user_withdraw_step:
        step_data = user_withdraw_step[user_id]
        if step_data['step'] == 'amount':
            try:
                amt = float(text)
                balance, _ = get_user(user_id)
                if amt < MIN_WITHDRAW:
                    bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র ${MIN_WITHDRAW} USDT। আবার সঠিক পরিমাণ লিখুন:")
                    return
                if amt > balance:
                    bot.reply_to(message, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! বর্তমান ব্যালেন্স: ${balance:.4f} USDT। সঠিক পরিমাণ লিখুন:")
                    return
                
                step_data['amount'] = amt
                step_data['step'] = 'number'
                bot.send_message(message.chat.id, f"📱 আপনি **{step_data['method']}** নম্বরে উইথড্র করবেন।\n👉 আপনার ১১ ডিজিটের **{step_data['method']} নম্বর**টি লিখে পাঠান (যেমন: 017xxxxxxxx):", parse_mode="Markdown")
            except ValueError:
                bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন (যেমন: 1.0):")
            return
            
        elif step_data['step'] == 'number':
            number = text
            if not is_valid_bd_number(number):
                bot.reply_to(message, "❌ ভুল নম্বর! সঠিক ১১ ডিজিটের বিকাশ/নগদ নম্বর দিন (যেমন: 017xxxxxxxx):")
                return
                
            method = step_data['method']
            amount_usdt = step_data['amount']
            amount_bdt = amount_usdt * USDT_TO_BDT
            
            del user_withdraw_step[user_id]
            add_balance(user_id, -amount_usdt)
            add_payment_history(user_id, method, amount_usdt, amount_bdt, number)
            
            check_duplicate_withdraw_number(user_id, first_name, number, method, amount_usdt, amount_bdt)
            
            channel_msg = (
                "My Earning All Payment\n"
                "✅ Withdrawal Paid\n\n"
                f"💵 {amount_usdt:.3f} USDT ({amount_bdt:.2f} BDT)\n"
                f"🌐 {method}\n"
                f"👛 {str(number)[:3]}xxxxx{str(number)[-2:]}"
            )
            try:
                bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=channel_msg)
            except Exception as e:
                print(f"Channel post error: {e}")

            _, current_user_data = get_user(user_id)
            user_phone = current_user_data.get("verified_phone", "নেই")
            ref_count = current_user_data.get("referrals_count", 0)
            admin_alert = (
                f"👤 নাম: {first_name}\n"
                f"🆔 আইডি: `{user_id}`\n"
                f"📱 ফোন: {user_phone}\n"
                f"💰 ব্যালেন্স: ${current_user_data.get('balance', 0.0):.4f} USDT (={current_user_data.get('balance', 0.0)*USDT_TO_BDT:.2f} BDT)\n"
                f"👥 মোট রেফারেল: {ref_count} জন\n\n"
                f"💸 **নতুন উইথড্র রিকোয়েস্ট:**\n"
                f"💵 পরিমাণ: ${amount_usdt:.3f} USDT ({amount_bdt:.2f} BDT)\n"
                f"🌐 মেথড: {method}\n"
                f"👛 নম্বর: `{number}`"
            )
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, admin_alert, parse_mode="Markdown")
                except Exception as e:
                    print(f"Admin notification error: {e}")

            bot.send_message(
                message.chat.id,
                f"✅ **উইথড্র সফলভাবে সাবমিট হয়েছে!**\n\n"
                f"💵 পরিমাণ: ${amount_usdt:.3f} USDT (={amount_bdt:.2f} BDT)\n"
                f"🌐 মেথড: {method}\n"
                f"📱 নম্বর: `{number}`\n\n"
                f"⏳ ২৪ ঘণ্টার মধ্যে পেমেন্ট পৌঁছে যাবে।",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return

    if text == "🖥 Account":
        balance, user = get_user(user_id, first_name)
        bdt_val = balance * USDT_TO_BDT
        phone = user.get("verified_phone", "ভেরিফাই করা হয়নি")
        ref_count = user.get("referrals_count", 0)
        bot.send_message(
            message.chat.id,
            f"🖥 **আপনার অ্যাকাউন্ট বিবরণী**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 নাম: {first_name}\n"
            f"🆔 আইডি: `{user_id}`\n"
            f"📱 ফোন: `{phone}`\n"
            f"💰 ব্যালেন্স: **${balance:.4f} USDT** (={bdt_val:.2f} BDT)\n"
            f"👥 মোট রেফারেল: {ref_count} জন\n"
            f"━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        return

    elif text == "✨ Referral":
        _, user = get_user(user_id, first_name)
        ref_count = user.get("referrals_count", 0)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.send_message(
            message.chat.id,
            f"✨ **রেফারেল প্রোগ্রাম**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"প্রতিটি সফল রেফারেলের জন্য পাবেন **${REFERRAL_BONUS:.3f} USDT** বোনাস!\n\n"
            f"🔗 আপনার রেফারেল লিংক:\n`{ref_link}`\n\n"
            f"👥 মোট রেফার: {ref_count} জন",
            parse_mode="Markdown"
        )
        return

    elif text == "💸 Withdraw":
        balance, user = get_user(user_id, first_name)
        if user.get("captcha_locked", False):
            bot.reply_to(message, "❌ আপনার অ্যাকাউন্টটি ক্যাপচা লক করা আছে। আগে ক্যাপচা পূরণ করুন।")
            return
        if balance < MIN_WITHDRAW:
            bot.reply_to(message, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। সর্বনিম্ন উইথড্র ${MIN_WITHDRAW} USDT। বর্তমান ব্যালেন্স: ${balance:.4f} USDT")
            return
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("bKash", callback_data="w_method_bKash"),
            InlineKeyboardButton("Nagad", callback_data="w_method_Nagad")
        )
        bot.send_message(
            message.chat.id,
            f"💸 **উইথড্র সেকশন**\n\nবর্তমান ব্যালেন্স: **${balance:.4f} USDT**\n👉 পেমেন্ট মেথড সিলেক্ট করুন:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    elif text == "📜 Payment History":
        _, user = get_user(user_id, first_name)
        history = user.get("history", [])
        if not history:
            bot.send_message(message.chat.id, "📜 আপনার কোনো পেমেন্ট হিস্ট্রি নেই।")
            return
        
        hist_text = "📜 **আপনার শেষ ৫টি উইথড্র রেকর্ড:**\n━━━━━━━━━━━━━━━━━━━\n"
        for h in history[-5:]:
            hist_text += f"💳 {h['method']} | ${h['amount_usdt']:.3f} ({h['amount_bdt']:.2f} BDT)\n📱 `{h['number']}`\n🕒 {h['date']}\n\n"
        bot.send_message(message.chat.id, hist_text, parse_mode="Markdown")
        return

    elif text == "📩 Support":
        bot.send_message(
            message.chat.id,
            "🌐 ALL IN ONE 🌐\n\n"
            "🖇️ আমাদের সাপোর্ট গ্রুপ লিংক: https://t.me/allinoneg1\n\n"
            "✅ টেলিগ্রাম এডমিন লিংক: @akadmin02"
        )
        return

# --- MAIN EXECUTION (WEBHOOK SETUP) ---
if __name__ == '__main__':
    SERVER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
    
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{SERVER_URL}/{BOT_TOKEN}")
    print(f"Webhook set to: {SERVER_URL}/{BOT_TOKEN}")

    threading.Thread(target=auto_post_loop, daemon=True).start()
    threading.Thread(target=inactivity_push_loop, daemon=True).start()

    print("Telegram Bot is running with Webhook...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
