import os
import random
import threading
import time
import pymongo
import telebot
from flask import Flask
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

MIN_WITHDRAW = 1.0    # সর্বনিম্ন উইথড্র ১ ডলার
USDT_TO_BDT = 110.0   # ১ ডলার = ১১০ টাকা
REFERRAL_BONUS = 0.005
FAKE_USER_OFFSET = 506  # ৫০৬+ ফেক ইউজার কাউন্ট

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

# --- DATABASE HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    if users_col is None:
        return 0.0, {"user_id": user_id, "first_name": first_name, "balance": 0.0, "is_banned": False, "verified_phone": None}
    try:
        user = users_col.find_one({"user_id": user_id})
        if not user:
            user = {
                "user_id": user_id, 
                "first_name": str(first_name)[:30],
                "balance": 0.0, 
                "daily_count": 0,
                "last_reset": time.time(),
                "last_task_time": 0,
                "can_claim": False,
                "referred_by": referred_by,
                "referrals_count": 0,
                "ref_reward_given": False,
                "is_banned": False,
                "verified_phone": None,
                "history": [],
                "ip_logs": []
            }
            users_col.insert_one(user)
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

def add_balance(user_id, amount):
    if users_col is not None:
        try:
            users_col.update_one({"user_id": user_id}, {"$inc": {"balance": float(amount)}})
        except Exception as e:
            print(f"DB Balance Error: {e}")

def add_payment_history(user_id, method, amount_usdt, amount_bdt, number):
    if users_col is not None:
        try:
            record = {
                "method": method,
                "amount_usdt": amount_usdt,
                "amount_bdt": amount_bdt,
                "number": str(number).strip(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            users_col.update_one({"user_id": user_id}, {"$push": {"history": record}})
        except Exception as e:
            print(f"DB History Error: {e}")

# --- DUPLICATE WITHDRAW NUMBER CHECK & ALERT ---
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
                "আপনি চাইলে নিচের বাটনে ক্লিক করে একশনে নিতে পারেন:"
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

# --- AUTO PAYMENT PROOF LOOP (EVERY 2 MINUTES) ---
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
            bot.send_message(PROOF_CHANNEL, msg)
        except Exception as e:
            print(f"Auto post loop error: {e}")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['manage'])
def manage_user_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ ফরম্যাট: /manage [USER_ID]")
            return

        target_id = int(args[1])
        if users_col is None:
            bot.reply_to(message, "❌ ডাটাবেজ কানেকশন নেই!")
            return

        user = users_col.find_one({"user_id": target_id})
        if not user:
            bot.reply_to(message, f"❌ {target_id} আইডি পাওয়া যায়নি।")
            return

        user_bal = user.get("balance", 0.0)
        bdt_val = user_bal * USDT_TO_BDT
        name = user.get("first_name", "Unknown")
        ref_count = user.get("referrals_count", 0)
        phone = user.get("verified_phone", "ভেরিফাই করা হয়নি")
        is_banned = user.get("is_banned", False)

        msg = (
            f"👤 **ইউজার এডভান্সড প্যানেল**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📛 নাম: {name}\n"
            f"🆔 ইউজার আইডি: `{target_id}`\n"
            f"📱 ফোন: `{phone}`\n"
            f"💰 ব্যালেন্স: ${user_bal:.4f} USDT (={bdt_val:.2f} টাকা)\n"
            f"👥 মোট রেফার: {ref_count} জন\n"
            f"🚫 ব্যান স্ট্যাটাস: {'🚫 Banned' if is_banned else '✅ Active'}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )

        markup = InlineKeyboardMarkup()
        if is_banned:
            markup.add(InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_id}"))
        else:
            markup.add(InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_id}"))

        bot.reply_to(message, msg, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ ফরম্যাট: /addbalance [USER_ID] [AMOUNT]")
            return
        target_id = int(args[1])
        amount = float(args[2])
        
        add_balance(target_id, amount)
        bot.reply_to(message, f"✅ সফলভাবে ${amount:.4f} USDT যোগ করা হয়েছে।")

        try:
            user_msg = (
                f"🎉 **আপনার অ্যাকাউন্টে ব্যালেন্স যোগ করা হয়েছে!**\n\n"
                f"💰 **যোগ করা পরিমাণ:** ${amount:.4f} USDT\n"
                f"নিয়মিত কাজ করে আরও ইনকাম করুন।"
            )
            bot.send_message(target_id, user_msg, parse_mode="Markdown")
        except Exception:
            pass

    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

@bot.message_handler(commands=['cutbalance'])
def cut_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ ফরম্যাট: /cutbalance [USER_ID] [AMOUNT]")
            return
        target_id = int(args[1])
        amount = float(args[2])
        add_balance(target_id, -amount)
        bot.reply_to(message, f"✂️ সফলভাবে ${amount:.4f} USDT কেটে নেওয়া হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

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
        phone_number = message.contact.phone_number
        update_user_field(user_id, {"verified_phone": phone_number})
        
        bot.send_message(
            message.chat.id,
            "✅ আপনার ফোন নম্বর সফলভাবে ভেরিফাই হয়েছে!",
            reply_markup=main_menu_keyboard()
        )

        if not check_user_channels(user_id):
            send_force_join_msg(message.chat.id)

# --- TEXT MESSAGE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

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

    # 30 Ad Math Captcha Validation Step
    if user_id in user_captcha_step:
        correct_ans = user_captcha_step[user_id]
        if text.isdigit() and int(text) == correct_ans:
            del user_captcha_step[user_id]
            bot.send_message(
                message.chat.id,
                "🎉 ম্যাথ ক্যাপচা সঠিক হয়েছে! পরবর্তী দিনের জন্য আপনার অ্যাকাউন্টটি সফলভাবে আনলক ও রিকভার হয়েছে।",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "❌ ভুল উত্তর! আবার চেষ্টা করুন (যেমন: 7 + 3 = ?)।")
        return

    # Withdraw Number Step
    if user_id in user_withdraw_step:
        method = user_withdraw_step[user_id].get('method', 'bKash')
        del user_withdraw_step[user_id]

        if not is_valid_bd_number(text):
            bot.reply_to(message, "❌ ভুল ইনপুট! অনুগ্রহ করে সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন।")
            return

        if balance < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। মিনিমাম উইথড্র ${MIN_WITHDRAW:.2f} USDT।")
            return

        withdraw_amount = balance
        bdt_amount = withdraw_amount * USDT_TO_BDT

        # 🔍 ডুপ্লিকেট নম্বর ফিল্টার (পূর্বের রেকর্ড চেক করে অ্যাডমিনকে সতর্ক করার ব্যবস্থা)
        check_duplicate_withdraw_number(user_id, first_name, text, method, withdraw_amount, bdt_amount)

        # ইতিহাস আপডেট ও ব্যালেন্স শূন্যকরণ
        add_payment_history(user_id, method, withdraw_amount, bdt_amount, text)
        update_user_field(user_id, {"balance": 0.0})

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
            reply_markup=main_menu_keyboard()
        )

        try:
            bot.send_message(PROOF_CHANNEL, proof_msg)
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
                f"❌ আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!\n\n🧩 **Anti-Bot Math Captcha:**\nঅ্যাকাউন্ট রিকভার/আনলক করতে ৩ মিনিটের মধ্যে নিচের প্রশ্নের উত্তর দিন:\n\n👉 **{num1} + {num2} = ?**",
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
                f"💳 পেমেন্ট মেথড সিলেক্ট করুন:\n\nবর্তমান ব্যালেন্স: ${balance:.4f} USDT (={bdt_balance:.2f} টাকা)",
                reply_markup=markup
            )

    elif text == "🛑 Rule's":
        min_bdt = MIN_WITHDRAW * USDT_TO_BDT
        rules = (
            "📌 **বট নিয়মাবলী:**\n\n"
            "১. প্রতিদিন সর্বোচ্চ ৩০টি এড দেখতে পারবেন।\n"
            "২. এড লিংকে অন্তত ১৫ সেকেন্ড অপেক্ষা করতে হবে।\n"
            "৩. ৩০টি এড দেখা শেষে ম্যাথ ক্যাপচা পূরণ করে অ্যাকাউন্ট আনলক করতে হবে।\n"
            "৪. একাধিক একাউন্টে একই পেমেন্ট নাম্বার দিলে আপনার অ্যাকাউন্টে সমস্যা হতে পারে।\n"
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
        real_users = users_col.count_documents({}) if users_col is not None else 0
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

    # Admin Ban / Unban Handlers from Notification Message
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
        user_withdraw_step[user_id] = {'method': method}
        bot.send_message(call.message.chat.id, f"📝 আপনার {method} নম্বরটি লিখে মেসেজ পাঠান:")

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

    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"Webhook Removal Error: {e}")

    print("Bot starting polling mechanism with skip_pending=True...")

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60, skip_pending=True)
        except Exception as e:
            print(f"Polling loop error: {e}")
            time.sleep(5)
