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

# স্ক্রিনশট সাবমিট হওয়ার নির্দিষ্ট চ্যানেল
SCREENSHOT_TARGET_CHANNEL = "@allinoneg3"

PAYMENT_BANNER_URL = "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=800"

MIN_WITHDRAW = 1.0    # সর্বনিম্ন উইথড্র ১ ডলার[cite: 3]
USDT_TO_BDT = 100.0   # ১ ডলার = ১০০ টাকা[cite: 3]
REFERRAL_BONUS = 0.005
FAKE_USER_OFFSET = 506  # ৫০৬+ ফেক ইউজার কাউন্ট[cite: 3]

# --- DYNAMIC TASK REWARDS & LIMITS (Admin Controlled) ---
TASK_CONFIG = {
    "ad1_reward": 0.001,
    "ad1_limit": 30,
    "ad2_reward": 0.001,
    "ad2_limit": 15,
    "ad3_reward": 0.001,
    "ad3_limit": 15
}

# --- MAINTENANCE MODE ---
MAINTENANCE_MODE = False

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

# --- WATCH AD 3 15 EXE.IO LINKS ---
WATCH_AD_3_LINKS = [
    'https://exe.io/0gptze35',
    'https://exe.io/ry8Ka',
    'https://exe.io/7nLiu',
    'https://exe.io/57NKwlj',
    'https://exe.io/2qeCFj',
    'https://exe.io/Bo0QN',
    'https://exe.io/QcaC1jjV',
    'https://exe.io/uJ8x4v',
    'https://exe.io/4CMD9lc',
    'https://exe.io/7t5U3dg',
    'https://exe.io/h3s7q',
    'https://exe.io/vp05amHW',
    'https://exe.io/4VgpGc',
    'https://exe.io/FhwbU5QN',
    'https://exe.io/gCczg6'
]

# --- DATABASE SETUP ---
users_col = None
memory_users = {}

if MONGO_URI:
    try:
        client = pymongo.MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=3000, 
            maxPoolSize=200, 
            minPoolSize=10,
            maxIdleTimeMS=45000
        )
        db = client["telegram_bot"]
        users_col = db["users"]
        users_col.create_index("user_id", unique=True)
        print("MongoDB Connected Successfully with High Performance Pool.")
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)
app = Flask(__name__)

# --- WEBHOOK & FLASK ROUTES ---
@app.route('/')
def home():
    return "Bot is running with Advanced Admin Control Panel!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Invalid request", 403

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
                আপনার ডিভাইস এবং আইপি ভেরিফিকেশন প্রক্রিয়া সফল হয়েছে। নিচের বাটনে ক্লিক করে টেলিগ্রামে ফিরে যান এবং 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন।
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
user_waiting_ad3_screenshot = set()

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
        "ad2_last_reset": current_now,
        "ad3_index": 0,
        "ad3_completed_today": 0,
        "ad3_last_reset": current_now
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

def check_user_channels(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def send_step_by_step_verification(chat_id, user_id, first_name):
    _, user = get_user(user_id, first_name)
    
    if not user.get("verified_phone"):
        bot.send_message(
            chat_id,
            "📱 **ধাপ ১: ফোন নম্বর ভেরিফিকেশন প্রয়োজন!**\n\nবটটি ব্যবহার শুরু করতে নিচের '📱 Share Contact' বাটনে ক্লিক করে আপনার টেলিগ্রাম নম্বর ভেরিফাই করুন।",
            reply_markup=contact_keyboard(),
            parse_mode="Markdown"
        )
        return False

    if not user.get("device_verified", False):
        server_domain = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
        browser_link = f"{server_domain}/verify-device?user_id={user_id}&name={first_name}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌐 ১. ব্রাউজারে গিয়ে চেক করুন", url=browser_link))
        markup.add(InlineKeyboardButton("✅ ২. ভেরিফাই কমপ্লিট করুন", callback_data="check_device_ip"))

        bot.send_message(
            chat_id,
            "🛡️ **ধাপ ২: ডিভাইস ও আইপি সিকিউরিটি চেক!**\n\n"
            "👉 **ধাপ ১:** 'ব্রাউজারে গিয়ে চেক করুন' বাটনে ক্লিক করে ব্রাউজারে যান।\n"
            "👉 **ধাপ ২:** ব্রাউজার থেকে টেলিগ্রামে ফিরে এসে 'ভেরিফাই কমপ্লিট করুন' বাটনে ক্লিক করুন.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return False

    if not check_user_channels(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ Checked / Verified", callback_data="check_join"))
        
        bot.send_message(
            chat_id,
            "⚠️ **ধাপ ৩: চ্যানেল সাবস্ক্রিপশন চেক!**\n\nবটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return False

    return True

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
        KeyboardButton("📺 Watch Ad 3"),
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
        InlineKeyboardButton("📢 Broadcast", callback_data="adm_panel_broadcast"),
        InlineKeyboardButton("📊 Bot Statistics", callback_data="adm_panel_stats"),
        InlineKeyboardButton("👤 Manage User", callback_data="adm_panel_manage"),
        InlineKeyboardButton("✉️ Send Message", callback_data="adm_panel_sendmsg"),
        InlineKeyboardButton("➕ Add Balance", callback_data="adm_panel_addbal"),
        InlineKeyboardButton("✂️ Cut Balance", callback_data="adm_panel_cutbal"),
        InlineKeyboardButton("🔗 Manage Links", callback_data="adm_panel_links"),
        InlineKeyboardButton("⚙️ Task Reward/Limit", callback_data="adm_panel_tasks"),
        InlineKeyboardButton("🔘 Custom Buttons", callback_data="adm_panel_buttons"),
        InlineKeyboardButton("🛠 Maintenance Mode", callback_data="adm_panel_maint"),
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

    if MAINTENANCE_MODE and user_id not in ADMIN_IDS:
        bot.reply_to(message, "🛠️ বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):
        return

    limit = TASK_CONFIG["ad1_limit"]
    last_reset = user.get("last_reset", 0)
    if user.get("captcha_locked", False) or user.get("daily_count", 0) >= limit:
        if time.time() - last_reset >= 86400:
            update_user_field(user_id, {"daily_count": 0, "captcha_locked": False, "last_reset": time.time()})
            _, user = get_user(user_id)
        else:
            remaining_time = int(86400 - (time.time() - last_reset))
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            bot.reply_to(message, f"❌ আপনার আজকের {limit}টি কাজ সম্পন্ন হয়েছে এবং ক্যাপচা লক রয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")
            return

    current_count = user.get("daily_count", 0)
    if current_count >= limit:
        bot.reply_to(message, f"❌ আজকের {limit}টি কাজ সম্পন্ন হয়েছে!")
        return

    all_links = MONETAG_LINKS + ADSTERRA_LINKS
    if not all_links:
        bot.reply_to(message, "❌ বর্তমানে কোনো লিংক উপলব্ধ নেই।")
        return
    ad_link = random.choice(all_links)

    current_time = time.time()
    update_user_field(user_id, {"last_task_time": current_time, "can_claim": True})

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🌐 Visit Ad Link", url=ad_link))
    markup.add(InlineKeyboardButton("🎁 Claim Reward", callback_data="claim_reward"))

    bot.send_message(
        message.chat.id,
        f"📺 **বিজ্ঞাপন দেখুন এবং আয় করুন!**\n\n"
        f"👉 নিচের ভিজিট লিংকে ক্লিক করে ওয়েবসাইট ভিজিট করুন এবং অন্তত **২০ সেকেন্ড** অপেক্ষা করুন।\n"
        f"⏳ এরপর 'Claim Reward' বাটনে ক্লিক করে আপনার রিওয়ার্ড সংগ্রহ করুন。\n\n"
        f"📈 আজকের কাজ: {current_count}/{limit}",
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

    if MAINTENANCE_MODE and user_id not in ADMIN_IDS:
        bot.reply_to(message, "🛠️ বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):
        return

    limit = TASK_CONFIG["ad2_limit"]
    last_reset = user.get("ad2_last_reset", 0)
    completed_today = user.get("ad2_completed_today", 0)

    if completed_today >= limit:
        if time.time() - last_reset >= 86400:
            update_user_field(user_id, {"ad2_completed_today": 0, "ad2_index": 0, "ad2_last_reset": time.time()})
            _, user = get_user(user_id)
            completed_today = 0
        else:
            remaining_time = int(86400 - (time.time() - last_reset))
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            bot.reply_to(message, f"❌ আপনার আজকের {limit}টি লিংকের কাজ সম্পন্ন হয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")
            return

    if not WATCH_AD_2_LINKS:
        bot.reply_to(message, "❌ বর্তমানে কোনো লিংক নেই।")
        return

    current_index = user.get("ad2_index", 0)
    if current_index >= len(WATCH_AD_2_LINKS):
        current_index = 0

    ad_link = WATCH_AD_2_LINKS[current_index]
    user_waiting_screenshot.add(user_id)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔗 Visit Link", url=ad_link),
        InlineKeyboardButton("📹 কিভাবে কাজ করবেন (ভিডিও)", url="https://t.me/allinoneg1/843")
    )

    text_msg = (
        "📺 Watch Ad 2 - টাস্ক পেজ\n\n"
        "🔗 লিংক ক্লিক করার পর একটি স্ক্রিনশট নিবেন ভেরিফাই কমপ্লিট করবেন... স্ক্রিনশট পাঠিয়ে দিন ✅\n\n"
        f"💵 প্রতি কাজের রিওয়ার্ড: {TASK_CONFIG['ad2_reward']} USDT\n"
        f"📈 সম্পন্ন হয়েছে: {completed_today}/{limit} টি লিংক"
    )

    bot.send_message(message.chat.id, text_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📺 Watch Ad 3")
def watch_ad_3_handler(message):
    user_id = message.from_user.id
    _, user = get_user(user_id, message.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if MAINTENANCE_MODE and user_id not in ADMIN_IDS:
        bot.reply_to(message, "🛠️ বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return

    if not send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name):
        return

    limit = TASK_CONFIG["ad3_limit"]
    last_reset = user.get("ad3_last_reset", 0)
    completed_today = user.get("ad3_completed_today", 0)

    if completed_today >= limit:
        if time.time() - last_reset >= 86400:
            update_user_field(user_id, {"ad3_completed_today": 0, "ad3_index": 0, "ad3_last_reset": time.time()})
            _, user = get_user(user_id)
            completed_today = 0
        else:
            remaining_time = int(86400 - (time.time() - last_reset))
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            bot.reply_to(message, f"❌ আপনার আজকের {limit}টি লিংকের কাজ সম্পন্ন হয়েছে! নতুন কাজ শুরু হবে আরও {hours} ঘণ্টা {minutes} মিনিট পর।")
            return

    if not WATCH_AD_3_LINKS:
        bot.reply_to(message, "❌ বর্তমানে কোনো লিংক নেই।")
        return

    current_index = user.get("ad3_index", 0)
    if current_index >= len(WATCH_AD_3_LINKS):
        current_index = 0

    ad_link = WATCH_AD_3_LINKS[current_index]
    user_waiting_ad3_screenshot.add(user_id)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔗 Visit Exe.io Link", url=ad_link),
        InlineKeyboardButton("📹 কিভাবে কাজ করবেন (ভিডিও)", url="https://t.me/allinoneg1/843")
    )

    text_msg = (
        "📺 Watch Ad 3 - টাস্ক পেজ\n\n"
        "🔗 লিংক ক্লিক করার পর স্ক্রিনশট পাঠিয়ে দিন ✅\n\n"
        f"💵 প্রতি কাজের রিওয়ার্ড: {TASK_CONFIG['ad3_reward']} USDT\n"
        f"📈 সম্পন্ন হয়েছে: {completed_today}/{limit} টি লিংক"
    )

    bot.send_message(message.chat.id, text_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_user_screenshot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    if user_id in user_waiting_screenshot:
        user_waiting_screenshot.remove(user_id)
        _, user = get_user(user_id, first_name)
        
        file_id = message.photo[-1].file_id
        completed_today = user.get("ad2_completed_today", 0) + 1
        next_index = user.get("ad2_index", 0) + 1

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Approve", callback_data=f"scr_yes_{user_id}_{completed_today}_{next_index}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"scr_no_{user_id}")
        )

        caption_text = (
            f"📥 **নতুন স্ক্রিনশট (Watch Ad 2)**\n"
            f"👤 ইউজার: {first_name} (`{user_id}`)\n"
            f"📈 সম্পন্ন কাজ: {completed_today}/{TASK_CONFIG['ad2_limit']}"
        )

        try:
            bot.send_photo(SCREENSHOT_TARGET_CHANNEL, photo=file_id, caption=caption_text, parse_mode="Markdown", reply_markup=markup)
            bot.reply_to(message, "✅ আপনার স্ক্রিনশট অ্যাডমিনের কাছে পাঠানো হয়েছে!", reply_markup=main_menu_keyboard())
        except Exception as e:
            print(f"Error sending screenshot: {e}")
        return

    if user_id in user_waiting_ad3_screenshot:
        user_waiting_ad3_screenshot.remove(user_id)
        _, user = get_user(user_id, first_name)
        
        file_id = message.photo[-1].file_id
        completed_today = user.get("ad3_completed_today", 0) + 1
        next_index = user.get("ad3_index", 0) + 1

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Approve", callback_data=f"ad3_yes_{user_id}_{completed_today}_{next_index}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"ad3_no_{user_id}")
        )

        caption_text = (
            f"📥 **নতুন স্ক্রিনশট (Watch Ad 3)**\n"
            f"👤 ইউজার: {first_name} (`{user_id}`)\n"
            f"📈 সম্পন্ন কাজ: {completed_today}/{TASK_CONFIG['ad3_limit']}"
        )

        try:
            bot.send_photo(SCREENSHOT_TARGET_CHANNEL, photo=file_id, caption=caption_text, parse_mode="Markdown", reply_markup=markup)
            bot.reply_to(message, "✅ আপনার Exe.io স্ক্রিনশট অ্যাডমিনের কাছে পাঠানো হয়েছে!", reply_markup=main_menu_keyboard())
        except Exception as e:
            print(f"Error sending ad3 screenshot: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("scr_yes_") or call.data.startswith("scr_no_") or call.data.startswith("ad3_yes_") or call.data.startswith("ad3_no_"))
def screenshot_approval_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    data_parts = call.data.split("_")
    prefix = data_parts[0]
    action = data_parts[1]
    target_user_id = int(data_parts[2])

    if prefix == "scr":
        if action == "yes":
            completed_today = int(data_parts[3])
            next_index = int(data_parts[4])
            reward = TASK_CONFIG["ad2_reward"]
            
            add_balance(target_user_id, reward)
            update_user_field(target_user_id, {"ad2_completed_today": completed_today, "ad2_index": next_index})

            try:
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **Approved & Paid**", parse_mode="Markdown")
            except:
                pass
            bot.answer_callback_query(call.id, "✅ পেমেন্ট দেওয়া হয়েছে!")
            try:
                bot.send_message(target_user_id, f"🎉 আপনার স্ক্রিনশট অনুমোদিত হয়েছে! আপনি পেয়েছেন ${reward} USDT।", reply_markup=main_menu_keyboard())
            except:
                pass
        elif action == "no":
            try:
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **Rejected**", parse_mode="Markdown")
            except:
                pass
            bot.answer_callback_query(call.id, "❌ রিজেক্ট করা হয়েছে।")
            try:
                bot.send_message(target_user_id, "❌ আপনার স্ক্রিনশটটি রিজেক্ট করা হয়েছে।", reply_markup=main_menu_keyboard())
            except:
                pass

    elif prefix == "ad3":
        if action == "yes":
            completed_today = int(data_parts[3])
            next_index = int(data_parts[4])
            reward = TASK_CONFIG["ad3_reward"]
            
            add_balance(target_user_id, reward)
            update_user_field(target_user_id, {"ad3_completed_today": completed_today, "ad3_index": next_index})

            try:
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **Approved & Paid**", parse_mode="Markdown")
            except:
                pass
            bot.answer_callback_query(call.id, "✅ পেমেন্ট দেওয়া হয়েছে!")
            try:
                bot.send_message(target_user_id, f"🎉 আপনার Exe.io স্ক্রিনশট অনুমোদিত হয়েছে! আপনি পেয়েছেন ${reward} USDT।", reply_markup=main_menu_keyboard())
            except:
                pass
        elif action == "no":
            try:
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **Rejected**", parse_mode="Markdown")
            except:
                pass
            bot.answer_callback_query(call.id, "❌ রিজেক্ট করা হয়েছে।")
            try:
                bot.send_message(target_user_id, "❌ আপনার Exe.io স্ক্রিনশটটি রিজেক্ট করা হয়েছে।", reply_markup=main_menu_keyboard())
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
        "সমস্ত ১৪টি ফিচার ম্যানেজ করার জন্য নিচের বাটনগুলো ব্যবহার করুন:"
    )
    bot.send_message(message.chat.id, admin_msg, reply_markup=admin_dashboard_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_panel_"))
def admin_panel_callbacks(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    action = call.data.replace("adm_panel_", "")
    chat_id = call.message.chat.id

    if action == "close":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
    elif action == "stats":
        all_u = get_all_active_users()
        real_users = len(all_u)
        stats_text = (
            f"📊 **বট সার্বিক পরিসংখ্যান**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট ডাটাবেজ ইউজার: **{real_users}** জন\n"
            f"📈 ডিসপ্লেড ইউজার (ফেক সহ): **{FAKE_USER_OFFSET + real_users}** জন\n"
            f"🛠️ মেইনটেন্যান্স মোড: **{'ON' if MAINTENANCE_MODE else 'OFF'}**"
        )
        bot.send_message(chat_id, stats_text, parse_mode="Markdown")
    elif action == "broadcast":
        admin_step[call.from_user.id] = {"action": "broadcast"}
        bot.send_message(chat_id, "📢 সব ইউজারের কাছে পাঠানোর জন্য মেসেজটি লিখে বা ফরোয়ার্ড করে পাঠান:\n*(বাতিল করতে /cancel)*")
    elif action == "manage":
        admin_step[call.from_user.id] = {"action": "manage_user"}
        bot.send_message(chat_id, "👤 যে ইউজারের বিবরণ দেখতে চান তার **User ID** লিখে পাঠান:")
    elif action == "sendmsg":
        admin_step[call.from_user.id] = {"action": "sendmsg_step1"}
        bot.send_message(chat_id, "✉️ যে ইউজারের কাছে প্রাইভেট মেসেজ পাঠাবেন তার **User ID** লিখে পাঠান:")
    elif action == "addbal":
        admin_step[call.from_user.id] = {"action": "addbal_step1"}
        bot.send_message(chat_id, "➕ ব্যালেন্স যোগ করার জন্য ইউজারের **User ID** দিন:")
    elif action == "cutbal":
        admin_step[call.from_user.id] = {"action": "cutbal_step1"}
        bot.send_message(chat_id, "✂️ ব্যালেন্স কাটার জন্য ইউজারের **User ID** দিন:")
    elif action == "links":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Monetag Links", callback_data="adm_link_list_monetag"),
            InlineKeyboardButton("Adsterra Links", callback_data="adm_link_list_adsterra"),
            InlineKeyboardButton("ShrinkMe Links", callback_data="adm_link_list_ad2"),
            InlineKeyboardButton("Exe.io Links", callback_data="adm_link_list_ad3"),
            InlineKeyboardButton("⬅️ Back", callback_data="adm_panel_back")
        )
        bot.edit_message_text("🔗 **লিংক ম্যানেজমেন্ট সিস্টেম**\nየት ক্যাটাগরির লিংক ডিলিট বা দেখতে চান সিলেক্ট করুন:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif action == "tasks":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(f"Ad 1 (Reward: {TASK_CONFIG['ad1_reward']}, Limit: {TASK_CONFIG['ad1_limit']})", callback_data="adm_edit_task_ad1"),
            InlineKeyboardButton(f"Ad 2 (Reward: {TASK_CONFIG['ad2_reward']}, Limit: {TASK_CONFIG['ad2_limit']})", callback_data="adm_edit_task_ad2"),
            InlineKeyboardButton(f"Ad 3 (Reward: {TASK_CONFIG['ad3_reward']}, Limit: {TASK_CONFIG['ad3_limit']})", callback_data="adm_edit_task_ad3"),
            InlineKeyboardButton("⬅️ Back", callback_data="adm_panel_back")
        )
        bot.edit_message_text("⚙️ **টাস্ক রিওয়ার্ড ও লিমিট কনফিগারেশন**\nপরিবর্তন করতে টাস্ক সিলেক্ট করুন:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif action == "buttons":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("❌ ডিলিট কাস্টম বাটন/মেসেজ", callback_data="adm_del_custom_btn"),
            InlineKeyboardButton("⬅️ Back", callback_data="adm_panel_back")
        )
        bot.edit_message_text("🔘 **কাস্টম বাটন রিমুভ সিস্টেম**\nনিচের অপশনটি ব্যবহার করুন:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif action == "maint":
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        status_str = "ON 🛠️" if MAINTENANCE_MODE else "OFF ✅"
        bot.answer_callback_query(call.id, f"Maintenance Mode is now {status_str}")
        bot.edit_message_text(f"🛠️ মেইনটেন্যান্স মোড সফলভাবে **{status_str}** করা হয়েছে।", chat_id, call.message.message_id, reply_markup=admin_dashboard_keyboard(), parse_mode="Markdown")
    elif action == "back":
        bot.edit_message_text("👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n━━━━━━━━━━━━━━━━━━━\nনিচের বাটনগুলো ব্যবহার করুন:", chat_id, call.message.message_id, reply_markup=admin_dashboard_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_link_list_"))
def admin_link_list_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
        return
    cat = call.data.replace("adm_link_list_", "")
    links_arr = []
    if cat == "monetag": links_arr = MONETAG_LINKS
    elif cat == "adsterra": links_arr = ADSTERRA_LINKS
    elif cat == "ad2": links_arr = WATCH_AD_2_LINKS
    elif cat == "ad3": links_arr = WATCH_AD_3_LINKS

    markup = InlineKeyboardMarkup(row_width=1)
    for idx, link in enumerate(links_arr[:10]):
        markup.add(InlineKeyboardButton(f"❌ Delete: {link[:30]}...", callback_data=f"adm_dellink_{cat}_{idx}"))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="adm_panel_links"))

    bot.edit_message_text(f"🔗 **{cat.upper()} Link List**\nডিলিট করতে নির্দিষ্ট লিংকে ক্লিক করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_dellink_"))
def admin_delete_link_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
        return
    parts = call.data.split("_")
    cat = parts[2]
    idx = int(parts[3])

    if cat == "monetag" and idx < len(MONETAG_LINKS):
        del MONETAG_LINKS[idx]
    elif cat == "adsterra" and idx < len(ADSTERRA_LINKS):
        del ADSTERRA_LINKS[idx]
    elif cat == "ad2" and idx < len(WATCH_AD_2_LINKS):
        del WATCH_AD_2_LINKS[idx]
    elif cat == "ad3" and idx < len(WATCH_AD_3_LINKS):
        del WATCH_AD_3_LINKS[idx]

    bot.answer_callback_query(call.id, "✅ সফলভাবে লিংকটি ডিলিট করা হয়েছে!")
    bot.edit_message_text("✅ লিংক সফলভাবে রিমুভ করা হয়েছে। আবার দেখতে অ্যাডমিন প্যানেলে যান。", call.message.chat.id, call.message.message_id, reply_markup=admin_dashboard_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_edit_task_"))
def admin_edit_task_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
        return
    task_key = call.data.replace("adm_edit_task_", "")
    admin_step[call.from_user.id] = {"action": "edit_task", "task": task_key}
    bot.send_message(call.message.chat.id, f"✍️ {task_key.upper()} এর জন্য নতুন রিওয়ার্ড ও লিমিট এভাবে লিখুন (উদাহরণ: `0.001,30`):", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "adm_del_custom_btn")
def admin_del_custom_btn_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
        return
    admin_step[call.from_user.id] = {"action": "del_custom_button"}
    bot.send_message(call.message.chat.id, "🗑️ যে মেসেজ বা বাটনটি রিমুভ/ডিলিট করতে চান তার **Message ID** লিখে পাঠান:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_ban_") or call.data.startswith("adm_unban_"))
def admin_ban_unban_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
        return
    parts = call.data.split("_")
    action = parts[0] + "_" + parts[1]
    target_id = int(parts[2])
    
    if action == "adm_ban":
        update_user_field(target_id, {"is_banned": True})
        bot.answer_callback_query(call.id, f"User {target_id} banned.")
        bot.send_message(call.message.chat.id, f"🚫 ইউজার `{target_id}` কে সফলভাবে ব্যান করা হয়েছে।", parse_mode="Markdown")
    elif action == "adm_unban":
        update_user_field(target_id, {"is_banned": False})
        bot.answer_callback_query(call.id, f"User {target_id} unbanned.")
        bot.send_message(call.message.chat.id, f"✅ ইউজার `{target_id}` কে আনব্যান করা হয়েছে।", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    _, user_data = get_user(user_id, call.from_user.first_name)
    if user_data.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 ব্যানড!", show_alert=True)
        return

    if check_user_channels(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "✅ ভেরিফিকেশন সফল! মেনু থেকে কাজ করুন:", reply_markup=main_menu_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "claim_reward")
def claim_reward_callback(call):
    user_id = call.from_user.id
    _, user = get_user(user_id, call.from_user.first_name)
    
    if user.get("is_banned", False):
        bot.answer_callback_query(call.id, "🚫 ব্যানড!", show_alert=True)
        return

    if user.get("captcha_locked", False):
        bot.answer_callback_query(call.id, "❌ ক্যাপচা লক করা আছে!", show_alert=True)
        return

    if not user.get("can_claim", False):
        bot.answer_callback_query(call.id, "❌ ইতিমধ্যে ক্লাইম করা হয়েছে!", show_alert=True)
        return
        
    reward = TASK_CONFIG["ad1_reward"]
    limit = TASK_CONFIG["ad1_limit"]
    add_balance(user_id, reward)
    current_count = user.get("daily_count", 0) + 1
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    if current_count >= limit:
        num1, num2 = random.randint(10, 50), random.randint(1, 20)
        ans = num1 + num2
        user_captcha_step[user_id] = ans
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count, "captcha_locked": True, "last_reset": time.time()})
        bot.send_message(call.message.chat.id, f"🎉 আজকের লিমিট শেষ!\n🔐 ম্যাথ ক্যাপচা সমাধান করুন: **{num1} + {num2} = ?**", parse_mode="Markdown")
    else:
        update_user_field(user_id, {"can_claim": False, "daily_count": current_count})
        bot.send_message(call.message.chat.id, f"🎉 সফলভাবে ${reward} USDT উপার্জন করেছেন!\n📈 কাজ: {current_count}/{limit}", reply_markup=main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_method_"))
def withdraw_method_callback(call):
    user_id = call.from_user.id
    method = call.data.replace("w_method_", "")
    balance, _ = get_user(user_id)
    user_withdraw_step[user_id] = {'step': 'amount', 'method': method}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, f"💵 মেথড: **{method}**\nবর্তমান ব্যালেন্স: **${balance:.4f} USDT**\n👉 কত উইথড্র করতে চান সংখ্যায় লিখুন:", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_device_ip")
def check_device_ip_callback(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    _, user = get_user(user_id, first_name)
    user_ip = user.get("temp_ip")
    if not user_ip:
        bot.answer_callback_query(call.id, "❌ ব্রাউজারে লিংক ওপেন করা হয়নি!", show_alert=True)
        return
    update_user_field(user_id, {"device_verified": True})
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    send_step_by_step_verification(call.message.chat.id, user_id, first_name)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    if MAINTENANCE_MODE and user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "🛠️ বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return

    args = message.text.split()
    referred_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    _, user = get_user(user_id, first_name, referred_by=referred_by)
    if user.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if not send_step_by_step_verification(message.chat.id, user_id, first_name):
        return

    bot.send_message(message.chat.id, f"👋 স্বাগতম, 👤 {first_name}!\nনিচের মেনু থেকে কাজ শুরু করুন:", reply_markup=main_menu_keyboard())

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    if message.contact is not None:
        phone_number = str(message.contact.phone_number).strip()
        update_user_field(user_id, {"verified_phone": phone_number, "last_active": time.time()})
        bot.send_message(message.chat.id, "✅ ফোন নম্বর ভেরিফাই হয়েছে!")
        send_step_by_step_verification(message.chat.id, user_id, message.from_user.first_name)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    _, user_data = get_user(user_id, first_name)
    if user_data.get("is_banned", False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে।")
        return

    if text == "/cancel" and user_id in ADMIN_IDS:
        if user_id in admin_step:
            del admin_step[user_id]
        bot.send_message(message.chat.id, "❌ অপারেশন বাতিল করা হয়েছে।")
        return

    # --- ADMIN STEP HANDLERS ---
    if user_id in ADMIN_IDS and user_id in admin_step:
        state_data = admin_step[user_id]
        state = state_data.get("action")

        if state == "broadcast":
            del admin_step[user_id]
            all_users = get_all_active_users()
            success = 0
            for u in all_users:
                try:
                    bot.copy_message(chat_id=u.get("user_id"), from_chat_id=message.chat.id, message_id=message.message_id)
                    success += 1
                    time.sleep(0.03)
                except:
                    pass
            bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন! সফল: {success} জন।")
            return

        elif state == "manage_user":
            del admin_step[user_id]
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            target_id = int(text)
            _, target_user = get_user(target_id)
            user_bal = target_user.get("balance", 0.0)
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_id}"),
                InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_id}")
            )
            bot.send_message(message.chat.id, f"👤 ইউজার আইডি: `{target_id}`\nব্যালেন্স: ${user_bal} USDT\nস্ট্যাটাস ম্যানেজ করুন:", parse_mode="Markdown", reply_markup=markup)
            return

        elif state == "sendmsg_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")
                return
            admin_step[user_id] = {"action": "sendmsg_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, "✍️ ইউজারের কাছে যে প্রাইভেট মেসেজটি পাঠাবেন তা লিখুন:")
            return

        elif state == "sendmsg_step2":
            target_id = state_data.get("target_id")
            del admin_step[user_id]
            try:
                bot.send_message(target_id, f"📩 **অ্যাডমিনের বার্তা:**\n\n{text}", parse_mode="Markdown")
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-এর কাছে সফলভাবে মেসেজ পাঠানো হয়েছে।", parse_mode="Markdown")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ মেসেজ পাঠানো যায়নি: {e}")
            return

        elif state == "addbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            admin_step[user_id] = {"action": "addbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, "➕ কত USDT যোগ করতে চান লিখুন:")
            return

        elif state == "addbal_step2":
            target_id = state_data.get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, amt)
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-কে ${amt} USDT দেওয়া হয়েছে।", parse_mode="Markdown")
                try:
                    bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে ${amt} USDT যোগ করা হয়েছে!")
                except:
                    pass
            except:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

        elif state == "cutbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক আইডি দিন!")
                return
            admin_step[user_id] = {"action": "cutbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, "✂️ কত USDT কাটতে চান লিখুন:")
            return

        elif state == "cutbal_step2":
            target_id = state_data.get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                current_bal, _ = get_user(target_id)
                if amt > current_bal: amt = current_bal
                add_balance(target_id, -amt)
                bot.send_message(message.chat.id, f"✂️ ইউজার `{target_id}`-এর একাউন্ট থেকে ${amt} USDT কাটা হয়েছে।", parse_mode="Markdown")
            except:
                bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন!")
            return

        elif state == "edit_task":
            task_key = state_data.get("task")
            del admin_step[user_id]
            try:
                parts = text.split(",")
                new_rev = float(parts[0].strip())
                new_lim = int(parts[1].strip())
                if task_key == "ad1":
                    TASK_CONFIG["ad1_reward"] = new_rev
                    TASK_CONFIG["ad1_limit"] = new_lim
                elif task_key == "ad2":
                    TASK_CONFIG["ad2_reward"] = new_rev
                    TASK_CONFIG["ad2_limit"] = new_lim
                elif task_key == "ad3":
                    TASK_CONFIG["ad3_reward"] = new_rev
                    TASK_CONFIG["ad3_limit"] = new_lim
                bot.send_message(message.chat.id, f"✅ {task_key.upper()} সফলভাবে আপডেট হয়েছে! নতুন রিওয়ার্ড: {new_rev}, লিমিট: {new_lim}")
            except:
                bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল হয়েছে। সঠিক ফরম্যাটে দিন (যেমন: `0.001,30`)", parse_mode="Markdown")
            return

        elif state == "del_custom_button":
            del admin_step[user_id]
            try:
                msg_id_to_del = int(text)
                bot.delete_message(message.chat.id, msg_id_to_del)
                bot.send_message(message.chat.id, "✅ মেসেজ/বাটন সফলভাবে রিমুভ করা হয়েছে।")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ ডিলিট করা যায়নি: {e}")
            return

    if user_id in user_captcha_step:
        try:
            if int(text) == user_captcha_step[user_id]:
                del user_captcha_step[user_id]
                update_user_field(user_id, {"captcha_locked": False})
                bot.reply_to(message, "✅ ক্যাপচা সফল! ২৪ ঘণ্টা পর লিমিট রিসেট হবে।", reply_markup=main_menu_keyboard())
            else:
                bot.reply_to(message, "❌ ভুল উত্তর! আবার চেষ্টা করুন:")
        except:
            bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন:")
        return

    if user_id in user_withdraw_step:
        step_data = user_withdraw_step[user_id]
        if step_data['step'] == 'amount':
            try:
                amt = float(text)
                balance, _ = get_user(user_id)
                if amt < MIN_WITHDRAW or amt > balance:
                    bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র ${MIN_WITHDRAW} অথবা পর্যাপ্ত ব্যালেন্স নেই। সঠিক পরিমাণ দিন:")
                    return
                step_data['amount'] = amt
                step_data['step'] = 'number'
                bot.send_message(message.chat.id, f"📱 আপনার ১১ ডিজিটের **{step_data['method']} নম্বর** দিন:", parse_mode="Markdown")
            except:
                bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন:")
            return
        elif step_data['step'] == 'number':
            number = text
            if not is_valid_bd_number(number):
                bot.reply_to(message, "❌ সঠিক ১১ ডিজিটের নম্বর দিন:")
                return
            method = step_data['method']
            amount_usdt = step_data['amount']
            amount_bdt = amount_usdt * USDT_TO_BDT
            del user_withdraw_step[user_id]
            add_balance(user_id, -amount_usdt)
            add_payment_history(user_id, method, amount_usdt, amount_bdt, number)
            
            bot.send_message(message.chat.id, f"✅ উইথড্র সফলভাবে সাবমিট হয়েছে!\n💵 পরিমাণ: ${amount_usdt} USDT", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
            return

    if not send_step_by_step_verification(message.chat.id, user_id, first_name):
        return

    if text == "🖥 Account":
        balance, user = get_user(user_id, first_name)
        bot.send_message(message.chat.id, f"🖥 **অ্যাকাউন্ট বিবরণী**\nনাম: {first_name}\n🆔 আইডি: `{user_id}`\n💰 ব্যালেন্স: **${balance:.4f} USDT**", parse_mode="Markdown")
        return
    elif text == "✨ Referral":
        _, user = get_user(user_id, first_name)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.send_message(message.chat.id, f"✨ রেফারেল লিংক:\n`{ref_link}`", parse_mode="Markdown")
        return
    elif text == "💸 Withdraw":
        balance, _ = get_user(user_id, first_name)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("bKash", callback_data="w_method_bKash"), InlineKeyboardButton("Nagad", callback_data="w_method_Nagad"))
        bot.send_message(message.chat.id, f"💸 উইথড্র সেকশন\nব্যালেন্স: ${balance:.4f} USDT\nমেথড সিলেক্ট করুন:", reply_markup=markup)
        return
    elif text == "📜 Payment History":
        _, user = get_user(user_id, first_name)
        history = user.get("history", [])
        if not history:
            bot.send_message(message.chat.id, "📜 কোনো হিস্ট্রি নেই।")
            return
        hist_text = "📜 **শেষ উইথড্র রেকর্ড:**\n"
        for h in history[-5:]:
            hist_text += f"💳 {h['method']} | ${h['amount_usdt']} | {h['date']}\n"
        bot.send_message(message.chat.id, hist_text, parse_mode="Markdown")
        return
    elif text == "📩 Support":
        bot.send_message(message.chat.id, "🌐 সাপোর্ট গ্রুপ লিংক: https://t.me/allinoneg1")
        return

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    SERVER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://my-earning-all.onrender.com")
    
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{SERVER_URL}/{BOT_TOKEN}")
    print(f"Webhook set to: {SERVER_URL}/{BOT_TOKEN}")

    threading.Thread(target=auto_post_loop, daemon=True).start()
    threading.Thread(target=inactivity_push_loop, daemon=True).start()

    print("Telegram Bot is running with Advanced Features...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
