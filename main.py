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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8615856288:AAHsdARNnr1J4IEK_RodW0_xiLqnftct1C8")
MONGO_URI = os.environ.get("MONGO_URI", "")

BOT_USERNAME = "myearningall01_bot"
REQUIRED_CHANNELS = ["@myearningall", "@allinoneg1"]
PROOF_CHANNEL = "@myearningall"

MIN_WITHDRAW = 2.0
REFERRAL_BONUS = 0.005

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
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["telegram_bot"]
        users_col = db["users"]
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# --- MEMORY TRACKING ---
user_withdraw_step = {}

# --- DATABASE HELPERS ---
def get_user(user_id, first_name="User", referred_by=None):
    if users_col is None:
        return 0.0, {"user_id": user_id, "first_name": first_name, "balance": 0.0, "is_banned": False}
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
                "is_banned": False
            }
            users_col.insert_one(user)
        return user.get("balance", 0.0), user
    except Exception as e:
        print(f"DB Error: {e}")
        return 0.0, {"user_id": user_id, "first_name": first_name, "balance": 0.0, "is_banned": False}

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
        "⚠️ **বটটি ব্যবহার করতে আপনাকে নিচের সকল চ্যানেলগুলোতে জয়েন করতে হবে:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def is_valid_bd_number(number_str):
    number_str = str(number_str).strip()
    if len(number_str) == 11 and number_str.isdigit():
        if number_str.startswith(("017", "018", "019", "016", "015", "013", "014")):
            return True
    return False

# --- MAIN MENU KEYBOARD ---
def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📺 Watch Ad"),
        KeyboardButton("🖥 Account"),
        KeyboardButton("✨ Referral"),
        KeyboardButton("💸 Withdraw"),
        KeyboardButton("🛑 Rule's"),
        KeyboardButton("🔰 Whatsapp"),
        KeyboardButton("📩 Support"),
        KeyboardButton("📊 Status")
    )
    return markup

# --- ADMIN COMMANDS ---

@bot.message_handler(commands=['testpost'])
def test_post_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        msg = (
            f"**My Earning All Payment**\n"
            f"✅ **Withdrawal Paid**\n\n"
            f"💵 **5.250 USDT**\n"
            f"🌐 **bKash**\n"
            f"👛 **017*****123**"
        )
        bot.send_message(PROOF_CHANNEL, msg, parse_mode="Markdown")
        bot.reply_to(message, "✅ চ্যানেলে টেস্ট মেসেজ পাঠানো হয়েছে!")
    except Exception as e:
        bot.reply_to(message, f"❌ পোস্ট পাঠাতে ব্যর্থ! এরর: {e}")

@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ **ফরম্যাট:** `/addbalance [USER_ID] [AMOUNT]`", parse_mode="Markdown")
            return

        target_id = int(args[1])
        amount = float(args[2])

        add_balance(target_id, amount)
        _, target_user = get_user(target_id)
        new_bal = target_user.get("balance", 0.0)

        bot.reply_to(message, f"✅ সফলভাবে `{target_id}` আইডি-তে `${amount:.4f} USDT` যোগ করা হয়েছে।\nবর্তমান ব্যালেন্স: `${new_bal:.4f} USDT`", parse_mode="Markdown")

        try:
            bot.send_message(target_id, f"🎉 অ্যাডমিন আপনার অ্যাকাউন্টে `${amount:.4f} USDT` যোগ করেছেন!\nবর্তমান ব্যালেন্স: `${new_bal:.4f} USDT`", parse_mode="Markdown")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

@bot.message_handler(commands=['cutbalance'])
def cut_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ **ফরম্যাট:** `/cutbalance [USER_ID] [AMOUNT]`", parse_mode="Markdown")
            return

        target_id = int(args[1])
        amount = float(args[2])

        add_balance(target_id, -amount)
        _, target_user = get_user(target_id)
        new_bal = target_user.get("balance", 0.0)

        bot.reply_to(message, f"✂️ সফলভাবে `{target_id}` আইডি থেকে `${amount:.4f} USDT` কেটে নেওয়া হয়েছে।\nবর্তমান ব্যালেন্স: `${new_bal:.4f} USDT`", parse_mode="Markdown")

        try:
            bot.send_message(target_id, f"⚠️ অ্যাডমিন আপনার অ্যাকাউন্ট থেকে `${amount:.4f} USDT` কেটে নিয়েছেন।\nবর্তমান ব্যালেন্স: `${new_bal:.4f} USDT`", parse_mode="Markdown")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

@bot.message_handler(commands=['balance'])
def check_user_balance_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ **ফরম্যাট:** `/balance [USER_ID]`", parse_mode="Markdown")
            return

        target_id = int(args[1])
        if users_col is None:
            bot.reply_to(message, "❌ ডাটাবেজ কানেকশন নেই!")
            return

        user = users_col.find_one({"user_id": target_id})

        if not user:
            bot.reply_to(message, f"❌ `{target_id}` আইডি পাওয়া যায়নি।", parse_mode="Markdown")
            return

        user_bal = user.get("balance", 0.0)
        name = user.get("first_name", "Unknown")
        ref_count = user.get("referrals_count", 0)
        is_banned = "হ্যাঁ (Banned)" if user.get("is_banned", False) else "না (Active)"

        msg = (
            f"👤 **ইউজার ডিটেইলস:**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📛 **নাম:** `{name}`\n"
            f"🆔 **ইউজার আইডি:** `{target_id}`\n"
            f"💰 **বর্তমান ব্যালেন্স:** `${user_bal:.4f} USDT`\n"
            f"👥 **মোট রেফার:** `{ref_count}` জন\n"
            f"🚫 **ব্যান স্ট্যাটাস:** {is_banned}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

@bot.message_handler(commands=['ban'])
def ban_user_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ **ফরম্যাট:** `/ban [USER_ID]`", parse_mode="Markdown")
            return

        target_id = int(args[1])
        update_user_field(target_id, {"is_banned": True})

        bot.reply_to(message, f"🚫 ইউজার `{target_id}` কে **ব্যান** করা হয়েছে।", parse_mode="Markdown")

        try:
            bot.send_message(target_id, "🚫 আপনার অ্যাকাউন্টটি অ্যাডমিন কর্তৃক ব্যান করা হয়েছে।")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

@bot.message_handler(commands=['unban'])
def unban_user_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ **ফরম্যাট:** `/unban [USER_ID]`", parse_mode="Markdown")
            return

        target_id = int(args[1])
        update_user_field(target_id, {"is_banned": False})

        bot.reply_to(message, f"✅ ইউজার `{target_id}` কে **আনব্যান** করা হয়েছে।", parse_mode="Markdown")

        try:
            bot.send_message(target_id, "🎉 আপনার অ্যাকাউন্টটি আনব্যান করা হয়েছে!")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ ভুল ইনপুট! এরর: {e}")

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
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    if not check_user_channels(user_id):
        send_force_join_msg(message.chat.id)
    else:
        bot.send_message(
            message.chat.id,
            f"👋 **স্বাগতম, 👤 {first_name}!**\n\nআমাদের বটে কাজ করে আপনি সহজেই ইনকাম করতে পারবেন। নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# --- TEXT MESSAGE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    first_name = message.from_user.first_name

    balance, user = get_user(user_id, first_name)
    if user.get("is_banned", False):
        bot.send_message(message.chat.id, "🚫 আপনার অ্যাকাউন্টটি ব্যান করা হয়েছে!")
        return

    # Withdraw Number Step
    if user_id in user_withdraw_step:
        method = user_withdraw_step[user_id].get('method', 'bKash')
        del user_withdraw_step[user_id]

        if not is_valid_bd_number(text):
            bot.reply_to(
                message,
                "❌ **ভুল ইনপুট!**\n\nঅনুরোধ করে সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন (যেমন: 01712345678)।",
                parse_mode="Markdown"
            )
            return

        if balance < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই। মিনিমাম উইথড্র ${MIN_WITHDRAW:.2f} USDT।")
            return

        withdraw_amount = balance
        update_user_field(user_id, {"balance": 0.0})

        masked_acc = text[:3] + "*****" + text[-3:]

        msg = (
            f"**My Earning All Payment**\n"
            f"✅ **Withdrawal Paid**\n\n"
            f"💵 **{withdraw_amount:.3f} USDT**\n"
            f"🌐 **{method}**\n"
            f"👛 **{masked_acc}**"
        )

        bot.send_message(message.chat.id, f"✅ **আপনার উইথড্র রিকোয়েস্ট সফলভাবে প্রসেস হয়েছে!**\n\n💳 **পরিমাণ:** `${withdraw_amount:.4f} USDT`\n🔷 **মেথড:** {method}\n📱 **ডিটেইলস:** `{text}`\n\nধন্যবাদ!", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

        try:
            bot.send_message(PROOF_CHANNEL, msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error posting withdraw request: {e}")
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
            bot.send_message(
                message.chat.id,
                "❌ **আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!**\nআগামী ২৪ ঘণ্টা পর আবার নতুন কাজ করতে পারবেন।",
                reply_markup=main_menu_keyboard(),
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
            f"📌 **টাস্ক নিয়মাবলী (আজ দেখা হয়েছে: {daily_count}/30 - {provider}):**\n1. নিচের লিংকে ক্লিক করে কমপক্ষে **১৫ সেকেন্ড** অপেক্ষা করুন।\n2. ১৫ সেকেন্ড পর **Claim Reward** বাটনে চাপ দিন।",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif text == "🖥 Account":
        bot.send_message(
            message.chat.id,
            f"👤 **ইউজার:** {first_name}\n🆔 **আইডি:** `{user_id}`\n💰 **বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "✨ Referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        ref_count = user.get("referrals_count", 0)
        bot.send_message(
            message.chat.id,
            f"👥 **আপনার রেফারেল লিংক**\n\n"
            f"🔗 `{ref_link}`\n\n"
            f"📊 **মোট সফল রেফারেল:** `{ref_count}` জন\n"
            f"🎁 **রেফার কমিশন:** `${REFERRAL_BONUS:.3f} USDT`",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif text == "💸 Withdraw":
        if balance < MIN_WITHDRAW:
            msg = (
                f"💸 **উইথড্র ইনফরমেশন**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💳 **আপনার বর্তমান ব্যালেন্স:** `${balance:.4f} USDT`\n"
                f"📌 **সর্বনিম্ন উইথড্র:** `${MIN_WITHDRAW:.2f} USDT`\n\n"
                f"⚠️ **আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।**"
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
                f"💳 **পেমেন্ট মেথড সিলেক্ট করুন:**\n\nবর্তমান ব্যালেন্স: `${balance:.4f} USDT`\nমিনিমাম উইথড্র: `${MIN_WITHDRAW:.2f} USDT`",
                reply_markup=markup,
                parse_mode="Markdown"
            )

    elif text == "🛑 Rule's":
        rules = (
            "📌 **বট নিয়মাবলী:**\n\n"
            "১. প্রতিদিন সর্বোচ্চ ৩০টি অ্যাড দেখতে পারবেন।\n"
            "২. অ্যাড লিংকে অন্তত ১৫ সেকেন্ড অপেক্ষা করতে হবে।\n"
            "৩. ফেক রেফারেল করলে অ্যাকাউন্ট ব্যান করা হবে।\n"
            "৪. সর্বনিম্ন উইথড্র $২.০০ USDT।"
        )
        bot.send_message(message.chat.id, rules, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif text == "🔰 Whatsapp":
        msg = (
            "🌐 **ALL IN ONE** 🌐\n\n"
            "✅ **Whatsapp এডমিন লিংক:**\n"
            "https://wa.me/qr/TLGSBEYHL74LD1"
        )
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📩 Support":
        msg = (
            "🌐 **ALL IN ONE** 🌐\n\n"
            "🖇️ **আমাদের সাপোর্ট গ্রুপ লিংক:** https://t.me/allinoneg1\n\n"
            "✅ **টেলেগ্রাম এডমিন লিংক:** @akadmin02\n\n"
            "✅ **Whatsapp এডমিন লিংক:**\nhttps://wa.me/qr/TLGSBEYHL74LD1"
        )
        bot.send_message(message.chat.id, msg, reply_markup=main_menu_keyboard(), disable_web_page_preview=True)

    elif text == "📊 Status":
        total_users = users_col.count_documents({}) if users_col is not None else 0
        bot.send_message(
            message.chat.id,
            f"📊 **বট স্ট্যাটাস্টিকস:**\n\n👥 মোট সক্রিয় ইউজার: `{total_users}` জন",
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

    if call.data == "check_join":
        if check_user_channels(user_id):
            bot.send_message(call.message.chat.id, "✅ ধন্যবাদ! আপনি সব চ্যানেলে জয়েন আছেন।")
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
            bot.send_message(call.message.chat.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!")

    elif call.data == "claim_reward":
        if not user.get("can_claim", False):
            bot.send_message(
                call.message.chat.id, 
                "⚠️ **আপনি লিংকে প্রবেশ করেননি!**\nআগে **Visit Ad / Link** বাটনে ক্লিক করে অ্যাড দেখুন, তারপর এখানে চেষ্টা করুন।"
            )
            return

        current_time = time.time()
        last_task_time = user.get("last_task_time", 0)
        elapsed_time = current_time - last_task_time

        if elapsed_time < 15:
            remaining = int(15 - elapsed_time)
            bot.send_message(
                call.message.chat.id, 
                f"⏳ **১৫ সেকেন্ড পূর্ণ হয়নি!**\nঅনুগ্রহ করে আরো **{remaining} সেকেন্ড** এড পেজে সময় দিন এবং তারপর ক্লেম করুন।",
                parse_mode="Markdown"
            )
        else:
            daily_count = user.get("daily_count", 0)
            last_reset = user.get("last_reset", current_time)

            if current_time - last_reset >= 86400:
                daily_count = 0
                last_reset = current_time

            if daily_count >= 30:
                bot.send_message(call.message.chat.id, "❌ **আজকের কাজের সীমা (৩০/৩০) পূর্ণ হয়েছে!**")
                return

            add_balance(user_id, 0.001)
            update_user_field(user_id, {
                "daily_count": daily_count + 1, 
                "last_reset": last_reset, 
                "can_claim": False
            })

            updated_balance, _ = get_user(user_id, first_name)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass

            bot.send_message(
                call.message.chat.id,
                f"🎉 **রিওয়ার্ড সফলভাবে যোগ হয়েছে!**\n\n"
                f"💰 **প্রাপ্ত বোনাস:** `$0.0010 USDT`\n"
                f"💳 **বর্তমান ব্যালেন্স:** `${updated_balance:.4f} USDT`\n"
                f"📊 **আজকের টাস্ক:** `{daily_count + 1}/30`",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )

    elif call.data.startswith("with_"):
        method = call.data.split("_")[1]
        user_withdraw_step[user_id] = {'method': method}
        bot.send_message(
            call.message.chat.id,
            f"📝 আপনার {method} নম্বর বা এড্রেসটি লিখে মেসেজ পাঠান:"
        )

# --- AUTO POST ONLY BKASH & NAGAD (EVERY 20 SECONDS FOR FAST TESTING) ---
def auto_post_loop():
    prefixes = ["017", "018", "019", "016", "015", "013", "014"]
    methods = ["bKash", "Nagad"]
    
    # প্রথম পোস্ট সাথে সাথে দেওয়ার জন্য
    time.sleep(5)
    
    while True:
        try:
            amount = round(random.uniform(2.000, 10.000), 3)
            net = random.choice(methods)
            phone_num = random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(5)]) + "***"

            msg = (
                f"**My Earning All Payment**\n"
                f"✅ **Withdrawal Paid**\n\n"
                f"💵 **{amount:.3f} USDT**\n"
                f"🌐 **{net}**\n"
                f"👛 **{phone_num}**"
            )

            bot.send_message(PROOF_CHANNEL, msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Auto post error: {e}")
        
        time.sleep(20) # ২০ সেকেন্ড পর পর অটো পোস্ট হবে

# --- FLASK WEB SERVER ---
def keep_alive():
    @app.route('/')
    def home():
        return "Bot is running continuously!"

    def run():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive()

    # Clear old webhooks and pending updates to prevent Conflict 409
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"Webhook Removal Error: {e}")

    # Start auto posting thread
    t_auto = threading.Thread(target=auto_post_loop)
    t_auto.daemon = True
    t_auto.start()

    print("Bot is starting polling...")

    # Safe Polling Loop
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"Polling loop error: {e}")
            time.sleep(5)
