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
SCREENSHOT_REVIEW_CHANNEL = "-1002360214695" # আপনার allinoneg3 চ্যানেলের আইডি

PAYMENT_BANNER_URL = "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=800"

MIN_WITHDRAW = 1.0    # সর্বনিম্ন উইথড্র ১ ডলার
USDT_TO_BDT = 110.0   # ১ ডলার = ১১০ টাকা
REWARD_PER_LINK = 0.001 # প্রতি লিংকে আয়
REFERRAL_BONUS = 0.005
FAKE_USER_OFFSET = 506  # ৫০৬+ ফেক ইউজার কাউন্ট
VIDEO_TUTORIAL_URL = "https://t.me/allinoneg1/843"

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

# --- Watch Ad 2 নতুন ১৫টি লিংক ---
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

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running with Webhook!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid request', 403

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

user_withdraw_step = {}
user_captcha_step = {}
admin_step = {}
user_ad2_state = {}

def get_user(user_id, first_name="User", referred_by=None):
    current_now = time.time()
    
    if users_col is None:
        if user_id not in memory_users:
            memory_users[user_id] = {
                "user_id": user_id, 
                "first_name": str(first_name)[:30],
                "balance": 0.0, 
                "daily_count": 0,
                "ad2_count": 0,
                "ad2_last_reset": current_now,
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
                "last_inactivity_push": 0
            }
        else:
            memory_users[user_id]["last_active"] = current_now
        return memory_users[user_id].get("balance", 0.0), memory_users[user_id]
        
    try:
        user = users_col.find_one({"user_id": user_id})
        if not user:
            user = {
                "user_id": user_id, 
                "first_name": str(first_name)[:30],
                "balance": 0.0, 
                "daily_count": 0,
                "ad2_count": 0,
                "ad2_last_reset": current_now,
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
                "last_inactivity_push": 0
            }
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
        return 0.0, {"user_id": user_id, "first_name": first_name, "balance": 0.0, "is_banned": False, "verified_phone": None, "device_verified": False}

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
        bot.reply_to(message, "❌ আজকের ৩০টি এড দেখা সম্পন্ন হয়েছে!")
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
        f"👉 লিংকে ক্লিক করে ওয়েবসাইট ভিজিট করুন এবং অন্তত **১৫ সেকেন্ড** অপেক্ষা করুন。\n"
        f"⏳ এরপর 'Claim Reward' বাটনে ক্লিক করুন。\n\n"
        f"📈 আজকের দেখা এড: {current_count}/30",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad 2")
def watch_ad_2_handler(message):
    user_id = message.from_user.id
    _, user = get_user(user_id, message.from_user.first_name)

    if user.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    current_time = time.time()
    last_reset = user.get("ad2_last_reset", current_time)
    if current_time - last_reset >= 86400:
        update_user_field(user_id, {"ad2_count": 0, "ad2_last_reset": current_time})
        user["ad2_count"] = 0

    ad2_count = user.get("ad2_count", 0)
    if ad2_count >= 15:
        bot.reply_to(message, "❌ আজকের ১৫টি লিংক ক্লিকের লিমিট শেষ! দয়া করে ২৪ ঘণ্টা পর আবার চেষ্টা করুন।")
        return

    ad_link = random.choice(WATCH_AD_2_LINKS)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔗 Visit Link & Watch YouTube", url=ad_link))
    markup.add(InlineKeyboardButton("✅ ব্রাউজার থেকে ফিরে এসেছি (স্ক্রিনশট পাঠান)", callback_data="ad2_ready_to_send"))
    markup.add(InlineKeyboardButton("🎥 কিভাবে কাজ করবেন (ভিডিও গাইড)", url=VIDEO_TUTORIAL_URL))

    bot.send_message(
        message.chat.id,
        f"📺 **Watch Ad 2 (Task Section)**\n\n"
        f"📌 **নির্দেশনা:**\n"
        f"১. উপরে **'Visit Link & Watch YouTube'** এ ক্লিক করে ব্রাউজারে যান এবং কাজ শেষ করুন।\n"
        f"২. কাজ শেষ করে যখন টেলিগ্রামে ফিরবেন, তখন নিচের **'✅ ব্রাউজার থেকে ফিরে এসেছি'** বাটনে ক্লিক করুন।\n"
        f"৩. এরপর স্ক্রিনশট এখানে পাঠিয়ে দিন।\n\n"
        f"📈 আজকের সম্পন্ন লিংক: {ad2_count}/15",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "ad2_ready_to_send")
def ad2_ready_callback(call):
    user_id = call.from_user.id
    user_ad2_state[user_id] = True
    bot.answer_callback_query(call.id, "এখন আপনার স্ক্রিনশটটি এই চ্যাটে পাঠান!", show_alert=True)
    bot.send_message(
        call.message.chat.id,
        "📸 **ধন্যবাদ!** এখন আপনার কাজের স্ক্রিনশটটি এই চ্যাটে পাঠিয়ে দিন।"
    )

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    admin_msg = (
        "👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "নিচের বাটনগুলো ব্যবহার করে বটের কার্যক্রম ম্যানেজ করুন:"
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
            "📢 **ব্রডকাস্ট মেসেজ পাঠান:**\n\nসকলের কাছে যে মেসেজ পাঠাতে চান তা লিখে পাঠান:\n\n*(বাতিল করতে /cancel টাইপ করুন)*",
            parse_mode="Markdown"
        )
    elif action == "manage":
        admin_step[call.from_user.id] = {"action": "manage_user"}
        bot.send_message(call.message.chat.id, "👤 ইউজারের **User ID** লিখে পাঠান:")
    elif action == "addbal":
        admin_step[call.from_user.id] = {"action": "addbal_step1"}
        bot.send_message(call.message.chat.id, "➕ ব্যালেন্স যোগ করতে **User ID** দিন:")
    elif action == "cutbal":
        admin_step[call.from_user.id] = {"action": "cutbal_step1"}
        bot.send_message(call.message.chat.id, "✂️ ব্যালেন্স কাটতে **User ID** দিন:")

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
            "✅ ধন্যবাদ! চ্যানেল ভেরিফিকেশন সফল হয়েছে। এখন মেনু থেকে কাজ করতে পারেন:",
            reply_markup=main_menu_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "claim_reward")
def claim_reward_callback(call):
    user_id = call.from_user.id
    _, user = get_user(user_id, call.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!", show_alert=True)
        return

    if not user.get("can_claim", False):
        bot.answer_callback_query(call.id, "❌ ইতিমধ্যে রিওয়ার্ড ক্লাইম করা হয়েছে!", show_alert=True)
        return

    reward = 0.001
    add_balance(user_id, reward)
    current_count = user.get("daily_count", 0) + 1
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    update_user_field(user_id, {"can_claim": False, "daily_count": current_count})
    bot.send_message(
        call.message.chat.id,
        f"🎉 অভিনন্দন! ${reward:.3f} USDT উপার্জন করেছেন।\n📈 মোট এড: {current_count}/30",
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
    
    user_withdraw_step[user_id] = {'step': 'amount', 'method': method}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    bot.send_message(
        call.message.chat.id,
        f"💵 **{method}** এর মাধ্যমে উইথড্র। বর্তমান ব্যালেন্স: **${balance:.4f} USDT**\n👉 কত USDT উইথড্র করবেন তা লিখুন:",
        parse_mode="Markdown"
    )

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
        bot.answer_callback_query(call.id, "❌ আপনি ব্রাউজারে গিয়ে লিংক ওপেন করেননি!", show_alert=True)
        return

    update_user_field(user_id, {"last_ip": user_ip, "device_verified": True})
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    bot.send_message(
        call.message.chat.id,
        "✅ **ডিভাইস ভেরিফিকেশন সফল হয়েছে!**",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad2_app_") or call.data.startswith("ad2_rej_"))
def ad2_admin_action(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    parts = call.data.split("_")
    action = parts[0] + "_" + parts[1]
    target_user_id = int(parts[2])

    if action == "ad2_app":
        add_balance(target_user_id, REWARD_PER_LINK)
        _, t_user = get_user(target_user_id)
        new_count = t_user.get("ad2_count", 0) + 1
        update_user_field(target_user_id, {"ad2_count": new_count})

        try:
            bot.send_message(target_user_id, f"✅ আপনার Watch Ad 2 এর স্ক্রিনশট অনুমোদিত হয়েছে! অ্যাকাউন্টে ${REWARD_PER_LINK} USDT যোগ করা হয়েছে।")
        except:
            pass
        bot.answer_callback_query(call.id, "Approved successfully!")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
    elif action == "ad2_rej":
        try:
            bot.send_message(target_user_id, "❌ আপনার Watch Ad 2 এর স্ক্রিনশট রিজেক্ট করা হয়েছে! অনুগ্রহ করে নিয়ম মেনে সঠিক স্ক্রিনশট দিন।")
        except:
            pass
        bot.answer_callback_query(call.id, "Rejected!")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass

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
            "📱 **ফোন নম্বর ভেরিফিকেশন প্রয়োজন!**\n\nনিচের '📱 Share Contact' বাটনে ক্লিক করে নম্বর ভেরিফাই করুন।",
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
            f"👋 স্বাগতম, 👤 {first_name}!\n\nসিকিউরিটি ভেরিফিকেশন সম্পন্ন করুন:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 স্বাগতম, 👤 {first_name}!\n\nনিচের মেনু থেকে কাজ শুরু করুন:",
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
        update_user_field(user_id, {"verified_phone": phone_number, "last_active": time.time()})
        bot.send_message(message.chat.id, "✅ ফোন নম্বর সফলভাবে ভেরিফাই হয়েছে!", reply_markup=main_menu_keyboard())

        _, user = get_user(user_id)
        if not user.get("device_verified", False):
            server_domain = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
            browser_link = f"{server_domain}/verify-device?user_id={user_id}&name={message.from_user.first_name}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🌐 ১. ব্রাউজারে গিয়ে চেক করুন", url=browser_link))
            markup.add(InlineKeyboardButton("✅ ২. ভেরিফাই কমপ্লিট করুন", callback_data="check_device_ip"))

            bot.send_message(message.chat.id, "সিকিউরিটি ভেরিফিকেশন সম্পন্ন করুন:", reply_markup=markup, parse_mode="Markdown")
            return

        if not check_user_channels(user_id):
            send_force_join_msg(message.chat.id)

@bot.message_handler(content_types=['photo'])
def handle_photos_or_screenshots(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    _, user = get_user(user_id, first_name)

    if user.get("is_banned", False):
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Approve", callback_data=f"ad2_app_{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"ad2_rej_{user_id}")
    )

    caption_text = (
        f"📸 **Watch Ad 2 স্ক্রিনশট সাবমিশন**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {first_name}\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    try:
        bot.forward_message(chat_id=SCREENSHOT_REVIEW_CHANNEL, from_chat_id=message.chat.id, message_id=message.message_id)
        bot.send_message(SCREENSHOT_REVIEW_CHANNEL, caption_text, parse_mode="Markdown", reply_markup=markup)
        
        bot.reply_to(message, "✅ আপনার স্ক্রিনশট সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে! শীঘ্রই পেমেন্ট পেয়ে যাবেন।")
        if user_id in user_ad2_state:
            del user_ad2_state[user_id]
    except Exception as e:
        print(f"Screenshot forward error: {e}")
        bot.reply_to(message, "❌ স্ক্রিনশট পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    _, user_data = get_user(user_id, first_name)
    if user_data.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্লক/ব্যান করা হয়েছে।")
        return

    if text == "/cancel" and user_id in ADMIN_IDS:
        if user_id in admin_step:
            del admin_step[user_id]
        bot.send_message(message.chat.id, "❌ অপারেশন বাতিল করা হয়েছে।")
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
                except:
                    failed += 1
            bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন! সফল: {success}, ব্যর্থ: {failed}")
            return

        elif state == "manage_user":
            del admin_step[user_id]
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            target_id = int(text)
            _, target_user = get_user(target_id)
            user_bal = target_user.get("balance", 0.0)
            bdt_val = user_bal * USDT_TO_BDT
            name = target_user.get("first_name", "Unknown")
            ref_count = target_user.get("referrals_count", 0)
            phone = target_user.get("verified_phone", "নেই")
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
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            admin_step[user_id] = {"action": "addbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, "➕ কত USDT যোগ করবেন তা লিখুন:")
            return

        elif state == "addbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, amt)
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-কে ${amt:.4f} USDT দেওয়া হয়েছে।", parse_mode="Markdown")
            except:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

        elif state == "cutbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            admin_step[user_id] = {"action": "cutbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, "✂️ কত USDT কাটবেন তা লিখুন:")
            return

        elif state == "cutbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, -amt)
                bot.send_message(message.chat.id, f"✂️ ইউজার `{target_id}`-এর অ্যাকাউন্ট থেকে ${amt:.4f} USDT কাটা হয়েছে।", parse_mode="Markdown")
            except:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

    if user_id in user_withdraw_step:
        step_data = user_withdraw_step[user_id]
        if step_data['step'] == 'amount':
            try:
                amt = float(text)
                balance, _ = get_user(user_id)
                if amt < MIN_WITHDRAW:
                    bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র ${MIN_WITHDRAW} USDT।")
                    return
                if amt > balance:
                    bot.reply_to(message, "❌ পর্যাপ্ত ব্যালেন্স নেই!")
                    return
                
                step_data['amount'] = amt
                step_data['step'] = 'number'
                bot.send_message(message.chat.id, f"📱 আপনার ১১ ডিজিটের **{step_data['method']} নম্বর** লিখে পাঠান:", parse_mode="Markdown")
            except:
                bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন:")
            return
            
        elif step_data['step'] == 'number':
            number = text
            if not is_valid_bd_number(number):
                bot.reply_to(message, "❌ ভুল নম্বর! সঠিক ১১ ডিজিটের বিকাশ/নগদ নম্বর দিন:")
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
            except:
                pass

            bot.send_message(
                message.chat.id,
                f"✅ উইথড্র সফলভাবে সাবমিট হয়েছে! ২৪ ঘণ্টার মধ্যে পেমেন্ট পেয়ে যাবেন।",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return

    if text == "🖥 Account":
        balance, user = get_user(user_id, first_name)
        bdt_val = balance * USDT_TO_BDT
        phone = user.get("verified_phone", "ভেরিফাই করা হয়নি")
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
            f"প্রতি রেফারেল বোনাস: **${REFERRAL_BONUS:.3f} USDT**\n\n"
            f"🔗 আপনার লিংক:\n`{ref_link}`\n\n"
            f"👥 মোট রেফার: {ref_count} জন",
            parse_mode="Markdown"
        )
        return

    elif text == "💸 Withdraw":
        balance, user = get_user(user_id, first_name)
        if balance < MIN_WITHDRAW:
            bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র ${MIN_WITHDRAW} USDT। বর্তমান ব্যালেন্স: ${balance:.4f} USDT")
            return
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("bKash", callback_data="w_method_bKash"),
            InlineKeyboardButton("Nagad", callback_data="w_method_Nagad")
        )
        bot.send_message(
            message.chat.id,
            f"💸 **উইথড্র মেথড সিলেক্ট করুন:**\nবর্তমান ব্যালেন্স: **${balance:.4f} USDT**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    elif text == "📜 Payment History":
        _, user = get_user(user_id, first_name)
        history = user.get("history", [])
        if not history:
            bot.send_message(message.chat.id, "📜 কোনো পেমেন্ট হিস্ট্রি নেই।")
            return
        
        hist_text = "📜 **শেষ ৫টি উইথড্র রেকর্ড:**\n━━━━━━━━━━━━━━━━━━━\n"
        for h in history[-5:]:
            hist_text += f"💳 {h['method']} | ${h['amount_usdt']:.3f} ({h['amount_bdt']:.2f} BDT)\n📱 `{h['number']}`\n🕒 {h['date']}\n\n"
        bot.send_message(message.chat.id, hist_text, parse_mode="Markdown")
        return

    elif text == "📩 Support":
        bot.send_message(
            message.chat.id,
            "🌐 ALL IN ONE 🌐\n\n"
            "🖇️ আমাদের সাপোর্ট গ্রুপ লিংক: https://t.me/allinoneg1\n\n"
            "✅ টেলিগ্রাম এডমিন লিংক: @akadmin02\n\n"
            "✅ Whatsapp এডমিন লিংক: 👇\nhttps://wa.me/qr/TLGSBEYHL74LD1"
        )
        return

if __name__ == '__main__':
    server_domain = os.environ.get("RENDER_EXTERNAL_URL", "")
    if server_domain:
        webhook_url = f"{server_domain}/{BOT_TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to: {webhook_url}")

    threading.Thread(target=auto_post_loop, daemon=True).start()
    threading.Thread(target=inactivity_push_loop, daemon=True).start()

    print("Telegram Bot is running with Webhook...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
