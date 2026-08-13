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
BOT_TOKEN = "8615856288:AAHsdARNnr1J4IEK_RodW0_xiLqnftct1C8"
MONGO_URI = os.environ.get("MONGO_URI", "")

BOT_USERNAME = "myearningall01_bot"
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1", "@allinoneg2"]
PROOF_CHANNEL = "@myearningall"

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

# --- DATABASE SETUP ---
users_col = None
memory_users = {}  # Backup in-memory DB if MongoDB is unavailable

if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, maxPoolSize=100)
        db = client["telegram_bot"]
        users_col = db["users"]
        print("MongoDB Connected Successfully.")
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)
app = Flask(__name__)

# --- MEMORY TRACKING ---
user_withdraw_step = {}
user_captcha_step = {}
admin_step = {}

# --- DATABASE HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    current_now = time.time()
    
    if users_col is None:
        if user_id not in memory_users:
            memory_users[user_id] = {
                "user_id": user_id, 
                "first_name": str(first_name)[:30],
                "balance": 0.0, 
                "daily_count": 0,
                "last_reset": current_now,
                "last_task_time": 0,
                "can_claim": False,
                "referred_by": referred_by,
                "referrals_count": 0,
                "ref_reward_given": False,
                "is_banned": False,
                "verified_phone": None,
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
                "last_reset": current_now,
                "last_task_time": 0,
                "can_claim": False,
                "referred_by": referred_by,
                "referrals_count": 0,
                "ref_reward_given": False,
                "is_banned": False,
                "verified_phone": None,
                "history": [],
                "last_active": current_now,
                "last_inactivity_push": 0
            }
            users_col.insert_one(user)
        else:
            users_col.update_one({"user_id": user_id}, {"$set": {"last_active": current_now}})
            user["last_active"] = current_now

        return user.get("balance", 0.0), user
    except Exception as e:
        print(f"DB Error: {e}")
        return 0.0, {"user_id": user_id, "first_name": first_name, "balance": 0.0, "is_banned": False, "verified_phone": None}

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

# --- ALL USERS FETCH FOR BROADCAST ---
def get_all_active_users():
    if users_col is not None:
        try:
            return list(users_col.find({"is_banned": False}))
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
                f"📱 দেওয়া নম্বর: `{clean_num}` ({method})\n"
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
        "⚠️ বটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:",
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
        KeyboardButton("🖥 Account"),
        KeyboardButton("📜 Payment History"),
        KeyboardButton("✨ Referral"),
        KeyboardButton("💸 Withdraw"),
        KeyboardButton("🛑 Rule's"),
        KeyboardButton("🔰 Whatsapp"),
        KeyboardButton("📩 Support"),
        KeyboardButton("📊 Status")
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

# --- AUTO PAYMENT PROOF LOOP ---
def auto_post_loop():
    while True:
        try:
            time.sleep(120)
            methods = ["bKash", "Nagad"]
            m = random.choice(methods)
            rand_usdt = round(random.uniform(1.0, 5.0), 3)
            rand_bdt = rand_usdt * USDT_TO_BDT
            rand_num = f"017{random.randint(10,99)}xxxxx{random.randint(10,99)}"

            msg = (
                "My Earning All Payment\n"
                "✅ Withdrawal Paid\n\n"
                f"💵 {rand_usdt:.3f} USDT ({rand_bdt:.2f} BDT)\n"
                f"🌐 {m}\n"
                f"👛 {rand_num}"
            )
            bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=msg)
        except Exception as e:
            print(f"Auto post loop error: {e}")

# --- INACTIVITY PUSH NOTIFICATION LOOP ---
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
                        bot.send_message(u_id, "আজকের ৩০টি এড দেখে আপনার আয় নিশ্চিত করুন!")
                        update_user_field(u_id, {"last_inactivity_push": current_now})
                        time.sleep(0.05)
                    except Exception as push_err:
                        print(f"Push error for user {u_id}: {push_err}")
        except Exception as e:
            print(f"Inactivity push loop error: {e}")

# --- ADMIN PANEL COMMAND & CALLBACKS ---
@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    admin_msg = (
        "👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "নিচের বাটনগুলো ব্যবহার করে বটের যাবতীয় কার্যক্রম ম্যানেজ করুন:"
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
        except Exception:
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
            "📢 **ব্রডকাস্ট মেসেজ পাঠাক:**\n\nআপনি সব ইউজারের কাছে যে মেসেজ বা নোটিশটি পাঠাতে চান তা এখানে লিখে বা ফরোয়ার্ড করে মেসেজ দিন:\n\n*(বাতিল করতে /cancel টাইপ করুন)*",
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

# --- USER COMMAND HANDLERS ---
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

    # ইউজার /start চাপার সাথে সাথে ডাটাবেজে এন্ট্রি হয়ে যাবে
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

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 স্বাগতম, 👤 {first_name}!\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:",
            reply_markup=main_menu_keyboard()
        )

# --- CONTACT HANDLER ---
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    if message.contact is not None:
        phone_number = str(message.contact.phone_number).strip()
        
        # ইউনিক ফোন চেক (MongoDB থাকলে)
        if users_col is not None:
            existing_user = users_col.find_one({
                "verified_phone": phone_number, 
                "user_id": {"$ne": user_id}
            })
            
            if existing_user:
                other_id = existing_user.get("user_id")
                bot.send_message(
                    message.chat.id, 
                    "❌ **এই ফোন নম্বরটি দিয়ে ইতোমধ্যে একটি অ্যাকাউন্ট ভেরিফাই করা রয়েছে!**"
                )
                
                alert_msg = (
                    "🚨 **ডুপ্লিকেট ফোন নম্বর ভেরিফিকেশন চেষ্টা!**\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 ইউজার আইডি: `{user_id}`\n"
                    f"📱 চেষ্টা করা ফোন: `{phone_number}`\n"
                    f"⚠️ মূল নিবন্ধিত আইডি: `{other_id}`\n"
                    "━━━━━━━━━━━━━━━━━━━"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(admin_id, alert_msg, parse_mode="Markdown")
                    except Exception:
                        pass
                return

        update_user_field(user_id, {"verified_phone": phone_number, "last_active": time.time()})
        
        bot.send_message(
            message.chat.id,
            "✅ আপনার ফোন নম্বর সফলভাবে ভেরিফাই হয়েছে!",
            reply_markup=main_menu_keyboard()
        )

        if not check_user_channels(user_id):
            send_force_join_msg(message.chat.id)

# --- TEXT & BROADCAST HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    if text == "/cancel" and user_id in ADMIN_IDS:
        if user_id in admin_step:
            del admin_step[user_id]
        bot.send_message(message.chat.id, "❌ অ্যাডমিন অপারেশন বাতিল করা হয়েছে।")
        return

    # --- ADMIN INPUT STEPS PROCESSING ---
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
                except Exception:
                    failed += 1

            bot.send_message(
                message.chat.id,
                f"✅ **ব্রডকাস্ট সম্পন্ন হয়েছে!**\n\n"
                f"📊 মোট প্রাপক: {total}\n"
                f"✅ সফলভাবে পাঠানো হয়েছে: {success}\n"
                f"❌ ব্যর্থ (ব্লক বা ডিলেট): {failed}",
                parse_mode="Markdown"
            )
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
            if is_banned:
                markup.add(InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_id}"))
            else:
                markup.add(InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_id}"))

            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
            return

        elif state == "addbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")
                return
            admin_step[user_id] = {"action": "addbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, f"💰 আইডি `{text}`-এর জন্য কত USDT যোগ করতে চান তা লিখুন (যেমন: 0.50):")
            return

        elif state == "addbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, amt)
                bot.send_message(message.chat.id, f"✅ ইউজার `{target_id}`-কে ${amt:.4f} USDT প্রদান করা হয়েছে।", parse_mode="Markdown")
                try:
                    bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে ${amt:.4f} USDT যোগ করা হয়েছে!")
                except Exception:
                    pass
            except ValueError:
                bot.send_message(message.chat.id, "❌ টাকার পরিমাণ সঠিক সংখ্যায় লিখুন!")
            return

        elif state == "cutbal_step1":
            if not text.isdigit():
                bot.send_message(message.chat.id, "❌ সঠিক ইউজার আইডি দিন!")
                return
            admin_step[user_id] = {"action": "cutbal_step2", "target_id": int(text)}
            bot.send_message(message.chat.id, f"✂️ আইডি `{text}`-এর থেকে কত USDT কাটতে চান লিখুন (যেমন: 0.50):")
            return

        elif state == "cutbal_step2":
            target_id = admin_step[user_id].get("target_id")
            del admin_step[user_id]
            try:
                amt = float(text)
                add_balance(target_id, -amt)
                bot.send_message(message.chat.id, f"✂️ ইউজার `{target_id}`-এর ব্যালেন্স থেকে ${amt:.4f} USDT কেটে নেওয়া হয়েছে।", parse_mode="Markdown")
            except ValueError:
                bot.send_message(message.chat.id, "❌ টাকার পরিমাণ সঠিক সংখ্যায় লিখুন!")
            return

    # --- GENERAL USER PROCESSING ---
    balance, user = get_user(user_id, first_name)
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

    if user_id in user_captcha_step:
        correct_ans = user_captcha_step[user_id]
        if text.isdigit() and int(text) == correct_ans:
            del user_captcha_step[user_id]
            bot.send_message(
                message.chat.id,
                "🎉 ম্যাথ ক্যাপচা সঠিক হয়েছে! অ্যাকাউন্টটি আনলক হয়েছে।",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "❌ ভুল উত্তর! আবার চেষ্টা করুন।")
        return

    # STEP 1: Withdraw Amount Selection
    if user_id in user_withdraw_step and user_withdraw_step[user_id].get('step') == 'amount':
        try:
            req_amount = float(text)
            if req_amount < MIN_WITHDRAW:
                bot.reply_to(message, f"❌ সর্বনিম্ন উইথড্র পরিমাণ ${MIN_WITHDRAW:.2f} USDT।")
                return
            if req_amount > balance:
                bot.reply_to(message, f"❌ পর্যাপ্ত ব্যালেন্স নেই! বর্তমান ব্যালেন্স: ${balance:.4f} USDT।")
                return
            
            method = user_withdraw_step[user_id]['method']
            user_withdraw_step[user_id] = {
                'step': 'number',
                'method': method,
                'amount': req_amount
            }

            bdt_calc = req_amount * USDT_TO_BDT
            bot.send_message(
                message.chat.id,
                f"📝 **{method} নম্বর ইনপুট দিন**\n━━━━━━━━━━━━━━━━━━━\n"
                f"💵 আপনি উইথড্র করছেন: **${req_amount:.4f} USDT**\n"
                f"💰 টাকার পরিমাণ: **{bdt_calc:.2f} BDT**\n\n"
                f"👉 আপনার ১১ ডিজিটের {method} নম্বরটি লিখে পাঠান:",
                parse_mode="Markdown"
            )
            return
        except ValueError:
            bot.reply_to(message, "❌ সঠিক সংখ্যায় উইথড্র পরিমাণ লিখুন।")
            return

    # STEP 2: Withdraw Number Input & Confirmation
    if user_id in user_withdraw_step and user_withdraw_step[user_id].get('step') == 'number':
        method = user_withdraw_step[user_id]['method']
        withdraw_amount = user_withdraw_step[user_id]['amount']
        del user_withdraw_step[user_id]

        if not is_valid_bd_number(text):
            bot.reply_to(message, "❌ ভুল ইনপুট! সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন।")
            return

        bdt_amount = withdraw_amount * USDT_TO_BDT

        check_duplicate_withdraw_number(user_id, first_name, text, method, withdraw_amount, bdt_amount)

        add_payment_history(user_id, method, withdraw_amount, bdt_amount, text)
        add_balance(user_id, -withdraw_amount)

        masked_acc = text[:3] + "xxxxx" + text[-3:]
        proof_msg = (
            "My Earning All Payment\n"
            "✅ Withdrawal Paid\n\n"
            f"💵 {withdraw_amount:.3f} USDT ({bdt_amount:.2f} BDT)\n"
            f"🌐 {method}\n"
            f"👛 {masked_acc}"
        )

        admin_alert_msg = (
            "🚨 **নতুন রিয়েল উইথড্র রিকোয়েস্ট!**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👤 নাম: {first_name}\n"
            f"🆔 আইডি: `{user_id}`\n"
            f"💰 পরিমাণ: ${withdraw_amount:.4f} USDT (={bdt_amount:.2f} BDT)\n"
            f"💳 মেথড: {method}\n"
            f"📱 নম্বর: `{text}`\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

        bot.send_message(
            message.chat.id, 
            f"✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে প্রসেস হয়েছে!\n\n💳 পরিমাণ: ${withdraw_amount:.4f} USDT (={bdt_amount:.2f} টাকা)\n🔷 মেথড: {method}\n📱 নম্বর: `{text}`\n\nধন্যবাদ!", 
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

        try:
            bot.send_photo(PROOF_CHANNEL, photo=PAYMENT_BANNER_URL, caption=proof_msg)
        except Exception as e:
            print(f"Error posting withdraw request: {e}")

        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, admin_alert_msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to send admin notification: {e}")
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
        return

    # Menu Options
    if text == "📺 Watch Ad":
        current_time = time.time()
        last_reset = user.get("last_reset", current_time)
        daily_count = user.get("daily_count", 0)

        if current_time - last_reset >= 86400:
            daily_count = 0
            last_reset = current_time

        if daily_count >= 30:
            num1, num2 = random.randint(1, 10), random.randint(1, 10)
            user_captcha_step[user_id] = num1 + num2
            bot.send_message(
                message.chat.id,
                f"❌ আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!\n\n🧩 **Anti-Bot Math Captcha:**\nঅ্যাকাউন্ট রিকভার/আনলক করতে নিচের প্রশ্নের উত্তর দিন:\n\n👉 **{num1} + {num2} = ?**",
                parse_mode="Markdown"
            )
            return

        if daily_count < 15:
            selected_url = ADSTERRA_LINKS[daily_count % len(ADSTERRA_LINKS)]
            provider = "Adsterra"
        else:
            selected_url = MONETAG_LINKS[(daily_count - 15) % len(MONETAG_LINKS)]
            provider = "Monetag"

        update_user_field(user_id, {
            "last_task_time": current_time, 
            "can_claim": True,
            "daily_count": daily_count,
            "last_reset": last_reset
        })

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🌐 Visit Ad / Link", url=selected_url),
            InlineKeyboardButton("✅ Claim Reward", callback_data="claim_reward")
        )
        bot.send_message(
            message.chat.id,
            f"📌 টাস্ক নিয়মাবলী (আজ দেখা হয়েছে: {daily_count}/30 - {provider}):\n1. নিচের লিংকে ক্লিক করে কমপক্ষে ১৫ সেকেন্ড অপেক্ষা করুন。\n2. ১৫ সেকেন্ড পর Claim Reward বাটনে চাপ দিন।",
            reply_markup=markup
        )

    elif text == "🖥 Account":
        bdt_balance = balance * USDT_TO_BDT
        phone = user.get("verified_phone", "N/A")
        account_text = (
            f"👤 **ইউজার প্রোফাইল**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📛 নাম: {first_name}\n"
            f"🆔 আইডি: `{user_id}`\n"
            f"📱 ফোন: `{phone}`\n"
            f"💰 ব্যালেন্স: ${balance:.4f} USDT\n"
            f"            = {bdt_balance:.2f} টাকা\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, account_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "📜 Payment History":
        history = user.get("history", [])
        if not history:
            bot.send_message(message.chat.id, "📜 আপনার কোনো পূর্বের পেমেন্ট হিস্ট্রি পাওয়া যায়নি।", reply_markup=main_menu_keyboard())
        else:
            total_paid = sum(item.get("amount_usdt", 0) for item in history)
            msg = f"📜 **আপনার পেমেন্ট হিস্ট্রি**\n💰 মোট সফল পেমেন্ট: ${total_paid:.3f} USDT\n━━━━━━━━━━━━━━━━━━━\n"
            for idx, h in enumerate(history[-5:], 1):
                msg += f"💳 **রেকর্ড {idx}:**\n• মেথড: {h.get('method')}\n• পরিমাণ: ${h.get('amount_usdt'):.3f} USDT ({h.get('amount_bdt'):.2f} BDT)\n• তারিখ: {h.get('date')}\n━━━━━━━━━━━━━━━━━━━\n"
            bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "✨ Referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        ref_count = user.get("referrals_count", 0)
        ref_bdt = REFERRAL_BONUS * USDT_TO_BDT
        bot.send_message(
            message.chat.id,
            f"👥 **আপনার রেফারেল লিংক**\n\n`{ref_link}`\n\n📊 মোট সফল রেফারেল: {ref_count} জন\n🎁 রেফার কমিশন: ${REFERRAL_BONUS:.3f} USDT (={ref_bdt:.2f} টাকা)",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "💸 Withdraw":
        bdt_balance = balance * USDT_TO_BDT
        min_bdt = MIN_WITHDRAW * USDT_TO_BDT
        if balance < MIN_WITHDRAW:
            msg = (
                f"💸 **উইথড্র ইনফরমেশন**\n━━━━━━━━━━━━━━━━━━━\n"
                f"💳 বর্তমান ব্যালেন্স: ${balance:.4f} USDT (={bdt_balance:.2f} টাকা)\n"
                f"📌 সর্বনিম্ন উইথড্র: ${MIN_WITHDRAW:.2f} USDT (={min_bdt:.2f} টাকা)\n\n"
                f"⚠️ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।"
            )
            bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("বিকাশ (bKash)", callback_data="with_bKash"),
                InlineKeyboardButton("নগদ (Nagad)", callback_data="with_Nagad")
            )
            bot.send_message(
                message.chat.id,
                f"💳 **পেমেন্ট মেথড সিলেক্ট করুন:**\n\n💰 বর্তমান ব্যালেন্স: ${balance:.4f} USDT (={bdt_balance:.2f} টাকা)",
                reply_markup=markup,
                parse_mode="Markdown"
            )

    elif text == "🛑 Rule's":
        min_bdt = MIN_WITHDRAW * USDT_TO_BDT
        rules = (
            "📌 **বট নিয়মাবলী:**\n\n"
            "১. প্রতিদিন সর্বোচ্চ ৩০টি এড দেখতে পারবেন।\n"
            "২. এড লিংকে অন্তত ১৫ সেকেন্ড অপেক্ষা করতে হবে।\n"
            "৩. ৩০টি এড দেখা শেষে ম্যাথ ক্যাপচা পূরণ করতে হবে।\n"
            "৪. একাধিক একাউন্টে একই পেমেন্ট নাম্বার দিলে সিস্টেম ব্লক করবে।\n"
            f"৫. সর্বনিম্ন উইথড্র ${MIN_WITHDRAW:.2f} USDT (={min_bdt:.2f} টাকা)।"
        )
        bot.send_message(message.chat.id, rules, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "🔰 Whatsapp":
        msg = "🌐 ALL IN ONE 🌐\n\n✅ Whatsapp এডমিন লিংক:\nhttps://wa.me/qr/TLGSBEYHL74LD1"
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📩 Support":
        msg = (
            "🌐 ALL IN ONE 🌐\n\n"
            "🖇️ আমাদের সাপোর্ট গ্রুপ লিংক: https://t.me/allinoneg1\n\n"
            "✅ টেলেগ্রাম এডমিন লিংক: @akadmin02\n\n"
            "✅ Whatsapp এডমিন লিংক:\nhttps://wa.me/qr/TLGSBEYHL74LD1"
        )
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📊 Status":
        all_u = get_all_active_users()
        real_users = len(all_u)
        displayed_users = FAKE_USER_OFFSET + real_users
        bot.send_message(
            message.chat.id,
            f"📊 **বট স্ট্যাটাস্টিকস**:\n\n👥 মোট সক্রিয় ইউজার: {displayed_users} জন",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# --- CALLBACK QUERY HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name

    try:
        bot.answer_callback_query(call.id, text="প্রসেস করা হচ্ছে...")
    except Exception:
        pass

    balance, user = get_user(user_id, first_name)

    if call.data.startswith("adm_ban_"):
        if user_id in ADMIN_IDS:
            target = int(call.data.split("_")[2])
            update_user_field(target, {"is_banned": True})
            bot.send_message(call.message.chat.id, f"🚫 ইউজার `{target}` কে সফলভাবে ব্যান করা হয়েছে।", parse_mode="Markdown")
        return
    elif call.data.startswith("adm_unban_"):
        if user_id in ADMIN_IDS:
            target = int(call.data.split("_")[2])
            update_user_field(target, {"is_banned": False})
            bot.send_message(call.message.chat.id, f"✅ ইউজার `{target}` কে সফলভাবে আনব্যান করা হয়েছে।", parse_mode="Markdown")
        return

    if call.data == "check_join":
        if check_user_channels(user_id):
            bot.send_message(call.message.chat.id, "✅ ধন্যবাদ! আপনি সব চ্যানেলে জয়েন আছেন।")
            if user.get("referred_by") and not user.get("ref_reward_given", False):
                referrer_id = user.get("referred_by")
                add_balance(referrer_id, REFERRAL_BONUS)
                if users_col is not None:
                    users_col.update_one({"user_id": referrer_id}, {"$inc": {"referrals_count": 1}})
                update_user_field(user_id, {"ref_reward_given": True})

            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "🎉 স্বাগতম! কাজ শুরু করতে নিচের বাটন ব্যবহার করুন:", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(call.message.chat.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!")

    elif call.data == "claim_reward":
        if not user.get("can_claim", False):
            bot.send_message(call.message.chat.id, "⚠️ আপনি লিংকে প্রবেশ করেননি!")
            return

        current_time = time.time()
        last_task_time = user.get("last_task_time", 0)
        elapsed_time = current_time - last_task_time

        if elapsed_time < 15:
            remaining = int(15 - elapsed_time)
            bot.send_message(call.message.chat.id, f"⏳ ১৫ সেকেন্ড পূর্ণ হয়নি! আরো {remaining} সেকেন্ড অপেক্ষা করুন।")
        else:
            daily_count = user.get("daily_count", 0)
            last_reset = user.get("last_reset", current_time)

            if current_time - last_reset >= 86400:
                daily_count = 0
                last_reset = current_time

            if daily_count >= 30:
                bot.send_message(call.message.chat.id, "❌ আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!")
                return

            add_balance(user_id, 0.001)
            update_user_field(user_id, {
                "daily_count": daily_count + 1, 
                "last_reset": last_reset, 
                "can_claim": False
            })

            updated_balance, _ = get_user(user_id, first_name)
            bdt_balance = updated_balance * USDT_TO_BDT
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass

            bot.send_message(
                call.message.chat.id,
                f"🎉 রিওয়ার্ড সফলভাবে যোগ হয়েছে!\n\n💰 প্রাপ্ত বোনাস: $0.0010 USDT\n💳 বর্তমান ব্যালেন্স: ${updated_balance:.4f} USDT (={bdt_balance:.2f} টাকা)\n📊 আজকের টাস্ক: {daily_count + 1}/30",
                reply_markup=main_menu_keyboard()
            )

    elif call.data.startswith("with_"):
        method = call.data.split("_")[1]
        user_withdraw_step[user_id] = {'step': 'amount', 'method': method}
        
        bdt_rate = USDT_TO_BDT
        min_bdt = MIN_WITHDRAW * bdt_rate
        
        msg = (
            f"💵 **উইথড্র অ্যামাউন্ট ইনপুট দিন ({method})**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 ১ USDT = {bdt_rate:.2f} BDT\n"
            f"📌 মিনিমাম উইথড্র: ${MIN_WITHDRAW:.2f} USDT (={min_bdt:.2f} BDT)\n"
            f"💳 আপনার মোট ব্যালেন্স: ${balance:.4f} USDT\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 আপনি কত USDT উইথড্র করতে চান তা সংখ্যায় লিখে মেসেজ দিন (যেমন: 1, 1.5, 2):"
        )
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

# --- FLASK WEB SERVER FOR KEEP ALIVE ---
def keep_alive():
    @app.route('/')
    def home():
        return "Bot is active and running!"

    def run():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive()

    t_auto = threading.Thread(target=auto_post_loop)
    t_auto.daemon = True
    t_auto.start()

    t_inactivity = threading.Thread(target=inactivity_push_loop)
    t_inactivity.daemon = True
    t_inactivity.start()

    bot.infinity_polling(skip_pending=True)
